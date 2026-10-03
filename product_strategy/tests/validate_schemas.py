"""
Standalone JSON Schema Validator for Vihara Meme Packs.

Can be run directly via CLI:
    python product_strategy/tests/validate_schemas.py
"""

import json
import sys
from pathlib import Path
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_DIR = REPO_ROOT / "product_strategy"


def validate_meme_pack(schema_path: Path, pack_path: Path) -> bool:
    print(f"Loading schema: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    print("Checking schema Draft-07 validity...")
    Draft7Validator.check_schema(schema)
    print("Schema is valid Draft-07 JSON Schema.")

    print(f"Loading pack manifest: {pack_path}")
    with open(pack_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(pack), key=lambda e: e.path)

    if errors:
        print(f"FAILED: Found {len(errors)} validation errors:")
        for err in errors:
            path_str = " -> ".join(str(p) for p in err.path) if err.path else "root"
            print(f"  [{path_str}]: {err.message}")
        return False

    print("SUCCESS: Pack manifest validates 100% against schema without errors.")
    return True


def main():
    schema_path = STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json"
    pack_path = STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "pack.json"

    if not schema_path.is_file():
        print(f"ERROR: Schema not found at {schema_path}", file=sys.stderr)
        sys.exit(1)

    if not pack_path.is_file():
        print(f"ERROR: Sample pack not found at {pack_path}", file=sys.stderr)
        sys.exit(1)

    valid = validate_meme_pack(schema_path, pack_path)
    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
