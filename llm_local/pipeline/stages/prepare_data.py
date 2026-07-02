"""Validate LLM SFT JSONL splits and prepare their lineage manifest."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from llm_local.pipeline.dataset import (
    DATASET_FORMATS,
    SCHEMA_NAME,
    SCHEMA_VERSION,
    DatasetValidationError,
    read_jsonl,
)
from llm_local.pipeline.stages.common import (
    PIPELINE_ROOT,
    dry_run_from_env_or_params,
    load_params,
    sha256_file,
    utc_now,
    write_json,
)

REQUIRED_SPLITS = ("train", "val", "test")


def build_manifest(params: dict[str, Any]) -> dict[str, Any]:
    dataset_cfg = params.get("dataset", {})
    source = Path(dataset_cfg.get("source", "data/raw"))
    if not source.is_absolute():
        source = PIPELINE_ROOT / source
    source = source.resolve()

    try:
        source_ref = source.relative_to(PIPELINE_ROOT.resolve())
    except ValueError as exc:
        raise DatasetValidationError("dataset.source must be inside training/pipeline") from exc

    data_format = str(dataset_cfg.get("format", "conversation"))
    if data_format not in DATASET_FORMATS:
        raise DatasetValidationError(
            f"dataset.format must be one of {', '.join(sorted(DATASET_FORMATS))}"
        )

    configured_splits = dataset_cfg.get("splits") or {}
    missing = [split for split in REQUIRED_SPLITS if split not in configured_splits]
    if missing:
        raise DatasetValidationError(f"dataset.splits missing: {', '.join(missing)}")

    dry_run = dry_run_from_env_or_params(params)
    split_inputs: dict[str, tuple[Path, str, int]] = {}
    dataset_digest = hashlib.sha256()
    for split in REQUIRED_SPLITS:
        split_path = (source / str(configured_splits[split])).resolve()
        if not split_path.is_relative_to(source):
            raise DatasetValidationError(f"dataset split escapes source directory: {split_path}")

        if not split_path.is_file() and dry_run:
            checksum, rows = "empty", 0
        else:
            rows = len(read_jsonl(split_path, data_format))
            checksum = sha256_file(split_path)
        dataset_digest.update(f"{split}:{checksum}".encode())
        split_inputs[split] = (split_path, checksum, rows)

    version_tag = str(dataset_cfg.get("version_tag", "v1"))
    dataset_checksum = dataset_digest.hexdigest()
    dataset_id = f"ds-{version_tag}-{dataset_checksum[:12]}"

    splits: dict[str, dict[str, Any]] = {}
    for split, (split_path, checksum, rows) in split_inputs.items():
        splits[split] = {
            "id": f"{dataset_id}-{split}",
            "checksum": checksum,
            "path": str(split_path.relative_to(PIPELINE_ROOT.resolve())),
            "rows": rows,
        }

    return {
        "dataset_id": dataset_id,
        "version_tag": version_tag,
        "source_path": str(source_ref),
        "checksum_sha256": dataset_checksum,
        "prepared_at": utc_now(),
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION, "format": data_format},
        "splits": splits,
    }


def main() -> int:
    params = load_params()
    try:
        manifest = build_manifest(params)
    except DatasetValidationError as exc:
        print(f"ERROR: {exc}")
        return 1

    out = PIPELINE_ROOT / "data/processed/dataset_manifest.json"
    write_json(out, manifest)
    print(f"[+] Wrote {out} dataset_id={manifest['dataset_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
