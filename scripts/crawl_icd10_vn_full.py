#!/usr/bin/env python3
"""Crawl the full Vietnamese ICD tree from the KCB / White Neuron API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llm_local.catalog import ROOT
from llm_local.ontology.icd10_tree import (
    EDITIONS,
    attach_english_label,
    walk_diseases,
)

DEFAULT_OUT_DIR = ROOT / "data" / "ontology" / "icd10-vn"


def load_seen(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    seen: set[str] = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        seen.add(str(row.get("id") or row.get("code")))
    return seen


def load_rows(path: Path) -> dict[str, dict[str, object]]:
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, object]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row.get("id") or row.get("code"))] = row
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--edition",
        choices=sorted(EDITIONS),
        default="tt06",
        help="KCB edition prefix (default: tt06 = Thông tư 06 / dual UI)",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--bilingual",
        action="store_true",
        help="Fetch label_en per disease during tree walk (writes bilingual jsonl)",
    )
    parser.add_argument(
        "--enrich-en",
        action="store_true",
        help="Read vi jsonl and append label_en to bilingual jsonl (no tree re-walk)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip disease ids already present in the output jsonl",
    )
    parser.add_argument("--max", type=int, default=0, help="Stop after N diseases (0 = all)")
    args = parser.parse_args(argv)
    if args.bilingual and args.enrich_en:
        parser.error("--bilingual and --enrich-en are mutually exclusive")

    out_dir = (ROOT / args.out_dir).resolve() if not args.out_dir.is_absolute() else args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    vi_file = out_dir / f"icd10-{args.edition}-vi.jsonl"
    bilingual_file = out_dir / f"icd10-{args.edition}-bilingual.jsonl"
    if args.enrich_en:
        out_file = bilingual_file
    elif args.bilingual:
        out_file = bilingual_file
    else:
        out_file = vi_file

    if args.enrich_en:
        if not vi_file.is_file():
            print(f"missing vi crawl output: {vi_file}", file=sys.stderr)
            return 1
        write_path = out_file.with_suffix(out_file.suffix + ".tmp") if args.resume else out_file
        existing = load_rows(out_file) if args.resume else {}
        if args.resume and write_path.is_file():
            existing.update(load_rows(write_path))
        written = 0
        skipped = 0
        errors = 0
        repaired = 0
        with write_path.open("w") as handle:
            for line in vi_file.read_text().splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                row_id = str(row.get("id") or row.get("code"))
                previous = existing.get(row_id)
                if previous and previous.get("label_en") and not previous.get("fetch_error"):
                    enriched = previous
                    skipped += 1
                else:
                    enriched = attach_english_label(args.edition, row)
                    written += 1
                    if previous and previous.get("fetch_error") and not enriched.get("fetch_error"):
                        repaired += 1
                    if written % 100 == 0:
                        print(f"[+] enriched {written} ({row.get('code')})", file=sys.stderr)
                if enriched.get("fetch_error"):
                    errors += 1
                handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                handle.flush()
        if args.resume:
            write_path.replace(out_file)
        report = {
            "edition": args.edition,
            "input": str(vi_file.relative_to(ROOT)),
            "output": str(out_file.relative_to(ROOT)),
            "written": written,
            "skipped": skipped,
            "repaired": repaired,
            "errors": errors,
            "mode": "enrich-en",
        }
        (out_dir / f"crawl-full-{args.edition}-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    seen = load_seen(out_file) if args.resume else set()

    written = 0
    skipped = 0
    errors = 0

    with out_file.open("a" if args.resume else "w") as handle:
        for disease in walk_diseases(args.edition, lang="vi"):
            if disease.node_id in seen or disease.code in seen:
                skipped += 1
                if skipped % 500 == 0:
                    print(
                        f"[~] skipped {skipped}, written {written} ({disease.code})",
                        file=sys.stderr,
                    )
                continue
            row: dict[str, object] = {
                "edition": args.edition,
                "id": disease.node_id,
                "code": disease.code,
                "label_vi": disease.name,
            }
            if args.bilingual:
                row = attach_english_label(args.edition, row)
                if row.get("fetch_error"):
                    errors += 1

            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            seen.add(disease.node_id)
            written += 1

            if written % 100 == 0:
                print(f"[+] {written} diseases written ({disease.code})", file=sys.stderr)

            if args.max and written >= args.max:
                break

    report = {
        "edition": args.edition,
        "output": str(out_file.relative_to(ROOT)),
        "written": written,
        "skipped": skipped,
        "errors": errors,
        "mode": "tree-bilingual" if args.bilingual else "tree-vi",
    }
    (out_dir / f"crawl-full-{args.edition}-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
