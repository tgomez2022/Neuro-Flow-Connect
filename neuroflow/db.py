"""SQLite persistence for synthetic NeuroFlow demo cases and audit evidence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    patient_alias TEXT NOT NULL,
                    age_group TEXT NOT NULL,
                    state TEXT NOT NULL,
                    workflow_status TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    next_action TEXT NOT NULL,
                    due_at TEXT,
                    priority TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    flags_json TEXT NOT NULL,
                    synthetic INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    state_before TEXT NOT NULL,
                    state_after TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    reason TEXT,
                    evidence_refs_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    owner_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_at TEXT,
                    approval_type TEXT,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_audit_case_time
                    ON audit_events(case_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_tasks_case_status
                    ON tasks(case_id, status);
                """
            )

    def reset(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM audit_events")
            connection.execute("DELETE FROM tasks")
            connection.execute("DELETE FROM cases")

    @staticmethod
    def _decode_case(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["fields"] = json.loads(result.pop("fields_json"))
        result["flags"] = json.loads(result.pop("flags_json"))
        result["synthetic"] = bool(result["synthetic"])
        return result

    def save_case(self, case: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        created_at = case.get("created_at", now)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO cases (
                    id, patient_alias, age_group, state, workflow_status,
                    owner, next_action, due_at, priority, fields_json,
                    flags_json, synthetic, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    patient_alias=excluded.patient_alias,
                    age_group=excluded.age_group,
                    state=excluded.state,
                    workflow_status=excluded.workflow_status,
                    owner=excluded.owner,
                    next_action=excluded.next_action,
                    due_at=excluded.due_at,
                    priority=excluded.priority,
                    fields_json=excluded.fields_json,
                    flags_json=excluded.flags_json,
                    synthetic=excluded.synthetic,
                    updated_at=excluded.updated_at
                """,
                (
                    case["id"],
                    case["patient_alias"],
                    case.get("age_group", "Not specified"),
                    case["state"],
                    case.get("workflow_status", "ACTIVE"),
                    case.get("owner", "Referral coordinator"),
                    case.get("next_action", "Review case"),
                    case.get("due_at"),
                    case.get("priority", "Routine"),
                    json.dumps(case.get("fields", {}), sort_keys=True),
                    json.dumps(case.get("flags", {}), sort_keys=True),
                    1 if case.get("synthetic", True) else 0,
                    created_at,
                    now,
                ),
            )
        return self.get_case(case["id"])

    def get_case(self, case_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown case: {case_id}")
        return self._decode_case(row)

    def list_cases(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM cases ORDER BY priority DESC, updated_at DESC, id"
            ).fetchall()
        return [self._decode_case(row) for row in rows]

    def append_audit(
        self,
        *,
        case_id: str,
        agent: str,
        actor: str,
        role: str,
        action: str,
        state_before: str,
        state_after: str,
        outcome: str,
        reason: str = "",
        evidence_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": f"AUD-{uuid.uuid4().hex[:10].upper()}",
            "case_id": case_id,
            "timestamp": utc_now(),
            "agent": agent,
            "actor": actor,
            "role": role,
            "action": action,
            "state_before": state_before,
            "state_after": state_after,
            "outcome": outcome,
            "reason": reason,
            "evidence_refs": evidence_refs or [],
            "metadata": metadata or {},
        }
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, case_id, timestamp, agent, actor, role, action,
                    state_before, state_after, outcome, reason,
                    evidence_refs_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"], event["case_id"], event["timestamp"],
                    event["agent"], event["actor"], event["role"], event["action"],
                    event["state_before"], event["state_after"], event["outcome"],
                    event["reason"], json.dumps(event["evidence_refs"], sort_keys=True),
                    json.dumps(event["metadata"], sort_keys=True),
                ),
            )
        return event

    def list_audit(self, case_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events WHERE case_id = ? ORDER BY timestamp DESC, rowid DESC",
                (case_id,),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["evidence_refs"] = json.loads(item.pop("evidence_refs_json"))
            item["metadata"] = json.loads(item.pop("metadata_json"))
            events.append(item)
        return events

    def create_task(
        self,
        *,
        case_id: str,
        task_type: str,
        title: str,
        owner_role: str,
        details: str,
        due_at: str | None = None,
        approval_type: str | None = None,
    ) -> dict[str, Any]:
        task = {
            "id": f"TSK-{uuid.uuid4().hex[:8].upper()}",
            "case_id": case_id,
            "task_type": task_type,
            "title": title,
            "owner_role": owner_role,
            "status": "OPEN",
            "due_at": due_at,
            "approval_type": approval_type,
            "details": details,
            "created_at": utc_now(),
            "resolved_at": None,
        }
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, case_id, task_type, title, owner_role, status,
                    due_at, approval_type, details, created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(task.values()),
            )
        return task

    def resolve_tasks(self, case_id: str, task_type: str | None = None) -> int:
        now = utc_now()
        with self.connect() as connection:
            if task_type:
                cursor = connection.execute(
                    """UPDATE tasks SET status='RESOLVED', resolved_at=?
                       WHERE case_id=? AND task_type=? AND status='OPEN'""",
                    (now, case_id, task_type),
                )
            else:
                cursor = connection.execute(
                    """UPDATE tasks SET status='RESOLVED', resolved_at=?
                       WHERE case_id=? AND status='OPEN'""",
                    (now, case_id),
                )
        return cursor.rowcount

    def list_tasks(self, case_id: str, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE case_id = ?"
        params: list[Any] = [case_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY status, created_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def detail(self, case_id: str) -> dict[str, Any]:
        case = self.get_case(case_id)
        case["tasks"] = self.list_tasks(case_id)
        case["audit"] = self.list_audit(case_id)
        return case

    def dashboard(self) -> dict[str, Any]:
        cases = self.list_cases()
        active = [case for case in cases if case["workflow_status"] != "COMPLETE"]
        visible = [case for case in active if case["owner"] and case["next_action"]]
        pending_reviews = 0
        open_tasks = 0
        with self.connect() as connection:
            open_tasks = connection.execute(
                "SELECT COUNT(*) FROM tasks WHERE status='OPEN'"
            ).fetchone()[0]
            pending_reviews = connection.execute(
                """SELECT COUNT(*) FROM tasks
                   WHERE status='OPEN' AND approval_type IS NOT NULL"""
            ).fetchone()[0]
        return {
            "total_cases": len(cases),
            "active_cases": len(active),
            "closed_loops": sum(case["state"] == "FOLLOW_UP_CONFIRMED" for case in cases),
            "open_tasks": open_tasks,
            "pending_human_reviews": pending_reviews,
            "visible_ownership_pct": round((len(visible) / len(active) * 100), 1) if active else 100.0,
        }

