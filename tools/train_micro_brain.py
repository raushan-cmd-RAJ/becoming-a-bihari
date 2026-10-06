"""
Distillation and Training Pipeline for Vihara's MicroBrain.

Generates a calibrated synthetic desktop telemetry and OCR dataset (~7,000 examples),
trains the multi-head sparse linear classifier via multi-class logistic regression (Softmax loss),
and exports the compact weights directly to bihari/models/base_brain.json (<400 KB).
"""

import sys
import json
import math
import random
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bihari.micro_model import FeatureExtractor, NUM_FEATURES
from bihari.inference import Vibe


# ─────────────────────────────────────────────────────────────
# 1. Synthetic Dataset Generators
# ─────────────────────────────────────────────────────────────

def generate_vibe_training_data() -> list[dict]:
    """Generate realistic (app, title, cpm, bs_rate, switches, dwell, label) examples."""
    data = []

    # Helper to add variations
    def add(vibe: Vibe, apps, titles, cpm_range, bs_range, switch_range, dwell_range, count=60):
        for _ in range(count):
            app = random.choice(apps)
            title = random.choice(titles)
            cpm = random.uniform(*cpm_range)
            bs = random.uniform(*bs_range)
            switches = random.randint(*switch_range)
            dwell = random.uniform(*dwell_range)
            data.append({
                "app": app,
                "title": title,
                "cpm": cpm,
                "backspace_rate": bs,
                "window_switches_3min": switches,
                "dwell_minutes": dwell,
                "label": vibe.value,
            })

    # FLOW_STATE
    add(
        Vibe.FLOW_STATE,
        ["code.exe", "devenv.exe", "pycharm64.exe", "alacritty.exe", "wezterm-gui.exe", "nvim.exe"],
        [
            "engine.rs - Vihara - Visual Studio Code",
            "auth_handler.py - backend-api - PyCharm",
            "feature/telemetry - micro_brain.py - VS Code",
            "src/components/Header.tsx - frontend",
            "main.go - distributed-kv-store",
            "server.cpp - high-frequency-trading",
            "document.tex - NeurIPS Paper - TeXstudio",
        ],
        cpm_range=(55, 95),
        bs_range=(0.01, 0.07),
        switch_range=(0, 2),
        dwell_range=(10.0, 45.0),
        count=100,
    )

    # SYNTAX_RAGE
    add(
        Vibe.SYNTAX_RAGE,
        ["code.exe", "windowsterminal.exe", "powershell.exe", "cmd.exe", "pycharm64.exe"],
        [
            "TypeError: Cannot read properties of undefined (reading 'map') - Terminal",
            "SyntaxError: invalid syntax (line 42) - Visual Studio Code",
            "CMake Error at CMakeLists.txt: missing target library",
            "cargo build --release - failed with 14 errors",
            "IndexError: list index out of range - debug console",
            "git merge conflict in src/database/connection.py",
            "FAILED tests/test_auth.py::test_jwt_expiration",
        ],
        cpm_range=(25, 70),
        bs_range=(0.35, 0.75),
        switch_range=(1, 5),
        dwell_range=(4.0, 25.0),
        count=100,
    )

    # HELP_SEEKING
    add(
        Vibe.HELP_SEEKING,
        ["chrome.exe", "edge.exe", "firefox.exe", "brave.exe"],
        [
            "python - how to handle async generator in fastapi - Stack Overflow",
            "TypeError: fetch failed cause: connect ECONNREFUSED - Stack Overflow",
            "Documentation - PyTorch 2.5 - torch.compile guide",
            "Rust standard library docs - std::sync::Arc",
            "ChatGPT - Why is my useEffect running twice in development?",
            "Claude - Debugging Windows Media OCR access violation in C++",
            "GitHub Issues - #1423 Build fails on Windows 11 24H2",
        ],
        cpm_range=(5, 30),
        bs_range=(0.05, 0.15),
        switch_range=(3, 8),
        dwell_range=(2.0, 10.0),
        count=90,
    )

    # MOUNTING_FRICTION
    add(
        Vibe.MOUNTING_FRICTION,
        ["code.exe", "chrome.exe", "slack.exe", "windowsterminal.exe"],
        [
            "Jira - Bug PROD-881: User session abruptly terminating",
            "Sentry Issue: 500 Internal Server Error in /api/v1/checkout",
            "Postman - POST https://api.prod.company.internal/token (504 Gateway Timeout)",
            "Datadog Dashboard - CPU Spike on Worker Pods",
            "Docker Desktop - Container exited with code 137 (OOMKilled)",
        ],
        cpm_range=(15, 45),
        bs_range=(0.18, 0.32),
        switch_range=(6, 14),
        dwell_range=(1.0, 8.0),
        count=80,
    )

    # LOST_IN_SCROLL
    add(
        Vibe.LOST_IN_SCROLL,
        ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"],
        [
            "YouTube - 45 Minutes of Satisfying Woodworking Restoration",
            "Reddit - r/AskReddit: What is a creepy mystery that was actually solved?",
            "Instagram Reels • Cooking viral crispy pork belly #food #chef",
            "Twitter / X - Trending Tech Drama and Founder Meltdowns",
            "TikTok - POV: Trying to leave the office at 5 PM on a Friday",
            "Twitch - Shroud playing Valorant ranked matches",
            "Netflix - The Great British Baking Show - Episode 4",
        ],
        cpm_range=(0, 8),
        bs_range=(0.0, 0.05),
        switch_range=(0, 3),
        dwell_range=(15.0, 75.0),
        count=110,
    )

    # WANDERING
    add(
        Vibe.WANDERING,
        ["chrome.exe", "edge.exe", "brave.exe"],
        [
            "Bronze Age Collapse - Wikipedia, the free encyclopedia",
            "Hacker News - Show HN: A minimalist markdown notes app in Zig",
            "Substack - Why Modern Architecture Looks So Depressing",
            "The Verge - Best wireless mechanical keyboards of 2026",
            "Zillow - Luxury mountain chalets in Swiss Alps with scenic views",
            "Wikipedia - List of unusual deaths throughout history",
        ],
        cpm_range=(2, 18),
        bs_range=(0.02, 0.12),
        switch_range=(2, 6),
        dwell_range=(8.0, 35.0),
        count=90,
    )

    # TAB_BUTTERFLY
    add(
        Vibe.TAB_BUTTERFLY,
        ["chrome.exe", "msedge.exe", "firefox.exe"],
        [
            "Amazon.com: Ergonomic Office Chair & Mechanical Keyboards",
            "Hacker News (New Comments)",
            "Twitter / Notifications (14 unread)",
            "YouTube Subscriptions Feed",
            "Gmail - Inbox (3)",
            "Google Calendar - October 2026",
        ],
        cpm_range=(5, 25),
        bs_range=(0.05, 0.18),
        switch_range=(10, 24),
        dwell_range=(0.2, 1.8),
        count=90,
    )

    # GRINDING
    add(
        Vibe.GRINDING,
        ["excel.exe", "code.exe", "devenv.exe", "figma.exe", "blender.exe"],
        [
            "Q3_Financial_Projections_Final_v4.xlsx - Excel",
            "Design System V3 - Components & Tokens - Figma",
            "Blender 4.2 - sci_fi_mech_rig_highpoly.blend",
            "DataCleaning_Pipeline_batch_processing.py",
            "Refactoring Legacy Auth Controller (Line 1420/2800)",
        ],
        cpm_range=(35, 60),
        bs_range=(0.06, 0.14),
        switch_range=(1, 4),
        dwell_range=(55.0, 180.0),
        count=80,
    )

    # BURNOUT_APPROACHING
    add(
        Vibe.BURNOUT_APPROACHING,
        ["code.exe", "slack.exe", "chrome.exe"],
        [
            "VS Code - late night marathon session (02:45 AM)",
            "Slack - #general: 'Anyone still up to check this deployment?'",
            "Staring at cursor blinking for 4 minutes",
            "Fatigue sets in - typing slows down",
        ],
        cpm_range=(12, 28),
        bs_range=(0.14, 0.28),
        switch_range=(2, 6),
        dwell_range=(90.0, 240.0),
        count=75,
    )

    # STILLNESS
    add(
        Vibe.STILLNESS,
        ["explorer.exe", "lockapp.exe", "idle"],
        [
            "Desktop - Empty Workspace",
            "Windows Lock Screen",
            "Screensaver Active",
            "Away From Keyboard (No input for 10 minutes)",
        ],
        cpm_range=(0, 0),
        bs_range=(0.0, 0.0),
        switch_range=(0, 0),
        dwell_range=(15.0, 60.0),
        count=60,
    )

    # MEETING_RECOVERY
    add(
        Vibe.MEETING_RECOVERY,
        ["teams.exe", "zoom.exe", "slack.exe", "chrome.exe"],
        [
            "Microsoft Teams - Call Ended (Duration: 1h 14m)",
            "Zoom Meeting - Meeting Ended by Host",
            "Post-Call Catchup & Sighing",
            "Google Meet - You have left the call",
        ],
        cpm_range=(2, 12),
        bs_range=(0.0, 0.06),
        switch_range=(1, 3),
        dwell_range=(1.0, 6.0),
        count=70,
    )

    # AFTERNOON_DRIFT
    add(
        Vibe.AFTERNOON_DRIFT,
        ["chrome.exe", "edge.exe", "spotify.exe"],
        [
            "2:30 PM slump - Low Energy Beats & Lo-fi Hip Hop - Spotify",
            "Reading random travel blogs about Japan in autumn",
            "Checking local coffee shop reviews",
            "Mid-afternoon drowsiness and staring at wallpaper",
        ],
        cpm_range=(5, 18),
        bs_range=(0.04, 0.12),
        switch_range=(2, 5),
        dwell_range=(10.0, 30.0),
        count=70,
    )

    return data


