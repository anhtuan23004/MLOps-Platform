"""Offline tests for ICD tree crawling and enrichment."""

import http.client
import json
import urllib.error

import pytest

from llm_local.ontology import icd10_tree
from llm_local.ontology.icd10_tree import TreeNode, attach_english_label, edition_prefix
from scripts import crawl_icd10_vn_full


def test_edition_prefix():
    assert edition_prefix("tt06") == "ICD10_TT06"
    assert edition_prefix("icd10") == "ICD10"


def test_tree_node_shape():
    node = TreeNode(model="disease", node_id="A000", code="A00.0", name="Bệnh tả", is_leaf=True)
    assert node.code == "A00.0"


def test_request_json_normalizes_url_error(monkeypatch):
    def fail(*_args, **_kwargs):
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(icd10_tree.urllib.request, "urlopen", fail)
    monkeypatch.setattr(icd10_tree.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="connection reset"):
        icd10_tree._request_json("https://example.test")


def test_request_json_normalizes_remote_disconnect(monkeypatch):
    def fail(*_args, **_kwargs):
        raise http.client.RemoteDisconnected("remote closed connection")

    monkeypatch.setattr(icd10_tree.urllib.request, "urlopen", fail)
    monkeypatch.setattr(icd10_tree.time, "sleep", lambda _seconds: None)

    with pytest.raises(RuntimeError, match="remote closed connection"):
        icd10_tree._request_json("https://example.test")


def test_attach_english_label_retries_transient_error(monkeypatch):
    calls = 0

    def fetch(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls < 4:
            raise RuntimeError("HTTP 400")
        return {"name": "Salmonella sepsis", "note": ""}

    monkeypatch.setattr(icd10_tree, "fetch_disease_detail", fetch)
    monkeypatch.setattr(icd10_tree.time, "sleep", lambda _seconds: None)

    result = attach_english_label("icd10", {"id": "A021", "code": "A02.1"})

    assert calls == 4
    assert result["label_en"] == "Salmonella sepsis"
    assert "fetch_error" not in result


def test_enrich_resume_repairs_failed_rows_without_duplicates(tmp_path, monkeypatch):
    vi_rows = [
        {"edition": "tt06", "id": "A000", "code": "A00.0", "label_vi": "Bệnh tả"},
        {"edition": "tt06", "id": "A021", "code": "A02.1", "label_vi": "Nhiễm khuẩn huyết"},
    ]
    bilingual_rows = [
        {**vi_rows[0], "label_en": "Cholera"},
        {**vi_rows[1], "label_en": "", "fetch_error": "HTTP 400"},
    ]
    vi_file = tmp_path / "icd10-tt06-vi.jsonl"
    bilingual_file = tmp_path / "icd10-tt06-bilingual.jsonl"
    vi_file.write_text("".join(json.dumps(row) + "\n" for row in vi_rows))
    bilingual_file.write_text("".join(json.dumps(row) + "\n" for row in bilingual_rows))

    monkeypatch.setattr(crawl_icd10_vn_full, "ROOT", tmp_path)
    monkeypatch.setattr(
        crawl_icd10_vn_full,
        "attach_english_label",
        lambda _edition, row: {**row, "label_en": "Salmonella sepsis"},
    )

    assert crawl_icd10_vn_full.main(
        ["--edition", "tt06", "--out-dir", str(tmp_path), "--enrich-en", "--resume"]
    ) == 0

    result = [json.loads(line) for line in bilingual_file.read_text().splitlines()]
    assert len(result) == 2
    assert result[0]["label_en"] == "Cholera"
    assert result[1]["label_en"] == "Salmonella sepsis"
    assert "fetch_error" not in result[1]

    checkpoint = bilingual_file.with_suffix(bilingual_file.suffix + ".tmp")
    checkpoint.write_text(bilingual_file.read_text())
    bilingual_file.write_text("".join(json.dumps(row) + "\n" for row in bilingual_rows))
    monkeypatch.setattr(
        crawl_icd10_vn_full,
        "attach_english_label",
        lambda *_args: (_ for _ in ()).throw(AssertionError("checkpoint was ignored")),
    )

    assert crawl_icd10_vn_full.main(
        ["--edition", "tt06", "--out-dir", str(tmp_path), "--enrich-en", "--resume"]
    ) == 0
