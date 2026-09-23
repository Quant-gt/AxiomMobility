# Axiom Network threat model

| Threat | Mitigation |
|---|---|
| Cross-tenant quote access | organization/program filters, RLS, ownership assertions, negative tests |
| Vendor sees competitor quote | quote-level authorization; comparison visible only to buyer roles |
| Quote tampering after submission | immutable quote versions and snapshots |
| Unauthorized award | role/approval checks and audit event |
| Fake vendor capability | invite-only profile, effective-dated evidence and approval state |
| Duplicate retries | idempotency keys and unique constraints |
| Service order activated without readiness | blocking activation checks |
| PII leakage in matching | zones/clusters, field minimization, scoped responses |
| GPS spoofing or stale data | provider signatures, coordinate validation, freshness indicators |
| Provider outage | timeout/retry/dead-letter/reconciliation adapters |
| Malicious document upload | type/size validation, malware scan and private storage |
| Commercial dispute without evidence | link settlement lines to completed operational evidence |
