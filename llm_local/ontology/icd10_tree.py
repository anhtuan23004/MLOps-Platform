"""ICD-10 KCB tree API client (full vocabulary crawl)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator

ICD10_API_BASE = os.getenv("ICD10_API_BASE", "https://ccs.whiteneuron.com/api")
REQUEST_TIMEOUT = float(os.getenv("ICD10_TIMEOUT", "30"))
REQUEST_DELAY = float(os.getenv("ICD10_REQUEST_DELAY", "0.08"))
MAX_ATTEMPTS = max(1, int(os.getenv("ICD10_MAX_ATTEMPTS", "6")))
RETRY_DELAY = float(os.getenv("ICD10_RETRY_DELAY", "2"))
USER_AGENT = os.getenv("ICD10_USER_AGENT", "MLOps-Platform/0.1 (icd-tree-crawler)")

EDITIONS = {
    "icd10": "ICD10",
    "tt06": "ICD10_TT06",
}


@dataclass(frozen=True)
class TreeNode:
    model: str
    node_id: str
    code: str
    name: str
    is_leaf: bool


def edition_prefix(edition: str) -> str:
    key = edition.lower()
    if key not in EDITIONS:
        raise ValueError(f"unsupported edition {edition!r}; expected icd10 or tt06")
    return EDITIONS[key]


def _request_json(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        path,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {path}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise RuntimeError(f"request failed for {path}: {exc}") from exc
    finally:
        if REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected payload type from {path}")
    return payload


def _api_url(edition: str, suffix: str, *, lang: str, **params: str) -> str:
    prefix = edition_prefix(edition)
    query = {"lang": lang, **params}
    query_string = urllib.parse.urlencode(query)
    return f"{ICD10_API_BASE}/{prefix}/{suffix}?{query_string}"


def fetch_root(edition: str, *, lang: str = "vi") -> list[TreeNode]:
    payload = _request_json(_api_url(edition, "root", lang=lang))
    return [_node_from_payload(item) for item in payload.get("data", [])]


def fetch_children(edition: str, parent_model: str, parent_id: str, *, lang: str = "vi") -> list[TreeNode]:
    payload = _request_json(
        _api_url(edition, f"childs/{parent_model}", lang=lang, id=parent_id)
    )
    return [_node_from_payload(item) for item in payload.get("data", [])]


def fetch_disease_detail(
    edition: str,
    disease_id: str,
    *,
    lang: str,
) -> dict[str, Any]:
    payload = _request_json(_api_url(edition, "data/disease", lang=lang, id=disease_id))
    data = (payload.get("data") or {}).get("data") or {}
    return {
        "id": str(data.get("id") or disease_id),
        "code": str(data.get("code") or ""),
        "name": str(data.get("name") or ""),
        "include": str(data.get("include") or ""),
        "exclude": str(data.get("exclude") or ""),
        "note": str(data.get("note") or ""),
    }


def attach_english_label(edition: str, row: dict[str, object]) -> dict[str, object]:
    """Fetch EN label for a disease row with simple retry/backoff."""
    disease_id = str(row.get("id") or "")
    if not disease_id:
        return row
    updated = dict(row)
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        try:
            detail_en = fetch_disease_detail(edition, disease_id, lang="en")
            if not detail_en.get("name"):
                raise RuntimeError(f"missing English label for {edition}:{disease_id}")
            updated["label_en"] = detail_en.get("name", "")
            updated["note_en"] = detail_en.get("note", "")
            updated.pop("fetch_error", None)
            return updated
        except RuntimeError as exc:
            last_error = str(exc)
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY * min(2**attempt, 8))
    updated["label_en"] = ""
    updated["fetch_error"] = last_error
    return updated


def _node_from_payload(item: dict[str, Any]) -> TreeNode:
    data = item.get("data") or {}
    return TreeNode(
        model=str(item.get("model") or ""),
        node_id=str(item.get("id") or data.get("id") or ""),
        code=str(data.get("code") or ""),
        name=str(data.get("name") or ""),
        is_leaf=bool(item.get("is_leaf")),
    )


def walk_diseases(edition: str, *, lang: str = "vi") -> Iterator[TreeNode]:
    """Depth-first walk; yield disease nodes from the KCB tree API."""
    for chapter in fetch_root(edition, lang=lang):
        for section in fetch_children(edition, "chapter", chapter.node_id, lang=lang):
            for type_node in fetch_children(edition, "section", section.node_id, lang=lang):
                diseases = fetch_children(edition, "type", type_node.node_id, lang=lang)
                for disease in diseases:
                    if disease.model == "disease":
                        yield disease
