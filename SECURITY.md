# Security and Clinical-Safety Notice

NeuroFlow Connect v0.1 is an educational prototype. It is not a medical device, production clinical system, emergency service, EHR, or HIPAA-ready application.

## Allowed use

- Local demonstration with the included fictional cases
- Software and usability testing with synthetic inputs
- Architecture discussion and IBM technology prototyping
- Import testing in an authorized sandbox that contains no PHI

## Prohibited use

- Entering or uploading real patient information
- Clinical triage, seizure detection, EEG interpretation, diagnosis, or treatment
- Medication advice or automated patient-specific medical guidance
- Production scheduling, messaging, EHR, or device integration
- Representing the prototype as validated, regulated, secure, or clinically effective

## Controls implemented in the MVP

- Synthetic-only case-creation requirement
- Deterministic role and state checks
- Clinical-request and emergency-language boundary rules
- Approved-source allowlist with versions and review dates
- Conflict detection and abstention
- Manual fallback after bounded tool retries
- Human gates for order validity, technical acceptance, physician signature, results communication, follow-up, and overrides
- Audit metadata allowlist
- Credentials read only from environment variables

## Controls not implemented

- User authentication or enterprise identity
- Production role-based access control
- Encryption key management or secrets vault
- EHR/FHIR integration and patient matching
- Consent, retention, deletion, backup, or breach workflows
- Clinical validation, quality-system controls, or regulatory review
- Production telemetry, anomaly monitoring, or incident response
- Tenant isolation, rate limiting, or denial-of-service protection

Before any real-data pilot, involve organizational privacy, security, compliance, legal, clinical-governance, and IT owners. Replace the local database and demo authorization model with approved enterprise services and complete a formal threat model, data-flow review, access-control design, and clinical-safety assessment.

