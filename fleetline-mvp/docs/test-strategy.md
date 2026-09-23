# Test strategy

## Existing gates

- Python syntax and domain/unit tests.
- 48/48 static regression checks.
- Backend, deep feature and provider smoke tests.
- Native TypeScript, Expo Doctor and Android bundle export.
- Native Driver replay/push integration test.

## P0 automated gates

`python3 p0_smoke_test.py` runs a fresh SQLite server and verifies:

- protected P0 route access, duplicate master handling, version snapshots and tenant isolation;
- canonical booking/duty references in route planning, ordered stops and publish transitions;
- dispatch offers, acceptance, idempotent replay, safe no-op replay and invalid transition rejection;
- safety policy versioning, escalation deadlines, incident acknowledgement/investigation/resolution/closure;
- invite-only Network region records and tenant isolation;
- permission-bundle visibility, explicit tenant deny overrides and authorization-negative behavior.

The test is intentionally local. Supabase migration execution, RLS with two real projects/tenants and Edge Function transaction behavior remain deployment gates.

## Network MVP automated gates

`python3 network_mvp_smoke_test.py` runs an isolated SQLite server and verifies:

- invite-only vendor profile creation and absence of public registration;
- program and requirement version lifecycle;
- deterministic city/capacity/capability/compliance filters and exclusion reasons;
- vendor-only quote submission, immutable quote versions and quote idempotency;
- buyer quote confidentiality before comparison and immutable comparison snapshots;
- pending-approval award lifecycle, contract signing and rejected alternatives;
- evidence-required activation checks and activation blocking;
- idempotent Fleet service-order activation with linked booking/duty IDs;
- scorecard/settlement evidence and net reconciliation;
- buyer tenant isolation and driver role denial.

## Next tests

- Supabase RLS matrix with two buyer tenants and two vendor tenants.
- Postgres RPC rollback/duplicate replay tests.
- Quote revision immutability and concurrent approval tests.
- PII and competitor quote leakage tests across every response shape.
- Contract/SLA version history and scorecard formula reproducibility.
- Load and queue/reconciliation tests for provider-backed pilot operations.

Use synthetic organizations, vendors, requirements and route evidence only. Physical Driver validation, real push, object storage and pilot evidence remain release gates.
