"""Synthetic demo fixtures. No real patient information is included."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .db import Database


def due_in(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def seed_demo(db: Database, reset: bool = False) -> None:
    if reset:
        db.reset()
    if db.list_cases():
        return

    cases = [
        {
            "id": "NF-001",
            "patient_alias": "Alex Rivera (fictional)",
            "age_group": "Adult",
            "state": "RECEIVED",
            "workflow_status": "ACTIVE",
            "owner": "Referral staff",
            "next_action": "Validate the referral and routine EEG order",
            "due_at": due_in(4),
            "priority": "Routine",
            "synthetic": True,
            "fields": {
                "order_type": "Routine EEG",
                "ordering_clinician": "Dr. Smith",
                "neurologist": "Dr. Jones",
                "order_signed": True,
                "referral_attached": True,
                "contact_consent": True,
                "preferred_contact": "Patient portal",
                "facility": "Neurodiagnostic Lab A",
                "language": "English",
                "accessibility_needs": "None reported",
                "referral_reason": (
                    "Seizure-like episodes documented after an urgent-care assessment; "
                    "the supplied referral describes the patient as stable at discharge."
                ),
            },
            "flags": {"demo_scenario": "happy_path"},
        },
        {
            "id": "NF-002",
            "patient_alias": "Morgan Lee (fictional)",
            "age_group": "Adult",
            "state": "RECEIVED",
            "workflow_status": "ACTIVE",
            "owner": "Referral staff",
            "next_action": "Validate the incomplete referral",
            "due_at": due_in(2),
            "priority": "Routine",
            "synthetic": True,
            "fields": {
                "order_type": "Routine EEG",
                "ordering_clinician": "Dr. Smith",
                "neurologist": "Dr. Jones",
                "order_signed": False,
                "referral_attached": False,
                "contact_consent": True,
                "preferred_contact": "Phone",
                "facility": "Neurodiagnostic Lab A",
                "language": "English",
                "accessibility_needs": "None reported",
                "referral_reason": "Outpatient evaluation requested; no acute concern documented.",
            },
            "flags": {"demo_scenario": "missing_information"},
        },
        {
            "id": "NF-003",
            "patient_alias": "Jordan Patel (fictional)",
            "age_group": "Adult",
            "state": "READY_TO_SCHEDULE",
            "workflow_status": "ACTIVE",
            "owner": "Scheduling coordinator",
            "next_action": "Resolve preparation-policy conflict before scheduling",
            "due_at": due_in(8),
            "priority": "Routine",
            "synthetic": True,
            "fields": {
                "order_type": "Routine EEG",
                "ordering_clinician": "Dr. Smith",
                "neurologist": "Dr. Jones",
                "order_signed": True,
                "referral_attached": True,
                "contact_consent": True,
                "preferred_contact": "Patient portal",
                "facility": "Facility not yet selected",
                "language": "English",
                "accessibility_needs": "None reported",
                "referral_reason": "Routine outpatient EEG coordination.",
            },
            "flags": {
                "demo_scenario": "conflicting_evidence",
                "intake_validated": True,
                "order_approved": True,
            },
        },
    ]

    for case in cases:
        db.save_case(case)
        db.append_audit(
            case_id=case["id"],
            agent="NeuroFlow Supervisor",
            actor="Demo seeder",
            role="system",
            action="create_synthetic_case",
            state_before="NONE",
            state_after=case["state"],
            outcome="SUCCESS",
            reason="Synthetic IBM Challenge scenario initialized",
            metadata={"new_state": case["state"]},
        )

