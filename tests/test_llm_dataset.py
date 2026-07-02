"""Contract tests for manifest-backed LLM SFT datasets."""

from __future__ import annotations

import json

import pytest

from llm_local.pipeline.dataset import DatasetValidationError, load_manifest_split, read_jsonl
from llm_local.pipeline.stages import prepare_data


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _conversation_row() -> dict:
    return {
        "messages": [
            {"role": "user", "content": "What is MLOps?"},
            {"role": "assistant", "content": "MLOps operationalizes the model lifecycle."},
        ]
    }


def test_conversation_manifest_loads_declared_train_split(tmp_path, monkeypatch):
    row = _conversation_row()
    raw = tmp_path / "data/raw"
    for split in ("train", "val", "test"):
        _write_jsonl(raw / f"{split}.jsonl", [row])

    monkeypatch.setattr(prepare_data, "PIPELINE_ROOT", tmp_path)
    manifest = prepare_data.build_manifest(
        {
            "dataset": {
                "source": "data/raw",
                "version_tag": "v1.0.0",
                "format": "conversation",
                "splits": {
                    "train": "train.jsonl",
                    "val": "val.jsonl",
                    "test": "test.jsonl",
                },
            },
            "train": {"dry_run": False},
        }
    )
    manifest_path = tmp_path / "data/processed/dataset_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest))

    data_format, records = load_manifest_split(
        manifest_path, pipeline_root=tmp_path, split="train"
    )

    assert data_format == "conversation"
    assert records == [row]
    assert manifest["splits"]["train"]["rows"] == 1


def test_text_schema_accepts_non_empty_text(tmp_path):
    path = tmp_path / "train.jsonl"
    _write_jsonl(path, [{"text": "A complete supervised fine-tuning sample."}])

    assert read_jsonl(path, "text")[0]["text"].startswith("A complete")


def test_conversation_schema_rejects_missing_assistant(tmp_path):
    path = tmp_path / "train.jsonl"
    _write_jsonl(path, [{"messages": [{"role": "user", "content": "Hello"}]}])

    with pytest.raises(DatasetValidationError, match="must end with assistant"):
        read_jsonl(path, "conversation")


def test_manifest_loader_rejects_changed_data(tmp_path, monkeypatch):
    row = {"text": "original"}
    raw = tmp_path / "data/raw"
    for split in ("train", "val", "test"):
        _write_jsonl(raw / f"{split}.jsonl", [row])
    monkeypatch.setattr(prepare_data, "PIPELINE_ROOT", tmp_path)
    manifest = prepare_data.build_manifest(
        {
            "dataset": {
                "source": "data/raw",
                "format": "text",
                "splits": {split: f"{split}.jsonl" for split in ("train", "val", "test")},
            },
            "train": {"dry_run": False},
        }
    )
    manifest_path = tmp_path / "data/processed/dataset_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest))
    _write_jsonl(raw / "train.jsonl", [{"text": "changed"}])

    with pytest.raises(DatasetValidationError, match="checksum changed"):
        load_manifest_split(manifest_path, pipeline_root=tmp_path)


def test_build_manifest_allows_missing_splits_in_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare_data, "PIPELINE_ROOT", tmp_path)
    manifest = prepare_data.build_manifest(
        {
            "dataset": {
                "source": "data/raw",
                "format": "conversation",
                "splits": {
                    "train": "train.jsonl",
                    "val": "val.jsonl",
                    "test": "test.jsonl",
                },
            },
            "train": {"dry_run": True},
        }
    )
    assert manifest["schema"]["format"] == "conversation"
    assert manifest["splits"]["train"]["rows"] == 0
    assert manifest["splits"]["train"]["checksum"] == "empty"
