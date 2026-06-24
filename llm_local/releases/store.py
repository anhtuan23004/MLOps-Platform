"""File-backed release registry store."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from llm_local.catalog import ROOT

from .schema import (
    ENVIRONMENTS,
    PROMOTION_GATES,
    ReleaseError,
    check_gate,
    new_alias,
    new_release_record,
    utc_now_iso,
    validate_dataset_versions,
)

yaml = YAML()
yaml.default_flow_style = False


def default_registry_root() -> Path:
    env = os.environ.get("RELEASE_REGISTRY_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return ROOT / "data" / "release-registry"


class ReleaseStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_registry_root()).resolve()
        self.releases_dir = self.root / "releases"
        self.aliases_dir = self.root / "aliases"
        self.audit_path = self.root / "audit" / "events.jsonl"

    def ensure_layout(self) -> None:
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.aliases_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        for environment in ENVIRONMENTS:
            alias_path = self.aliases_dir / f"{environment}.yaml"
            if not alias_path.exists():
                self._write_yaml(alias_path, new_alias(environment))

    def _release_path(self, release_id: str) -> Path:
        return self.releases_dir / f"{release_id}.yaml"

    def _alias_path(self, environment: str) -> Path:
        return self.aliases_dir / f"{environment}.yaml"

    @staticmethod
    def _write_yaml(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as handle:
            yaml.dump(data, handle)

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ReleaseError(f"not found: {path}")
        with path.open() as handle:
            data = yaml.load(handle) or {}
        if not isinstance(data, dict):
            raise ReleaseError(f"invalid YAML mapping: {path}")
        return data

    def audit(self, event: str, **fields: Any) -> None:
        payload = {"ts": utc_now_iso(), "event": event, **fields}
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def create_release(
        self,
        *,
        release_id: str,
        name: str,
        source_artifact: str,
        dataset_versions: dict[str, Any],
        training_config_ref: str,
        created_by: str = "cli",
    ) -> dict[str, Any]:
        self.ensure_layout()
        path = self._release_path(release_id)
        if path.exists():
            raise ReleaseError(f"release already exists: {release_id}")
        record = new_release_record(
            release_id=release_id,
            name=name,
            source_artifact=source_artifact,
            dataset_versions=dataset_versions,
            training_config_ref=training_config_ref,
            created_by=created_by,
        )
        self._write_yaml(path, record)
        self.audit("release_created", release_id=release_id)
        return record

    def get_release(self, release_id: str) -> dict[str, Any]:
        return self._read_yaml(self._release_path(release_id))

    def save_release(self, record: dict[str, Any]) -> None:
        release_id = record.get("release_id")
        if not release_id:
            raise ReleaseError("release record missing release_id")
        self._write_yaml(self._release_path(str(release_id)), record)

    def list_releases(self, state: str | None = None) -> list[dict[str, Any]]:
        self.ensure_layout()
        records: list[dict[str, Any]] = []
        for path in sorted(self.releases_dir.glob("*.yaml")):
            record = self._read_yaml(path)
            if state is None or record.get("promotion_state") == state:
                records.append(record)
        return records

    def attach_eval(self, release_id: str, *, eval_report_ref: str, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self.get_release(release_id)
        if not eval_report_ref.strip():
            raise ReleaseError("eval_report_ref is required")
        record["eval_report_ref"] = eval_report_ref.strip()
        if metrics is not None:
            record["eval_metrics"] = metrics
        self.save_release(record)
        self.audit("eval_attached", release_id=release_id, eval_report_ref=eval_report_ref)
        return record

    def submit(self, release_id: str) -> dict[str, Any]:
        record = self.get_release(release_id)
        check_gate(record, PROMOTION_GATES["submit"], "submit")
        record["promotion_state"] = "candidate"
        self.save_release(record)
        self.audit("submitted", release_id=release_id)
        return record

    def approve(self, release_id: str, *, approved_by: str = "cli") -> dict[str, Any]:
        record = self.get_release(release_id)
        check_gate(record, PROMOTION_GATES["approve"], "approve")
        record["promotion_state"] = "approved"
        record["approved_by"] = approved_by
        self.save_release(record)
        self.audit("approved", release_id=release_id, approved_by=approved_by)
        return record

    def get_alias(self, environment: str) -> dict[str, Any]:
        self.ensure_layout()
        return self._read_yaml(self._alias_path(environment))

    def save_alias(self, alias: dict[str, Any]) -> None:
        environment = alias.get("environment")
        if environment not in ENVIRONMENTS:
            raise ReleaseError(f"invalid alias environment: {environment}")
        alias["updated_at"] = utc_now_iso()
        self._write_yaml(self._alias_path(str(environment)), alias)

    def promote(self, release_id: str, *, environment: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if environment not in PROMOTION_GATES:
            raise ReleaseError(f"unknown promotion environment: {environment}")
        record = self.get_release(release_id)
        gate = PROMOTION_GATES[environment]
        check_gate(record, gate, f"promote to {environment}")

        alias = self.get_alias(environment)
        previous = alias.get("active_release_id")

        if gate.require_rollback_pointer and not previous and not alias.get("previous_release_id"):
            raise ReleaseError(
                f"cannot promote to {environment}: no previous_release_id on alias "
                "(promote once to establish rollback target, or set previous manually)"
            )

        if previous and previous != release_id:
            alias["previous_release_id"] = previous
            record["rollback_to_release_id"] = previous

        alias["active_release_id"] = release_id
        record["promotion_state"] = "promoted"
        self.save_alias(alias)
        self.save_release(record)
        self.audit(
            "promoted",
            release_id=release_id,
            environment=environment,
            previous_release_id=alias.get("previous_release_id"),
        )
        return record, alias

    def rollback(self, *, environment: str) -> tuple[dict[str, Any], dict[str, Any]]:
        alias = self.get_alias(environment)
        previous_id = alias.get("previous_release_id")
        if not previous_id:
            raise ReleaseError(f"cannot rollback {environment}: previous_release_id is not set")

        current_id = alias.get("active_release_id")
        alias["active_release_id"] = previous_id
        alias["previous_release_id"] = current_id
        self.save_alias(alias)

        record = self.get_release(previous_id)
        record["promotion_state"] = "promoted"
        self.save_release(record)
        self.audit(
            "rolled_back",
            environment=environment,
            active_release_id=previous_id,
            previous_release_id=current_id,
        )
        return record, alias

    def validate(self) -> list[str]:
        """Return list of validation errors (empty if valid)."""
        errors: list[str] = []
        try:
            self.ensure_layout()
        except OSError as exc:
            return [str(exc)]

        for path in self.releases_dir.glob("*.yaml"):
            try:
                record = self._read_yaml(path)
                if not record.get("release_id"):
                    errors.append(f"{path}: missing release_id")
                if record.get("promotion_state") not in {"draft", "candidate", "approved", "promoted", "retired"}:
                    errors.append(f"{path}: invalid promotion_state")
                if record.get("dataset_versions"):
                    validate_dataset_versions(record["dataset_versions"])
            except ReleaseError as exc:
                errors.append(f"{path}: {exc}")

        for environment in ENVIRONMENTS:
            alias_path = self._alias_path(environment)
            if not alias_path.exists():
                errors.append(f"{alias_path}: missing alias file")
                continue
            alias = self._read_yaml(alias_path)
            active = alias.get("active_release_id")
            if active:
                release_path = self._release_path(str(active))
                if not release_path.exists():
                    errors.append(f"{environment}: active_release_id {active} not found")

        return errors