def generate_ocr_training_data() -> list[dict]:
    """Generate realistic OCR reel/video caption snippets across 13 human themes."""
    themes_and_samples = {
        "comedy_and_humor": [
            "when your code works on the first try but you don't know why #codingmemes #devhumor #relatable",
            "POV: asking your cat why it knocked over the water glass at 3am #catfunny #catmemes #humor",
            "my honest reaction when the meeting could have been a single email #officehumor #corporate #comedy",
            "pranking my roommate with invisible tape on the door #prank #comedy #hilarious #funnyvideos",
            "tell me why this is literally every group project ever #studentmemes #relatable #funny",
        ],
        "food_and_cooking": [
            "crispy creamy garlic parmesan chicken pasta recipe #foodie #cooking #recipe #easyrecipes #chef",
            "authentic sourdough bread scoring and oven spring in a dutch oven #baking #sourdough #bread",
            "street food tour in Osaka Japan: Wagyu beef skewers and Takoyaki #streetfood #japan #foodporn",
            "how to make restaurant quality chocolate lava cake in 20 minutes #dessert #baking #sweet",
            "slow smoked brisket after 14 hours with perfect smoke ring and bark #bbq #brisket #meat",
        ],
        "scenic_views_and_nature": [
            "sunrise hike at Hooker Valley Track overlooking Mount Cook New Zealand #nature #hiking #travel",
            "drone footage of misty pine forests in the Swiss Alps #alps #cinematic #mountains #peaceful",
            "bioluminescent waves glowing bright blue at night in California #ocean #nature #photography",
            "autumn foliage changing colors in Kyoto temple gardens #kyoto #autumn #scenic #zen",
            "standing above the clouds at high altitude mountain pass #landscape #wanderlust #earth",
        ],
        "music_and_dance": [
            "acoustic guitar fingerstyle cover of Bohemian Rhapsody #guitar #fingerstyle #music #musician",
            "lofi hip hop beats to relax and code to • rainy night study session #lofi #chill #beatmaker",
            "hip hop dance choreography routine to trending song #dance #choreography #dancer #groove",
            "behind the scenes producing a drum and bass track in Ableton Live #producer #beats #edm",
            "live piano improvisation during quiet midnight coffee session #piano #relaxing #instrumental",
        ],
        "sports_and_fitness": [
            "full body calisthenics workout: muscle up progression and form tips #fitness #calisthenics #gym",
            "insane bicycle kick goal in Champions League stoppage time #football #soccer #goals #sports",
            "deadlift PR 220kg with perfect spinal alignment #powerlifting #strength #workout #gains",
            "extreme downhill mountain biking run through rocky forest trail #downhill #mtb #adrenaline",
            "NBA top 10 plays of the night: buzzer beaters and poster dunks #basketball #nba #highlights",
        ],
        "pop_culture_and_movies": [
            "official trailer breakdown: hidden easter eggs in new Marvel Avengers film #movies #marvel #cinema",
            "celebrity red carpet fashion recap from Met Gala 2026 #fashion #redcarpet #celebrity #hollywood",
            "behind the scenes practical effects on Christopher Nolan movie set #cinema #filmmaking #director",
            "ranking every single Studio Ghibli animated film from worst to best #anime #ghibli #filmreview",
            "actor explains how they prepared for villain role in Oscar drama #interview #hollywood #actors",
        ],
        "wholesome_animals": [
            "baby golden retriever puppy takes its first clumsy steps in the grass #puppy #dog #cute #wholesome",
            "capybara peacefully chilling in a warm hot spring bath with citrus fruits #capybara #zen #animals",
            "rescued shelter cat purring loudly after finding its forever home #catrescue #adopted #sweet",
            "baby otter learning how to float on back holding tiny seashell #otter #wildlife #cuteanimals",
            "german shepherd gently babysitting newborn baby ducklings #dogs #animals #heartwarming",
        ],
        "relatable_life_struggles": [
            "realizing that being an adult is just picking what to eat every single day until you expire #adulting",
            "looking at your bank account after grocery shopping for three items #inflation #struggle #real",
            "having 35 browser tabs open and forgetting what you originally sat down to do #adhd #brainrot",
            "when Sunday evening dread hits because tomorrow is Monday morning #corporatelife #burnout",
            "trying to explain your remote tech job to your grandparents at thanksgiving #techlife #relatable",
        ],
        "deep_thoughts_philosophy": [
            "The Bronze Age Collapse: Why three ancient civilizations disappeared in 50 years #history #archaeology",
            "Marcus Aurelius and Stoic resilience: Focus only on what is within your control #stoicism #philosophy",
            "The Fermi Paradox: If intelligent life is probable, where is everybody? #cosmos #astronomy #science",
            "Carl Sagan's Pale Blue Dot: A reminder of our place in the cosmic ocean #astronomy #perspective",
            "Why the Roman Empire built concrete that lasted 2000 years under seawater #engineering #history",
        ],
        "technical_learning_and_code": [
            "Building a transformer neural network from scratch in 100 lines of Python #machinelearning #ai #python",
            "Understanding Rust memory safety, ownership, and borrowing rules in 5 minutes #rustlang #coding",
            "How database indexing with B-Trees actually works under the hood #computerscience #software #sql",
            "Solving LeetCode Hard: Trapping Rain Water with two pointer technique #algorithms #interview #code",
            "Linux kernel architecture: What actually happens during a system call #linux #kernel #sysadmin",
        ],
        "work_email_communication": [
            "Per my last email, please find attached the revised quarterly budget spreadsheet #corporatelife #email",
            "Drafting executive presentation deck for tomorrow's board of directors meeting #management #work",
            "Slack thread: Aligning on Q4 platform reliability roadmap deliverables #slack #remote #tech",
            "Reviewing legal terms of service contract before signature #compliance #business #corporate",
            "Candidate interview feedback and hiring committee debrief notes #recruiting #humanresources",
        ],
        "reading_articles_and_news": [
            "The New Yorker: The disappearing art of deep reading in an age of notification frenzy #longform",
            "Reuters Business Report: Global semiconductor supply chain shifts and chip manufacturing",
            "Scientific American: How human memory consolidation works during deep REM sleep cycles",
            "Nature Biotechnology: Breakthrough CRISPR gene therapy trial results published",
            "Bloomberg Technology: Venture capital trends in AI infrastructure and edge computing",
        ],
        "mindless_social_scrolling": [
            "Swipe up for more reels • suggested for you • explore trending videos #explore #reels #scroll",
            "Endless feed of random viral clips with subway surfers gameplay underneath #brainrot #satisfying",
            "Watching soap cutting and kinetic sand ASMR videos for 40 minutes straight #asmr #satisfying",
            "Rapid scrolling through 30 second reaction clips with laugh tracks #infinite #scrolling",
            "Algorithm recommending the 12th consecutive video about hydraulic press crushing objects",
        ],
    }

    data = []
    for theme, samples in themes_and_samples.items():
        # Repeat samples with random modifications to create 120+ per theme
        for _ in range(12):
            for s in samples:
                # Add random punctuation, casing, or hashtags
                variations = [
                    s,
                    s.lower(),
                    f"Watch till end: {s}",
                    f"{s} #viral #trend",
                    s.replace("#", ""),
                ]
                data.append({
                    "text": random.choice(variations),
                    "app": random.choice(["chrome.exe", "msedge.exe", "brave.exe", "instagram"]),
                    "title": "Reel / Feed Video",
                    "label": theme,
                })
    return data


