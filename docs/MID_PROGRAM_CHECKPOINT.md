# Mid-Program Milestone Checkpoint

## Preliminary idea and description

NeuroFlow Connect is a human-supervised, multi-agent care-coordination prototype for the referral-to-results journey of a fictional patient experiencing seizure-like episodes. It follows the patient from Dr. Smith's routine EEG order and neurology referral through scheduling, preparation, study completion, physician interpretation by Dr. Jones, results communication, and confirmed follow-up. A supervisor maintains one visible case state while bounded specialists handle administrative intake, approved knowledge retrieval, scheduling/readiness, EEG handoff completeness, and results follow-up. The solution does not interpret EEG waveforms, diagnose, choose treatment, or automate emergency triage. Instead, it prevents unfinished work from becoming invisible by assigning every task an owner, status, next action, due time, evidence trail, and human approval point.

## Value proposition

For patients, NeuroFlow Connect reduces uncertainty by showing what has happened, what comes next, and who owns the next step. For PCP offices, schedulers, EEG technologists, neurologists, and hospital staff, it targets avoidable callbacks, missing-information rework, stalled referrals, unclear handoffs, and delayed results communication. Its value will be tested through referral-to-appointment time, missing-order detection, preparation acknowledgment, report-to-communication time, and the percentage of cases with a visible owner and next action. The state-and-agent design can later extend to other diagnostic pathways that depend on referrals, preparation, testing, interpretation, and follow-up.

## AI-use justification

AI is justified because the journey combines unstructured referral notes, changing workflow context, approved knowledge retrieval, role-specific communication, and asynchronous coordination across several people and systems. IBM Granite in watsonx.ai is proposed for structured extraction, grounded summarization, classification, and plain-language drafts; watsonx Orchestrate is proposed for multi-agent routing and approvals; IBM Bob supports implementation and troubleshooting. Deterministic rules still control required fields, state transitions, deadlines, permissions, and closure. Human clinicians retain urgency, procedure, technical-quality, interpretation, diagnosis, treatment, and patient-communication authority. This division uses AI where language and coordination add value without transferring clinical accountability to a model.

## Evidence note

Current evidence consists of the creator's neurodiagnostic workflow experience, the mapped patient journey, a runnable synthetic MVP, and automated behavioral tests. Formal representative-user validation and measured current-workflow baselines have not yet been completed. Weeks 6–8 will test the prototype with representative roles and record findings, failures, design changes, and before/after task timing.

