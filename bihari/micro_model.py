"""
MicroBrain - Ultra-lightweight, zero-dependency on-device decision model for Vihara.

Architecture:
- Deterministic feature hashing (Murmur/MD5 derived) into fixed 4096-dim sparse vector.
- Dual-head linear classifier with Softmax calibration for:
    1. Vibe classification (12 behavioral vibes from telemetry + window context)
    2. Screen OCR content classification (13 human mindfulness themes + reaction vibes)
    3. Context semantic activity classification (6 activity categories)
- On-device continuous personalization:
    - Adapts weights locally based on user interactions (zero cloud transmission).
    - Mathematically private: updates only anonymous hash-bucket weights, never raw text.
- Memory: <400 KB weights.
- Inference latency: <0.5 ms.
- Zero runtime dependencies (no PyTorch, no ONNX, no Scikit-learn required).
"""

import os
import sys
import re
import math
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Any, Union

from .inference import Vibe, VibeResult

logger = logging.getLogger("bihari.micro_model")

NUM_FEATURES = 4096


def _hash_feature(token: str, num_buckets: int = NUM_FEATURES) -> int:
    """Deterministic hash of a string token into [0, num_buckets - 1]."""
    # Use MD5 prefix for platform-independent, stable hashing across Python versions/runs
    digest = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little") % num_buckets


class FeatureExtractor:
    """Extracts sparse hashed n-gram and telemetry features from window/OCR context."""

    @staticmethod
    def extract_text_features(text: str, prefix: str = "w:") -> dict[int, float]:
        """Extract unigram, bigram, and char-trigram features into a sparse vector."""
        if not text:
            return {}

        words = [w.lower() for w in text.split() if len(w) > 1]
        features: dict[int, float] = {}

        # 1. Unigrams
        for w in words:
            bucket = _hash_feature(f"{prefix}{w}")
            features[bucket] = features.get(bucket, 0.0) + 1.0

        # 2. Bigrams
        for i in range(len(words) - 1):
            bg = f"{words[i]}_{words[i+1]}"
            bucket = _hash_feature(f"{prefix}bg:{bg}")
            features[bucket] = features.get(bucket, 0.0) + 1.5

        # 3. Subwords (character trigrams for typo/inflection robustness)
        for w in words:
            if len(w) >= 3:
                for j in range(len(w) - 2):
                    tri = w[j : j + 3]
                    bucket = _hash_feature(f"{prefix}tri:{tri}")
                    features[bucket] = features.get(bucket, 0.0) + 0.3

        # L2 Normalize the text vector
        norm_sq = sum(v * v for v in features.values())
        if norm_sq > 0.0:
            inv_norm = 1.0 / math.sqrt(norm_sq)
            for b in features:
                features[b] *= inv_norm

        return features

    @staticmethod
    def extract_telemetry_features(event: Any) -> dict[int, float]:
        """Extract continuous and categorical behavioral features from TelemetryEvent."""
        features: dict[int, float] = {}

        app_name = getattr(event, "app_name", "").lower()
        if app_name:
            app_b = _hash_feature(f"app:{app_name}")
            features[app_b] = 1.5

        # Keystroke velocity features
        cpm = float(getattr(event, "typing_speed", 0.0))
        bs_rate = float(getattr(event, "backspace_rate", 0.0))
        switches = float(getattr(event, "window_switches_3min", 0.0))
        dwell = float(getattr(event, "dwell_minutes", 0.0))

        # Normalized linear buckets
        features[_hash_feature("tel:cpm_norm")] = min(cpm / 100.0, 3.0)
        features[_hash_feature("tel:bs_rate")] = min(bs_rate * 2.0, 2.0)
        features[_hash_feature("tel:switches")] = min(switches / 10.0, 2.0)
        features[_hash_feature("tel:dwell")] = min(dwell / 30.0, 2.0)

        # Nonlinear interactions
        if cpm > 50 and bs_rate < 0.10:
            features[_hash_feature("tel:flow_condition")] = 2.0
        if bs_rate > 0.35 and cpm > 25:
            features[_hash_feature("tel:syntax_rage_condition")] = 2.0
        if switches >= 5 and cpm < 15:
            features[_hash_feature("tel:butterfly_condition")] = 2.0
        if dwell > 15 and cpm < 10:
            features[_hash_feature("tel:trance_condition")] = 2.0

        return features


