# IBM Integration Guide

The default demonstration is deliberately local and reliable. IBM components are separated into **confirmed**, **optional**, and **proposed** status so the team never overclaims an integration.

## 1. IBM Bob — confirmed development use

Open this project in IBM Bob and use it to:

- Explain `neuroflow/workflow.py` and the human-gate logic.
- Run `python -m unittest discover -s tests -v`.
- Add or refine one bounded specialist without changing the clinical boundary.
- Troubleshoot a failing acceptance test and record the change in version control.

IBM Bob is the development partner in this design, not the production agent runtime.

## 2. watsonx.ai and IBM Granite — optional live generation

The adapter in `neuroflow/watsonx_adapter.py` uses `ModelInference` from IBM's Python SDK. Without the SDK or credentials, it returns no model output and the retrieval layer uses its deterministic, cited fallback.

Install the optional SDK:

```bash
python -m pip install -r requirements-ibm.txt
```

Set only values from your own authorized watsonx.ai project. A model ID is intentionally not hard-coded because availability varies by account and region.

Windows PowerShell example:

```powershell
$env:WATSONX_URL="https://us-south.ml.cloud.ibm.com"
$env:WATSONX_API_KEY="your-authorized-key"
$env:WATSONX_PROJECT_ID="your-project-id"
$env:WATSONX_MODEL_ID="a-granite-model-id-visible-in-your-project"
py run.py
```

macOS/Linux example:

```bash
export WATSONX_URL="https://us-south.ml.cloud.ibm.com"
export WATSONX_API_KEY="your-authorized-key"
export WATSONX_PROJECT_ID="your-project-id"
export WATSONX_MODEL_ID="a-granite-model-id-visible-in-your-project"
python run.py
```

Verify `/api/health` reports `"mode": "granite"`, then test all knowledge questions again. Never put a key in source code, screenshots, the ZIP, GitHub, or the presentation.

The prompt constrains Granite to the retrieved evidence, a 90-word answer, source-ID citations, and a fixed abstention phrase. The deterministic safety filter runs before model invocation, and the answer remains a staff-review draft.

## 3. watsonx Orchestrate — proposed tool orchestration

IBM documents that watsonx Orchestrate can use Python or OpenAPI-defined tools and can support human-validation steps. This package includes `openapi.yaml` for that path.

Before import:

1. Obtain access to the cohort's approved watsonx Orchestrate environment.
2. Deploy the API to an approved HTTPS environment. Do not expose the local demo or real data to the public internet.
3. Change the `servers[0].url` in `openapi.yaml` to that authorized endpoint.
4. Add production authentication; the Week 5 local server has none.
5. Import the OpenAPI specification as tools.
6. Build a supervisor that first calls `getNeuroFlowCase`, selects only an advertised `available_action`, and calls `performBoundedNeuroFlowAction` with the responsible human role.
7. Configure explicit human validation before `approve_order`, `complete_study`, `accept_handoff`, `sign_report`, `approve_results`, `confirm_followup`, and any override.
8. Enable traces and test the same cases used by the local acceptance suite.

Do not let the language model invent a state transition or substitute for the role check. The API remains the authoritative workflow policy.

## 4. Demo fallback

If either IBM cloud component is unavailable:

- Keep the local Python supervisor running.
- Show the `IBM-ready • local fallback` badge.
- Demonstrate that the agent contracts, citations, approvals, failures, and audit evidence still work.
- Describe Granite and Orchestrate as the next verified integration step, not as completed work.

## Official IBM references

- [watsonx.ai API documentation](https://cloud.ibm.com/docs/apis/watsonx-ai)
- [IBM watsonx.ai Python SDK — ModelInference](https://ibm.github.io/watsonx-ai-python-sdk/v1.4.11/fm_model_inference.html)
- [watsonx Orchestrate developer overview](https://www.ibm.com/products/watsonx-orchestrate/developers)
- [Managing tools in watsonx Orchestrate](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=configuring-managing-tools)