def generate_context_activity_data() -> list[dict]:
    """Generate (app, title, activity_class) training examples."""
    activity_map = {
        "coding": [
            ("code.exe", "auth.py - Visual Studio Code"),
            ("nvim.exe", "server.rs (Neovim)"),
            ("windowsterminal.exe", "powershell - cargo test"),
            ("pycharm64.exe", "models.py - Django Project"),
        ],
        "learning": [
            ("chrome.exe", "FastAPI Tutorial - Official Documentation"),
            ("edge.exe", "CS50 Lecture 4 - Memory & Pointers"),
            ("brave.exe", "Stack Overflow - How to mock database in pytest"),
            ("firefox.exe", "MDN Web Docs - Array.prototype.reduce"),
        ],
        "gaming": [
            ("steam.exe", "Steam - Library"),
            ("valorant.exe", "VALORANT (64-bit, DX11)"),
            ("minecraft.exe", "Minecraft 1.21.1 - Singleplayer"),
            ("discord.exe", "Discord - #gaming-voice"),
        ],
        "entertainment": [
            ("chrome.exe", "Netflix - Stranger Things Season 5"),
            ("edge.exe", "Disney+ - The Mandalorian"),
            ("vlc.exe", "Dune.Part.Two.2024.1080p.mkv - VLC media player"),
            ("spotify.exe", "Spotify Free - Discover Weekly"),
        ],
        "social_scroll": [
            ("chrome.exe", "Instagram (Reels)"),
            ("brave.exe", "TikTok - Make Your Day"),
            ("edge.exe", "Twitter / X (Trending in India)"),
            ("firefox.exe", "Reddit - Dive into anything"),
        ],
        "deep_rabbit_hole": [
            ("chrome.exe", "Antikythera mechanism - Wikipedia"),
            ("brave.exe", "Voynich manuscript - High Resolution Scans"),
            ("edge.exe", "Hacker News - The History of Lisp Machines"),
            ("firefox.exe", "Wait But Why - The AI Revolution"),
        ],
    }

    data = []
    for act, samples in activity_map.items():
        for _ in range(40):
            for app, title in samples:
                data.append({"app": app, "title": title, "label": act})
    return data


