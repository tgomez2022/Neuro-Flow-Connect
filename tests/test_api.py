from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from neuroflow.app import KNOWLEDGE_ROOT, NeuroFlowHandler
from neuroflow.db import Database
from neuroflow.knowledge import KnowledgeBase
from neuroflow.seed import seed_demo
from neuroflow.watsonx_adapter import GraniteAdapter
from neuroflow.workflow import WorkflowEngine


class NeuroFlowApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        db = Database(Path(cls.temp_dir.name) / "api.db")
        granite = GraniteAdapter()
        knowledge = KnowledgeBase(KNOWLEDGE_ROOT, granite)
        engine = WorkflowEngine(db, knowledge)
        seed_demo(db)
        handler = type(
            "TestNeuroFlowHandler",
            (NeuroFlowHandler,),
            {"db": db, "granite": granite, "engine": engine},
        )
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()

    @classmethod
    def get(cls, path: str):
        with urllib.request.urlopen(cls.base_url + path, timeout=3) as response:
            return response.status, response.headers, response.read()

    @classmethod
    def post(cls, path: str, payload: dict):
        request = urllib.request.Request(
            cls.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())

    def test_health_and_dashboard(self) -> None:
        status, _headers, body = self.get("/api/health")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["data_mode"], "synthetic-only")
        self.assertIn(payload["watsonx"]["mode"], {"granite", "deterministic-fallback"})

        status, _headers, body = self.get("/api/dashboard")
        dashboard = json.loads(body)["dashboard"]
        self.assertEqual(status, 200)
        self.assertEqual(dashboard["total_cases"], 3)

    def test_web_interface_is_served(self) -> None:
        status, headers, body = self.get("/")
        html = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("NeuroFlow Connect", html)
        self.assertIn("Synthetic data only", html)

    def test_action_endpoint_runs_the_bounded_intake_agent(self) -> None:
        status, payload = self.post(
            "/api/cases/NF-001/action",
            {
                "action": "validate_intake",
                "actor": "API Test Referral Staff",
                "role": "referral_staff",
                "payload": {},
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["case"]["available_actions"][0]["id"], "approve_order")


if __name__ == "__main__":
    unittest.main()

