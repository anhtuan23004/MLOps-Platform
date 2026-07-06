"""Deterministic span and ontology enrichment for medical predictions."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

DIAGNOSIS = "CHẨN_ĐOÁN"
DRUG = "THUỐC"
ALLOWED_TYPES = {
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    DIAGNOSIS,
    DRUG,
}
ALLOWED_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}
ASSERTION_TYPES = {"TRIỆU_CHỨNG", DIAGNOSIS, DRUG}
FINAL_FIELDS = {"text", "type", "position", "assertions", "candidates"}


def normalize_term(value: str) -> str:
    value = value.casefold().replace("đ", "d")
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    value = re.sub(r"\b(?:type|typ)\b", "tip", value)
    return " ".join(re.findall(r"[a-z0-9]+", value))


def query_variants(value: str) -> list[str]:
    variants = [normalize_term(value)]
    before_dose = normalize_term(re.split(r"\s+\d", value, maxsplit=1)[0])
    if before_dose and before_dose not in variants:
        variants.append(before_dose)
    return variants


@dataclass(frozen=True)
class Term:
    identifier: str
    name: str
    kind: str = ""
    priority: float = 0.0


class TerminologyIndex:
    def __init__(self, terms: Iterable[Term], *, aliases: dict[str, list[str]] | None = None):
        self.terms = list(terms)
        self._aliases: list[list[str]] = []
        self._exact: dict[str, list[int]] = defaultdict(list)
        self._by_token: dict[str, set[int]] = defaultdict(set)
        aliases = aliases or {}
        for index, term in enumerate(self.terms):
            normalized_aliases = {normalize_term(term.name)}
            normalized_aliases.update(normalize_term(alias) for alias in aliases.get(term.identifier, []))
            normalized_aliases.discard("")
            ordered = sorted(normalized_aliases)
            self._aliases.append(ordered)
            for alias in ordered:
                self._exact[alias].append(index)
                for token in alias.split():
                    self._by_token[token].add(index)

    def lookup(self, value: str, *, limit: int = 5) -> list[str]:
        queries = query_variants(value)
        scores: dict[int, float] = {}
        for query in queries:
            for index in self._exact.get(query, []):
                scores[index] = max(
                    scores.get(index, 0.0),
                    100.0 + self.terms[index].priority,
                )

            query_tokens = set(query.split())
            pool: set[int] = set()
            for token in query_tokens:
                pool.update(self._by_token.get(token, set()))
            for index in pool:
                score = max(self._score(query, alias) for alias in self._aliases[index])
                score += self.terms[index].priority
                if score >= 2.0:
                    scores[index] = max(scores.get(index, 0.0), score)

        ranked = sorted(
            scores,
            key=lambda index: (
                -scores[index],
                0 if len(self.terms[index].identifier) == 3 else 1,
                len(normalize_term(self.terms[index].name)),
                self.terms[index].identifier,
            ),
        )
        result: list[str] = []
        for index in ranked:
            identifier = self.terms[index].identifier
            if identifier not in result:
                result.append(identifier)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _score(query: str, alias: str) -> float:
        query_tokens = set(query.split())
        alias_tokens = set(alias.split())
        overlap = query_tokens & alias_tokens
        if not query_tokens or not overlap:
            return 0.0
        coverage = len(overlap) / len(query_tokens)
        precision = len(overlap) / len(alias_tokens)
        containment = 1.0 if query in alias or alias in query else 0.0
        similarity = SequenceMatcher(None, query, alias).ratio()
        return 2.0 * coverage + precision + containment + 0.5 * similarity


def load_icd10(path: Path) -> TerminologyIndex:
    terms: list[Term] = []
    aliases: dict[str, list[str]] = defaultdict(list)
    for row in _read_jsonl(path):
        code_match = re.match(r"[A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?", str(row.get("code", "")))
        if not code_match or not row.get("label_vi"):
            continue
        code = code_match.group(0)
        label = str(row["label_vi"])
        terms.append(Term(code, label, priority=0.5 if "." not in code else 0.0))
        aliases[code].extend(re.findall(r"\[([^]]+)\]", label))
        aliases[code].append(re.sub(r"\[[^]]+\]", " ", label))
    return TerminologyIndex(terms, aliases=aliases)


def load_rxnorm(path: Path) -> TerminologyIndex:
    priorities = {"IN": 0.4, "PIN": 0.3, "MIN": 0.2, "BN": 0.1}
    terms = [
        Term(
            str(row["rxcui"]),
            str(row["name"]),
            str(row.get("tty", "")),
            priorities.get(str(row.get("tty", "")), 0.0),
        )
        for row in _read_jsonl(path)
        if row.get("rxcui") and row.get("name")
    ]
    return TerminologyIndex(terms)


def enrich_entities(
    source: str,
    entities: list[dict[str, object]],
    *,
    icd10: TerminologyIndex,
    rxnorm: TerminologyIndex,
    candidate_limit: int = 5,
) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    cursor = 0
    for index, entity in enumerate(entities):
        text = entity.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"entity {index}: text must be a non-empty string")
        start = source.find(text, cursor)
        if start < 0:
            start = source.find(text)
        if start < 0:
            raise ValueError(f"entity {index}: text is not an exact source span: {text!r}")
        end = start + len(text)
        cursor = max(cursor, end)

        entity_type = entity.get("type")
        if entity_type == DIAGNOSIS:
            candidates = icd10.lookup(text, limit=candidate_limit)
        elif entity_type == DRUG:
            candidates = rxnorm.lookup(text, limit=candidate_limit)
        else:
            candidates = []
        enriched.append(
            {
                "text": text,
                "type": entity_type,
                "position": [start, end],
                "assertions": entity.get("assertions"),
                "candidates": candidates,
            }
        )
    return enriched


def validate_enriched(source: str, entities: object) -> list[str]:
    if not isinstance(entities, list):
        return ["top-level value must be an array"]
    errors: list[str] = []
    for index, entity in enumerate(entities):
        location = f"entity {index}"
        if not isinstance(entity, dict) or set(entity) != FINAL_FIELDS:
            errors.append(f"{location}: requires exactly {', '.join(sorted(FINAL_FIELDS))}")
            continue
        text = entity["text"]
        entity_type = entity["type"]
        assertions = entity["assertions"]
        if not isinstance(text, str) or not text:
            errors.append(f"{location}: text must be a non-empty string")
        if entity_type not in ALLOWED_TYPES:
            errors.append(f"{location}: invalid type")
        if (
            not isinstance(assertions, list)
            or not all(value in ALLOWED_ASSERTIONS for value in assertions)
            or len(assertions) != len(set(assertions))
            or len(assertions) > 3
            or (entity_type not in ASSERTION_TYPES and assertions)
        ):
            errors.append(f"{location}: invalid assertions")
        position = entity["position"]
        if (
            not isinstance(position, list)
            or len(position) != 2
            or not all(isinstance(value, int) and not isinstance(value, bool) for value in position)
            or not 0 <= position[0] <= position[1] <= len(source)
            or source[position[0] : position[1]] != text
        ):
            errors.append(f"{location}: invalid exact character position")
        candidates = entity["candidates"]
        if not isinstance(candidates, list) or not all(
            isinstance(value, str) and value for value in candidates
        ) or len(candidates) != len(set(candidates)):
            errors.append(f"{location}: candidates must be an array of non-empty strings")
        elif entity_type == DIAGNOSIS and not all(
            re.fullmatch(r"[A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?", value)
            for value in candidates
        ):
            errors.append(f"{location}: invalid ICD-10 candidate")
        elif entity_type == DRUG and not all(value.isdigit() for value in candidates):
            errors.append(f"{location}: invalid RxCUI candidate")
        elif entity_type not in {DIAGNOSIS, DRUG} and candidates:
            errors.append(f"{location}: candidates must be empty for this type")
    return errors


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
