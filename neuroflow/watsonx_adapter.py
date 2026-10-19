"""Optional IBM watsonx.ai / Granite adapter with a deterministic fallback."""

from __future__ import annotations

import os
from typing import Any


class GraniteAdapter:
    """Uses IBM Granite only when credentials, project, model, and SDK are available."""

    def __init__(self) -> None:
        self.url = os.getenv("WATSONX_URL", "")
        self.api_key = os.getenv("WATSONX_API_KEY", "")
        self.project_id = os.getenv("WATSONX_PROJECT_ID", "")
        self.model_id = os.getenv("WATSONX_MODEL_ID", "")
        self.last_error = ""

    def status(self) -> dict[str, Any]:
        configured = all((self.url, self.api_key, self.project_id, self.model_id))
        sdk_available = False
        try:
            import ibm_watsonx_ai  # noqa: F401

            sdk_available = True
        except ImportError:
            pass
        return {
            "provider": "IBM watsonx.ai / Granite",
            "configured": configured,
            "sdk_available": sdk_available,
            "mode": "granite" if configured and sdk_available else "deterministic-fallback",
            "last_error": self.last_error,
        }

    def draft_grounded(self, question: str, evidence: list[dict[str, str]]) -> str | None:
        status = self.status()
        if status["mode"] != "granite":
            return None
        evidence_text = "\n".join(
            f"[{item['source_id']} v{item['version']}] {item['content']}" for item in evidence
        )
        prompt = f"""
You are the bounded Knowledge & Preparation component of NeuroFlow Connect.
Use only the supplied approved evidence. Do not diagnose, interpret EEG results,
recommend treatment, change medication, or infer missing facts. If the evidence
does not answer the question, respond exactly: ABSTAIN: HUMAN REVIEW REQUIRED.
Write at most 90 words and cite source IDs in square brackets.

QUESTION:
{question}

APPROVED EVIDENCE:
{evidence_text}

ANSWER:
""".strip()
        try:
            from ibm_watsonx_ai.foundation_models import ModelInference

            model = ModelInference(
                model_id=self.model_id,
                credentials={"url": self.url, "apikey": self.api_key},
                project_id=self.project_id,
                params={
                    "decoding_method": "greedy",
                    "max_new_tokens": 180,
                    "min_new_tokens": 1,
                    "repetition_penalty": 1.05,
                },
            )
            generated = model.generate_text(prompt=prompt)
            if isinstance(generated, str) and generated.strip():
                return generated.strip()
            self.last_error = "Granite returned an empty response"
        except Exception as exc:  # The local MVP must survive unavailable cloud services.
            self.last_error = f"{type(exc).__name__}: {exc}"
        return None

