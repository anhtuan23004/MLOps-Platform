"""Release registry schema, states, and promotion gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROMOTION_STATES = ("draft", "candidate", "approved", "promoted", "retired")
ENVIRONMENTS = ("dev", "staging", "prod")

REQUIRED_DATASET_SPLITS = ("train", "val", "test")


class ReleaseError(Exception):
    """Invalid release operation or schema violation."""


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_dataset_versions(dataset_versions: Any) -> dict[str, dict[str, str]]:
    if not isinstance(dataset_versions, dict):
        raise ReleaseError("dataset_versions must be a mapping")
    missing = [split for split in REQUIRED_DATASET_SPLITS if split not in dataset_versions]
    if missing:
        raise ReleaseError(f"dataset_versions missing split(s): {', '.join(missing)}")
    normalized: dict[str, dict[str, str]] = {}
    for split, value in dataset_versions.items():
        if isinstance(value, str):
            normalized[split] = {"id": value, "checksum": ""}
        elif isinstance(value, dict):
            if "id" not in value:
                raise ReleaseError(f"dataset_versions.{split} requires id")
            normalized[split] = {
                "id": str(value["id"]),
                "checksum": str(value.get("checksum", "")),
            }
        else:
            raise ReleaseError(f"dataset_versions.{split} must be a string or mapping")
    return normalized


def new_release_record(
    *,
    release_id: str,
    name: str,
    source_artifact: str,
    dataset_versions: dict[str, Any],
    training_config_ref: str,
    created_by: str = "cli",
) -> dict[str, Any]:
    if not release_id.strip():
        raise ReleaseError("release_id is required")
    if not name.strip():
        raise ReleaseError("name is required")
    if not source_artifact.strip():
        raise ReleaseError("source_artifact is required")
    if not training_config_ref.strip():
        raise ReleaseError("training_config_ref is required")
    return {
        "release_id": release_id.strip(),
        "name": name.strip(),
        "promotion_state": "draft",
        "source_artifact": source_artifact.strip(),
        "dataset_versions": validate_dataset_versions(dataset_versions),
        "training_config_ref": training_config_ref.strip(),
        "eval_report_ref": None,
        "serving_bundle_ref": None,
        "rollback_to_release_id": None,
        "created_at": utc_now_iso(),
        "created_by": created_by,
        "approved_by": None,
    }


def require_state(record: dict[str, Any], allowed: tuple[str, ...], action: str) -> None:
    state = record.get("promotion_state")
    if state not in allowed:
        raise ReleaseError(
            f"cannot {action}: release {record.get('release_id')} is {state!r}; "
            f"expected one of {', '.join(allowed)}"
        )


def require_fields(record: dict[str, Any], fields: tuple[str, ...], action: str) -> None:
    for field in fields:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ReleaseError(f"cannot {action}: missing required field {field}")


@dataclass(frozen=True)
class PromotionGate:
    min_states: tuple[str, ...]
    required_fields: tuple[str, ...]
    require_rollback_pointer: bool = False
    require_serving_bundle: bool = False


PROMOTION_GATES: dict[str, PromotionGate] = {
    "submit": PromotionGate(
        min_states=("draft",),
        required_fields=("source_artifact", "dataset_versions", "training_config_ref"),
    ),
    "approve": PromotionGate(min_states=("candidate",), required_fields=("eval_report_ref",)),
    "dev": PromotionGate(min_states=("candidate", "approved"), required_fields=()),
    "staging": PromotionGate(
        min_states=("approved",),
        required_fields=("eval_report_ref",),
        require_rollback_pointer=True,
    ),
    "prod": PromotionGate(
        min_states=("approved",),
        required_fields=("eval_report_ref", "serving_bundle_ref"),
        require_rollback_pointer=True,
        require_serving_bundle=True,
    ),
}


def check_gate(record: dict[str, Any], gate: PromotionGate, action: str) -> None:
    require_state(record, gate.min_states, action)
    require_fields(record, gate.required_fields, action)


def new_alias(environment: str) -> dict[str, Any]:
    if environment not in ENVIRONMENTS:
        raise ReleaseError(f"unknown environment: {environment}")
    return {
        "environment": environment,
        "active_release_id": None,
        "previous_release_id": None,
        "updated_at": utc_now_iso(),
    }
