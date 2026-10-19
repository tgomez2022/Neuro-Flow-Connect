# Week 5 Deliverable — End-to-End MVP Core Flow

## Milestone decision

**Status: ready for the Week 5 demonstration.** NeuroFlow Connect v0.2.0 proves one complete, human-supervised routine EEG journey with synthetic data. The flow begins when an order and referral arrive and ends only when results communication is approved and follow-up ownership is confirmed.

This milestone demonstrates software behavior, not clinical effectiveness or production readiness.

## One-sentence promise

NeuroFlow Connect keeps a routine EEG referral from disappearing between teams by giving every step a state, owner, next action, evidence trail, and human approval point.

## Hero workflow

**Trigger:** A fictional PCP submits a routine EEG order and neurology referral for a patient experiencing seizure-like episodes.

**User outcome:** The patient can see what is happening next while referral staff, scheduling, the EEG technologist, and neurology receive an owned task at the correct time.

**Completion point:** The journey reaches `FOLLOW_UP_CONFIRMED` only after the report is signed, patient-facing communication is approved and delivered, and a named clinician owns the next step.

```text
RECEIVED
  → human-approved order and referral
READY_TO_SCHEDULE
  → scheduled with cited preparation guidance
SCHEDULED
  → patient preparation acknowledgment
READY_FOR_STUDY
  → technologist checklist
STUDY_COMPLETE
  → human handoff acceptance
AWAITING_INTERPRETATION
  → physician-signed report
REPORT_SIGNED
  → clinician-approved results notice
RESULTS_COMMUNICATED
  → named follow-up owner and timing
FOLLOW_UP_CONFIRMED
```

Missing information branches to `NEEDS_INFORMATION`. Acute-risk language pauses automation. Tool failure, conflicting sources, an unauthorized role, or an unsigned report preserves the last safe state.

## What the MVP demonstrates

| Capability | Working evidence |
|---|---|
| Intake validation | NF-002 identifies a missing signature and referral attachment and creates a correction task. |
| Safe coordination | NF-001 advances only through advertised actions and authorized roles. |
| Grounded retrieval | Preparation guidance displays source IDs and versions from the allowlisted demonstration corpus. |
| Conflict handling | NF-003 cites both caffeine sources, abstains, and routes the conflict for human review. |
| Tool-failure recovery | Scheduling performs two bounded retries, preserves state, and creates a manual fallback task. |
| Clinical boundary | Diagnostic or EEG-interpretation questions are refused and routed to a qualified clinician. |
| Human oversight | Order approval, technical acceptance, report signature, results communication, and follow-up remain human gates. |
| Auditability | Actions, failures, approvals, overrides, owners, and state transitions appear in the timeline. |

## Why this is agentic

The supervisor observes case state, selects an eligible bounded action, routes work to the responsible specialist, retrieves approved evidence when needed, checks policy, requests human approval, and records the outcome. It adapts to incomplete information, conflicting evidence, role violations, and tool failure rather than following one unconditional script.

Agentic AI is deliberately bounded:

- **AI-suitable work:** extracting or summarizing variable language, retrieving relevant approved passages, drafting plain-language guidance, and coordinating the next eligible task.
- **Deterministic work:** required-field checks, permissions, deadlines, allowed transitions, retry limits, and closure criteria.
- **Human-only work:** urgency decisions, procedure acceptance, technical-quality judgment, EEG interpretation, diagnosis, treatment, results approval, and follow-up decisions.

## IBM technology status

| IBM component | Week 5 status | Meaningful role |
|---|---|---|
| IBM Bob | Confirmed development support | Explain, refine, test, and troubleshoot the code and documentation. |
| watsonx.ai + IBM Granite | Optional; requires verified participant access | Produce bounded, evidence-grounded language drafts through the included adapter. |
| watsonx Orchestrate | Proposed; access and deployment must be verified | Import the included OpenAPI tools for routing, approvals, and traces. |
| Local Python supervisor | Working fallback | Preserves the same agent contracts and makes the entire demo reliable offline. |

Never describe Granite or Orchestrate as live unless the configured environment has been tested and the interface reports it.

## Acceptance evidence

The current automated suite reports:

```text
12 tests run
12 passed
0 failures
0 errors
```

The suite covers the happy path, missing information, evidence conflict, clinical refusal, emergency pause, scheduling failure, wrong-role rejection, human override logging, audit-data minimization, and HTTP/UI endpoints. See `TEST_RESULTS.md` for the complete record.

## Five-minute proof

1. Start the app and open NF-001.
2. Validate intake and show that the agent stops for PCP approval.
3. Approve the order and referral as Dr. Smith.
4. At `READY_TO_SCHEDULE`, inject the tool failure. Show the preserved state, bounded retries, manual task, and audit event.
5. Retry scheduling successfully and expand the cited preparation guidance.
6. Continue through patient acknowledgment, technologist checklist, handoff acceptance, physician signature, approved results notice, and follow-up confirmation.
7. Show the final `FOLLOW_UP_CONFIRMED` state, 100% progress, resolved tasks, and audit timeline.
8. Open NF-002 to prove incomplete intake is blocked.
9. Open NF-003 to prove conflicting evidence causes abstention and a clinical question is refused.

## Evidence to capture this week

- [ ] Screenshot: NF-001 initial state with owner and next action
- [ ] Screenshot: scheduling failure, manual fallback task, and preserved state
- [ ] Screenshot: cited preparation guidance
- [ ] Screenshot: physician/human approval gate
- [ ] Screenshot: NF-001 at `FOLLOW_UP_CONFIRMED`
- [ ] Screenshot: NF-002 blocked for missing information
- [ ] Screenshot: NF-003 abstaining on conflicting sources
- [ ] Screen recording: one uninterrupted 4–6 minute walkthrough
- [x] Automated test record: 12 of 12 passing

## Paste-ready milestone statement

NeuroFlow Connect now has a working end-to-end MVP core flow for a synthetic routine EEG journey. The prototype validates intake, coordinates scheduling and preparation, tracks the technical handoff, waits for physician report signature, controls patient-facing results communication, and confirms follow-up ownership. It demonstrates cited retrieval, role-based human approvals, audit logging, missing-information handling, conflicting-source abstention, clinical-boundary refusal, and safe recovery from a scheduling-tool failure. Twelve automated tests currently pass. IBM Bob supports development and troubleshooting; watsonx.ai with Granite and watsonx Orchestrate remain clearly labeled as optional or proposed until our access and integrations are verified. The MVP does not diagnose, interpret EEG waveforms, or replace clinical judgment.

## Evidence boundary and next step

This build uses fictional cases and proves technical behavior only. It does not yet prove time savings, usability, clinical safety, or patient outcomes. Weeks 6–8 should test the same workflow with five representative users, capture comparable baselines, document failures and design changes, and measure task completion, time to identify the next action, correct escalation, and citation coverage.
