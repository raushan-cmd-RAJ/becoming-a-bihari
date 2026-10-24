"""
ONNX Semantic Decision Intelligence (Option B).

Lightweight (~23MB INT8 quantized), high-accuracy semantic classification using
all-MiniLM-L6-v2 running locally via onnxruntime.

Combines transformer semantic embeddings with physical telemetry signals (typing velocity,
backspace ratio, context switching, dwell time) to match and exceed System 1 / Laya accuracy.
"""

from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Check if onnxruntime is available
try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    ort = None
    HAS_ORT = False

# Check if tokenizers library is available (optional; pure-python fallback provided)
try:
    from tokenizers import Tokenizer
    HAS_TOKENIZERS = True
except ImportError:
    Tokenizer = None
    HAS_TOKENIZERS = False

# Import numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

from .inference import (
    Vibe,
    VibeResult,
    WORK_APPS,
    BROWSER_APPS,
    COMMS_APPS,
    MEDIA_APPS,
    UTILITY_APPS,
    HELP_SEEKING_KEYWORDS,
    ALL_SOCIAL_VIDEO_KEYWORDS,
    MINDFUL_THEME_REFLECTIONS,
)


class SimpleWordPieceTokenizer:
    """
    Zero-dependency, pure-Python WordPiece tokenizer for BERT / MiniLM vocabularies.
    Guarantees Option B works even if the Rust 'tokenizers' wheel is not installed.
    """

    def __init__(self, vocab_file: Path):
        self.vocab: Dict[str, int] = {}
        with open(vocab_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                self.vocab[line.strip()] = i
        self.unk_id = self.vocab.get("[UNK]", 100)
        self.cls_id = self.vocab.get("[CLS]", 101)
        self.sep_id = self.vocab.get("[SEP]", 102)
        self.pad_id = self.vocab.get("[PAD]", 0)

    def encode(self, text: str, max_len: int = 128) -> Tuple[List[int], List[int]]:
        tokens = [self.cls_id]
        words = re.findall(r"\w+|[^\w\s]", text.lower(), re.UNICODE)
        for word in words:
            if word in self.vocab:
                tokens.append(self.vocab[word])
                continue
            is_bad = False
            start = 0
            sub_tokens = []
            while start < len(word):
                end = len(word)
                cur_substr = None
                while start < end:
                    sub = word[start:end]
                    if start > 0:
                        sub = "##" + sub
                    if sub in self.vocab:
                        cur_substr = sub
                        break
                    end -= 1
                if cur_substr is None:
                    is_bad = True
                    break
                sub_tokens.append(self.vocab[cur_substr])
                start = end
            if is_bad:
                tokens.append(self.unk_id)
            else:
                tokens.extend(sub_tokens)

        tokens.append(self.sep_id)
        if len(tokens) > max_len:
            tokens = tokens[: max_len - 1] + [self.sep_id]
        mask = [1] * len(tokens)
        pad_len = max_len - len(tokens)
        tokens.extend([self.pad_id] * pad_len)
        mask.extend([0] * pad_len)
        return tokens, mask


class ONNXBrain:
    """
    On-device Semantic Decision Intelligence powered by quantized MiniLM ONNX.
    Runs in ~5-15ms on CPU, using <25MB RAM and 0 cloud calls.
    """

    def __init__(self, model_dir: Optional[Path] = None, enable_learning: bool = True):
        self.enable_learning = enable_learning
        if model_dir is None:
            self.model_dir = Path(__file__).resolve().parent / "models"
        else:
            self.model_dir = Path(model_dir)

        self.model_path = self.model_dir / "semantic_brain.onnx"
        self.tokenizer_json = self.model_dir / "tokenizer.json"
        self.vocab_path = self.model_dir / "vocab.txt"
        self.anchors_path = self.model_dir / "vibe_anchors.json"

        self._available = False
        self._session = None
        self._fast_tokenizer = None
        self._simple_tokenizer = None
        self._anchor_matrix: Optional[np.ndarray] = None
        self._vibe_names: List[str] = []
        self._user_biases: Dict[str, float] = {}

        if not (HAS_ORT and HAS_NUMPY):
            logger.debug("ONNXBrain: onnxruntime or numpy not installed.")
            return

        if not self.model_path.exists() or not self.anchors_path.exists():
            logger.debug(f"ONNXBrain: model files not found at {self.model_dir}")
            return

        try:
            self._load_tokenizer()
            self._load_anchors()
            self._load_user_biases()
            self._available = True
            logger.info("🧠 ONNXBrain initialized successfully (Option B: MiniLM semantic transformer).")
        except Exception as e:
            logger.warning(f"ONNXBrain initialization failed: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def _load_tokenizer(self):
        if HAS_TOKENIZERS and self.tokenizer_json.exists():
            try:
                self._fast_tokenizer = Tokenizer.from_file(str(self.tokenizer_json))
                return
            except Exception as e:
                logger.debug(f"Fast tokenizer load failed, falling back to SimpleWordPiece: {e}")

        if self.vocab_path.exists():
            self._simple_tokenizer = SimpleWordPieceTokenizer(self.vocab_path)
        else:
            raise FileNotFoundError("Neither tokenizer.json nor vocab.txt found for ONNXBrain.")

    def _load_anchors(self):
        with open(self.anchors_path, "r", encoding="utf-8") as f:
            anchors_dict: Dict[str, List[float]] = json.load(f)

        self._vibe_names = list(anchors_dict.keys())
        self._anchor_matrix = np.array([anchors_dict[k] for k in self._vibe_names], dtype=np.float32)

    def _get_session(self):
        if self._session is None:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                str(self.model_path),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
        return self._session

    def embed(self, text: str) -> Optional[np.ndarray]:
        """Generate a 384-dimensional normalized semantic embedding for text."""
        if not self._available:
            return None

        try:
            sess = self._get_session()
            if self._fast_tokenizer:
                enc = self._fast_tokenizer.encode(text)
                ids = np.array([enc.ids], dtype=np.int64)
                mask = np.array([enc.attention_mask], dtype=np.int64)
            else:
                token_ids, attn_mask = self._simple_tokenizer.encode(text)
                ids = np.array([token_ids], dtype=np.int64)
                mask = np.array([attn_mask], dtype=np.int64)

            ttypes = np.zeros_like(ids)
            outputs = sess.run(
                None,
                {
                    "input_ids": ids,
                    "attention_mask": mask,
                    "token_type_ids": ttypes,
                },
            )
            token_embeddings = outputs[0]  # shape (1, seq_len, 384)

            # Mean pooling with attention mask
            mask_expanded = np.broadcast_to(np.expand_dims(mask, -1), token_embeddings.shape).astype(float)
            sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
            sum_mask = np.clip(mask_expanded.sum(axis=1), 1e-9, None)
            embedding = (sum_embeddings / sum_mask)[0]

            # L2 normalization
            norm = np.linalg.norm(embedding)
            if norm > 1e-9:
                embedding = embedding / norm
            return embedding
        except Exception as e:
            logger.warning(f"ONNX embedding error: {e}")
            return None

    def classify_vibe(self, event) -> VibeResult:
        """
        Multimodal classification fusing transformer semantic context with real-time physical telemetry.
        """
        if not self._available:
            return VibeResult(Vibe.WANDERING, 0.40, "onnx_unavailable")

        app = getattr(event, "app_name", "").lower()
        title = getattr(event, "window_title", "")
        speed = float(getattr(event, "typing_speed", 0.0) or 0.0)
        bs_rate = float(getattr(event, "backspace_rate", 0.0) or 0.0)
        switches = int(getattr(event, "window_switches_3min", 0) or 0)
        dwell_min = float(getattr(event, "dwell_minutes", 0.0) or 0.0)
        session_min = float(getattr(event, "session_minutes", 0.0) or 0.0)
        idle_sec = float(getattr(event, "idle_seconds", 0.0) or 0.0)
        hour = int(getattr(event, "hour_of_day", 12) or 12)

        # 1. Semantic Embedding & Cosine Similarities
        ctx_text = f"{app} - {title}"
        vec = self.embed(ctx_text)
        if vec is None:
            return VibeResult(Vibe.WANDERING, 0.40, "onnx_fallback")

        similarities = np.dot(self._anchor_matrix, vec)  # shape (12,)
        logits = similarities * 4.0

        v_map = {name: i for i, name in enumerate(self._vibe_names)}

        # 2. Telemetry and Domain Knowledge Fusion
        is_terminal = any(t in app for t in ["powershell", "cmd", "terminal", "wt.exe", "bash", "wsl", "alacritty", "wezterm", "kitty"])
        is_ide = any(e in app for e in ["code", "cursor", "devenv", "pycharm", "idea", "sublime", "nvim", "vim", "zed", "studio"])
        is_work_app = is_terminal or is_ide or (app in WORK_APPS)

        if is_work_app:
            if speed > 20 and bs_rate < 0.12:
                logits[v_map["FLOW_STATE"]] += 2.5
            elif speed > 10 and bs_rate < 0.08:
                logits[v_map["FLOW_STATE"]] += 1.8

            if speed > 15 and bs_rate > 0.30:
                logits[v_map["SYNTAX_RAGE"]] += 2.8
            elif speed > 15 and 0.18 < bs_rate <= 0.30:
                logits[v_map["MOUNTING_FRICTION"]] += 2.0

            if dwell_min > 45.0:
                logits[v_map["GRINDING"]] += 1.6
            if session_min > 180 and speed < 15 and speed > 0:
                logits[v_map["BURNOUT_APPROACHING"]] += 2.2

            # Work apps strongly penalize distraction vibes
            logits[v_map["LOST_IN_SCROLL"]] -= 4.0
            if speed > 15:
                logits[v_map["WANDERING"]] -= 2.0

        # Browser Contexts
        if app in BROWSER_APPS:
            title_lower = title.lower()
            if any(kw in title_lower for kw in HELP_SEEKING_KEYWORDS):
                logits[v_map["HELP_SEEKING"]] += 2.6
            if any(kw in title_lower for kw in ALL_SOCIAL_VIDEO_KEYWORDS):
                logits[v_map["LOST_IN_SCROLL"]] += 2.8
                logits[v_map["FLOW_STATE"]] -= 3.0
            if switches > 8:
                logits[v_map["TAB_BUTTERFLY"]] += 2.2

        # Media Apps
        if app in MEDIA_APPS:
            logits[v_map["LOST_IN_SCROLL"]] += 2.5
            logits[v_map["FLOW_STATE"]] -= 3.0

        # Physical Inactivity / Stillness
        if idle_sec > 45 or (speed == 0 and dwell_min < 1.0 and switches == 0):
            logits[v_map["STILLNESS"]] += 2.5

        # Circadian Drift
        if 13 <= hour <= 15 and 0 < speed < 15 and switches < 3:
            logits[v_map["AFTERNOON_DRIFT"]] += 1.3

        # Apply continuous personalization bias
        for v_name, bias in self._user_biases.items():
            if v_name in v_map:
                logits[v_map[v_name]] += bias

        # 3. Softmax & Final Confidence
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        best_idx = int(np.argmax(probs))
        best_vibe_name = self._vibe_names[best_idx]
        conf = float(probs[best_idx])

        # Clamp confidence to [0.40, 0.98]
        conf = max(0.40, min(0.98, conf))

        try:
            vibe_enum = Vibe[best_vibe_name]
        except KeyError:
            vibe_enum = Vibe(best_vibe_name)

        return VibeResult(vibe_enum, round(conf, 3), "onnx_brain")

    def classify_screen_content(self, screen_text: str, app_name: str, window_title: str) -> dict:
        """
        Classify on-screen OCR content into mindfulness theme, reaction, and reflection.
        """
        if not self._available or not screen_text:
            return {}

        text_sample = screen_text[:300].strip()
        if len(text_sample) < 15:
            return {}

        THEME_PROTOTYPES = {
            "comedy_and_humor": "funny hilarious joke comedy laugh humor prank video",
            "food_and_cooking": "recipe food delicious cooking dinner chef meal bakery",
            "scenic_views_and_nature": "nature landscape mountains ocean travel outdoors sunset hiking",
            "music_and_dance": "music song concert dancing groove audio beats headphones",
            "sports_and_fitness": "sports gym workout exercise fitness match highlights running athletic",
            "pop_culture_and_movies": "celebrity movies film show hollywood drama entertainment actor",
            "wholesome_animals": "cute puppy kitten cat dog adorable pets wholesome animal",
            "relatable_life_struggles": "exhausted tired life struggle overwhelmed adulting stressed Monday",
            "deep_thoughts_philosophy": "philosophy deep thoughts meaning reflection contemplation meditation wisdom",
            "technical_learning_and_code": "programming code python tutorial documentation software engineering algorithm",
            "work_email_communication": "email schedule calendar meeting slack zoom outlook message conversation",
            "reading_articles_and_news": "news article journalism essay report analysis current events",
            "mindless_social_scrolling": "infinite feed scrolling comments likes upvotes reels tiktok memes",
        }

        THEME_VIBE_MAP = {
            "comedy_and_humor": (Vibe.LOST_IN_SCROLL, "laughing_out_loud"),
            "food_and_cooking": (Vibe.WANDERING, "food_craving"),
            "scenic_views_and_nature": (Vibe.WANDERING, "peaceful_moment"),
            "music_and_dance": (Vibe.LOST_IN_SCROLL, "vibing_and_grooving"),
            "sports_and_fitness": (Vibe.LOST_IN_SCROLL, "jaw_drop_awe"),
            "pop_culture_and_movies": (Vibe.LOST_IN_SCROLL, "side_eye_scrolling"),
            "wholesome_animals": (Vibe.STILLNESS, "peaceful_moment"),
            "relatable_life_struggles": (Vibe.BURNOUT_APPROACHING, "tired_acceptance"),
            "deep_thoughts_philosophy": (Vibe.WANDERING, "deep_contemplation"),
            "technical_learning_and_code": (Vibe.FLOW_STATE, "deep_contemplation"),
            "work_email_communication": (Vibe.FLOW_STATE, "deep_contemplation"),
            "reading_articles_and_news": (Vibe.WANDERING, "deep_contemplation"),
            "mindless_social_scrolling": (Vibe.LOST_IN_SCROLL, "side_eye_scrolling"),
        }

        # Embed screen text and match against theme prototypes
        text_vec = self.embed(text_sample)
        if text_vec is None:
            return {}

        best_theme = "mindless_social_scrolling"
        best_score = -1.0

        for theme, proto in THEME_PROTOTYPES.items():
            proto_vec = self.embed(proto)
            if proto_vec is not None:
                score = float(np.dot(text_vec, proto_vec))
                if score > best_score:
                    best_score = score
                    best_theme = theme

        mapped_vibe, reaction = THEME_VIBE_MAP.get(best_theme, (Vibe.LOST_IN_SCROLL, "side_eye_scrolling"))

        # Contextual guardrail: viewing technical/code content while on a social feed is exploratory wandering, not flow state
        is_social = any(s in app_name.lower() or s in window_title.lower() for s in ["instagram", "tiktok", "reels", "shorts", "twitter", "x.com", "reddit", "facebook"])
        if is_social and mapped_vibe in (Vibe.FLOW_STATE, Vibe.GRINDING):
            mapped_vibe = Vibe.WANDERING

        import random
        reflections = MINDFUL_THEME_REFLECTIONS.get(best_theme, ["Present with screen time."])
        reflection = random.choice(reflections)

        reaction_pools = {
            "laughing_out_loud": ["laughing", "cracking up", "spit take"],
            "food_craving": ["craving food", "hungry looking", "snack mode"],
            "peaceful_moment": ["peaceful cat", "chilling dog", "zen moment"],
            "vibing_and_grooving": ["cat vibing", "grooving", "head bob"],
            "jaw_drop_awe": ["jaw dropped", "blown away", "staring in awe"],
            "side_eye_scrolling": ["side eye", "blank stare", "caught staring"],
            "tired_acceptance": ["facepalm", "tired dog", "exhausted"],
            "deep_contemplation": ["thinking monkey", "galaxy brain", "contemplating"],
        }
        search_query = random.choice(reaction_pools.get(reaction, ["side eye"]))

        return {
            "human_theme": best_theme,
            "reaction_vibe": reaction,
            "meme_subject": best_theme.replace("_", " "),
            "search_queries": [search_query],
            "vibe": mapped_vibe,
            "reflection": reflection,
            "screen_text": screen_text,
        }

    def _load_user_biases(self):
        user_dir = Path.home() / ".vihara"
        biases_file = user_dir / "onnx_user_weights.json"
        if biases_file.exists():
            try:
                with open(biases_file, "r", encoding="utf-8") as f:
                    self._user_biases = json.load(f)
            except Exception:
                self._user_biases = {}

    def adapt_vibe(self, event, target_vibe: Any, was_positive: bool = True) -> None:
        """Continuous on-device personal adaptation (100% private, zero cloud)."""
        if not self.enable_learning or not self._available:
            return

        target_name = target_vibe.name if hasattr(target_vibe, "name") else str(target_vibe)
        delta = 0.15 if was_positive else -0.15
        self._user_biases[target_name] = round(self._user_biases.get(target_name, 0.0) + delta, 3)

        try:
            user_dir = Path.home() / ".vihara"
            user_dir.mkdir(parents=True, exist_ok=True)
            with open(user_dir / "onnx_user_weights.json", "w", encoding="utf-8") as f:
                json.dump(self._user_biases, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not persist user biases: {e}")
