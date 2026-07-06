#!/usr/bin/env python3
"""Fetch a compact, pinned RxNorm concept snapshot from the official RxNav API."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from llm_local.catalog import ROOT

API_BASE = "https://rxnav.nlm.nih.gov/REST"
DEFAULT_TYPES = ("IN", "MIN", "PIN", "BN", "SCD", "SBD")


def fetch_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "MLOps-Platform/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="01-Jun-2026")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/ontology/rxnorm/2026-06-01/rxnorm-concepts.jsonl",
    )
    parser.add_argument("--term-types", nargs="+", default=list(DEFAULT_TYPES))
    args = parser.parse_args(argv)

    version_payload = fetch_json(f"{API_BASE}/version.json")
    actual_version = str(version_payload.get("version", ""))
    if actual_version != args.version:
        raise RuntimeError(
            f"RxNorm API version changed: expected {args.version}, got {actual_version}; "
            "select a new snapshot path explicitly"
        )

    query = urllib.parse.urlencode({"tty": " ".join(args.term_types)})
    payload = fetch_json(f"{API_BASE}/allconcepts.json?{query}")
    rows = payload.get("minConceptGroup", {}).get("minConcept", [])  # type: ignore[union-attr]
    unique = {
        (str(row["rxcui"]), str(row["name"]), str(row["tty"]))
        for row in rows
        if row.get("rxcui") and row.get("name") and row.get("tty")
    }

    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w") as handle:
        for rxcui, name, tty in sorted(unique, key=lambda row: (row[1].casefold(), row[0], row[2])):
            handle.write(json.dumps({"rxcui": rxcui, "name": name, "tty": tty}) + "\n")
    temporary.replace(output)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata = {
        "source": f"{API_BASE}/allconcepts.json",
        "version": actual_version,
        "api_version": version_payload.get("apiVersion"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "term_types": args.term_types,
        "records": len(unique),
        "sha256": digest,
        "license": "RxNorm normalized names and RXCUIs returned by RxNorm API; NLM public domain",
    }
    output.with_name("snapshot.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
