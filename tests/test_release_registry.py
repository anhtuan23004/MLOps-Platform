"""Tests for release registry store and promotion gates."""

from __future__ import annotations

import pytest

from llm_local.releases.schema import ReleaseError
from llm_local.releases.store import ReleaseStore


def _datasets() -> dict[str, str]:
    return {"train": "ds-train", "val": "ds-val", "test": "ds-test"}


def _create_draft(store: ReleaseStore, release_id: str, *, source: str = "model-a") -> dict:
    return store.create_release(
        release_id=release_id,
        name=f"Release {release_id}",
        source_artifact=source,
        dataset_versions=_datasets(),
        training_config_ref="training/unsloth/configs/README.md",
    )


def test_create_and_submit(tmp_path):
    store = ReleaseStore(tmp_path)
    record = _create_draft(store, "rel-001")
    assert record["promotion_state"] == "draft"

    submitted = store.submit("rel-001")
    assert submitted["promotion_state"] == "candidate"


def test_approve_requires_eval(tmp_path):
    store = ReleaseStore(tmp_path)
    _create_draft(store, "rel-002")
    store.submit("rel-002")

    with pytest.raises(ReleaseError, match="eval_report_ref"):
        store.approve("rel-002")

    store.attach_eval("rel-002", eval_report_ref="evaluation/results/report.json")
    approved = store.approve("rel-002")
    assert approved["promotion_state"] == "approved"


def test_promote_dev_and_rollback(tmp_path):
    store = ReleaseStore(tmp_path)
    _create_draft(store, "rel-a", source="model-a")
    store.submit("rel-a")
    store.attach_eval("rel-a", eval_report_ref="evaluation/results/a.json")
    store.approve("rel-a")
    store.promote("rel-a", environment="dev")

    _create_draft(store, "rel-b", source="model-b")
    store.submit("rel-b")
    store.attach_eval("rel-b", eval_report_ref="evaluation/results/b.json")
    store.approve("rel-b")
    record_b, alias = store.promote("rel-b", environment="dev")

    assert alias["active_release_id"] == "rel-b"
    assert alias["previous_release_id"] == "rel-a"
    assert record_b["rollback_to_release_id"] == "rel-a"

    rolled, alias_after = store.rollback(environment="dev")
    assert rolled["release_id"] == "rel-a"
    assert alias_after["active_release_id"] == "rel-a"
    assert alias_after["previous_release_id"] == "rel-b"


def test_staging_requires_prior_active(tmp_path):
    store = ReleaseStore(tmp_path)
    _create_draft(store, "rel-stg")
    store.submit("rel-stg")
    store.attach_eval("rel-stg", eval_report_ref="evaluation/results/stg.json")
    store.approve("rel-stg")

    with pytest.raises(ReleaseError, match="previous_release_id"):
        store.promote("rel-stg", environment="staging")


def test_validate_clean_registry(tmp_path):
    store = ReleaseStore(tmp_path)
    _create_draft(store, "rel-val")
    assert store.validate() == []
