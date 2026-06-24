#!/usr/bin/env python3
"""Validate story evidence freshness metadata blocks.

The harness backfills historical evidence incrementally. New or refreshed story
packets opt in with an Evidence Metadata block and are checked strictly here.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {
    "validated_at",
    "host_type",
    "gpu",
    "image_tags",
    "model_ids",
    "commands",
    "stale_when",
}
BLOCK_RE = re.compile(r"<!-- evidence-metadata\n(.*?)\n-->", re.DOTALL)


def validate_block(path: Path, block: str) -> list[str]:
    errors: list[str] = []
    data = YAML().load(block) or {}
    if not isinstance(data, dict):
        return [f"{path}: evidence metadata block must be a mapping"]

    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        errors.append(f"{path}: missing evidence metadata field(s): {', '.join(missing)}")

    for key in ("image_tags", "model_ids", "commands", "stale_when"):
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, list) or not value:
            errors.append(f"{path}: {key} must be a non-empty list")

    validated_at = data.get("validated_at")
    if validated_at is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(validated_at)):
        errors.append(f"{path}: validated_at must use YYYY-MM-DD")

    return errors


def main() -> int:
    errors: list[str] = []
    checked = 0
    for path in sorted((ROOT / "docs" / "stories").rglob("*.md")):
        text = path.read_text()
        for match in BLOCK_RE.finditer(text):
            checked += 1
            errors.extend(validate_block(path.relative_to(ROOT), match.group(1)))

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print(f"PASS evidence metadata blocks validated ({checked} checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
