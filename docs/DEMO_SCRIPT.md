# NeuroFlow Connect Demo Script

Target length: 4–6 minutes. Use the local fallback for reliability unless IBM access has been tested before the presentation.

## 1. Open with the human problem — 30 seconds

“A fictional patient, Alex Rivera, experiences seizure-like episodes. Dr. Smith orders a routine EEG and refers Alex to Dr. Jones. The clinical decisions belong to those qualified humans, but the coordination work passes across referral staff, scheduling, the patient, the EEG technologist, and neurology. When ownership becomes unclear, missing information and delayed handoffs become invisible.”

“NeuroFlow Connect gives every task a state, owner, next action, due time, evidence trail, and human decision point.”

## 2. Show the hero workflow — 2 minutes

1. Select **NF-001**.
2. Point to the owner strip and the ten-stage journey.
3. Run **Validate intake**. Explain that the agent may verify administrative completeness, but Dr. Smith must approve order validity.
4. Run **Approve order & referral** as Dr. Smith.
5. At scheduling, run **Inject tool failure** first.
6. Point out that NeuroFlow stays in `READY_TO_SCHEDULE`, logs two bounded retries, and assigns a manual task rather than inventing an appointment.
7. Run scheduling again and expand the preparation knowledge evidence. Note the source ID and version.
8. Continue the case through patient acknowledgment and the technologist checklist.
9. Emphasize that the agent never inspects or interprets an EEG waveform.
10. Record Dr. Jones's signed report, approve the patient-facing notice, and confirm follow-up ownership.
11. Show `FOLLOW_UP_CONFIRMED`, 100% journey completion, resolved tasks, and the complete audit timeline.

## 3. Demonstrate safe failure — 60 seconds

Select **NF-002** and run intake validation.

Say: “The order signature and referral attachment are missing. NeuroFlow blocks scheduling, names the exact missing fields, assigns a correction task, and preserves the evidence.”

Select **NF-003** and ask:

> Can I drink coffee before my EEG?

Say: “Two approved demonstration sources disagree. NeuroFlow cites both, abstains, and routes the issue to the SOP owner. It does not silently choose.”

Then ask:

> What does my EEG mean and do I have epilepsy?

Say: “The request crosses a clinical boundary, so the agent refuses it and routes the question to a qualified clinician.”

## 4. Explain the IBM story — 45 seconds

“IBM Bob supports development and troubleshooting. The local MVP proves the full workflow without depending on cloud availability. When our cohort access is confirmed, IBM Granite in watsonx.ai can produce cited, bounded drafts from the same approved evidence. The included OpenAPI contract lets these tools be imported into watsonx Orchestrate, where the supervisor, specialist tools, approvals, and traces can be managed.”

Never say Granite or Orchestrate is live unless the interface status and your tested environment prove it.

## 5. Close with value and evidence — 30 seconds

“This is differentiated because it does not promise automated EEG diagnosis. It solves the invisible-handoff problem across the diagnostic journey while protecting clinical accountability.”

“The software behavior is tested. Our next evidence step is five representative-user sessions and measured baselines for scheduling time, missing-order rework, preparation acknowledgment, report-to-communication time, and closed-loop ownership.”

## Backup plan

- Reset the demo before recording.
- Record a screen capture after one full rehearsal.
- Keep NF-001 for the happy path, NF-002 for incomplete intake, and NF-003 for evidence conflict.
- If Granite is unavailable, show the `IBM-ready • local fallback` badge and explain that the fallback is intentional.

