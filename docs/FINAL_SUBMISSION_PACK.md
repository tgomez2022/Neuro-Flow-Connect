# NeuroFlow Connect — Submission Pack (MVP v0.2.0)

## Problem and solution statement (under 500 words)

Patients referred for neurological testing can experience fragmented handoffs among primary care, referral staff, scheduling, EEG technologists, neurologists, and care coordinators. A routine EEG referral may be delayed by an unsigned order, missing documentation, unavailable appointments, unclear ownership, or a signed report that never reaches the next responsible person. These gaps increase administrative work and make it difficult for patients and clinicians to know what happens next.

NeuroFlow Connect addresses this coordination problem with a human-supervised, synthetic-data prototype that follows a routine EEG referral from receipt through confirmed follow-up. Each case has a visible state, responsible owner, next permitted action, unresolved tasks, and audit history. A deterministic supervisor coordinates five bounded specialist roles: intake and referral; knowledge and preparation; scheduling and readiness; EEG operations and handoff; and results and follow-up.

In the demonstration, a fictional patient is referred for a routine EEG. The intake agent checks administrative completeness, while a clinician retains authority to validate the order. Scheduling uses approved preparation guidance with source citations. The technologist and neurologist retain their respective technical and clinical responsibilities. Results communication and follow-up require explicit human approval and ownership before the workflow closes.

NeuroFlow Connect also demonstrates safe failure behavior. Missing information blocks scheduling and generates a correction task; scheduling-tool failure preserves the last safe state and creates a manual fallback; conflicting approved guidance produces an abstention and human-review task. Clinical interpretation requests are refused rather than answered by the agents.

The intended value is fewer invisible handoffs, clearer accountability, and a measurable basis for future workflow improvements. This prototype does not interpret EEG recordings, diagnose conditions, recommend treatment, handle real patient data, or claim validated clinical outcomes. Future evaluation will measure usability and coordination performance with representative users.

## Technology statement

IBM Bob is the AI-assisted development environment used to explore, troubleshoot, test, and improve the NeuroFlow Connect codebase. The runnable MVP uses Python 3.11+, the Python standard-library HTTP server, SQLite, deterministic workflow policies, versioned demonstration knowledge documents, and a browser dashboard. It is **not currently a FastAPI application**.

The local supervisor coordinates five bounded specialist roles, with backend-enforced state transitions, role checks, approval gates, retry limits, and audit events. Retrieval from an allowlisted knowledge corpus produces cited operational guidance or abstains when evidence conflicts. The optional IBM Granite adapter in `neuroflow/watsonx_adapter.py` is designed for bounded evidence-grounded drafts through watsonx.ai, but it must be configured and tested before claiming live model inference.

The repository includes `openapi.yaml`, which describes tool endpoints for a future watsonx Orchestrate integration. The Orchestrate runtime is **not yet verified as connected**. Importing these tools requires an authorized HTTPS deployment, authentication, a configured Orchestrate environment, and validation of human approvals and traces. The local Python supervisor is the working demonstration fallback.

No agent may independently interpret EEGs, diagnose, prescribe, authorize clinical decisions, or perform emergency triage. All demo cases are fictional. The application is not a production clinical or HIPAA-ready system.

## Demonstration checklist

1. Run `py -m unittest discover -s tests -v` and capture complete output.
2. Run `py run.py`, then open `http://127.0.0.1:8000`.
3. Show NF-001 and its owner, state, and next action.
4. Validate intake; demonstrate the clinician approval gate.
5. Inject scheduling failure; show preserved state and manual task.
6. Schedule successfully; show cited preparation guidance.
7. Complete the fictional EEG handoff, physician signature, results approval, and follow-up; show `FOLLOW_UP_CONFIRMED`.
8. Show NF-002 blocked for missing documents.
9. Show NF-003 abstaining on conflicting preparation guidance and refusing a clinical interpretation question.
10. Record a 4–6 minute screen capture with no real patient information.

## Evidence and limitations

- Historical verification record: `docs/TEST_RESULTS.md` reports 12 passing tests on 2026-10-16; **rerun before submission**.
- Architecture and milestone: `docs/ARCHITECTURE.md`, `docs/WEEK_5_MVP_CORE_FLOW.md`.
- Demo script: `docs/DEMO_SCRIPT.md`.
- IBM setup and status: `docs/IBM_INTEGRATION.md`.
- Security boundary: `SECURITY.md`.
- Pending: current test output, screenshots, video, independently verified IBM Bob evidence, optional cloud integrations, and representative-user validation.

Do not present optional Granite or proposed watsonx Orchestrate integrations as live.
