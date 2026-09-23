# Implementation plan

## Slice 1 — Network domain foundation (implemented locally)

1. Additive SQLite schema and indexes in `backend_network.py`.
2. Closed, invite-only tenant and role boundary with a feature flag.
3. Program → requirement/version → publish lifecycle.
4. Deterministic hard eligibility followed by explainable ranking and exclusion reasons.
5. Immutable quote versions, normalized line items, confidentiality boundary and idempotent replay.
6. Buyer comparison snapshots, explicit pending-approval awards and rejected alternatives.
7. Contract/SLA creation, evidence-backed activation checks and signed-contract gate.
8. Fleet handoff creating a linked `domain_bookings` row and `domain_duties` row, with no parallel trip source of truth.
9. Evidence-backed scorecards, settlements, event ledger and cross-entity version snapshots.
10. Supabase/Postgres migration, RLS baseline and atomic `network_activate_award` RPC direction; browser adapter routes complex commands to a deployable orchestration edge boundary.

Validation is covered by `network_mvp_smoke_test.py`, including tenant isolation, role restrictions, deterministic exclusions, quote confidentiality, idempotency, lifecycle transitions and activation blocking.

## Slice 2 — operator UX

- Add feature-flagged Network navigation to the protected Axiom Fleet console.
- Add buyer requirement, candidate, comparison, award and activation views.
- Add vendor quote workspace with strict field visibility and no public registration.
- Add scorecard/settlement evidence views.
- Add a first-class Masters workspace with grouped setup navigation, searchable registers and a real vehicle create/edit/import flow. This slice is now implemented locally for vehicles, suppliers and branches; duty types, vehicle groups, taxes, billing items, documents, labels, employees and feedback forms remain follow-on master slices.
- Replace blank loading areas with skeleton/retry/empty states and make the mobile decision path explicit.

## Slice 2A — usability follow-on

- Run moderated task tests for dispatcher, fleet owner and driver roles.
- Add sticky actions and inline validation to long master forms.
- Add object storage-backed document upload and expiry/renewal workflows.
- Build the mobile Operations home around the next urgent decision, rather than reproducing desktop tables.

## Slice 3 — Supabase and pilot hardening

- Apply the migration to a real Supabase project and deploy the orchestration edge adapter.
- Configure Auth memberships, object storage, provider credentials and workers.
- Run security/RLS, load, privacy and operational acceptance tests.
- Run the two-fleet Network/Driver pilot and physical Android matrix before any Passenger native work.

## Release gates

No production-readiness claim is valid until Supabase deployment, provider credentials, production object storage, real push delivery, physical Android testing and pilot evidence exist. No public vendor registration, consumer marketplace, financial escrow or autonomous award path is in scope.
