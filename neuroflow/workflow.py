"""Deterministic state machine and bounded agent orchestration for NeuroFlow."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .db import Database
from .knowledge import KnowledgeBase
from .safety import assess_text, audit_safe_metadata


STATES = [
    "RECEIVED",
    "NEEDS_INFORMATION",
    "READY_TO_SCHEDULE",
    "SCHEDULED",
    "READY_FOR_STUDY",
    "STUDY_COMPLETE",
    "AWAITING_INTERPRETATION",
    "REPORT_SIGNED",
    "RESULTS_COMMUNICATED",
    "FOLLOW_UP_CONFIRMED",
]

REQUIRED_FIELDS = (
    "order_type",
    "ordering_clinician",
    "neurologist",
    "order_signed",
    "referral_attached",
    "contact_consent",
    "preferred_contact",
    "facility",
)

ACTION_SPECS: dict[str, dict[str, Any]] = {
    "validate_intake": {
        "label": "Validate intake",
        "roles": ["referral_staff", "pcp"],
        "human_gate": False,
        "agent": "Intake & Referral Agent",
    },
    "approve_order": {
        "label": "Approve order & referral",
        "roles": ["pcp", "referral_clinician"],
        "human_gate": True,
        "agent": "Intake & Referral Agent",
    },
    "resolve_information": {
        "label": "Supply missing information",
        "roles": ["referral_staff", "pcp"],
        "human_gate": True,
        "agent": "Intake & Referral Agent",
    },
    "schedule_case": {
        "label": "Ground guidance & schedule",
        "roles": ["scheduler"],
        "human_gate": False,
        "agent": "Scheduling & Readiness Agent",
    },
    "acknowledge_preparation": {
        "label": "Record preparation acknowledgment",
        "roles": ["patient", "scheduler"],
        "human_gate": True,
        "agent": "Scheduling & Readiness Agent",
    },
    "complete_study": {
        "label": "Complete technical checklist",
        "roles": ["eeg_technologist"],
        "human_gate": True,
        "agent": "EEG Operations & Handoff Agent",
    },
    "accept_handoff": {
        "label": "Accept study handoff",
        "roles": ["eeg_technologist", "neurologist"],
        "human_gate": True,
        "agent": "EEG Operations & Handoff Agent",
    },
    "sign_report": {
        "label": "Record physician-signed report",
        "roles": ["neurologist"],
        "human_gate": True,
        "agent": "Results & Follow-Up Agent",
    },
    "approve_results": {
        "label": "Approve & send results notice",
        "roles": ["neurologist", "authorized_clinician"],
        "human_gate": True,
        "agent": "Results & Follow-Up Agent",
    },
    "confirm_followup": {
        "label": "Confirm follow-up ownership",
        "roles": ["care_coordinator", "neurologist"],
        "human_gate": True,
        "agent": "Results & Follow-Up Agent",
    },
}

AGENT_BY_STATE = {
    "RECEIVED": "Intake & Referral Agent",
    "NEEDS_INFORMATION": "Intake & Referral Agent",
    "READY_TO_SCHEDULE": "Knowledge + Scheduling Agents",
    "SCHEDULED": "Scheduling & Readiness Agent",
    "READY_FOR_STUDY": "EEG Operations & Handoff Agent",
    "STUDY_COMPLETE": "EEG Operations & Handoff Agent",
    "AWAITING_INTERPRETATION": "Results & Follow-Up Agent",
    "REPORT_SIGNED": "Results & Follow-Up Agent",
    "RESULTS_COMMUNICATED": "Results & Follow-Up Agent",
    "FOLLOW_UP_CONFIRMED": "NeuroFlow Supervisor",
}


class WorkflowError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def due_in(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


class WorkflowEngine:
    def __init__(self, db: Database, knowledge: KnowledgeBase):
        self.db = db
        self.knowledge = knowledge
        self.handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "validate_intake": self._validate_intake,
            "approve_order": self._approve_order,
            "resolve_information": self._resolve_information,
            "schedule_case": self._schedule_case,
            "acknowledge_preparation": self._acknowledge_preparation,
            "complete_study": self._complete_study,
            "accept_handoff": self._accept_handoff,
            "sign_report": self._sign_report,
            "approve_results": self._approve_results,
            "confirm_followup": self._confirm_followup,
        }

    @staticmethod
    def missing_fields(case: dict[str, Any]) -> list[str]:
        fields = case["fields"]
        missing: list[str] = []
        for key in REQUIRED_FIELDS:
            value = fields.get(key)
            if value is None or value == "" or value is False:
                missing.append(key)
        return missing

    def available_actions(self, case: dict[str, Any]) -> list[dict[str, Any]]:
        if case["workflow_status"] in {"PAUSED", "QUARANTINED", "COMPLETE"}:
            return []
        state = case["state"]
        if state == "RECEIVED":
            action_ids = ["approve_order"] if case["flags"].get("intake_validated") else ["validate_intake"]
        elif state == "NEEDS_INFORMATION":
            action_ids = ["resolve_information"]
        else:
            action_ids = {
                "READY_TO_SCHEDULE": ["schedule_case"],
                "SCHEDULED": ["acknowledge_preparation"],
                "READY_FOR_STUDY": ["complete_study"],
                "STUDY_COMPLETE": ["accept_handoff"],
                "AWAITING_INTERPRETATION": ["sign_report"],
                "REPORT_SIGNED": ["approve_results"],
                "RESULTS_COMMUNICATED": ["confirm_followup"],
            }.get(state, [])
        return [{"id": action_id, **ACTION_SPECS[action_id]} for action_id in action_ids]

    def decorate(self, case: dict[str, Any], include_history: bool = True) -> dict[str, Any]:
        item = deepcopy(case)
        state_index = STATES.index(item["state"])
        item["progress_pct"] = round(state_index / (len(STATES) - 1) * 100)
        item["state_index"] = state_index
        item["active_agent"] = AGENT_BY_STATE[item["state"]]
        item["available_actions"] = self.available_actions(item)
        if include_history:
            item["tasks"] = self.db.list_tasks(item["id"])
            item["audit"] = self.db.list_audit(item["id"])
        return item

    def list_cases(self) -> list[dict[str, Any]]:
        return [self.decorate(case, include_history=False) for case in self.db.list_cases()]

    def detail(self, case_id: str) -> dict[str, Any]:
        return self.decorate(self.db.get_case(case_id), include_history=True)

    def perform(
        self,
        case_id: str,
        action: str,
        *,
        actor: str,
        role: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if action not in self.handlers:
            raise WorkflowError(f"Unsupported action: {action}")
        case = self.db.get_case(case_id)
        allowed = {item["id"] for item in self.available_actions(case)}
        if action not in allowed:
            raise WorkflowError(f"Action {action} is not available while the case is {case['state']}", 409)
        if role not in ACTION_SPECS[action]["roles"]:
            raise WorkflowError(
                f"Role '{role}' cannot perform {action}. Allowed roles: "
                + ", ".join(ACTION_SPECS[action]["roles"]),
                403,
            )
        return self.handlers[action](case, actor, role, payload or {})

    def _record(
        self,
        case: dict[str, Any],
        *,
        action: str,
        actor: str,
        role: str,
        before: str,
        outcome: str = "SUCCESS",
        reason: str = "",
        evidence_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.db.append_audit(
            case_id=case["id"],
            agent=ACTION_SPECS[action]["agent"],
            actor=actor,
            role=role,
            action=action,
            state_before=before,
            state_after=case["state"],
            outcome=outcome,
            reason=reason,
            evidence_refs=evidence_refs,
            metadata=audit_safe_metadata(metadata),
        )

    def _save_result(self, case: dict[str, Any], message: str, **extra: Any) -> dict[str, Any]:
        self.db.save_case(case)
        return {"ok": True, "message": message, "case": self.detail(case["id"]), **extra}

    def _validate_intake(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        safety = assess_text(case["fields"].get("referral_reason", ""))
        if safety["category"] == "EMERGENCY_ESCALATION":
            case["workflow_status"] = "PAUSED"
            case["owner"] = "PCP / emergency clinician"
            case["next_action"] = "Immediate human assessment required"
            case["flags"]["safety_stop"] = True
            task = self.db.create_task(
                case_id=case["id"], task_type="EMERGENCY_REVIEW",
                title="Immediate clinical review", owner_role="emergency_clinician",
                details=safety["message"], due_at=due_in(0), approval_type="CLINICAL_URGENCY",
            )
            self._record(
                case, action="validate_intake", actor=actor, role=role, before=before,
                outcome="ESCALATED", reason="Emergency-language safety rule triggered",
                metadata={"task_id": task["id"], "policy_rule": "emergency-language-stop"},
            )
            return self._save_result(case, safety["message"], escalated=True)

        missing = self.missing_fields(case)
        if missing:
            case["state"] = "NEEDS_INFORMATION"
            case["owner"] = "Referral staff"
            case["next_action"] = "Correct: " + ", ".join(field.replace("_", " ") for field in missing)
            case["due_at"] = due_in(4)
            case["flags"]["missing_fields"] = missing
            task = self.db.create_task(
                case_id=case["id"], task_type="CORRECTION",
                title="Complete the referral packet", owner_role="referral_staff",
                details="Supply the exact missing fields: " + ", ".join(missing), due_at=case["due_at"],
            )
            self._record(
                case, action="validate_intake", actor=actor, role=role, before=before,
                outcome="BLOCKED", reason="Required administrative fields are missing",
                metadata={"missing_fields": missing, "task_id": task["id"]},
            )
            return self._save_result(case, "Scheduling blocked; a precise correction task was created.", blocked=True)

        case["flags"]["intake_validated"] = True
        case["owner"] = case["fields"].get("ordering_clinician", "PCP")
        case["next_action"] = "Human review: approve order and referral"
        case["due_at"] = due_in(4)
        task = self.db.create_task(
            case_id=case["id"], task_type="APPROVAL",
            title="Approve order and referral validity", owner_role="pcp",
            details="Review the synthetic administrative packet and approve, correct, or cancel.",
            due_at=case["due_at"], approval_type="ORDER_VALIDITY",
        )
        self._record(
            case, action="validate_intake", actor=actor, role=role, before=before,
            reason="Administrative packet complete; human validity gate created",
            metadata={"task_id": task["id"], "approval_type": "ORDER_VALIDITY"},
        )
        return self._save_result(case, "Intake is complete. Dr. Smith must approve the order and referral.")

    def _resolve_information(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        supplied = payload.get("fields") or {
            "order_signed": True,
            "referral_attached": True,
        }
        case["fields"].update(supplied)
        case["state"] = "RECEIVED"
        case["owner"] = "Referral staff"
        case["next_action"] = "Revalidate the corrected referral"
        case["due_at"] = due_in(2)
        case["flags"].pop("missing_fields", None)
        case["flags"].pop("intake_validated", None)
        self.db.resolve_tasks(case["id"], "CORRECTION")
        self._record(
            case, action="resolve_information", actor=actor, role=role, before=before,
            reason="Human supplied the missing administrative fields",
            metadata={"new_state": case["state"], "human_gate": True},
        )
        return self._save_result(case, "Missing information was supplied. The referral is ready for revalidation.")

    def _approve_order(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        if not case["flags"].get("intake_validated"):
            raise WorkflowError("The administrative packet must be validated before clinical approval.", 409)
        case["flags"]["order_approved"] = True
        case["state"] = "READY_TO_SCHEDULE"
        case["owner"] = "Scheduling coordinator"
        case["next_action"] = "Retrieve approved preparation guidance and offer a valid slot"
        case["due_at"] = due_in(8)
        self.db.resolve_tasks(case["id"], "APPROVAL")
        self._record(
            case, action="approve_order", actor=actor, role=role, before=before,
            reason=payload.get("reason", "Order and referral approved by an authorized human"),
            metadata={"approval_type": "ORDER_VALIDITY", "human_gate": True},
        )
        return self._save_result(case, "Human approval recorded. The case can now be scheduled.")

    def _schedule_case(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        if payload.get("failure_mode") == "scheduling_api":
            existing = [task for task in self.db.list_tasks(case["id"], "OPEN") if task["task_type"] == "MANUAL_SCHEDULING"]
            task = existing[0] if existing else self.db.create_task(
                case_id=case["id"], task_type="MANUAL_SCHEDULING",
                title="Schedule manually after tool failure", owner_role="scheduler",
                details="The mock scheduling tool failed after two bounded retries. Do not invent a slot.",
                due_at=due_in(4),
            )
            case["owner"] = "Scheduling coordinator"
            case["next_action"] = "Use manual scheduling fallback; case state preserved"
            case["flags"]["tool_failure"] = "scheduling_api"
            self._record(
                case, action="schedule_case", actor=actor, role=role, before=before,
                outcome="FALLBACK", reason="Scheduling tool failed after bounded retries",
                metadata={"retry_count": 2, "failure_mode": "scheduling_api", "task_id": task["id"]},
            )
            result = self._save_result(
                case,
                "Scheduling tool failed safely. The state was preserved and a manual task was assigned.",
                fallback=True,
            )
            return result

        guidance = self.knowledge.ask("How should a patient prepare for a routine EEG appointment?")
        if guidance["status"] != "ANSWERED":
            task = self.db.create_task(
                case_id=case["id"], task_type="KNOWLEDGE_REVIEW",
                title="Resolve preparation guidance", owner_role="sop_owner",
                details=guidance["answer"], due_at=due_in(4), approval_type="SOP_REVIEW",
            )
            case["owner"] = "SOP owner / clinician"
            case["next_action"] = "Resolve evidence gap before patient guidance"
            self._record(
                case, action="schedule_case", actor=actor, role=role, before=before,
                outcome="ABSTAINED", reason=guidance["evidence_status"],
                evidence_refs=[c["source_id"] for c in guidance["citations"]],
                metadata={"task_id": task["id"], "model_mode": guidance["model_mode"]},
            )
            return self._save_result(case, guidance["answer"], blocked=True, guidance=guidance)

        slot = payload.get("slot") or "Tuesday, 9:00 AM — Neurodiagnostic Lab A"
        case["fields"].update(
            {
                "appointment_slot": slot,
                "preparation_guidance": guidance["answer"],
                "preparation_citations": guidance["citations"],
                "preparation_acknowledged": False,
            }
        )
        case["state"] = "SCHEDULED"
        case["owner"] = "Patient / scheduling coordinator"
        case["next_action"] = "Acknowledge the approved preparation instructions"
        case["due_at"] = due_in(24)
        case["flags"].pop("tool_failure", None)
        self.db.resolve_tasks(case["id"], "MANUAL_SCHEDULING")
        source_ids = [citation["source_id"] for citation in guidance["citations"]]
        self._record(
            case, action="schedule_case", actor=actor, role=role, before=before,
            reason="Valid mock slot selected; approved preparation evidence attached",
            evidence_refs=source_ids,
            metadata={
                "source_ids": source_ids,
                "source_versions": [citation["version"] for citation in guidance["citations"]],
                "slot_id": "DEMO-SLOT-001",
                "model_mode": guidance["model_mode"],
            },
        )
        return self._save_result(case, "Appointment scheduled with cited preparation guidance.", guidance=guidance)

    def _acknowledge_preparation(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        case["fields"]["preparation_acknowledged"] = True
        case["state"] = "READY_FOR_STUDY"
        case["owner"] = "EEG technologist"
        case["next_action"] = "Perform the study and complete the technical checklist"
        case["due_at"] = due_in(48)
        self._record(
            case, action="acknowledge_preparation", actor=actor, role=role, before=before,
            reason="Human acknowledgment recorded",
            metadata={"acknowledged": True, "human_gate": True},
        )
        return self._save_result(case, "Preparation acknowledgment recorded. The patient is ready for the study.")

    def _complete_study(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        case["fields"].update(
            {
                "study_completed": True,
                "technical_checklist": "Completed by qualified EEG technologist",
                "waveform_interpretation": "Not performed by NeuroFlow",
            }
        )
        case["state"] = "STUDY_COMPLETE"
        case["owner"] = "EEG technologist / neurology service"
        case["next_action"] = "Human review: accept the study handoff"
        case["due_at"] = due_in(4)
        task = self.db.create_task(
            case_id=case["id"], task_type="TECHNICAL_REVIEW",
            title="Accept study-completion handoff", owner_role="eeg_technologist",
            details="Confirm the completion packet is present. NeuroFlow does not interpret waveforms.",
            due_at=case["due_at"], approval_type="TECHNICAL_ACCEPTANCE",
        )
        self._record(
            case, action="complete_study", actor=actor, role=role, before=before,
            reason="Qualified technologist completed the procedural checklist",
            metadata={"task_id": task["id"], "approval_type": "TECHNICAL_ACCEPTANCE", "human_gate": True},
        )
        return self._save_result(case, "Study completion recorded. A human must accept the handoff.")

    def _accept_handoff(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        case["state"] = "AWAITING_INTERPRETATION"
        case["owner"] = case["fields"].get("neurologist", "Neurologist")
        case["next_action"] = "Qualified physician interprets and signs the EEG report"
        case["due_at"] = due_in(24)
        case["fields"]["handoff_accepted"] = True
        self.db.resolve_tasks(case["id"], "TECHNICAL_REVIEW")
        task = self.db.create_task(
            case_id=case["id"], task_type="INTERPRETATION",
            title="Interpret and sign the EEG report", owner_role="neurologist",
            details="Physician-only clinical task. No automated interpretation is performed.",
            due_at=case["due_at"], approval_type="PHYSICIAN_SIGNATURE",
        )
        self._record(
            case, action="accept_handoff", actor=actor, role=role, before=before,
            reason="Human accepted the technical handoff",
            metadata={"task_id": task["id"], "approval_type": "PHYSICIAN_SIGNATURE", "human_gate": True},
        )
        return self._save_result(case, "Study packet accepted and routed to Dr. Jones for interpretation.")

    def _sign_report(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        case["fields"].update(
            {
                "report_status": "SIGNED",
                "report_signed_by": actor,
                "report_notice": (
                    "A physician-signed report is available. NeuroFlow does not display, summarize, "
                    "or interpret the clinical findings in this MVP."
                ),
            }
        )
        case["state"] = "REPORT_SIGNED"
        case["owner"] = actor
        case["next_action"] = "Human review: approve patient-facing results communication"
        case["due_at"] = due_in(8)
        self.db.resolve_tasks(case["id"], "INTERPRETATION")
        task = self.db.create_task(
            case_id=case["id"], task_type="RESULTS_APPROVAL",
            title="Approve results communication and follow-up plan", owner_role="neurologist",
            details="Review the neutral message, add clinically appropriate language, and approve before release.",
            due_at=case["due_at"], approval_type="PATIENT_RESULTS_COMMUNICATION",
        )
        self._record(
            case, action="sign_report", actor=actor, role=role, before=before,
            reason="Physician signature status recorded; report content remains outside the agent",
            metadata={"task_id": task["id"], "approval_type": "PHYSICIAN_SIGNATURE", "human_gate": True},
        )
        return self._save_result(case, "Physician-signed report detected. Results communication still requires approval.")

    def _approve_results(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        if case["fields"].get("report_status") != "SIGNED":
            raise WorkflowError("A draft or unsigned report cannot be communicated.", 409)
        message = payload.get("approved_message") or (
            "Your EEG report has been reviewed and signed by Dr. Jones. Please use the care-team "
            "contact information in your portal for questions and follow the clinician-approved next steps."
        )
        case["fields"].update(
            {
                "approved_results_message": message,
                "results_approved_by": actor,
                "delivery_status": "DELIVERED_DEMO",
                "delivery_channel": case["fields"].get("preferred_contact", "Patient portal"),
            }
        )
        case["state"] = "RESULTS_COMMUNICATED"
        case["owner"] = "Care coordinator"
        case["next_action"] = "Confirm patient acknowledgment and follow-up ownership"
        case["due_at"] = due_in(24)
        self.db.resolve_tasks(case["id"], "RESULTS_APPROVAL")
        task = self.db.create_task(
            case_id=case["id"], task_type="FOLLOW_UP",
            title="Confirm acknowledgment and named follow-up owner", owner_role="care_coordinator",
            details="Do not close the case until delivery, acknowledgment, owner, and date are recorded.",
            due_at=case["due_at"], approval_type="FOLLOW_UP_OWNERSHIP",
        )
        self._record(
            case, action="approve_results", actor=actor, role=role, before=before,
            reason="Authorized clinician approved the patient-facing communication",
            metadata={
                "task_id": task["id"], "approval_type": "PATIENT_RESULTS_COMMUNICATION",
                "human_gate": True, "delivery_channel": case["fields"]["delivery_channel"],
            },
        )
        return self._save_result(case, "Approved results notice sent through the synthetic delivery channel.")

    def _confirm_followup(self, case: dict[str, Any], actor: str, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = case["state"]
        case["fields"].update(
            {
                "patient_acknowledged": True,
                "followup_owner": payload.get("followup_owner", "Dr. Jones care team"),
                "followup_at": payload.get("followup_at", "Next available neurology appointment (demo)"),
            }
        )
        case["state"] = "FOLLOW_UP_CONFIRMED"
        case["workflow_status"] = "COMPLETE"
        case["owner"] = case["fields"]["followup_owner"]
        case["next_action"] = "Closed loop — monitor only"
        case["due_at"] = None
        self.db.resolve_tasks(case["id"])
        self._record(
            case, action="confirm_followup", actor=actor, role=role, before=before,
            reason="Delivery, acknowledgment, follow-up owner, and timing confirmed",
            metadata={"acknowledged": True, "human_gate": True},
        )
        return self._save_result(case, "Closed loop confirmed. Every required owner and evidence point is recorded.")

    def ask(self, case_id: str, question: str, *, actor: str, role: str) -> dict[str, Any]:
        case = self.db.get_case(case_id)
        result = self.knowledge.ask(question)
        source_ids = [citation["source_id"] for citation in result.get("citations", [])]
        self.db.append_audit(
            case_id=case_id,
            agent="Knowledge & Preparation Agent",
            actor=actor,
            role=role,
            action="knowledge_query",
            state_before=case["state"],
            state_after=case["state"],
            outcome=result["status"],
            reason=result["evidence_status"],
            evidence_refs=source_ids,
            metadata=audit_safe_metadata({"source_ids": source_ids, "model_mode": result["model_mode"]}),
        )
        if result["status"] in {"ABSTAIN", "ESCALATE"}:
            existing = [
                task for task in self.db.list_tasks(case_id, "OPEN")
                if task["task_type"] == "KNOWLEDGE_REVIEW"
            ]
            if not existing:
                self.db.create_task(
                    case_id=case_id,
                    task_type="KNOWLEDGE_REVIEW",
                    title="Review evidence exception",
                    owner_role="sop_owner" if result["status"] == "ABSTAIN" else "clinician",
                    details=result["answer"],
                    due_at=due_in(4),
                    approval_type="SOP_REVIEW" if result["status"] == "ABSTAIN" else "CLINICAL_URGENCY",
                )
        return {"ok": result["status"] == "ANSWERED", "result": result, "case": self.detail(case_id)}

    def override(
        self,
        case_id: str,
        *,
        actor: str,
        role: str,
        new_state: str,
        reason: str,
    ) -> dict[str, Any]:
        if role not in {"workflow_admin", "neurologist", "compliance_lead"}:
            raise WorkflowError("This role cannot override workflow state.", 403)
        if new_state not in STATES:
            raise WorkflowError("Unknown target state.")
        if len(reason.strip()) < 8:
            raise WorkflowError("A meaningful override reason is required.")
        case = self.db.get_case(case_id)
        before = case["state"]
        case["state"] = new_state
        case["workflow_status"] = "COMPLETE" if new_state == "FOLLOW_UP_CONFIRMED" else "ACTIVE"
        case["owner"] = actor
        case["next_action"] = "Human override recorded; review downstream tasks"
        case["flags"]["last_override_reason"] = reason
        self.db.save_case(case)
        self.db.append_audit(
            case_id=case_id,
            agent="NeuroFlow Supervisor",
            actor=actor,
            role=role,
            action="human_override",
            state_before=before,
            state_after=new_state,
            outcome="OVERRIDDEN",
            reason=reason,
            metadata=audit_safe_metadata(
                {"old_state": before, "new_state": new_state, "human_gate": True}
            ),
        )
        return {"ok": True, "message": "Human override recorded with reason and state change.", "case": self.detail(case_id)}

    def create_synthetic_case(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("synthetic") is not True:
            raise WorkflowError("This MVP accepts synthetic cases only.")
        alias = str(payload.get("patient_alias", "New fictional patient")).strip()
        if not re.fullmatch(r"[A-Za-z0-9 .()'-]{2,80}", alias):
            raise WorkflowError("Use a short fictional alias without sensitive identifiers.")
        next_number = len(self.db.list_cases()) + 1
        case_id = f"NF-{next_number:03d}"
        case = {
            "id": case_id,
            "patient_alias": alias,
            "age_group": payload.get("age_group", "Adult"),
            "state": "RECEIVED",
            "workflow_status": "ACTIVE",
            "owner": "Referral staff",
            "next_action": "Validate the referral and routine EEG order",
            "due_at": due_in(4),
            "priority": "Routine",
            "fields": payload.get("fields", {}),
            "flags": {"demo_scenario": "custom_synthetic"},
            "synthetic": True,
        }
        self.db.save_case(case)
        self.db.append_audit(
            case_id=case_id,
            agent="NeuroFlow Supervisor",
            actor="Demo operator",
            role="system",
            action="create_synthetic_case",
            state_before="NONE",
            state_after="RECEIVED",
            outcome="SUCCESS",
            reason="User-created synthetic demo case",
            metadata={"new_state": "RECEIVED"},
        )
        return self.detail(case_id)

