"""Allowlisted local retrieval with citations, conflict detection, and abstention."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .safety import assess_text
from .watsonx_adapter import GraniteAdapter


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "can", "do", "for",
    "from", "how", "i", "in", "is", "it", "my", "of", "on", "or", "should",
    "the", "to", "what", "when", "with",
}


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if token not in STOP_WORDS and len(token) > 1
    }


class KnowledgeBase:
    def __init__(self, directory: str | Path, granite: GraniteAdapter | None = None):
        self.directory = Path(directory)
        self.granite = granite or GraniteAdapter()
        self.documents = self._load()

    def _load(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for path in sorted(self.directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_path"] = str(path)
            if payload.get("status") == "approved":
                docs.append(payload)
        return docs

    def retrieve(self, question: str, limit: int = 3) -> list[dict[str, Any]]:
        query_tokens = tokens(question)
        scored: list[tuple[int, dict[str, Any]]] = []
        for doc in self.documents:
            trigger_terms = set(doc.get("trigger_terms", []))
            if trigger_terms and not (query_tokens & trigger_terms):
                continue
            weighted = " ".join(
                [doc.get("title", ""), doc.get("topic", ""), " ".join(doc.get("keywords", []))]
            )
            score = 3 * len(query_tokens & tokens(weighted))
            score += len(query_tokens & tokens(doc.get("content", "")))
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: (item[0], item[1].get("review_date", "")), reverse=True)
        return [item[1] for item in scored[:limit]]

    @staticmethod
    def _citation(doc: dict[str, Any]) -> dict[str, str]:
        content = doc["content"]
        excerpt = content if len(content) <= 220 else content[:217].rstrip() + "..."
        return {
            "source_id": doc["source_id"],
            "title": doc["title"],
            "version": doc["version"],
            "review_date": doc["review_date"],
            "excerpt": excerpt,
        }

    @staticmethod
    def _has_conflict(docs: list[dict[str, Any]]) -> bool:
        groups: dict[str, set[str]] = {}
        for doc in docs:
            group = doc.get("conflict_group")
            directive = doc.get("directive")
            if group and directive:
                groups.setdefault(group, set()).add(directive)
        return any(len(values) > 1 for values in groups.values())

    def ask(self, question: str) -> dict[str, Any]:
        safety = assess_text(question)
        model_status = self.granite.status()
        if not safety["allowed"]:
            return {
                "status": "ESCALATE" if safety["category"] == "EMERGENCY_ESCALATION" else "REFUSED",
                "answer": safety["message"],
                "citations": [],
                "evidence_status": safety["category"],
                "model_mode": model_status["mode"],
                "human_review_required": True,
            }

        docs = self.retrieve(question)
        if not docs:
            return {
                "status": "ABSTAIN",
                "answer": "No approved source answered this question. A staff member must review it.",
                "citations": [],
                "evidence_status": "NO_APPROVED_EVIDENCE",
                "model_mode": model_status["mode"],
                "human_review_required": True,
            }

        if self._has_conflict(docs):
            return {
                "status": "ABSTAIN",
                "answer": (
                    "Approved sources conflict for this question. NeuroFlow will not choose between "
                    "them; the facility SOP owner or clinician must resolve the guidance."
                ),
                "citations": [self._citation(doc) for doc in docs],
                "evidence_status": "CONFLICTING_APPROVED_SOURCES",
                "model_mode": model_status["mode"],
                "human_review_required": True,
            }

        evidence = [
            {
                "source_id": doc["source_id"],
                "version": doc["version"],
                "content": doc["content"],
            }
            for doc in docs
        ]
        generated = self.granite.draft_grounded(question, evidence)
        if generated:
            answer = generated
            model_mode = "granite"
        else:
            answer = docs[0]["content"]
            model_mode = "deterministic-fallback"
        return {
            "status": "ANSWERED",
            "answer": answer,
            "citations": [self._citation(doc) for doc in docs],
            "evidence_status": "APPROVED_CITED_EVIDENCE",
            "model_mode": model_mode,
            "human_review_required": True,
            "notice": "Draft operational guidance; staff approval is required before patient use.",
        }

