# Gaps and risks

## Implementation gaps

- Network operator and vendor UI is not yet expanded; the backend slice is intentionally ahead of UI.
- The Supabase migration/RLS/RPC has not been applied to a project from this environment.
- The browser adapter expects a deployed `network-orchestrator` edge boundary for complex Supabase matching/comparison/award transitions; only the activation RPC contract is included locally.
- Production push/storage providers, provider credentials and real workers are not configured.
- Network vendor/HRMS/ERP integrations are mock or contract-only.
- Physical Android Driver validation and the two-fleet pilot are outstanding.

## Risks

- Commercial/legal settlement terms may change quote, contract and evidence requirements.
- Poor vendor capacity/compliance evidence can make matching misleading.
- Exact-address and employee movement data creates high privacy risk.
- A match without activation readiness can create operational failure.
- A scorecard based on low sample sizes can unfairly penalize vendors.
- Compatibility edge/offer/bid routes are intentionally shallow and must not be mistaken for the governed MVP.
- Supabase RLS policy interactions and Postgres RPC behavior require deployment validation.

## Mitigations

- Feature flag, additive migration and reversible compatibility boundary.
- Immutable snapshots, explicit evidence, samples and rule versions.
- Closed invite-only pilot with approved tenants and vendors.
- Negative authorization, confidentiality and duplicate-replay tests.
- Blocking activation checks and Fleet source-of-truth handoff.
- Legal/privacy/RLS review before commercial or PII-heavy pilot.
