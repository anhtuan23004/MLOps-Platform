"""Medical concept extraction system prompt (prose + structural JSON Schema)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from llm_local.config_paths import config_path

SYSTEM_SUFFIX = "\n\nJSON Schema: "


@lru_cache(maxsize=1)
def medical_extraction_system_path() -> Path:
    return config_path("medical_extraction_system")


@lru_cache(maxsize=1)
def medical_extraction_schema_path() -> Path:
    return config_path("medical_extraction_schema")


@lru_cache(maxsize=1)
def load_medical_extraction_schema() -> dict:
    return json.loads(medical_extraction_schema_path().read_text())


def medical_extraction_schema_json(*, compact: bool = True) -> str:
    schema = load_medical_extraction_schema()
    if compact:
        return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(schema, ensure_ascii=False, indent=2)


def build_medical_extraction_system_prompt() -> str:
    prose = medical_extraction_system_path().read_text().rstrip()
    if prose.endswith("JSON Schema:"):
        return f"{prose} {medical_extraction_schema_json()}"
    return f"{prose}{SYSTEM_SUFFIX}{medical_extraction_schema_json()}"