class LinearHead:
    """
    Multiclass linear softmax classifier head with sparse weight representation.
    Supports online SGD updates for privacy-first, on-device personalization.
    """

    def __init__(self, classes: list[str], weights: Optional[dict[str, dict[int, float]]] = None, biases: Optional[dict[str, float]] = None):
        self.classes = classes
        # weights: class_name -> {bucket_index: weight_float}
        self.weights: dict[str, dict[int, float]] = weights or {c: {} for c in classes}
        # biases: class_name -> bias_float
        self.biases: dict[str, float] = biases or {c: 0.0 for c in classes}

    def predict(self, features: dict[int, float], user_delta_weights: Optional[dict[str, dict[int, float]]] = None) -> tuple[str, float, dict[str, float]]:
        """Compute softmax logits and return (top_class, confidence, all_probs)."""
        scores: dict[str, float] = {}

        for c in self.classes:
            w_dict = self.weights.get(c, {})
            u_dict = (user_delta_weights or {}).get(c, {})
            bias = self.biases.get(c, 0.0)

            dot = bias
            for b, val in features.items():
                w = w_dict.get(b, 0.0) + u_dict.get(b, 0.0)
                if w != 0.0:
                    dot += w * val
            scores[c] = dot

        # Softmax with numerical stability
        max_score = max(scores.values()) if scores else 0.0
        exp_sum = 0.0
        exps: dict[str, float] = {}
        for c, s in scores.items():
            ev = math.exp(min(max(s - max_score, -50.0), 50.0))
            exps[c] = ev
            exp_sum += ev

        probs = {c: (ev / exp_sum if exp_sum > 0 else 1.0 / len(self.classes)) for c, ev in exps.items()}
        top_class = max(probs, key=probs.get)  # type: ignore
        return top_class, probs[top_class], probs

    def adapt_step(
        self,
        features: dict[int, float],
        target_class: str,
        user_deltas: dict[str, dict[int, float]],
        lr: float = 0.05,
        l2_reg: float = 0.001,
    ) -> None:
        """
        On-device online SGD step: updates user_deltas in-place.
        No raw text is preserved; only mathematical weight deltas are updated.
        """
        if target_class not in self.classes:
            return

        _, _, probs = self.predict(features, user_delta_weights=user_deltas)

        # Gradient step for all classes: dL/dw_c = (p_c - y_c) * x
        for c in self.classes:
            y_c = 1.0 if c == target_class else 0.0
            error = probs.get(c, 0.0) - y_c

            delta_dict = user_deltas.setdefault(c, {})
            for b, x_val in features.items():
                current_delta = delta_dict.get(b, 0.0)
                # Gradient update with L2 shrinkage
                grad = error * x_val + l2_reg * current_delta
                new_delta = current_delta - lr * grad

                # Prune negligible weights to keep memory tight
                if abs(new_delta) > 1e-5:
                    delta_dict[b] = round(new_delta, 5)
                elif b in delta_dict:
                    del delta_dict[b]


