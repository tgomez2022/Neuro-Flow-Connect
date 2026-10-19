"""Bounded safety checks for a non-diagnostic healthcare workflow demo."""

from __future__ import annotations

import re
from typing import Any


EMERGENCY_PATTERNS = (
    r"\bseizure (?:is )?(?:happening|now|won't stop|will not stop)\b",
    r"\bstatus epilepticus\b",
    r"\bunconscious\b",
    r"\bnot breathing\b",
    r"\bblue lips\b",
    r"\bsevere injury\b",
    r"\bcall 911\b",
)

CLINICAL_DECISION_PATTERNS = (
    r"\bdiagnos(?:e|is)\b",
    r"\bdo i have epilepsy\b",
    r"\bwhat does (?:my|the) eeg mean\b",
    r"\binterpret (?:my|the) eeg\b",
    r"\bchange (?:my|the) medication\b",
    r"\bstop (?:my|the) medication\b",
    r"\bwhat treatment\b",
    r"\bmedical advice\b",
)


def assess_text(text: str) -> dict[str, str | bool]:
    normalized = " ".join((text or "").lower().split())
    if any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS):
        return {
            "allowed": False,
            "category": "EMERGENCY_ESCALATION",
            "message": (
                "This prototype cannot assess an emergency. Stop the automated workflow and "
                "contact local emergency services or the responsible clinician now."
            ),
        }
    if any(re.search(pattern, normalized) for pattern in CLINICAL_DECISION_PATTERNS):
        return {
            "allowed": False,
            "category": "CLINICAL_BOUNDARY",
            "message": (
                "NeuroFlow does not diagnose, interpret EEG findings, recommend treatment, or "
                "change medication. Route this question to a qualified clinician."
            ),
        }
    return {"allowed": True, "category": "ADMINISTRATIVE", "message": "Allowed"}


def audit_safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Keep audit metadata useful without copying case narrative or identifiers."""
    if not metadata:
        return {}
    allowed = {
        "missing_fields",
        "source_ids",
        "source_versions",
        "task_id",
        "slot_id",
        "retry_count",
        "failure_mode",
        "approval_type",
        "old_state",
        "new_state",
        "policy_rule",
        "delivery_channel",
        "acknowledged",
        "human_gate",
        "model_mode",
    }
    return {key: value for key, value in metadata.items() if key in allowed}

