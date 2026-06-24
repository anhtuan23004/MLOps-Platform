"""CLI for release registry operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ruamel.yaml import YAML

from .schema import ENVIRONMENTS, ReleaseError
from .serving import apply_release_serving, docker_available, serving_env_ready
from .store import ReleaseStore, default_registry_root

yaml = YAML()


def _parse_dataset_versions(raw: str) -> dict[str, str]:
    """Parse train=ds-1,val=ds-2,test=ds-3 style argument."""
    if not raw.strip():
        return {}
    result: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ReleaseError(f"invalid dataset split: {part!r} (expected split=id)")
        split, ds_id = part.split("=", 1)
        result[split.strip()] = ds_id.strip()
    return result


def _print_record(record: dict) -> None:
    print(yaml.dump(record))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-local release")
    parser.add_argument(
        "--registry-root",
        default=None,
        help="Override RELEASE_REGISTRY_ROOT (default: data/release-registry)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a draft release")
    create.add_argument("--id", required=True, dest="release_id")
    create.add_argument("--name", required=True)
    create.add_argument("--source", required=True, dest="source_artifact")
    create.add_argument("--datasets", required=True, help="train=id,val=id,test=id")
    create.add_argument("--config-ref", required=True, dest="training_config_ref")
    create.add_argument("--by", default="cli", dest="created_by")

    show = sub.add_parser("show", help="Show one release")
    show.add_argument("release_id")

    list_cmd = sub.add_parser("list", help="List releases")
    list_cmd.add_argument("--state", default=None)

    attach = sub.add_parser("attach-eval", help="Attach evaluation report reference")
    attach.add_argument("release_id")
    attach.add_argument("--ref", required=True, dest="eval_report_ref")
    attach.add_argument("--metrics-json", default=None, help="Path to metrics JSON file")

    sub.add_parser("submit", help="draft -> candidate").add_argument("release_id")
    approve = sub.add_parser("approve", help="candidate -> approved")
    approve.add_argument("release_id")
    approve.add_argument("--by", default="cli", dest="approved_by")

    promote = sub.add_parser("promote", help="Promote release to an environment")
    promote.add_argument("release_id")
    promote.add_argument("--to", required=True, choices=ENVIRONMENTS, dest="environment")
    promote.add_argument(
        "--apply-serving",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Switch vLLM to release model (default: true when Docker available)",
    )
    promote.add_argument("--no-restart", action="store_true", help="Do not restart vLLM container")

    rollback = sub.add_parser("rollback", help="Rollback environment alias")
    rollback.add_argument("--env", required=True, choices=ENVIRONMENTS, dest="environment")
    rollback.add_argument(
        "--apply-serving",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    rollback.add_argument("--no-restart", action="store_true")

    sub.add_parser("validate", help="Validate registry files")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.registry_root).expanduser() if args.registry_root else default_registry_root()
    store = ReleaseStore(root)

    try:
        if args.command == "create":
            record = store.create_release(
                release_id=args.release_id,
                name=args.name,
                source_artifact=args.source_artifact,
                dataset_versions=_parse_dataset_versions(args.datasets),
                training_config_ref=args.training_config_ref,
                created_by=args.created_by,
            )
            _print_record(record)
            return 0

        if args.command == "show":
            _print_record(store.get_release(args.release_id))
            return 0

        if args.command == "list":
            records = store.list_releases(state=args.state)
            if not records:
                print("No releases found.")
                return 0
            for record in records:
                rid = record.get("release_id", "?")
                state = record.get("promotion_state", "?")
                name = record.get("name", "?")
                print(f"{rid:30s} {state:12s} {name}")
            return 0

        if args.command == "attach-eval":
            metrics = None
            if args.metrics_json:
                metrics = json.loads(Path(args.metrics_json).read_text())
            record = store.attach_eval(
                args.release_id,
                eval_report_ref=args.eval_report_ref,
                metrics=metrics,
            )
            _print_record(record)
            return 0

        if args.command == "submit":
            _print_record(store.submit(args.release_id))
            return 0

        if args.command == "approve":
            _print_record(store.approve(args.release_id, approved_by=args.approved_by))
            return 0

        if args.command == "promote":
            record, alias = store.promote(args.release_id, environment=args.environment)
            apply_serving = args.apply_serving and docker_available() and serving_env_ready()
            if args.apply_serving and not apply_serving:
                print("[!] Skipping serving apply (Docker unavailable or serving not configured)")
            elif apply_serving:
                apply_release_serving(record, restart=not args.no_restart)
                print(f"[+] Applied serving for {record['source_artifact']}")
            print(f"[+] Promoted {args.release_id} to {args.environment}")
            print(f"    active={alias.get('active_release_id')} previous={alias.get('previous_release_id')}")
            return 0

        if args.command == "rollback":
            record, alias = store.rollback(environment=args.environment)
            apply_serving = args.apply_serving and docker_available() and serving_env_ready()
            if args.apply_serving and not apply_serving:
                print("[!] Skipping serving apply (Docker unavailable or serving not configured)")
            elif apply_serving:
                apply_release_serving(record, restart=not args.no_restart)
                print(f"[+] Applied serving for {record['source_artifact']}")
            print(f"[+] Rolled back {args.environment}")
            print(f"    active={alias.get('active_release_id')} previous={alias.get('previous_release_id')}")
            return 0

        if args.command == "validate":
            errors = store.validate()
            if errors:
                for error in errors:
                    print(f"ERROR: {error}")
                return 1
            print(f"[+] Release registry valid at {store.root}")
            return 0

    except ReleaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
