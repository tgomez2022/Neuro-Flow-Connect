# Weeks 6–8 Validation Plan

No user interviews, usability scores, time savings, or operational outcomes are claimed yet. This plan creates the evidence needed for the final submission.

## Five representative sessions

| Session | Representative role | Core task | Failure branch |
|---|---|---|---|
| 1 | Referral coordinator | Identify and correct an incomplete order/referral | Missing signature and attachment |
| 2 | Scheduler | Move a complete case to a confirmed appointment | Scheduling tool unavailable |
| 3 | EEG technologist | Complete and accept the study handoff | Missing technical item |
| 4 | Neurologist or authorized clinician | Find the signature and communication gates | Attempt release before signature |
| 5 | Patient or patient advocate | Find current status, preparation evidence, and contact path | Conflicting preparation sources |

Use fictional cases only. If an actual organizational user participates, collect role and workflow feedback—not patient information.

## Test protocol

1. Explain that this is a non-clinical prototype and obtain permission to record notes.
2. Ask the participant to complete the task without coaching.
3. Record baseline method and time for the comparable current workflow when available.
4. Record completion, time, errors, hesitations, questions, and the point where help was needed.
5. Ask: “What did you expect to happen next?” and “What would prevent you from trusting this?”
6. Rank each issue as critical, high, medium, or low.
7. Change one design element, rerun the task, and document the result.

## Metrics

| Metric | Definition | Provisional target | Guardrail |
|---|---|---|---|
| Task completion | Participants completing the assigned scenario without facilitator rescue | At least 4 of 5 | No unsafe shortcut counts as success |
| Time to identify next action | Seconds from case opening to correctly naming the owner and next step | Improve vs. measured baseline | Accuracy must not decline |
| Missing-input detection | Incomplete synthetic packets blocked before scheduling | 100% in test set | No complete case falsely blocked |
| Citation coverage | Operational answers containing an approved source ID and version | 100% | Conflicts must abstain |
| Correct escalation | Failure/clinical cases routed to the named human role | 100% | Zero autonomous clinical decisions |
| Usability rating | Post-task 1–5 ease rating | Median 4 or higher | Capture reasons, not just score |

Targets are hypotheses until measured.

## Validation record template

```text
Participant role:
Date and build version:
Scenario and task:
Current-workflow baseline:
MVP result and time:
Observed errors or hesitation:
Direct feedback (only with permission):
Failure encountered:
Severity:
Change made:
Retest result:
```

## Highest-leverage evidence

The strongest Week 9 story will compare the same referral-to-next-action task before and after NeuroFlow, while also proving that missing data, evidence conflict, role violations, and tool failure remain safely contained.

