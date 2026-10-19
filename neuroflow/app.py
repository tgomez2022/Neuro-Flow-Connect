"""Dependency-free HTTP application for the NeuroFlow Connect MVP."""

from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .db import Database
from .knowledge import KnowledgeBase
from .seed import seed_demo
from .watsonx_adapter import GraniteAdapter
from .workflow import STATES, WorkflowEngine, WorkflowError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
KNOWLEDGE_ROOT = PROJECT_ROOT / "data" / "knowledge"
DEFAULT_DB = PROJECT_ROOT / "data" / "neuroflow.db"


class NeuroFlowHandler(BaseHTTPRequestHandler):
    engine: WorkflowEngine
    db: Database
    granite: GraniteAdapter

    server_version = "NeuroFlowConnect/0.2"

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path) -> None:
        if not path.is_file():
            self._json({"ok": False, "error": "Not found"}, 404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise WorkflowError("Request body is too large.", 413)
        if length == 0:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WorkflowError("Request body must be valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise WorkflowError("Request body must be a JSON object.")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                self._json(
                    {
                        "ok": True,
                        "service": "NeuroFlow Connect MVP",
                        "version": __version__,
                        "data_mode": "synthetic-only",
                        "clinical_mode": "coordination-only; no diagnosis or EEG interpretation",
                        "watsonx": self.granite.status(),
                    }
                )
            elif path == "/api/dashboard":
                self._json({"ok": True, "dashboard": self.db.dashboard()})
            elif path == "/api/cases":
                self._json({"ok": True, "cases": self.engine.list_cases(), "states": STATES})
            elif match := re.fullmatch(r"/api/cases/([A-Za-z0-9-]+)", path):
                self._json({"ok": True, "case": self.engine.detail(match.group(1))})
            elif path in {"/", "/index.html"}:
                self._file(WEB_ROOT / "index.html")
            elif path == "/app.js":
                self._file(WEB_ROOT / "app.js")
            elif path == "/styles.css":
                self._file(WEB_ROOT / "styles.css")
            elif path == "/openapi.yaml":
                self._file(PROJECT_ROOT / "openapi.yaml")
            elif path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self._json({"ok": False, "error": "Not found"}, 404)
        except KeyError as exc:
            self._json({"ok": False, "error": str(exc)}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": f"Server error: {type(exc).__name__}"}, 500)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/reset":
                seed_demo(self.db, reset=True)
                self._json(
                    {
                        "ok": True,
                        "message": "Synthetic demo reset.",
                        "dashboard": self.db.dashboard(),
                        "cases": self.engine.list_cases(),
                    }
                )
                return
            if path == "/api/cases":
                case = self.engine.create_synthetic_case(body)
                self._json({"ok": True, "case": case}, HTTPStatus.CREATED)
                return
            if match := re.fullmatch(r"/api/cases/([A-Za-z0-9-]+)/action", path):
                result = self.engine.perform(
                    match.group(1),
                    str(body.get("action", "")),
                    actor=str(body.get("actor", "Demo operator")),
                    role=str(body.get("role", "")),
                    payload=body.get("payload") if isinstance(body.get("payload"), dict) else {},
                )
                self._json(result)
                return
            if match := re.fullmatch(r"/api/cases/([A-Za-z0-9-]+)/ask", path):
                question = str(body.get("question", "")).strip()
                if len(question) < 3:
                    raise WorkflowError("Enter a question with at least three characters.")
                result = self.engine.ask(
                    match.group(1), question,
                    actor=str(body.get("actor", "Demo operator")),
                    role=str(body.get("role", "scheduler")),
                )
                self._json(result)
                return
            if match := re.fullmatch(r"/api/cases/([A-Za-z0-9-]+)/override", path):
                result = self.engine.override(
                    match.group(1),
                    actor=str(body.get("actor", "Workflow administrator")),
                    role=str(body.get("role", "")),
                    new_state=str(body.get("new_state", "")),
                    reason=str(body.get("reason", "")),
                )
                self._json(result)
                return
            self._json({"ok": False, "error": "Not found"}, 404)
        except WorkflowError as exc:
            self._json({"ok": False, "error": str(exc)}, exc.status)
        except KeyError as exc:
            self._json({"ok": False, "error": str(exc)}, 404)
        except Exception as exc:
            self._json({"ok": False, "error": f"Server error: {type(exc).__name__}: {exc}"}, 500)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[NeuroFlow] {self.address_string()} - {format % args}")


def build_runtime(db_path: str | Path = DEFAULT_DB) -> tuple[Database, GraniteAdapter, KnowledgeBase, WorkflowEngine]:
    db = Database(db_path)
    granite = GraniteAdapter()
    knowledge = KnowledgeBase(KNOWLEDGE_ROOT, granite)
    engine = WorkflowEngine(db, knowledge)
    seed_demo(db)
    return db, granite, knowledge, engine


def serve(host: str = "127.0.0.1", port: int = 8000, db_path: str | Path = DEFAULT_DB) -> None:
    db, granite, _knowledge, engine = build_runtime(db_path)
    handler = type(
        "ConfiguredNeuroFlowHandler",
        (NeuroFlowHandler,),
        {"db": db, "granite": granite, "engine": engine},
    )
    server = ThreadingHTTPServer((host, port), handler)
    print("NeuroFlow Connect MVP")
    print(f"Open http://{host}:{port}")
    print("Synthetic data only. No diagnosis, EEG interpretation, or treatment decisions.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NeuroFlow Connect.")
    finally:
        server.server_close()