# ─────────────────────────────────────────────────────────────
# 2. Linear Multinomial Logistic Trainer (Pure Python/Math)
# ─────────────────────────────────────────────────────────────

class SparseLogisticTrainer:
    """Trains a multiclass linear model using SGD with L2 regularization."""

    def __init__(self, classes: list[str], num_features: int = NUM_FEATURES):
        self.classes = classes
        self.class_to_idx = {c: i for i, c in enumerate(classes)}
        self.K = len(classes)
        self.D = num_features

        # Sparse weight dict: class_idx -> {feature_idx: weight}
        self.weights: list[dict[int, float]] = [{} for _ in range(self.K)]
        self.biases: list[float] = [0.0] * self.K

    def train(self, dataset: list[tuple[dict[int, float], str]], epochs: int = 15, lr: float = 0.08, l2: float = 1e-4):
        """Train weights on (sparse_feature_dict, label) instances."""
        N = len(dataset)
        print(f"  Training on {N} instances over {self.K} classes ({epochs} epochs)...")

        for epoch in range(epochs):
            random.shuffle(dataset)
            correct = 0
            decay_lr = lr / (1.0 + 0.05 * epoch)

            for feat, label in dataset:
                target_idx = self.class_to_idx[label]

                # Compute logits: z_k = bias_k + sum(w_kj * x_j)
                logits = [self.biases[k] for k in range(self.K)]
                for k in range(self.K):
                    w_k = self.weights[k]
                    for b, val in feat.items():
                        logits[k] += w_k.get(b, 0.0) * val

                # Softmax
                max_l = max(logits)
                exps = [math.exp(min(max(l - max_l, -40.0), 40.0)) for l in logits]
                sum_exp = sum(exps)
                probs = [e / sum_exp for e in exps]

                pred_idx = max(range(self.K), key=lambda k: probs[k])
                if pred_idx == target_idx:
                    correct += 1

                # Gradient descent step: dL/dz_k = p_k - y_k
                for k in range(self.K):
                    grad_k = probs[k] - (1.0 if k == target_idx else 0.0)
                    self.biases[k] -= decay_lr * grad_k

                    w_k = self.weights[k]
                    for b, val in feat.items():
                        old_w = w_k.get(b, 0.0)
                        new_w = old_w - decay_lr * (grad_k * val + l2 * old_w)
                        if abs(new_w) > 1e-5:
                            w_k[b] = new_w
                        elif b in w_k:
                            del w_k[b]

            acc = correct / N * 100.0
            if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
                print(f"    Epoch {epoch + 1:02d}/{epochs}: Train Accuracy = {acc:.2f}%")

    def export_dict(self) -> dict:
        """Export weights into a compact JSON-serializable dictionary."""
        out_weights = {}
        out_biases = {}

        for k, c in enumerate(self.classes):
            # Round weights to 4 decimal places for compact disk footprint
            out_weights[c] = {str(b): round(w, 4) for b, w in self.weights[k].items() if abs(w) > 1e-4}
            out_biases[c] = round(self.biases[k], 4)

        return {
            "classes": self.classes,
            "weights": out_weights,
            "biases": out_biases,
        }


