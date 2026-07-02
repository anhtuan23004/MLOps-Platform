"""Validation and loading for manifest-backed LLM SFT datasets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_NAME = "llm-sft-jsonl"
SCHEMA_VERSION = 1
DATASET_FORMATS = {"text", "conversation"}
MESSAGE_ROLES = {"system", "user", "assistant"}


class DatasetValidationError(ValueError):
    """Raised when dataset content or lineage metadata is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_record(record: Any, data_format: str, *, source: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise DatasetValidationError(f"{source}: record must be a JSON object")

    if data_format == "text":
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            raise DatasetValidationError(f"{source}: text record requires non-empty 'text'")
        return record

    if data_format != "conversation":
        raise DatasetValidationError(
            f"{source}: unsupported format {data_format!r}; expected text or conversation"
        )

    messages = record.get("messages")
    if not isinstance(messages, list) or not messages:
        raise DatasetValidationError(f"{source}: conversation requires non-empty 'messages'")

    roles: list[str] = []
    for index, message in enumerate(messages, start=1):
        location = f"{source}.messages[{index}]"
        if not isinstance(message, dict):
            raise DatasetValidationError(f"{location}: message must be a JSON object")
        role = message.get("role")
        content = message.get("content")
        if role not in MESSAGE_ROLES:
            raise DatasetValidationError(
                f"{location}: role must be one of {', '.join(sorted(MESSAGE_ROLES))}"
            )
        if not isinstance(content, str) or not content.strip():
            raise DatasetValidationError(f"{location}: content must be a non-empty string")
        roles.append(role)

    if "user" not in roles or "assistant" not in roles or roles[-1] != "assistant":
        raise DatasetValidationError(
            f"{source}: conversation requires user and assistant messages and must end with assistant"
        )
    return record


def read_jsonl(path: Path, data_format: str) -> list[dict[str, Any]]:
    if data_format not in DATASET_FORMATS:
        raise DatasetValidationError(
            f"unsupported dataset format {data_format!r}; expected text or conversation"
        )
    if not path.is_file():
        raise DatasetValidationError(f"dataset split not found: {path}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        records.append(validate_record(record, data_format, source=f"{path}:{line_number}"))

    if not records:
        raise DatasetValidationError(f"dataset split is empty: {path}")
    return records


def load_manifest_split(
    manifest_path: Path,
    *,
    pipeline_root: Path,
    split: str = "train",
) -> tuple[str, list[dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text())
    schema = manifest.get("schema") or {}
    if schema.get("name") != SCHEMA_NAME or schema.get("version") != SCHEMA_VERSION:
        raise DatasetValidationError(
            f"unsupported dataset schema: expected {SCHEMA_NAME} v{SCHEMA_VERSION}"
        )

    data_format = str(schema.get("format", ""))
    split_meta = (manifest.get("splits") or {}).get(split)
    if not isinstance(split_meta, dict) or not split_meta.get("path"):
        raise DatasetValidationError(f"manifest does not define split {split!r}")

    root = pipeline_root.resolve()
    split_path = (root / str(split_meta["path"])).resolve()
    if not split_path.is_relative_to(root):
        raise DatasetValidationError(f"split path escapes pipeline root: {split_meta['path']}")

    records = read_jsonl(split_path, data_format)
    if len(records) != split_meta.get("rows"):
        raise DatasetValidationError(f"row count changed for split {split!r}: {split_path}")
    if _sha256(split_path) != split_meta.get("checksum"):
        raise DatasetValidationError(f"checksum changed for split {split!r}: {split_path}")
    return data_format, records
