"""Prepare dataset manifest for DVC / release lineage."""

from __future__ import annotations

from pathlib import Path

from llm_local.pipeline.stages.common import PIPELINE_ROOT, hash_directory, load_params, utc_now, write_json


def main() -> int:
    params = load_params()
    dataset_cfg = params.get("dataset", {})
    source = Path(dataset_cfg.get("source", "data/raw"))
    if not source.is_absolute():
        source = PIPELINE_ROOT / source

    checksum = hash_directory(source)
    version_tag = str(dataset_cfg.get("version_tag", "v1"))
    dataset_id = f"ds-{version_tag}-{checksum[:12]}"

    manifest = {
        "dataset_id": dataset_id,
        "version_tag": version_tag,
        "source_path": str(source.relative_to(PIPELINE_ROOT)),
        "checksum_sha256": checksum,
        "prepared_at": utc_now(),
        "splits": {
            "train": {"id": f"{dataset_id}-train", "checksum": checksum},
            "val": {"id": f"{dataset_id}-val", "checksum": checksum},
            "test": {"id": f"{dataset_id}-test", "checksum": checksum},
        },
    }

    out = PIPELINE_ROOT / "data/processed/dataset_manifest.json"
    write_json(out, manifest)
    print(f"[+] Wrote {out} dataset_id={dataset_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