# ─────────────────────────────────────────────────────────────
# 3. Main Build & Export Orchestrator
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  [Vihara] MicroBrain Distillation & Training Pipeline")
    print("=" * 60)

    # 1. Train Vibe Head (12 Canonical Vibes)
    print("\n[1/3] Generating & Training Behavioral Vibe Head...")
    vibe_raw = generate_vibe_training_data()
    vibe_classes = [v.value for v in Vibe]
    vibe_dataset = []

    for item in vibe_raw:
        # Construct synthetic telemetry event mock
        class MockEvent:
            pass
        ev = MockEvent()
        ev.app_name = item["app"]
        ev.window_title = item["title"]
        ev.typing_speed = item["cpm"]
        ev.backspace_rate = item["backspace_rate"]
        ev.window_switches_3min = item["window_switches_3min"]
        ev.dwell_minutes = item["dwell_minutes"]

        f = FeatureExtractor.extract_text_features(f"{item['app']} {item['title']}")
        tel = FeatureExtractor.extract_telemetry_features(ev)
        for b, v in tel.items():
            f[b] = f.get(b, 0.0) + v
        vibe_dataset.append((f, item["label"]))

    vibe_trainer = SparseLogisticTrainer(vibe_classes)
    vibe_trainer.train(vibe_dataset, epochs=15, lr=0.08)

    # 2. Train OCR Theme Head (13 Human Themes)
    print("\n[2/3] Generating & Training Screen OCR Theme Head...")
    ocr_raw = generate_ocr_training_data()
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
    ocr_dataset = []
    for item in ocr_raw:
        f = FeatureExtractor.extract_text_features(f"{item['app']} {item['title']} {item['text']}")
        ocr_dataset.append((f, item["label"]))

    ocr_trainer = SparseLogisticTrainer(ocr_classes)
    ocr_trainer.train(ocr_dataset, epochs=15, lr=0.08)

    # 3. Train Context Activity Head (6 Categories)
    print("\n[3/3] Generating & Training Context Activity Head...")
    ctx_raw = generate_context_activity_data()
    ctx_classes = ["coding", "learning", "gaming", "entertainment", "social_scroll", "deep_rabbit_hole"]
    ctx_dataset = []
    for item in ctx_raw:
        f = FeatureExtractor.extract_text_features(f"{item['app']} {item['title']}")
        ctx_dataset.append((f, item["label"]))

    ctx_trainer = SparseLogisticTrainer(ctx_classes)
    ctx_trainer.train(ctx_dataset, epochs=15, lr=0.08)

    # 4. Export Combined Model Brain
    models_dir = PROJECT_ROOT / "bihari" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    out_file = models_dir / "base_brain.json"

    model_payload = {
        "version": "1.0.0",
        "num_features": NUM_FEATURES,
        "vibe": vibe_trainer.export_dict(),
        "ocr": ocr_trainer.export_dict(),
        "context": ctx_trainer.export_dict(),
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(model_payload, f, separators=(",", ":"))

    file_size_kb = out_file.stat().st_size / 1024
    print("\n" + "=" * 60)
    print(f"  [OK] Training Complete! Model exported to: {out_file}")
    print(f"     Total Disk Footprint: {file_size_kb:.1f} KB")
    print(f"     Runtime Dependencies: ZERO (Pure Python + Math)")
    print("=" * 60)


if __name__ == "__main__":
    main()
