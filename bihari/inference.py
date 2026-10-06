"""
Module 2: THE INFERENCE BRIDGE — Hybrid vibe classifier.

Architecture:
  1. Rule Engine (primary): Instant, zero-cost deterministic classifier.
     Uses app context, typing metrics, window title keywords, time-of-day,
     and session duration to classify into one of 12 vibes.
  2. Laya Router (secondary): 421M non-autoregressive decision model.
     Only loaded when rules are ambiguous. Returns calibrated probabilities.

Philosophy:
  The tool is a mirror, not a judge. Vibes are internal labels for accurate
  detection. What the user sees is a first-person reflection phrase — never
  a verdict or a command. The humor creates a tiny gap between the user and
  their current state, and that gap is mindfulness.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
import os
import re
import random
import logging
import warnings

# Suppress upstream Laya checkpoint temperature calibration RuntimeWarning
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*laya: this checkpoint ships invalid temperatures.*")

logger = logging.getLogger(__name__)


def _get_micro_brain():
    try:
        from .micro_model import MicroBrain
        return MicroBrain
    except Exception:
        return None


# ──────────────────────────────────────────────
# The 12 Vibes — 4 categories × 3 states
# ──────────────────────────────────────────────

class Vibe(str, Enum):
    """
    12 emotional/behavioral states organized into 4 categories.

    These labels are internal only — the user never sees them.
    What the user sees are first-person reflection phrases.
    """
    # ── Intensity: How hard you're pushing ──
    FLOW_STATE = "FLOW_STATE"
    GRINDING = "GRINDING"
    BURNOUT_APPROACHING = "BURNOUT_APPROACHING"

    # ── Frustration: How much you're struggling ──
    SYNTAX_RAGE = "SYNTAX_RAGE"
    HELP_SEEKING = "HELP_SEEKING"
    MOUNTING_FRICTION = "MOUNTING_FRICTION"

    # ── Avoidance: How much you're dodging ──
    WANDERING = "WANDERING"
    LOST_IN_SCROLL = "LOST_IN_SCROLL"
    TAB_BUTTERFLY = "TAB_BUTTERFLY"

    # ── Downtime: Breaks and transitions ──
    STILLNESS = "STILLNESS"
    MEETING_RECOVERY = "MEETING_RECOVERY"
    AFTERNOON_DRIFT = "AFTERNOON_DRIFT"


# ──────────────────────────────────────────────
# Vibe → Human-readable folder name mapping
# ──────────────────────────────────────────────

VIBE_FOLDER_NAMES: dict[Vibe, str] = {
    Vibe.FLOW_STATE: "in-the-zone",
    Vibe.GRINDING: "the-long-grind",
    Vibe.BURNOUT_APPROACHING: "running-on-fumes",
    Vibe.SYNTAX_RAGE: "fighting-the-code",
    Vibe.HELP_SEEKING: "asking-the-internet",
    Vibe.MOUNTING_FRICTION: "mounting-friction",
    Vibe.WANDERING: "just-wandering",
    Vibe.LOST_IN_SCROLL: "lost-in-the-scroll",
    Vibe.TAB_BUTTERFLY: "tab-butterfly",
    Vibe.STILLNESS: "the-great-pause",
    Vibe.MEETING_RECOVERY: "post-meeting-recovery",
    Vibe.AFTERNOON_DRIFT: "afternoon-drift",
}


# ──────────────────────────────────────────────
# Dual-Track Reflection Architecture
#
# Track A (Becoming a Bihari): Irreverent, witty roast reflections.
# Track B (Vihara): Dignified, stoic mindfulness reflections.
# ──────────────────────────────────────────────

REFLECTIONS_TRACK_A: dict[Vibe, list[str]] = {
    Vibe.FLOW_STATE: [
        "you and the code are one right now",
        "the zone. you're in it.",
        "fingers moving, thoughts flowing",
        "this is the good part",
        "you didn't blink for a while there",
        "when the code just writes itself",
    ],
    Vibe.GRINDING: [
        "pounding keys. the code is crying.",
        "still here. still going.",
        "hour after hour, line after line",
        "quiet persistence. won't quit.",
        "between stubborn and devoted",
        "this is the part no one sees",
        "you and the grind understand each other",
    ],
    Vibe.BURNOUT_APPROACHING: [
        "typing cadence like dial-up modem.",
        "you've been at this for a while",
        "the screen is still here. so are you.",
        "maybe the code needs a break too",
        "future you would appreciate water",
        "even machines need to cool down",
        "there is a world outside this window",
    ],
    Vibe.SYNTAX_RAGE: [
        "the compiler isn't attacking you",
        "you and compiler having a moment",
        "that backspace key is working hard",
        "rewriting the same line... again",
        "always the semicolons. always.",
        "a rubber duck is worried about you",
        "delete, retype — the daily ritual",
    ],
    Vibe.HELP_SEEKING: [
        "Stack Overflow tab 14. 2013 code.",
        "asking the internet for answers",
        "copy-paste engineering art form",
        "reading another dev's solution",
        "pilgrimage to Stack Overflow",
        "when docs don't have what you need",
        "googling is a skill. you have it.",
    ],
    Vibe.MOUNTING_FRICTION: [
        "30 window switches in 60s. file 1.",
        "everything is completely fine.",
        "code is testing your patience",
        "wrestling with this for a bit",
        "it's that kind of day",
        "the bug isn't personal at all.",
        "the keyboard did nothing wrong",
    ],
    Vibe.WANDERING: [
        "dentist appointment to papal conclave",
        "just... looking around",
        "scenic detour entered",
        "reorganizing the mental space",
        "not lost. just scenic route.",
        "exploring all adjacent spaces",
        "future you will find this funny",
    ],
    Vibe.LOST_IN_SCROLL: [
        "absorbed in the endless stream.",
        "time dissolved in the stream.",
        "the scroll has you now",
        "came for one thing. wasn't this.",
        "infinite feed thanks your attention",
        "simply witnessing the feed.",
        "down the rabbit hole comfortably",
    ],
    Vibe.TAB_BUTTERFLY: [
        "47 open tabs. a universe of ideas.",
        "tab tab tab — none the right one",
        "visiting windows like a diplomat",
        "can't decide where to be? same.",
        "browser has 47 tabs. you need 48.",
        "window shopping, but for windows",
        "alt-tab: unplanned cardio",
    ],
    Vibe.STILLNESS: [
        "staring at wallpaper. epiphany?",
        "the screen waits. so do you.",
        "a pause. nothing wrong with that.",
        "sometimes best code is no code",
        "away. being a human for a moment.",
        "the keyboard rests. it deserves it.",
        "gone. doing something real, probably.",
    ],
    Vibe.MEETING_RECOVERY: [
        "that meeting could have been an email",
        "survived another meeting",
        "that could've been an email",
        "re-entering reality after 45m nod",
        "meeting is over. recovery begins.",
        "back from conference call dimension",
        "now... where were you before?",
    ],
    Vibe.AFTERNOON_DRIFT: [
        "2:30 PM post-lunch food coma.",
        "post-lunch autopilot engaged",
        "afternoon slump asks no permission",
        "2 PM hits different after lunch",
        "thinking half speed, fully okay",
        "the screen is blurry or eyes are",
        "lunch was worth it though",
    ],
}

# Track B: Vihara Dignified Mindfulness Reflections (per dual_track_branding_guide.md §6)
REFLECTIONS_TRACK_B: dict[Vibe, list[str]] = {
    Vibe.FLOW_STATE: [
        "deep work flow. cognitive symmetry.",
        "focused awareness in optimal resonance.",
        "sustained flow state protected.",
        "absorbed in productive clarity.",
    ],
    Vibe.GRINDING: [
        "sustained effort observed.",
        "honoring the sustained effort.",
        "deep focus in this moment.",
        "steady dedication present.",
    ],
    Vibe.BURNOUT_APPROACHING: [
        "fatigue signature recognized.",
        "cognitive energy resting naturally.",
        "mental stillness arriving.",
        "natural pause in the stream.",
    ],
    Vibe.SYNTAX_RAGE: [
        "syntax friction in awareness.",
        "complexity rising in the space.",
        "calm witness to compiler errors.",
        "syntax challenge acknowledged.",
        "compiler friction calmly noted.",
    ],
    Vibe.HELP_SEEKING: [
        "clarity seeking clarity.",
        "curiosity in search of answers.",
        "clarity of intent precedes answer.",
        "seeking insight with discernment.",
    ],
    Vibe.MOUNTING_FRICTION: [
        "attentional turbulence passing.",
        "awareness with the complexity.",
        "friction witnessed with calm.",
    ],
    Vibe.WANDERING: [
        "attentional drift observed.",
        "observing the meandering thought.",
        "gentle awareness of the drift.",
    ],
    Vibe.LOST_IN_SCROLL: [
        "passive browsing. pure awareness.",
        "noticing the endless stream.",
        "awareness resting on the stream.",
        "a gentle pause. simply observing.",
    ],
    Vibe.TAB_BUTTERFLY: [
        "cognitive motion across tabs.",
        "attention across many spaces.",
        "observing the shifting context.",
        "spacious awareness across windows.",
    ],
    Vibe.STILLNESS: [
        "quiet contemplation observed.",
        "quiet contemplation and space.",
        "thoughts settling naturally.",
        "a mindful pause in digital flow.",
    ],
    Vibe.MEETING_RECOVERY: [
        "post-meeting recovery phase.",
        "faculties decompressing gently.",
        "quiet decompression underway.",
        "re-centering after collaboration.",
    ],
    Vibe.AFTERNOON_DRIFT: [
        "circadian afternoon rhythm.",
        "afternoon dip recognized.",
        "natural biological rhythm here.",
        "body and mind resting gently.",
    ],
}

# Backward compatibility alias
REFLECTIONS: dict[Vibe, list[str]] = REFLECTIONS_TRACK_A


# ──────────────────────────────────────────────
# Contextual Reflection Templates
#
# Formatted with the active subject (file, video, query, doc, command).
# ──────────────────────────────────────────────

CONTEXTUAL_TEMPLATES_TRACK_A: dict[Vibe, list[str]] = {
    Vibe.FLOW_STATE: [
        "locked into '{subject}'",
        "flowing in '{subject}'",
        "in the zone: {subject}",
        "locked on: {subject}",
    ],
    Vibe.GRINDING: [
        "still on '{subject}'",
        "hours on '{subject}'",
        "devoted to '{subject}'",
        "locked into {subject}",
    ],
    Vibe.BURNOUT_APPROACHING: [
        "{subject} can wait",
        "resting with '{subject}'",
        "pause on '{subject}'",
        "space around '{subject}'",
    ],
    Vibe.SYNTAX_RAGE: [
        "glaring at '{subject}'",
        "rewriting '{subject}'",
        "you vs '{subject}'",
        "{subject}: round 5",
        "battling '{subject}'",
    ],
    Vibe.HELP_SEEKING: [
        "googling '{subject}'",
        "researching '{subject}'",
        "seeking fix: {subject}",
        "docs for '{subject}'",
    ],
    Vibe.MOUNTING_FRICTION: [
        "wrestling '{subject}'",
        "{subject} resisting",
        "friction in {subject}",
        "patience on {subject}",
    ],
    Vibe.WANDERING: [
        "detour into '{subject}'",
        "wandering in '{subject}'",
        "detour: {subject}",
    ],
    Vibe.LOST_IN_SCROLL: [
        "watching: {subject}",
        "lost in '{subject}'",
        "rabbit hole: {subject}",
        "hooked on: {subject}",
    ],
    Vibe.TAB_BUTTERFLY: [
        "tab hop: '{subject}'",
        "fluttering: {subject}",
        "briefly on: {subject}",
    ],
    Vibe.STILLNESS: [
        "resting on '{subject}'",
        "paused on '{subject}'",
    ],
    Vibe.MEETING_RECOVERY: [
        "back to '{subject}'",
        "recovering: {subject}",
        "post-meeting: {subject}",
    ],
    Vibe.AFTERNOON_DRIFT: [
        "drifting on '{subject}'",
        "staring at '{subject}'",
        "autopilot on {subject}",
    ],
}

CONTEXTUAL_TEMPLATES_TRACK_B: dict[Vibe, list[str]] = {
    Vibe.FLOW_STATE: [
        "focused on '{subject}'",
        "advancing on '{subject}'",
        "clarity on '{subject}'",
    ],
    Vibe.GRINDING: [
        "steady focus: {subject}",
        "progress on '{subject}'",
        "steady on '{subject}'",
    ],
    Vibe.BURNOUT_APPROACHING: [
        "stillness with '{subject}'",
        "witnessing: {subject}",
        "quiet space: {subject}",
    ],
    Vibe.SYNTAX_RAGE: [
        "debugging '{subject}'",
        "inspecting: {subject}",
        "calm debugging: {subject}",
        "{subject}: error noted",
    ],
    Vibe.HELP_SEEKING: [
        "researching '{subject}'",
        "clarity on '{subject}'",
        "docs on '{subject}'",
    ],
    Vibe.MOUNTING_FRICTION: [
        "friction in '{subject}'",
        "centering on '{subject}'",
        "focus on: {subject}",
    ],
    Vibe.WANDERING: [
        "noticing drift: {subject}",
        "detour to: {subject}",
        "evaluating: {subject}",
    ],
    Vibe.LOST_IN_SCROLL: [
        "observing: {subject}",
        "mindful of: {subject}",
        "mindful pause: {subject}",
    ],
    Vibe.TAB_BUTTERFLY: [
        "shifting to: {subject}",
        "visit to: {subject}",
        "context: {subject}",
    ],
    Vibe.STILLNESS: [
        "pause with '{subject}'",
        "stillness on '{subject}'",
    ],
    Vibe.MEETING_RECOVERY: [
        "decompress: {subject}",
        "center after '{subject}'",
    ],
    Vibe.AFTERNOON_DRIFT: [
        "drift in: {subject}",
        "gentle drift: {subject}",
        "gentle gaze: {subject}",
    ],
}

CONTEXTUAL_TEMPLATES: dict[Vibe, list[str]] = CONTEXTUAL_TEMPLATES_TRACK_A


def condense_subject(subject: str, max_chars: int = 16) -> str:
    """Condense long video or window titles into a short, punchy 2-4 word subject <= max_chars."""
    if not subject:
        return ""
    s = re.sub(r"['\"]", "", subject).strip()
    if ":" in s:
        parts = [p.strip() for p in s.split(":") if p.strip()]
        s = parts[1] if len(parts) > 1 and len(parts[1]) >= 4 else parts[0]
    elif " - " in s:
        parts = [p.strip() for p in s.split(" - ") if p.strip()]
        s = parts[0]

    words = s.split()
    if len(words) > 4:
        s = " ".join(words[:4])
        s = re.sub(r"\s+(?:on|with|and|in|at|of|to|for|from|by|about|the|a|an)$", "", s, flags=re.IGNORECASE)

    if len(s) > max_chars:
        trimmed = s[:max_chars].rsplit(" ", 1)[0].strip()
        s = trimmed if trimmed else s[:max_chars].strip()
    return s.strip()


# Track A Video & Short Reflections
SHORT_VIDEO_REFLECTIONS = [
    "Invested in: {subject}",
    "Deep in: {subject}",
    "Hooked on: {subject}",
    "Studying: {subject}",
    "Down the rabbit hole: {subject}",
    "Essential research: {subject}",
    "Watching: {subject}",
]

SHORT_PUNCHY_REFLECTIONS = [
    "Essential research, obviously.",
    "Priorities: 10/10.",
    "Down the rabbit hole.",
    "🪞 Present with this moment.",
    "Observing what is right here.",
    "Just 5 more minutes...",
    "Awareness resting on the screen.",
    "Very important life research.",
    "Deep in the flow right now.",
    "Deep in the trance.",
    "Brain: 'We need to know this.'",
    "Completely locked in.",
]

SHORT_SOCIAL_REFLECTIONS = [
    "🪞 Resting in the feed right now.",
    "Just one more reel, right?",
    "Scrolling on pure autopilot.",
    "Witnessing the endless stream.",
    "Down the feed rabbit hole.",
    "Present with the stream.",
    "Priorities: 10/10.",
    "A moment of pure presence.",
]

# Track B Video & Short Reflections (Vihara Dignified Mindfulness)
SHORT_VIDEO_REFLECTIONS_TRACK_B = [
    "Observing: {subject}",
    "Contemplating: {subject}",
    "Mindful pause: {subject}",
    "Attentive presence: {subject}",
    "Viewing: {subject}",
]

SHORT_PUNCHY_REFLECTIONS_TRACK_B = [
    "A mindful pause in your day.",
    "Present in this exact moment.",
    "Awareness of where attention rests.",
    "Present in the living now.",
    "The drift witnessed without judgment.",
    "Natural rhythm in motion.",
    "Clarity precedes action.",
    "Grounded in the present moment.",
]

SHORT_SOCIAL_REFLECTIONS_TRACK_B = [
    "Passive browsing loop identified.",
    "Peaceful awareness in the stream.",
    "Pure presence in this moment.",
    "Gentle awareness in the stream.",
    "The pull of the feed witnessed.",
    "A quiet breath amidst the stream.",
]

SHORT_SOCIAL_CONTEXTUAL = [
    "Scrolling: {subject}",
    "Feed trance: {subject}",
    "Reels hook: {subject}",
    "Lost in: {subject}",
]

SHORT_SOCIAL_CONTEXTUAL_TRACK_B = [
    "Observing feed: {subject}",
    "Feed loop: {subject}",
    "Mindful pause: {subject}",
    "Noticing: {subject}",
]


def format_dwell_reflection(
    dwell_minutes: float,
    subject: Optional[str] = None,
    vibe: Optional[Vibe] = None,
) -> str:
    """
    Format a concise, lighthearted, non-prescriptive dwell-aware reflection (< 40 chars).
    Mirrors continuous dwell time with warmth, humor, and pure present awareness.
    """
    try:
        m = max(1, int(round(float(dwell_minutes))))
    except (ValueError, TypeError, OverflowError):
        m = 1
    if subject:
        sub_med = condense_subject(subject, max_chars=14)
        sub_compact = condense_subject(subject, max_chars=8)
        if sub_med and len(sub_med) >= 2:
            candidates = [
                f"🪞 {m} minutes with: {sub_compact}. Present.",
                f"🪞 {m}m with: {sub_med}. Present.",
                f"🪞 {m}m deep in: {sub_med}",
                f"🪞 Lost in time: {sub_med}",
                f"🪞 Present with {sub_med}.",
            ]
            valid = [c for c in candidates if len(c) < 40]
            if valid:
                return random.choice(valid)

    if vibe in (Vibe.FLOW_STATE, Vibe.GRINDING):
        candidates = [
            f"🪞 {m} minutes deep in the code.",
            f"🪞 {m}m deep in the flow.",
            f"🪞 {m} minutes present here.",
        ]
    elif vibe in (Vibe.STILLNESS, Vibe.AFTERNOON_DRIFT):
        candidates = [
            f"🪞 {m} minutes of stillness.",
            f"🪞 {m}m in quiet contemplation.",
            "🪞 A moment of still presence.",
        ]
    elif vibe in (Vibe.LOST_IN_SCROLL, Vibe.WANDERING):
        candidates = [
            f"🪞 {m}m observing the stream.",
            "🪞 Lost in time, simply present.",
            f"🪞 {m} minutes present here.",
        ]
    else:
        candidates = [
            f"🪞 {m} minutes present here.",
            f"🪞 {m}m in this moment.",
            "🪞 Lost in time, simply present.",
        ]

    chosen = random.choice(candidates)
    if len(chosen) >= 40:
        chosen = chosen[:36].rstrip() + "..."
    return chosen


def get_reflection(
    vibe: Vibe,
    context=None,
    brand_track: str = "vihara",
    dwell_minutes: Optional[float] = None,
) -> str:
    """
    Get a short, punchy, non-judgmental reflection phrase for the active moment.
    Keeps reflections under 35-40 characters so they are instant to read
    and fit comfortably on a single line.

    Supports dual-track brand architecture:
      - 'vihara' (Track B): Stoic, dignified mindfulness copy.
      - 'bihari' (Track A): Witty, roast, gentle humor copy.

    Supports dwell-aware reflections when dwell_minutes is provided or available on context.
    """
    is_bihari = str(brand_track).lower() in ("bihari", "consumer", "track_a", "savage")
    reflections_pool = REFLECTIONS_TRACK_A if is_bihari else REFLECTIONS_TRACK_B
    context_templates = CONTEXTUAL_TEMPLATES_TRACK_A if is_bihari else CONTEXTUAL_TEMPLATES_TRACK_B
    short_video = SHORT_VIDEO_REFLECTIONS if is_bihari else SHORT_VIDEO_REFLECTIONS_TRACK_B
    short_punchy = SHORT_PUNCHY_REFLECTIONS if is_bihari else SHORT_PUNCHY_REFLECTIONS_TRACK_B
    short_social = SHORT_SOCIAL_REFLECTIONS if is_bihari else SHORT_SOCIAL_REFLECTIONS_TRACK_B
    short_social_ctx = SHORT_SOCIAL_CONTEXTUAL if is_bihari else SHORT_SOCIAL_CONTEXTUAL_TRACK_B

    dwell_val = dwell_minutes if dwell_minutes is not None else getattr(context, "dwell_minutes", None)
    refl = None

    # When dwell time is significant (>= 2 minutes), blend dwell mirroring with warmth and presence
    if dwell_val is not None and dwell_val >= 2.0 and random.random() < 0.50:
        sub_str = getattr(context, "subject", "") if (context and getattr(context, "is_specific", False)) else None
        refl = format_dwell_reflection(dwell_val, subject=sub_str, vibe=vibe)

    if not refl and context and getattr(context, "is_specific", False) and getattr(context, "subject", ""):
        sub = condense_subject(context.subject, max_chars=16)
        cat = getattr(context, "category", "")

        # Dedicated video reflections (>= 80% inclusion rate target)
        if cat == "video":
            if sub and len(sub) >= 3 and random.random() < 0.88:
                refl = random.choice(short_video).format(subject=sub)
            else:
                refl = random.choice(short_punchy)

        # Dedicated social reflections (>= 80% inclusion rate target)
        elif getattr(context, "is_social", False) and cat == "social":
            if sub and len(sub) >= 3 and random.random() < 0.88:
                refl = random.choice(short_social_ctx).format(subject=sub)
            else:
                refl = random.choice(short_social)

        # Dedicated reading reflections
        elif cat == "reading":
            if sub and len(sub) >= 3 and random.random() < 0.88:
                reading_opts = [
                    f"Reading: {sub}",
                    f"Immersed in: {sub}",
                    f"Absorbed in: {sub}",
                    f"Studying: {sub}",
                    f"Deep in: {sub}",
                ]
                refl = random.choice([o for o in reading_opts if len(o) < 40])
            else:
                refl = "Absorbed in reading right now."

        # Dedicated email / messaging reflections
        elif cat == "email":
            if sub and len(sub) >= 3 and random.random() < 0.88:
                email_opts = [
                    f"Tending to: {sub}",
                    f"Present with: {sub}",
                    f"Handling: {sub}",
                    f"Focused on: {sub}",
                ]
                refl = random.choice([o for o in email_opts if len(o) < 40])
            else:
                refl = "Present with communications."

        # Contextual templates for code/docs/terminal (>= 80% inclusion rate target)
        elif random.random() < 0.88 and vibe in context_templates:
            template = random.choice(context_templates[vibe])
            refl = template.format(subject=sub)

    if not refl:
        if dwell_val is not None and dwell_val > 0:
            sub_str = getattr(context, "subject", "") if (context and getattr(context, "is_specific", False)) else None
            refl = format_dwell_reflection(dwell_val, subject=sub_str, vibe=vibe)
        else:
            phrases = reflections_pool.get(vibe, ["something is happening"])
            refl = random.choice(phrases)

    # Hard clamp: 100% adherence to < 40 chars under all conditions
    if len(refl) >= 40:
        refl = refl[:36].rstrip() + "..."
        if len(refl) >= 40:
            refl = refl[:39]

    return refl



# ──────────────────────────────────────────────
# Classification result
# ──────────────────────────────────────────────

@dataclass
class VibeResult:
    """Classification result with provenance tracking."""
    vibe: Vibe
    confidence: float
    source: str  # "rules", "laya", or "laya_fallback"

    def __repr__(self):
        return f"VibeResult({self.vibe.value}, conf={self.confidence:.2f}, src={self.source})"


# ──────────────────────────────────────────────
# App categories for rule-based classification
# ──────────────────────────────────────────────

CODE_APPS = frozenset({
    "code.exe",          # VS Code
    "devenv.exe",        # Visual Studio
    "idea64.exe",        # IntelliJ IDEA
    "pycharm64.exe",     # PyCharm
    "rider64.exe",       # JetBrains Rider
    "webstorm64.exe",    # WebStorm
    "goland64.exe",      # GoLand
    "sublime_text.exe",  # Sublime Text
    "notepad++.exe",     # Notepad++
    "windowsterminal.exe",  # Windows Terminal
    "powershell.exe",
    "cmd.exe",
    "wt.exe",
    "alacritty.exe",
    "wezterm-gui.exe",
    "antigravity.exe",   # Antigravity IDE
})

BROWSER_APPS = frozenset({
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "vivaldi.exe",
    "arc.exe",
})

COMMS_APPS = frozenset({
    "zoom.exe",
    "teams.exe",
    "slack.exe",
    "discord.exe",
    "telegram.exe",
    "whatsapp.exe",
    "webex.exe",
})

# ── Title keyword patterns for context detection ──

SOCIAL_KEYWORDS = frozenset({
    "instagram", "youtube", "tiktok", "twitter", "x.com",
    "reddit", "facebook", "reels", "shorts", "twitch"
})

VIDEO_KEYWORDS = frozenset({
    "youtube", "twitch", "netflix", "vimeo", "hulu",
    "disney", "prime video", "dailymotion"
})

ALL_SOCIAL_VIDEO_KEYWORDS = SOCIAL_KEYWORDS | VIDEO_KEYWORDS

MEDIA_APPS = frozenset({
    "vlc.exe", "mpv.exe", "netflix.exe", "spotify.exe", "wmplayer.exe"
})

PRODUCTIVITY_APPS = frozenset({
    "obsidian.exe",
    "notion.exe",
    "winword.exe",
    "excel.exe",
    "powerpnt.exe",
    "typora.exe",
    "onenote.exe",
    "writer.exe",
    "scrivener.exe",
})

WORK_APPS = CODE_APPS | PRODUCTIVITY_APPS

UTILITY_APPS = frozenset({
    "taskmgr.exe", "explorer.exe", "systemsettings.exe",
    "regedit.exe"
})

HELP_SEEKING_KEYWORDS = frozenset({
    "stackoverflow", "stack overflow", "stackexchange",
    "github.com/issues", "github issue",
    "chatgpt", "claude", "gemini", "copilot chat",
    "docs.", "documentation", "api reference",
    "how to", "error:", "exception",
    "geeksforgeeks", "w3schools", "mdn web docs",
})

MEETING_KEYWORDS = frozenset({
    "zoom meeting", "teams meeting", "google meet",
    "microsoft teams", "webex meeting",
    "screen sharing", "video call",
})

WORK_BROWSER_KEYWORDS = frozenset({
    "github", "gitlab", "bitbucket",
    "gmail", "google mail", "mail.google", "outlook", "protonmail", "webmail",
    "google docs", "google sheets", "google slides", "notion", "trello",
    "jira", "confluence", "linear", "asana", "figma", "canva",
    "pull request", "commit", "repository", "diff",
})

READING_BROWSER_KEYWORDS = frozenset({
    "arxiv", "wikipedia", "medium", "substack", "dev.to", "hashnode",
    "hackernews", "ycombinator", "docs.", "documentation", "api reference",
    "blog", "article", "paper", "newsletter", "guide", "tutorial", "reading",
    "stackoverflow", "stack overflow", "stackexchange",
})


# ──────────────────────────────────────────────
# Rule-based classifier (instant, zero RAM cost)
# ──────────────────────────────────────────────

def classify_by_rules(event) -> Optional[VibeResult]:
    """
    Deterministic rule engine with 12-vibe classification.

    Returns a VibeResult if confident, or None if the situation is
    ambiguous and should be deferred to Laya.

    Rules are ordered by specificity (most specific first).
    Uses app context, typing metrics, title keywords, time-of-day,
    and extended telemetry signals when available.
    """
    app = event.app_name.lower()
    title = getattr(event, "window_title", "").lower()
    speed = event.typing_speed          # chars/min in 30s window
    bs_rate = event.backspace_rate      # backspace / total strokes ratio
    bs_count = event.backspace_count    # raw backspace count in 30s window
    switches = event.window_switches_3min

    # Extended signals (graceful fallback for older TelemetryEvent objects)
    hour = getattr(event, "hour_of_day", -1)
    session_min = getattr(event, "session_minutes", -1)
    dwell_min = getattr(event, "dwell_minutes", -1)

    # ── SOCIAL / VIDEO MEDIA: Context-specific dwell thresholds (R2) ──
    # Short dwell (<2 min) = transient glance (TAB_BUTTERFLY)
    # Medium dwell (2–8 min, up to 12 min) = focused engagement (LOST_IN_SCROLL)
    # Extended dwell (>12 min) = absorbed trance state (WANDERING)
    is_code_or_work_site = any(
        kw in title for kw in ["github", "gitlab", "bitbucket", "stackoverflow", "gmail", "outlook", "mail.google", "docs.google", "notion"]
    )
    is_social_video = (
        not is_code_or_work_site and (
            (app in BROWSER_APPS and any(kw in title for kw in ALL_SOCIAL_VIDEO_KEYWORDS))
            or (app in MEDIA_APPS)
        )
    )
    if is_social_video:
        if 0 <= dwell_min < 2.0:
            return VibeResult(Vibe.TAB_BUTTERFLY, 0.78, "rules")
        elif dwell_min > 12.0:
            return VibeResult(Vibe.WANDERING, 0.88, "rules")
        else:
            # 2.0 <= dwell_min <= 12.0 or unspecified dwell (< 0)
            return VibeResult(Vibe.LOST_IN_SCROLL, 0.92, "rules")

    # ── BROWSER WORK & READING DETECTION ──
    is_work_or_reading_browser = (
        app in BROWSER_APPS and not is_social_video and (
            any(kw in title for kw in WORK_BROWSER_KEYWORDS)
            or any(kw in title for kw in READING_BROWSER_KEYWORDS)
            or any(kw in title for kw in HELP_SEEKING_KEYWORDS)
        )
    )
    is_work_context = (app in WORK_APPS) or is_work_or_reading_browser

    # ── STILLNESS & DRIFT: Inactivity (R2) ──
    if speed == 0 and switches == 0 and bs_count == 0:
        is_idle_heartbeat = getattr(event, "trigger_reason", "") == "idle_heartbeat"
        # In work apps, short dwell (<3 min) is orientation/settling, not prolonged stillness
        if not (is_work_context and 0 <= dwell_min < 3.0 and not is_idle_heartbeat):
            if 13 <= hour <= 15 and dwell_min > 3:
                return VibeResult(Vibe.AFTERNOON_DRIFT, 0.75, "rules")
            return VibeResult(Vibe.STILLNESS, 0.92, "rules")

    # ── STILLNESS: idle heartbeat trigger ──
    if hasattr(event, "trigger_reason") and event.trigger_reason == "idle_heartbeat":
        return VibeResult(Vibe.STILLNESS, 0.88, "rules")

    # ── UTILITY / SYSTEM MANAGEMENT ──
    if app in UTILITY_APPS:
        return VibeResult(Vibe.WANDERING, 0.65, "rules")

    # ── MEETING_RECOVERY: just came from a comms app ──
    if app in COMMS_APPS or any(kw in title for kw in MEETING_KEYWORDS):
        return None  # In a meeting — don't interrupt

    # ── HELP_SEEKING: browser with help-seeking title keywords ──
    if app in BROWSER_APPS and any(kw in title for kw in HELP_SEEKING_KEYWORDS):
        conf = 0.80 if speed < 15 else 0.65  # Reading docs vs. actively typing in search
        return VibeResult(Vibe.HELP_SEEKING, conf, "rules")

    # ── CODE / WRITING / PRODUCTIVITY: Frustration triggers (most specific) ──
    # SYNTAX_RAGE: coding app + high backspace ratio + active typing
    if app in WORK_APPS and bs_rate > 0.30 and speed > 20:
        conf = min(0.95, 0.70 + bs_rate)
        return VibeResult(Vibe.SYNTAX_RAGE, conf, "rules")

    # MOUNTING_FRICTION: coding app + moderate backspace + rising frustration
    if app in WORK_APPS and 0.18 < bs_rate <= 0.30 and speed > 15:
        return VibeResult(Vibe.MOUNTING_FRICTION, 0.70, "rules")

    # ── CODE / WRITING / PRODUCTIVITY / BROWSER WORK & READING: Dwell thresholds (R2) ──
    # Short dwell (<5 min) = orientation/settling (WANDERING)
    # Medium dwell (5–30 min, up to 45 min) = immersion / sustained flow (FLOW_STATE)
    # Extended dwell (>45 min) = deep grind / mental fatigue (GRINDING / BURNOUT_APPROACHING)
    if is_work_context and dwell_min >= 0:
        if dwell_min > 45.0:
            if (speed < 15 and speed > 0) or session_min > 180 or dwell_min > 60:
                return VibeResult(Vibe.BURNOUT_APPROACHING, 0.75, "rules")
            return VibeResult(Vibe.GRINDING, 0.72, "rules")
        elif 5.0 <= dwell_min <= 45.0:
            if session_min > 180 and speed < 20 and speed > 0:
                return VibeResult(Vibe.BURNOUT_APPROACHING, 0.75, "rules")
            if session_min > 90 and speed > 10:
                return VibeResult(Vibe.GRINDING, 0.72, "rules")
            conf = 0.88 if dwell_min > 10 else 0.80
            return VibeResult(Vibe.FLOW_STATE, conf, "rules")
        else:
            # 0 <= dwell_min < 5.0: orientation / settling
            return VibeResult(Vibe.WANDERING, 0.72, "rules")

    # ── AFTERNOON_DRIFT: post-lunch hours + slow activity ──
    if 13 <= hour <= 15 and speed < 15 and speed > 0 and switches < 3:
        return VibeResult(Vibe.AFTERNOON_DRIFT, 0.68, "rules")

    # ── TAB_BUTTERFLY: very rapid context switching ──
    if switches > 10 and speed < 15:
        return VibeResult(Vibe.TAB_BUTTERFLY, 0.78, "rules")

    # ── CODE / WRITING / BROWSER WORK: Fallback when dwell_min is unspecified (< 0) ──
    if is_work_context:
        if speed > 50 and bs_rate < 0.12:
            return VibeResult(Vibe.FLOW_STATE, 0.82, "rules")
        if speed > 25 and bs_rate < 0.08:
            return VibeResult(Vibe.FLOW_STATE, 0.70, "rules")
        if session_min > 180 and speed < 20 and speed > 0:
            return VibeResult(Vibe.BURNOUT_APPROACHING, 0.75, "rules")
        if session_min > 90 and speed > 10:
            return VibeResult(Vibe.GRINDING, 0.72, "rules")
        return VibeResult(Vibe.FLOW_STATE if is_work_or_reading_browser else Vibe.GRINDING, 0.70, "rules")

    # ── WANDERING: moderate switching + browser + low typing ──
    if switches > 5 and app in BROWSER_APPS and speed < 20:
        return VibeResult(Vibe.WANDERING, 0.68, "rules")

    # ── WANDERING: rapid switching + low output ──
    if switches > 8 and speed < 15:
        return VibeResult(Vibe.WANDERING, 0.72, "rules")

    # ── Non-social browser reading / browsing (never LOST_IN_SCROLL) ──
    if app in BROWSER_APPS and not is_social_video:
        if dwell_min > 5:
            return VibeResult(Vibe.FLOW_STATE, 0.70, "rules")
        else:
            return VibeResult(Vibe.WANDERING, 0.60, "rules")

    # ── LOST_IN_SCROLL: strictly for social media or video trance with minimal typing ──
    if is_social_video and speed < 10 and bs_rate < 0.05:
        if dwell_min > 5:
            return VibeResult(Vibe.LOST_IN_SCROLL, 0.80, "rules")
        else:
            return VibeResult(Vibe.WANDERING, 0.60, "rules")

    # ── GENERAL BROWSER (social fallback) ──
    if app in BROWSER_APPS and is_social_video:
        return VibeResult(Vibe.LOST_IN_SCROLL if dwell_min > 3 else Vibe.WANDERING, 0.65, "rules")

    # ── GRINDING: any app + sustained moderate work ──
    if app in WORK_APPS and speed > 10 and bs_rate < 0.20:
        return VibeResult(Vibe.GRINDING, 0.60, "rules")

    # Ambiguous — can't confidently classify with rules alone
    return None


def is_flow_gate_suppressed(event: Any, result: Optional[VibeResult] = None) -> bool:
    """
    Contract F1: Flow State Zero-Interruption Gate.
    Suppresses 100% of toasts when the user is in sustained, high-velocity flow:
    typing > 50 chars/min, backspace rate < 8% (0.08), and dwell >= 10.0 minutes.
    """
    if result is not None and result.vibe != Vibe.FLOW_STATE:
        return False
    if result is None:
        res = classify_by_rules(event)
        if res is None or res.vibe != Vibe.FLOW_STATE:
            return False
    return (
        getattr(event, "typing_speed", 0.0) > 50.0
        and getattr(event, "backspace_rate", 1.0) < 0.08
        and getattr(event, "dwell_minutes", 0.0) >= 10.0
    )


# ──────────────────────────────────────────────
# Laya-based classifier (lazy-loaded, cached)
# ──────────────────────────────────────────────

class LayaBridge:
    """
    Wraps the Laya System 1 decision engine for ambiguous classification
    and semantic context understanding.

    Uses Agent('convaiinnovations/laya') for fast, calibrated non-autoregressive
    inference. Includes in-memory title caching so subsequent ticks on the same
    video or page cost 0ms and zero CPU.
    """

    def __init__(self):
        self._agent = None
        self._available = None  # None = not checked, True/False = checked
        self._title_cache: dict[tuple[str, str], dict] = {}

    def is_available(self) -> bool:
        """Check if Laya is installed without loading the model into RAM."""
        if self._available is None:
            try:
                import laya.agent  # noqa: F401
                self._available = True
            except ImportError:
                self._available = False
                logger.warning(
                    "Laya is not installed. Using rule-based classification only. "
                    "Install with: pip install laya"
                )
        return self._available

    def _ensure_loaded(self):
        """Load the model weights on first ambiguous event or context request."""
        if self._agent is None:
            try:
                logger.info("Loading Laya Agent ('convaiinnovations/laya')...")
                try:
                    import torch
                    torch.set_num_threads(min(2, os.cpu_count() or 2))
                except Exception:
                    pass
                from laya.agent import Agent
                self._agent = Agent("convaiinnovations/laya")
                logger.info("Laya Agent loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load Laya Agent (running in offline/rules fallback): {e}")
                self._agent = None
                self._available = False

    def classify_context(self, app_name: str, window_title: str) -> dict:
        """
        Classify a window title into an activity vibe and optimal meme search category.
        Results are cached per (app, title) so a 15-minute video only runs once.
        """
        if not window_title or not self.is_available():
            return {"activity": None, "meme_category": None}

        cache_key = (app_name.lower(), window_title.strip())
        if cache_key in self._title_cache:
            return self._title_cache[cache_key]

        try:
            self._ensure_loaded()
            state = {
                "title": window_title,
                "app": app_name,
            }
            schema = {
                "activity": {
                    "type": "choice",
                    "instructions": "Classify the user activity and mental vibe from this window context.",
                    "criteria": [
                        "coding", "learning", "gaming", "entertainment", "social_scroll", "deep_rabbit_hole"
                    ]
                },
                "meme_category": {
                    "type": "choice",
                    "instructions": "What general meme search category will find the most relatable visual reaction meme for this context?",
                    "criteria": [
                        "programming", "bugs", "gaming", "existential", "tired", "doomscrolling", "shocked", "confused", "rabbit_hole"
                    ]
                }
            }
            res = self._agent.predict(state, schema)
            act = res.get("answers", {}).get("activity", {}).get("choice")
            cat = res.get("answers", {}).get("meme_category", {}).get("choice")
            out = {"activity": act, "meme_category": cat}

            # Bounded LRU cache (keep last 200 titles)
            if len(self._title_cache) > 200:
                self._title_cache.clear()
            self._title_cache[cache_key] = out
            return out
        except Exception as e:
            logger.warning(f"Laya context classification failed: {e}")
            return {"activity": None, "meme_category": None}

    def classify(self, event) -> VibeResult:
        """Classify ambiguous behavioral telemetry using the Laya decision model."""
        if not self.is_available():
            return VibeResult(Vibe.WANDERING, 0.35, "laya_unavailable")

        try:
            self._ensure_loaded()
            if self._agent is None:
                return VibeResult(Vibe.STILLNESS, 0.30, "laya_fallback")

            # Build compact telemetry state description for Laya
            state = {
                "context": (
                    f"Application: '{event.app_name}'. Window: '{event.window_title}'. "
                    f"Typing speed: {event.typing_speed} chars/min. "
                    f"Backspace rate: {event.backspace_rate:.0%}. "
                    f"Window switches (3min): {event.window_switches_3min}."
                )
            }

            # Define calibrated decision schema
            schema = {
                "vibe": {
                    "type": "choice",
                    "instructions": (
                        "Classify the user's current behavioral vibe. Choose the most fitting state:\n"
                        "- FLOW_STATE: Productive flow, steady typing, low errors.\n"
                        "- GRINDING: Sustained work over a long session.\n"
                        "- BURNOUT_APPROACHING: Declining energy and speed.\n"
                        "- SYNTAX_RAGE: Frustrated while coding, lots of backspaces.\n"
                        "- HELP_SEEKING: Searching docs, Stack Overflow, or tutorials.\n"
                        "- MOUNTING_FRICTION: Moderate frustration or obstacles.\n"
                        "- WANDERING: Aimlessly switching between apps or browsing.\n"
                        "- LOST_IN_SCROLL: Mindlessly consuming feeds, minimal input.\n"
                        "- TAB_BUTTERFLY: Rapid switching across many tabs/windows.\n"
                        "- STILLNESS: Idle or away from keyboard.\n"
                        "- MEETING_RECOVERY: Recovering after a call.\n"
                        "- AFTERNOON_DRIFT: Post-lunch energy dip."
                    ),
                    "criteria": [v.value for v in Vibe],
                }
            }

            result = self._agent.predict(state, schema)
            choice = result["answers"]["vibe"]["choice"]
            confidence = result["answers"]["vibe"]["confidence"]
            return VibeResult(Vibe(choice), confidence, "laya")
        except Exception as e:
            logger.warning(f"Laya inference failed: {e}")
            return VibeResult(Vibe.STILLNESS, 0.30, "laya_fallback")

    def classify_screen_content(self, screen_text: str, app_name: str, window_title: str) -> dict:
        """
        Classify in-the-moment on-screen text (from OCR) into a compassionate mindfulness theme,
        reaction emotion, corresponding Vibe, and gentle reflection phrase.
        """
        if not screen_text or not self.is_available():
            return {}

        try:
            self._ensure_loaded()
            if self._agent is None:
                return {}
        except Exception as e:
            logger.warning(f"Laya loading failed: {e}")
            return {}

        state = {
            "context": (
                f"Application: '{app_name}'. Window: '{window_title}'. "
                f"On-screen text or caption: '{screen_text[:300]}'"
            )
        }
        schema = {
            "human_theme": {
                "type": "choice",
                "instructions": "Determine the theme of the social media post, video, or window content the user is viewing.",
                "criteria": [
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
            },
            "reaction_vibe": {
                "type": "choice",
                "instructions": "What visual reaction best mirrors this moment in a funny, relatable way?",
                "criteria": [
                    "food_craving",
                    "jaw_drop_awe",
                    "side_eye_scrolling",
                    "vibing_and_grooving",
                    "laughing_out_loud",
                    "deep_contemplation",
                    "mild_disbelief",
                    "tired_acceptance",
                    "peaceful_moment",
                ]
            }
        }
        try:
            res = self._agent.predict(state, schema)
            theme = res["answers"]["human_theme"]["choice"]
            reaction = res["answers"]["reaction_vibe"]["choice"]

            # Semantic alignment guardrails: ensure reaction genuinely mirrors the theme
            text_lower = screen_text.lower()
            if theme == "comedy_and_humor" or any(w in text_lower for w in ["prank", "comedy", "joke", "funny", "hilarious", "meme", "couplescomedy"]):
                if reaction not in ("laughing_out_loud", "mild_disbelief"):
                    reaction = random.choice(["laughing_out_loud", "mild_disbelief"])
            elif theme == "pop_culture_and_movies" or any(w in text_lower for w in ["red-carpet", "celebrity", "drama", "hollywood", "actor"]):
                if reaction not in ("side_eye_scrolling", "jaw_drop_awe", "mild_disbelief"):
                    reaction = random.choice(["side_eye_scrolling", "jaw_drop_awe"])
            elif theme == "sports_and_fitness" or any(w in text_lower for w in ["jumping", "fall season", "ziptrek", "workout", "fitness", "stunt"]):
                if reaction not in ("jaw_drop_awe", "tired_acceptance"):
                    reaction = "jaw_drop_awe"
            elif theme == "food_and_cooking":
                reaction = "food_craving"
            elif theme == "music_and_dance":
                reaction = "vibing_and_grooving"
            elif theme == "deep_thoughts_philosophy":
                reaction = "deep_contemplation"

            vibe_map = {
                "comedy_and_humor": Vibe.LOST_IN_SCROLL,
                "food_and_cooking": Vibe.WANDERING,
                "scenic_views_and_nature": Vibe.WANDERING,
                "music_and_dance": Vibe.LOST_IN_SCROLL,
                "sports_and_fitness": Vibe.LOST_IN_SCROLL,
                "pop_culture_and_movies": Vibe.LOST_IN_SCROLL,
                "wholesome_animals": Vibe.STILLNESS,
                "relatable_life_struggles": Vibe.BURNOUT_APPROACHING,
                "deep_thoughts_philosophy": Vibe.WANDERING,
                "technical_learning_and_code": Vibe.FLOW_STATE,
                "work_email_communication": Vibe.FLOW_STATE,
                "reading_articles_and_news": Vibe.FLOW_STATE,
                "mindless_social_scrolling": Vibe.LOST_IN_SCROLL,
            }
            mapped_vibe = vibe_map.get(theme, Vibe.FLOW_STATE)

            # Extract specific subject from OCR text for personalized reflection
            from .ocr import extract_caption_keywords
            kw_list = extract_caption_keywords(screen_text)
            subject_str = kw_list[0] if kw_list else ""

            if subject_str and len(subject_str) >= 3:
                s_clean = condense_subject(subject_str, max_chars=16)
                topic_reflections = {
                    "comedy_and_humor": [
                        f"Quick chuckle: {s_clean}",
                        "A moment of pure humor.",
                        "Smiling at the absurdity.",
                    ],
                    "food_and_cooking": [
                        f"Craving: {s_clean}",
                        "Appreciating good food.",
                        "Savoring the moment.",
                    ],
                    "scenic_views_and_nature": [
                        f"Viewing: {s_clean}",
                        "A breath of fresh scenery.",
                        "Quiet beauty right here.",
                    ],
                    "music_and_dance": [
                        f"Vibing to: {s_clean}",
                        "Caught in the rhythm.",
                        "Music filling the space.",
                    ],
                    "sports_and_fitness": [
                        f"Energy: {s_clean}",
                        "Witnessing peak effort.",
                        "Pure momentum right now.",
                    ],
                    "pop_culture_and_movies": [
                        f"Invested in: {s_clean}",
                        "Deep in the narrative.",
                        "Watching the story unfold.",
                    ],
                    "wholesome_animals": [
                        f"Delight in: {s_clean}",
                        "Gentle animal presence.",
                        "A simple moment of joy.",
                    ],
                    "deep_thoughts_philosophy": [
                        f"Contemplating: {s_clean}",
                        "Exploring deep questions.",
                        "Reflecting on the world.",
                    ],
                    "relatable_life_struggles": [
                        f"Relatable: {s_clean}",
                        "Shared human experience.",
                        "Witnessing everyday life.",
                    ],
                    "technical_learning_and_code": [
                        f"Studying: {s_clean}",
                        "Deep in documentation.",
                        "Building and learning.",
                    ],
                    "work_email_communication": [
                        f"Tending to: {s_clean}",
                        "Present with email.",
                        "Handling communications.",
                    ],
                    "reading_articles_and_news": [
                        f"Reading: {s_clean}",
                        "Absorbed in thought.",
                        "Present with the article.",
                    ],
                    "mindless_social_scrolling": [
                        f"Resting with: {s_clean}",
                        "Observing the infinite feed.",
                        "Present with the stream.",
                    ],
                }
                if theme in topic_reflections:
                    reflection = random.choice(topic_reflections[theme])
                else:
                    reflection = f"Detour: {s_clean}"
            else:
                phrases = MINDFUL_THEME_REFLECTIONS.get(theme, [
                    "Present with the screen.",
                    "Observing this moment.",
                    "Awareness right here.",
                ])
                reflection = random.choice(phrases)

            if len(reflection) >= 40:
                reflection = reflection[:36].rstrip() + "..."
                if len(reflection) >= 40:
                    reflection = reflection[:39]

            # High-entropy visual emotion reaction query pools
            reaction_query_pools = {
                "food_craving": ["drooling", "hungry cat", "chef kiss", "looking at food", "mouth watering", "snack craving"],
                "jaw_drop_awe": ["jaw dropped", "daydreaming", "staring in awe", "looking out window", "blown away", "mesmerized cat"],
                "side_eye_scrolling": ["side eye", "monkey puppet looking away", "caught staring", "blank stare", "cat staring", "dog judging"],
                "vibing_and_grooving": ["cat vibing", "grooving", "head bob", "dancing cat", "headphones vibing", "bopping head", "swaying cat", "chill groove"],
                "laughing_out_loud": ["laughing", "wheezing", "snicker", "smirk", "crying laughing", "giggling dog", "cracking up", "spit take"],
                "deep_contemplation": ["thinking monkey", "galaxy brain", "contemplating", "philosophical stare", "staring ceiling", "pondering dog"],
                "mild_disbelief": ["squinting", "confused stare", "double take", "raised eyebrow", "shocked dog", "disbelief cat", "wait what"],
                "tired_acceptance": ["facepalm", "tired dog", "exhausted", "deflated", "sigh cat", "lying on floor"],
                "peaceful_moment": ["peaceful cat", "chilling dog", "zen", "cozy blanket", "sleeping otter", "pure peace"],
            }

            pool = reaction_query_pools.get(reaction, ["side eye", "smirk", "stare"])
            # Pick a random term from the pool for maximum variety
            search_term = random.choice(pool)

            return {
                "human_theme": theme,
                "reaction_vibe": reaction,
                "meme_subject": subject_str or theme.replace("_", " "),
                "search_queries": [search_term],
                "vibe": mapped_vibe,
                "reflection": reflection,
                "screen_text": screen_text,
            }
        except Exception as e:
            logger.warning(f"Laya screen content classification failed: {e}")
            return {}


MINDFUL_THEME_REFLECTIONS = {
    "comedy_and_humor": [
        "A quiet laugh in the day.",
        "Smiling at the absurdity.",
        "Humor in the present moment.",
    ],
    "scenic_views_and_nature": [
        "A scenic pause in screen time.",
        "Visual stillness from the desk.",
        "Quiet nature on display.",
    ],
    "mindless_social_scrolling": [
        "Observing the endless stream.",
        "Awareness resting on the feed.",
        "Present with the scroll.",
    ],
    "technical_learning_and_code": [
        "Deep in technical learning.",
        "Observing the documentation.",
        "Building and understanding.",
    ],
    "work_email_communication": [
        "Tending to communications.",
        "Present with email.",
        "Calm attention on messages.",
    ],
    "reading_articles_and_news": [
        "Absorbed in reading.",
        "Engaged with ideas.",
        "Present with the written word.",
    ],
    "wholesome_animals": [
        "A simple moment of animal joy.",
        "Gentle presence on screen.",
        "A quiet, joyful pause.",
    ],
    "bargaining_with_time": [
        "Noticing time passing quietly.",
        "Present with where you are.",
        "Awareness of this moment.",
    ],
    "relatable_exhaustion": [
        "Honoring the body's tiredness.",
        "Gentle awareness of low energy.",
        "Resting right here.",
    ],
    "technical_debugging_struggle": [
        "Observing the stubborn logic.",
        "Calm gaze at the stack trace.",
        "Patience with the code.",
    ],
    "self_improvement_trap": [
        "Already complete in this moment.",
        "Simply being, right now.",
        "Present without needing to fix.",
    ],
    "curiosity_rabbit_hole": [
        "Curiosity exploring freely.",
        "Following an interesting thread.",
        "Scenic route of knowledge.",
    ],
}


# ──────────────────────────────────────────────
# Hybrid classifier (public API)
# ──────────────────────────────────────────────

class VibeClassifier:
    """
    Hybrid classifier: rules first, Laya for ambiguous cases.

    This is the primary classification interface.
    """

    def __init__(self, use_laya: bool = True, enable_learning: bool = True):
        """
        Args:
            use_laya: If True, allow legacy Laya as fallback when installed.
            enable_learning: If True, enable on-device continuous personalization.
        """
        self.use_laya = use_laya
        self.laya_bridge = LayaBridge() if use_laya else None

        # MicroBrain: Zero-dependency, on-device decision intelligence (<500 KB, <0.5ms)
        micro_cls = _get_micro_brain()
        self.micro_brain = micro_cls(enable_learning=enable_learning) if micro_cls else None

    def classify_context(self, app_name: str, window_title: str) -> dict:
        """Helper to get semantic classification of the current window."""
        if self.micro_brain:
            res = self.micro_brain.classify_context(app_name, window_title)
            if res.get("activity"):
                return res
        if self.laya_bridge and self.laya_bridge.is_available():
            return self.laya_bridge.classify_context(app_name, window_title)
        return {"activity": None, "meme_category": None}

    def classify_screen_content(self, screen_text: str, app_name: str, window_title: str) -> dict:
        """Helper to classify on-screen OCR content into mindfulness theme & reflection."""
        # 1. Primary: Instant on-device MicroBrain (<0.5ms, zero dependencies)
        if self.micro_brain:
            res = self.micro_brain.classify_screen_content(screen_text, app_name, window_title)
            if res:
                return res
        # 2. Secondary: Laya fallback if installed and available
        if self.laya_bridge and self.laya_bridge.is_available():
            return self.laya_bridge.classify_screen_content(screen_text, app_name, window_title)
        return {}

    def classify(self, event, allow_laya: bool = True) -> VibeResult:
        """
        Classify a TelemetryEvent into a Vibe.

        Steps:
          1. Try deterministic rules (instant, 0% CPU)
          2. If ambiguous, run MicroBrain (instant <0.5ms on-device decision model)
          3. If MicroBrain uncertain or disabled, try Laya (if installed/available)
          4. Default heuristic fallback (0% CPU)
        """
        # Step 1: Rules
        result = classify_by_rules(event)
        if result is not None:
            logger.debug(f"Rules classified: {result}")
            return result

        trigger = getattr(event, "trigger_reason", "")

        # Step 2: MicroBrain on-device decision model (0% CPU, <0.5ms)
        if allow_laya and trigger != "dwell_tick" and self.micro_brain:
            micro_res = self.micro_brain.classify_vibe(event)
            if micro_res.confidence >= 0.50:
                logger.debug(f"MicroBrain classified: {micro_res}")
                return micro_res

        # Step 3: Laya fallback (if installed in dev environment)
        if allow_laya and trigger != "dwell_tick" and self.laya_bridge and self.laya_bridge.is_available():
            result = self.laya_bridge.classify(event)
            logger.debug(f"Laya classified: {result}")
            return result

        # Step 4: Fast default fallback (0% CPU)
        app = event.app_name.lower()
        title = getattr(event, "window_title", "").lower()
        dwell_min = getattr(event, "dwell_minutes", -1)
        if (app in BROWSER_APPS and any(kw in title for kw in ALL_SOCIAL_VIDEO_KEYWORDS)) or (app in MEDIA_APPS):
            if 0 <= dwell_min < 2.0:
                return VibeResult(Vibe.TAB_BUTTERFLY, 0.75, "rules_default")
            elif dwell_min > 12.0:
                return VibeResult(Vibe.WANDERING, 0.85, "rules_default")
            return VibeResult(Vibe.LOST_IN_SCROLL, 0.85, "rules_default")
        if app in WORK_APPS:
            if 0 <= dwell_min < 5.0:
                return VibeResult(Vibe.WANDERING, 0.70, "rules_default")
            elif 5.0 <= dwell_min <= 45.0:
                return VibeResult(Vibe.FLOW_STATE, 0.75, "rules_default")
            elif dwell_min > 45.0:
                return VibeResult(Vibe.GRINDING, 0.70, "rules_default")
        return VibeResult(Vibe.WANDERING, 0.40, "rules_default")

    def adapt_user_vibe(self, event, target_vibe: Any, was_positive: bool = True) -> None:
        """On-device continuous personalization (100% private, zero cloud)."""
        if self.micro_brain:
            self.micro_brain.adapt_vibe(event, target_vibe, was_positive=was_positive)
