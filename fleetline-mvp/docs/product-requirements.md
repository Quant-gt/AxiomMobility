# Axiom Network MVP product requirements

## Objective

Allow an authorized employer or fleet operator to source a recurring employee-transport requirement from approved vendors, compare structured and explainable offers, award a contract, activate an operational service order in Axiom Fleet and measure performance from completed-trip evidence.

## In scope

- Feature-flagged, tenant-scoped Network programs.
- Invite-only approved vendor profiles and eligibility evidence.
- Versioned transport requirements/RFPs.
- Deterministic hard eligibility filters and explainable match candidates.
- Draft/submitted/versioned structured quotes with line items and assumptions.
- Immutable comparison snapshots.
- Award approval with rejected alternatives and reason.
- Contract/SLA records and activation checks.
- Service-order activation into an Axiom Fleet duty/route configuration.
- Operational scorecard observations and settlement statement drafts.
- Role/tenant visibility, audit events and idempotency.

## Out of scope for this slice

- Public vendor registration.
- Payment escrow or wallet functionality.
- Autonomous award decisions.
- Production provider delivery.
- Full employee roster/HRMS implementation.
- Passenger native app.

## Acceptance criteria

1. A tenant can create a Network program and requirement only when the feature is enabled.
2. A requirement is versioned and moves through a strict lifecycle.
3. Only approved, active vendors with matching city/service/capability and capacity can appear as eligible.
4. Every excluded candidate has an explainable reason.
5. Quotes are immutable after submission; revisions create new versions.
6. Quote comparison is a stored snapshot tied to exact quote/rules versions.
7. Awards require an authorized approval and preserve rejected alternatives.
8. An award cannot activate until contract/SLA and readiness checks pass.
9. Activation creates an Axiom Fleet service order and linked operational configuration, never a parallel source of truth.
10. Scorecard/settlement observations link back to service order and evidence IDs.
11. Repeated writes with the same idempotency key do not duplicate records.
12. All state transitions and sensitive views are auditable.
