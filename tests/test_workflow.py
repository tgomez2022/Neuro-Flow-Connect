from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from neuroflow.db import Database
from neuroflow.knowledge import KnowledgeBase
from neuroflow.seed import seed_demo
from neuroflow.watsonx_adapter import GraniteAdapter
from neuroflow.workflow import WorkflowEngine, WorkflowError


ROOT = Path(__file__).resolve().parents[1]


class NeuroFlowWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")
        self.kb = KnowledgeBase(ROOT / "data" / "knowledge", GraniteAdapter())
        self.engine = WorkflowEngine(self.db, self.kb)
        seed_demo(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def perform(self, case_id: str, action: str, role: str, actor: str = "Test human", payload=None):
        return self.engine.perform(
            case_id, action, actor=actor, role=role, payload=payload or {}
        )

    def test_happy_path_closes_only_after_all_human_gates(self) -> None:
        case_id = "NF-001"
        self.perform(case_id, "validate_intake", "referral_staff")
        self.assertEqual(self.db.get_case(case_id)["state"], "RECEIVED")
        self.perform(case_id, "approve_order", "pcp", "Dr. Smith")
        self.perform(case_id, "schedule_case", "scheduler")
        scheduled = self.db.get_case(case_id)
        self.assertEqual(scheduled["state"], "SCHEDULED")
        self.assertTrue(scheduled["fields"]["preparation_citations"])
        self.perform(case_id, "acknowledge_preparation", "patient", "Alex (demo)")
        self.perform(case_id, "complete_study", "eeg_technologist", "Terry")
        self.perform(case_id, "accept_handoff", "eeg_technologist", "Terry")
        self.perform(case_id, "sign_report", "neurologist", "Dr. Jones")
        self.perform(case_id, "approve_results", "neurologist", "Dr. Jones")
        result = self.perform(case_id, "confirm_followup", "care_coordinator", "Casey")

        self.assertEqual(result["case"]["state"], "FOLLOW_UP_CONFIRMED")
        self.assertEqual(result["case"]["workflow_status"], "COMPLETE")
        self.assertEqual(result["case"]["available_actions"], [])
        self.assertGreaterEqual(len(result["case"]["audit"]), 10)
        self.assertFalse([task for task in result["case"]["tasks"] if task["status"] == "OPEN"])

    def test_missing_information_blocks_scheduling(self) -> None:
        result = self.perform("NF-002", "validate_intake", "referral_staff")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["case"]["state"], "NEEDS_INFORMATION")
        self.assertIn("order_signed", result["case"]["flags"]["missing_fields"])
        self.assertIn("referral_attached", result["case"]["flags"]["missing_fields"])
        self.assertEqual(result["case"]["available_actions"][0]["id"], "resolve_information")

    def test_bounded_tool_failure_preserves_state_and_creates_manual_task(self) -> None:
        result = self.perform(
            "NF-003", "schedule_case", "scheduler", payload={"failure_mode": "scheduling_api"}
        )
        self.assertTrue(result["fallback"])
        self.assertEqual(result["case"]["state"], "READY_TO_SCHEDULE")
        tasks = [task for task in result["case"]["tasks"] if task["status"] == "OPEN"]
        self.assertTrue(any(task["task_type"] == "MANUAL_SCHEDULING" for task in tasks))
        self.assertEqual(result["case"]["audit"][0]["outcome"], "FALLBACK")
        self.assertEqual(result["case"]["audit"][0]["metadata"]["retry_count"], 2)

    def test_conflicting_approved_sources_force_abstention(self) -> None:
        result = self.engine.ask(
            "NF-003", "Can I drink coffee before my EEG?", actor="Test", role="scheduler"
        )
        answer = result["result"]
        self.assertEqual(answer["status"], "ABSTAIN")
        self.assertEqual(answer["evidence_status"], "CONFLICTING_APPROVED_SOURCES")
        self.assertGreaterEqual(len(answer["citations"]), 2)
        self.assertTrue(answer["human_review_required"])

    def test_clinical_request_is_refused(self) -> None:
        result = self.engine.ask(
            "NF-001", "What does my EEG mean and do I have epilepsy?", actor="Test", role="scheduler"
        )["result"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["evidence_status"], "CLINICAL_BOUNDARY")
        self.assertFalse(result["citations"])

    def test_emergency_language_pauses_automation(self) -> None:
        case = self.engine.create_synthetic_case(
            {
                "synthetic": True,
                "patient_alias": "Emergency Scenario (fictional)",
                "fields": {
                    "order_type": "Routine EEG",
                    "ordering_clinician": "Dr. Smith",
                    "neurologist": "Dr. Jones",
                    "order_signed": True,
                    "referral_attached": True,
                    "contact_consent": True,
                    "preferred_contact": "Phone",
                    "facility": "Demo Lab",
                    "referral_reason": "The seizure is happening now and will not stop."
                },
            }
        )
        result = self.perform(case["id"], "validate_intake", "referral_staff")
        self.assertTrue(result["escalated"])
        self.assertEqual(result["case"]["workflow_status"], "PAUSED")
        self.assertEqual(result["case"]["available_actions"], [])
        self.assertTrue(
            any(task["task_type"] == "EMERGENCY_REVIEW" for task in result["case"]["tasks"])
        )

    def test_wrong_role_cannot_cross_a_human_gate(self) -> None:
        self.perform("NF-001", "validate_intake", "referral_staff")
        with self.assertRaises(WorkflowError) as context:
            self.perform("NF-001", "approve_order", "scheduler")
        self.assertEqual(context.exception.status, 403)
        self.assertEqual(self.db.get_case("NF-001")["state"], "RECEIVED")

    def test_human_override_requires_reason_and_is_audited(self) -> None:
        with self.assertRaises(WorkflowError):
            self.engine.override(
                "NF-001", actor="Admin", role="workflow_admin",
                new_state="READY_TO_SCHEDULE", reason="short",
            )
        result = self.engine.override(
            "NF-001", actor="Admin", role="workflow_admin",
            new_state="READY_TO_SCHEDULE", reason="Referral corrected and verified outside the demo",
        )
        event = result["case"]["audit"][0]
        self.assertEqual(event["action"], "human_override")
        self.assertEqual(event["state_before"], "RECEIVED")
        self.assertEqual(event["state_after"], "READY_TO_SCHEDULE")

    def test_audit_metadata_does_not_copy_patient_alias_or_narrative(self) -> None:
        self.perform("NF-001", "validate_intake", "referral_staff")
        serialized = json.dumps(self.db.list_audit("NF-001"))
        self.assertNotIn("Alex Rivera", serialized)
        self.assertNotIn("stable at discharge", serialized)


if __name__ == "__main__":
    unittest.main()

