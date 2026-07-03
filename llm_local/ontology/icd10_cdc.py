"""Load ICD-10-CM compact code lists published by CDC NCHS."""

from __future__ import annotations

import re
from pathlib import Path

from llm_local.catalog import ROOT

DEFAULT_CDC_CODES_FILE = (
    ROOT
    / "data/ontology/icd10cm/2027/extracted/icd10cm-code-descriptions-2027"
    / "icd10cm-code-descriptions-2027"
    / "icd10cm-codes-2027.txt"
)


def compact_to_dotted(code: str) -> str:
    """Convert CDC compact code (e.g. E110) to dotted ICD form (E11.0)."""
    compact = code.strip().upper()
    if len(compact) <= 3:
        return compact
    return f"{compact[:3]}.{compact[3:]}"


def normalize_code(code: str) -> str:
    """Alphanumeric uppercase code without punctuation."""
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def load_cdc_codes(path: Path | None = None) -> list[dict[str, str]]:
    """Parse CDC tab-separated code file into records."""
    source = path or DEFAULT_CDC_CODES_FILE
    if not source.is_file():
        raise FileNotFoundError(f"CDC code file not found: {source}")

    records: list[dict[str, str]] = []
    for line in source.read_text().splitlines():
        if not line.strip():
            continue
        compact, _, description = line.partition(" ")
        description = description.strip()
        if not compact:
            continue
        records.append(
            {
                "code_compact": compact,
                "code_dotted": compact_to_dotted(compact),
                "description_en": description,
            }
        )
    return records


def parent_compacts(compact: str) -> list[str]:
    """Return a small set of parent prefixes for API fallback lookup."""
    compact = compact.strip().upper()
    if len(compact) <= 3:
        return []

    prefixes: list[str] = []
    for length in (len(compact) - 1, len(compact) - 2, 4, 3):
        if 3 <= length < len(compact):
            prefix = compact[:length]
            if prefix not in prefixes:
                prefixes.append(prefix)
    return prefixes[:4]
