"""
Repackage packs/default.lucidpack with 120 genuinely unique, Pillow-decodable reaction images.

Ensures:
- Exactly 10 unique images per vibe folder across all 12 vibes.
- Exactly 120 globally unique SHA-256 hashes across the entire archive (0 duplicates).
- ZIP64 archive format with compression=zipfile.ZIP_DEFLATED.
- Valid pack.json conforming to meme_pack_schema.json.
- Authentic icon.png retained.
"""

import collections
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bihari.inference import Vibe, VIBE_FOLDER_NAMES
from bihari.packs import validate_pack_manifest, VIBE_TO_PACK_FOLDER


def build_authentic_pack(output_path: Path):
    localappdata = Path(os.environ.get("LOCALAPPDATA", "")) / "Bihari" / "memes"
    workspace_memes = Path("memes")

    folder_to_vibe = {
        "in-the-zone": "FLOW_STATE",
        "the-long-grind": "GRINDING",
        "running-on-fumes": "BURNOUT_APPROACHING",
        "fighting-the-code": "SYNTAX_RAGE",
        "asking-the-internet": "HELP_SEEKING",
        "mounting-friction": "MOUNTING_FRICTION",
        "just-wandering": "WANDERING",
        "lost-in-the-scroll": "LOST_IN_SCROLL",
        "tab-butterfly": "TAB_BUTTERFLY",
        "the-great-pause": "STILLNESS",
        "post-meeting-recovery": "MEETING_RECOVERY",
        "afternoon-drift": "AFTERNOON_DRIFT",
    }

    # Harvest all candidate images and compute hashes
    unique_candidates = {}
    for root in [localappdata, workspace_memes]:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif") and f.name != "icon.png":
                try:
                    with Image.open(f) as img:
                        img.verify()
                    data = f.read_bytes()
                    h = hashlib.sha256(data).hexdigest()
                    if h not in unique_candidates:
                        unique_candidates[h] = {
                            "path": f,
                            "name": f.name,
                            "folder": f.parent.name,
                            "orig_vibe": folder_to_vibe.get(f.parent.name, None),
                            "sha256": h,
                            "data": data,
                        }
                except Exception:
                    pass

    print(f"Discovered {len(unique_candidates)} unique, valid candidate images on disk.")
    assert len(unique_candidates) >= 120, f"Insufficient candidates: {len(unique_candidates)}"

    def get_sub(name):
        if name.startswith("reddit_"):
            parts = name.split("_")
            return parts[1] if len(parts) > 1 else "other"
        elif name.startswith("live_"):
            return "live"
        return "other"

    for h, info in unique_candidates.items():
        info["sub"] = get_sub(info["name"])

    vibes_list = [
        "FLOW_STATE", "GRINDING", "BURNOUT_APPROACHING",
        "SYNTAX_RAGE", "HELP_SEEKING", "MOUNTING_FRICTION",
        "WANDERING", "LOST_IN_SCROLL", "TAB_BUTTERFLY",
        "STILLNESS", "MEETING_RECOVERY", "AFTERNOON_DRIFT",
    ]

    allowed_vibes = {}
    for h, info in unique_candidates.items():
        sub = info["sub"]
        orig = info["orig_vibe"]
        cand = []
        if orig:
            cand.append(orig)
        if sub == "oddlysatisfying":
            cand.extend(["FLOW_STATE", "STILLNESS"])
        elif sub == "GetMotivated":
            cand.extend(["FLOW_STATE", "GRINDING"])
        elif sub == "reactionpics":
            cand.extend(["SYNTAX_RAGE", "HELP_SEEKING", "MOUNTING_FRICTION", "GRINDING", "BURNOUT_APPROACHING", "MEETING_RECOVERY", "WANDERING"])
        elif sub == "ReactionMemes":
            cand.extend(["SYNTAX_RAGE", "HELP_SEEKING", "BURNOUT_APPROACHING", "MOUNTING_FRICTION"])
        elif sub == "wholesomememes":
            cand.extend(["STILLNESS", "FLOW_STATE", "BURNOUT_APPROACHING", "MEETING_RECOVERY", "GRINDING"])
        elif sub == "hmmm":
            cand.extend(["WANDERING", "MOUNTING_FRICTION", "TAB_BUTTERFLY"])
        elif sub == "wunkus":
            cand.extend(["TAB_BUTTERFLY", "AFTERNOON_DRIFT", "LOST_IN_SCROLL", "BURNOUT_APPROACHING"])
        elif sub == "aww":
            cand.extend(["STILLNESS", "AFTERNOON_DRIFT"])
        elif sub == "rarepuppers":
            cand.extend(["AFTERNOON_DRIFT", "STILLNESS"])
        elif sub == "Eyebleach":
            cand.extend(["STILLNESS", "AFTERNOON_DRIFT", "FLOW_STATE"])
        elif sub == "blurrypicturesofcats":
            cand.extend(["TAB_BUTTERFLY", "SYNTAX_RAGE"])
        elif sub == "me":
            cand.extend(["MEETING_RECOVERY", "BURNOUT_APPROACHING", "GRINDING"])
        elif sub == "live":
            cand.extend(["LOST_IN_SCROLL", "TAB_BUTTERFLY", "HELP_SEEKING", "GRINDING", "WANDERING"])

        seen = set()
        final_cand = []
        for v in cand:
            if v in vibes_list and v not in seen:
                seen.add(v)
                final_cand.append(v)
        allowed_vibes[h] = final_cand

    # Max flow bipartite matching
    adj = collections.defaultdict(dict)
    for h in unique_candidates:
        adj["source"][h] = 1
        adj[h]["source"] = 0
        for v in allowed_vibes[h]:
            adj[h][v] = 1
            adj[v][h] = 0

    for v in vibes_list:
        adj[v]["sink"] = 10
        adj["sink"][v] = 0

    def bfs(parent):
        visited = set(["source"])
        queue = collections.deque(["source"])
        while queue:
            u = queue.popleft()
            if u == "sink":
                return True
            for v, cap in adj[u].items():
                if v not in visited and cap > 0:
                    visited.add(v)
                    parent[v] = u
                    queue.append(v)
        return False

    flow = 0
    parent = {}
    while bfs(parent):
        v = "sink"
        while v != "source":
            u = parent[v]
            adj[u][v] -= 1
            adj[v][u] += 1
            v = u
        flow += 1

    print(f"Max flow matched: {flow} images.")
    assert flow == 120, f"Expected 120 matches, got {flow}"

    # Extract vibe assignment
    vibe_to_images = collections.defaultdict(list)
    for h in unique_candidates:
        for v in vibes_list:
            if v in adj[h] and adj[h][v] == 0:  # used in flow
                vibe_to_images[v].append(unique_candidates[h])

    for v in vibes_list:
        assert len(vibe_to_images[v]) == 10, f"Vibe {v} has {len(vibe_to_images[v])} images (expected 10)"

    # Read existing pack.json and icon.png from current default.lucidpack
    with zipfile.ZipFile(output_path, "r") as zf:
        manifest = json.loads(zf.read("pack.json").decode("utf-8"))
        icon_bytes = zf.read("icon.png")

    # Update manifest assets per vibe
    for v_str, images in vibe_to_images.items():
        vibe_enum = getattr(Vibe, v_str)
        folder_name = VIBE_TO_PACK_FOLDER[vibe_enum]
        if v_str not in manifest["vibes"]:
            manifest["vibes"][v_str] = {}
        manifest["vibes"][v_str]["folder"] = folder_name
        assets_list = []
        for img in images:
            assets_list.append({
                "filename": img["name"],
                "sha256": img["sha256"],
                "caption": img["name"].rsplit(".", 1)[0].replace("_", " "),
            })
        manifest["vibes"][v_str]["assets"] = assets_list

    # Validate updated manifest
    is_valid, err_msg = validate_pack_manifest(manifest)
    assert is_valid, f"Updated manifest validation failed: {err_msg}"

    # Build new ZIP archive
    tmp_pack_file = output_path.with_suffix(".tmp.lucidpack")
    with zipfile.ZipFile(tmp_pack_file, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        # Write pack.json
        manifest_json_str = json.dumps(manifest, indent=2, ensure_ascii=False)
        zf.writestr("pack.json", manifest_json_str.encode("utf-8"))

        # Write icon.png
        zf.writestr("icon.png", icon_bytes)

        # Write images
        all_written_hashes = set()
        for v_str, images in vibe_to_images.items():
            vibe_enum = getattr(Vibe, v_str)
            folder_name = VIBE_TO_PACK_FOLDER[vibe_enum]
            for img in images:
                entry_name = f"{folder_name}/{img['name']}"
                zf.writestr(entry_name, img["data"])
                assert img["sha256"] not in all_written_hashes, f"Duplicate hash detected: {img['sha256']}"
                all_written_hashes.add(img["sha256"])

    assert len(all_written_hashes) == 120, f"Expected 120 unique hashes, got {len(all_written_hashes)}"

    # Replace target archive
    tmp_pack_file.replace(output_path)
    print(f"Successfully packaged authentic {output_path} with 120 globally unique images.")


if __name__ == "__main__":
    pack_path = Path("packs/default.lucidpack")
    build_authentic_pack(pack_path)