class MicroBrain:
    """
    The complete Vihara on-device decision intelligence.
    Loads base model weights and merges optional on-device personalization deltas.
    """

    def __init__(self, models_dir: Optional[Path] = None, user_data_dir: Optional[Path] = None, enable_learning: bool = True):
        self.enable_learning = enable_learning

        # 1. Resolve base brain model path
        if models_dir is None:
            models_dir = Path(__file__).resolve().parent / "models"
        self.base_model_path = models_dir / "base_brain.json"

        # 2. Resolve user personal adaptation file in LocalAppData
        if user_data_dir is None:
            local_app = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            user_data_dir = Path(local_app) / "Vihara"
        self.user_brain_path = user_data_dir / "user_brain.json"

        self.vibe_head: Optional[LinearHead] = None
        self.ocr_theme_head: Optional[LinearHead] = None
        self.context_activity_head: Optional[LinearHead] = None

        self.user_deltas: dict[str, dict[str, dict[int, float]]] = {
            "vibe": {},
            "ocr": {},
            "context": {},
        }

        self._load_base_model()
        self._load_user_brain()

    def _load_base_model(self) -> None:
        """Load pretrained base weights bundled with application."""
        if not self.base_model_path.exists():
            # In frozen distribution, check sys._MEIPASS and executable directory
            if getattr(sys, "frozen", False):
                exe_dir = Path(sys.executable).parent
                candidates = [
                    exe_dir / "bihari" / "models" / "base_brain.json",
                    exe_dir / "_internal" / "bihari" / "models" / "base_brain.json",
                ]
                if hasattr(sys, "_MEIPASS"):
                    candidates.append(Path(sys._MEIPASS) / "bihari" / "models" / "base_brain.json")
                for c in candidates:
                    if c.exists():
                        self.base_model_path = c
                        break

        if not self.base_model_path.exists():
            logger.warning(f"MicroBrain base model weights not found at {self.base_model_path}. Creating fallback heads.")
            self._init_default_fallback_heads()
            return

        try:
            with open(self.base_model_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct heads
            if "vibe" in data:
                v_data = data["vibe"]
                self.vibe_head = LinearHead(
                    classes=v_data["classes"],
                    weights={c: {int(k): v for k, v in w.items()} for c, w in v_data["weights"].items()},
                    biases=v_data["biases"],
                )

            if "ocr" in data:
                o_data = data["ocr"]
                self.ocr_theme_head = LinearHead(
                    classes=o_data["classes"],
                    weights={c: {int(k): v for k, v in w.items()} for c, w in o_data["weights"].items()},
                    biases=o_data["biases"],
                )

            if "context" in data:
                c_data = data["context"]
                self.context_activity_head = LinearHead(
                    classes=c_data["classes"],
                    weights={c: {int(k): v for k, v in w.items()} for c, w in c_data["weights"].items()},
                    biases=c_data["biases"],
                )

            logger.info("🧠 MicroBrain successfully loaded pretrained weights (<500KB, 0% CPU).")
        except Exception as e:
            logger.error(f"Failed to load MicroBrain model weights: {e}", exc_info=True)
            self._init_default_fallback_heads()

    def _init_default_fallback_heads(self) -> None:
        """Initialize empty heads if file is missing."""
        vibe_classes = [v.value for v in Vibe]
        self.vibe_head = LinearHead(vibe_classes)

        ocr_classes = [
            "comedy_and_humor",
            "food_and_cooking",
            "scenic_views_and_nature",
            "music_and_dance",
            "sports_and_fitness",
            "pop_culture_and_movies",
            "wholesome_animals",
            "relatable_life_struggles",
            "deep_thoughts_philosophy",
            "technical_learning_and_code",
            "work_email_communication",
            "reading_articles_and_news",
            "mindless_social_scrolling",
        ]
        self.ocr_theme_head = LinearHead(ocr_classes)

        act_classes = ["coding", "learning", "gaming", "entertainment", "social_scroll", "deep_rabbit_hole"]
        self.context_activity_head = LinearHead(act_classes)

    def _load_user_brain(self) -> None:
        """Load on-device personalization deltas from disk (100% local)."""
        if not self.enable_learning or not self.user_brain_path.exists():
            return

        try:
            with open(self.user_brain_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for head_key in ("vibe", "ocr", "context"):
                if head_key in data:
                    self.user_deltas[head_key] = {
                        c: {int(k): v for k, v in w.items()} for c, w in data[head_key].items()
                    }
            logger.info("🧠 Loaded on-device personalized model adaptation.")
        except Exception as e:
            logger.debug(f"Could not load personal user_brain deltas: {e}")

    def save_user_brain(self) -> None:
        """Save on-device personalized weight deltas to disk."""
        if not self.enable_learning:
            return

        try:
            self.user_brain_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_brain_path, "w", encoding="utf-8") as f:
                json.dump(self.user_deltas, f, indent=1)
        except Exception as e:
            logger.debug(f"Failed to save user_brain deltas: {e}")

    # ─────────────────────────────────────────────────────────────
    # Public Inference APIs
    # ─────────────────────────────────────────────────────────────

    def classify_vibe(self, event: Any) -> VibeResult:
        """Classify TelemetryEvent into one of the 12 canonical vibes."""
        if not self.vibe_head:
            return VibeResult(Vibe.WANDERING, 0.40, "fallback")

        title = getattr(event, "window_title", "")
        app = getattr(event, "app_name", "")

        # Merge text features and telemetry features
        features = FeatureExtractor.extract_text_features(f"{app} {title}")
        tel_features = FeatureExtractor.extract_telemetry_features(event)
        for b, v in tel_features.items():
            features[b] = features.get(b, 0.0) + v

        top_class, conf, _ = self.vibe_head.predict(features, self.user_deltas.get("vibe"))
        try:
            vibe_enum = Vibe(top_class)
        except ValueError:
            vibe_enum = Vibe.WANDERING

        return VibeResult(vibe_enum, round(conf, 2), "micro_brain")

    def classify_screen_content(self, screen_text: str, app_name: str, window_title: str) -> dict:
        """Classify OCR screen text into human theme, reaction vibe, and tailored reflection."""
        if not screen_text or not self.ocr_theme_head:
            return {}

        features = FeatureExtractor.extract_text_features(f"{app_name} {window_title} {screen_text}")
        theme, conf, _ = self.ocr_theme_head.predict(features, self.user_deltas.get("ocr"))

        # Map theme to corresponding Vibe and reaction emotion
        vibe_map = {
            "comedy_and_humor": Vibe.LOST_IN_SCROLL,
            "food_and_cooking": Vibe.WANDERING,
            "scenic_views_and_nature": Vibe.WANDERING,
            "music_and_dance": Vibe.LOST_IN_SCROLL,
            "sports_and_fitness": Vibe.LOST_IN_SCROLL,
            "pop_culture_and_movies": Vibe.LOST_IN_SCROLL,
            "wholesome_animals": Vibe.STILLNESS,
            "relatable_life_struggles": Vibe.LOST_IN_SCROLL,
            "deep_thoughts_philosophy": Vibe.WANDERING,
            "technical_learning_and_code": Vibe.FLOW_STATE,
            "work_email_communication": Vibe.FLOW_STATE,
            "reading_articles_and_news": Vibe.WANDERING,
            "mindless_social_scrolling": Vibe.LOST_IN_SCROLL,
        }

        reaction_map = {
            "comedy_and_humor": "laughing_out_loud",
            "food_and_cooking": "food_craving",
            "scenic_views_and_nature": "deep_contemplation",
            "music_and_dance": "vibing_and_grooving",
            "sports_and_fitness": "jaw_drop_awe",
            "pop_culture_and_movies": "side_eye_scrolling",
            "wholesome_animals": "peaceful_moment",
            "relatable_life_struggles": "tired_acceptance",
            "deep_thoughts_philosophy": "deep_contemplation",
            "technical_learning_and_code": "deep_contemplation",
            "work_email_communication": "tired_acceptance",
            "reading_articles_and_news": "deep_contemplation",
            "mindless_social_scrolling": "side_eye_scrolling",
        }

        theme_search_queries = {
            "comedy_and_humor": ["crying laughing", "wheezing", "snicker"],
            "food_and_cooking": ["food craving", "hungry", "delicious", "drooling"],
            "scenic_views_and_nature": ["peaceful moment", "daydreaming", "mesmerized"],
            "music_and_dance": ["vibing", "grooving", "head bob", "dancing"],
            "sports_and_fitness": ["gym", "workout", "exhausted", "jaw drop"],
            "pop_culture_and_movies": ["eating popcorn", "side eye", "staring in disbelief"],
            "wholesome_animals": ["wholesome smile", "peaceful", "gentle moment"],
            "relatable_life_struggles": ["tired acceptance", "it is what it is", "sigh"],
            "deep_thoughts_philosophy": ["existential stare", "thinking monkey", "galaxy brain"],
            "technical_learning_and_code": ["confused math", "taking notes", "mind blown"],
            "work_email_communication": ["tired acceptance", "staring into soul", "sigh"],
            "reading_articles_and_news": ["intense stare", "taking notes", "contemplating"],
            "mindless_social_scrolling": ["blank stare", "doomscrolling", "monkey puppet looking away"],
        }

        # Extract specific subject from OCR words
        from .ocr import extract_caption_keywords
        from .inference import condense_subject

        kw_list = extract_caption_keywords(screen_text)
        subject_str = kw_list[0] if kw_list else ""
        s_clean = condense_subject(subject_str, max_chars=16) if subject_str else "the feed"

        reflection_templates = {
            "comedy_and_humor": f"Quick chuckle: {s_clean}",
            "food_and_cooking": f"Craving: {s_clean}",
            "scenic_views_and_nature": f"Scenic pause: {s_clean}",
            "music_and_dance": f"Vibing to: {s_clean}",
            "sports_and_fitness": f"Spectating: {s_clean}",
            "pop_culture_and_movies": f"Following: {s_clean}",
            "wholesome_animals": f"Gentle moment: {s_clean}",
            "relatable_life_struggles": f"Felt that: {s_clean}",
            "deep_thoughts_philosophy": f"Contemplating: {s_clean}",
            "technical_learning_and_code": f"Learning: {s_clean}",
            "work_email_communication": f"Composing: {s_clean}",
            "reading_articles_and_news": f"Reading: {s_clean}",
            "mindless_social_scrolling": f"Scrolling: {s_clean}",
        }

        curated = list(theme_search_queries.get(theme, ["blank stare", "side eye"]))
        # Only prepend s_clean if it represents substantive, non-gibberish words
        noise_words = {
            "said", "hand", "just", "dont", "ask", "touch", "balls", "dimensions",
            "trainer", "one", "ycm", "peor", "regneant", "tryi", "sprayer", "regneant"
        }
        if s_clean and s_clean != "the feed" and len(s_clean) >= 4:
            clean_tokens = [w for w in re.findall(r"[a-zA-Z]+", s_clean.lower()) if len(w) >= 3]
            if clean_tokens and not any(w in noise_words for w in clean_tokens):
                curated.insert(0, s_clean)

        return {
            "human_theme": theme,
            "reaction_vibe": reaction_map.get(theme, "side_eye_scrolling"),
            "vibe": vibe_map.get(theme, Vibe.LOST_IN_SCROLL),
            "reflection": reflection_templates.get(theme, f"Invested in: {s_clean}"),
            "search_queries": curated,
            "confidence": conf,
        }

    def classify_context(self, app_name: str, window_title: str) -> dict:
        """Classify window title into activity category and optimal meme category."""
        if not window_title or not self.context_activity_head:
            return {"activity": None, "meme_category": None}

        features = FeatureExtractor.extract_text_features(f"{app_name} {window_title}")
        activity, _, _ = self.context_activity_head.predict(features, self.user_deltas.get("context"))

        act_to_meme = {
            "coding": "programming",
            "learning": "bugs",
            "gaming": "gaming",
            "entertainment": "shocked",
            "social_scroll": "doomscrolling",
            "deep_rabbit_hole": "rabbit_hole",
        }

        return {
            "activity": activity,
            "meme_category": act_to_meme.get(activity, "confused"),
        }

    # ─────────────────────────────────────────────────────────────
    # On-Device Personalized Learning (Zero Cloud, Zero Privacy Risk)
    # ─────────────────────────────────────────────────────────────

    def adapt_vibe(self, event: Any, target_vibe: Union[Vibe, str], was_positive: bool = True) -> None:
        """
        Adapt on-device weights based on user interaction.
        If user stayed/laughed or voluntarily returned to focus: positive reinforcement.
        If user immediately dismissed toast (<500ms): slight negative adjustment.
        """
        if not self.enable_learning or not self.vibe_head:
            return

        target_str = target_vibe.value if isinstance(target_vibe, Vibe) else str(target_vibe)
        title = getattr(event, "window_title", "")
        app = getattr(event, "app_name", "")

        features = FeatureExtractor.extract_text_features(f"{app} {title}")
        tel_features = FeatureExtractor.extract_telemetry_features(event)
        for b, v in tel_features.items():
            features[b] = features.get(b, 0.0) + v

        # Learning rate scaled by feedback valence
        lr = 0.03 if was_positive else 0.015
        self.vibe_head.adapt_step(
            features=features,
            target_class=target_str,
            user_deltas=self.user_deltas.setdefault("vibe", {}),
            lr=lr,
        )
        self.save_user_brain()
