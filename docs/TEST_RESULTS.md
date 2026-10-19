# Verification Record

Build: NeuroFlow Connect MVP v0.2.0  
Verification date: 2026-10-16 (Cohort Week 5)  
Environment: Python 3.12.14; Node.js v24.19.0

## Automated result

Command:

```bash
python -m unittest discover -s tests -v
```

Result: **12 tests run; 12 passed; 0 failures; 0 errors.** The complete suite was rerun after the Week 5 evidence package and version update.

Verified behaviors:

1. Complete referral-to-follow-up happy path
2. Human order-approval gate
3. Missing-order information blocks scheduling
4. Bounded scheduling retry and manual fallback
5. Conflicting approved sources force abstention
6. Clinical interpretation request is refused
7. Emergency language pauses automation
8. Wrong role cannot cross an approval gate
9. Human override requires a reason and is audited
10. Audit metadata excludes patient alias and referral narrative
11. HTTP health and dashboard endpoints respond
12. Web interface and action endpoint are served

## Static validation

- Python modules compiled successfully.
- Browser JavaScript passed `node --check`.
- HTML contained 39 unique IDs and no duplicate IDs.
- CSS opening and closing brace counts matched.
- `openapi.yaml` parsed as OpenAPI 3.0.3 with seven documented paths.

## Live smoke test

- Local server started successfully on `127.0.0.1:8000`.
- `/api/health` returned `ok: true`, version `0.2.0`, and the expected `deterministic-fallback` mode.
- `/api/dashboard` returned the synthetic demonstration dashboard.
- `/` returned the NeuroFlow Connect interface.

## Evidence boundary

These results demonstrate expected software behavior with synthetic data. They do not establish production security, clinical safety, accessibility conformance, usability, workflow improvement, or patient outcomes. A manual visual check on the presentation computer and the five representative-user sessions in `VALIDATION_PLAN.md` remain required.

