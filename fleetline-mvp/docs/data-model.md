# Axiom Network data model

Axiom Network owns sourcing and governance state; Axiom Fleet remains the operational source of truth after activation.

## Local SQLite tables

| Table | Purpose | Invariants |
|---|---|---|
| `domain_network_feature_flags` | Per-tenant closed-module flag | default mode is `closed_invite_only` |
| `domain_network_invites` | Buyer-controlled partner invitation | no public registration; idempotent invite commands |
| `domain_network_programs` | Tenant sourcing program | code unique per tenant; explicit draft/active/paused state |
| `domain_network_requirements` | Requirement header | program-scoped; current version pointer; explicit lifecycle |
| `domain_network_requirement_versions` | Immutable demand snapshot | unique requirement/version; only a published version can match |
| `domain_network_vendor_profiles` | Invited supplier capability profile | buyer tenant owns profile; status, cities, capability, capacity and compliance evidence |
| `domain_network_match_runs` | Deterministic rules execution | requirement version and rules version are stored |
| `domain_network_candidates` | Eligible/excluded result | hard-filter reasons and explainable score JSON are retained |
| `domain_network_quotes` | Vendor/requirement envelope | one current quote state per buyer/profile/requirement |
| `domain_network_quote_versions` | Immutable commercial submission | new revisions create versions; prior current version becomes superseded |
| `domain_network_quote_line_items` | Normalized quote lines | linked to an immutable quote version |
| `domain_network_comparisons` | Buyer decision snapshot | exact quote-version IDs, quote payload snapshots and comparison rules |
| `domain_network_awards` | Controlled selection | begins pending approval; rejected alternatives retained |
| `domain_network_contracts` | Commercial agreement | draft → signed → active; terms are snapshotted |
| `domain_network_slas` | Measurable commitment | metric, target, unit, severity and evidence requirement |
| `domain_network_activation_checks` | Readiness gate | blocking status and evidence; activation requires all blocking checks passed |
| `domain_network_service_orders` | Network-to-Fleet handoff | links award, contract, Fleet booking and Fleet duty; no duplicate trip state |
| `domain_network_scorecards` | Periodic performance review | metrics and evidence are required and snapshotted |
| `domain_network_settlements` | Evidence-backed reconciliation draft | gross, deductions and calculated net; optional scorecard link |
| `domain_network_record_versions` | Cross-entity audit snapshots | versioned award, contract, SLA, check, service-order, scorecard and settlement changes |
| `domain_network_events` | Append-only domain event ledger | tenant, actor, aggregate, payload and timestamp |

The production migration mirrors these as `network_*` UUID tables under Supabase/Postgres, adds foreign keys and RLS, and exposes `network_activate_award` as an atomic activation RPC.

## Shared invariants

- Every buyer-owned row has `organization_id`; all reads and writes are tenant-scoped.
- A vendor organization can access a buyer requirement only through an eligible candidate/profile link.
- Requirement and quote payloads are immutable snapshots; revisions do not overwrite prior versions.
- Comparison snapshots are the only buyer decision input for an award.
- Awards require explicit authorized approval; there is no autonomous award path.
- Activation must create/link Fleet operational records and must never create a parallel Network trip ledger.
- Evidence is required for passed checks, scorecards and settlements.
- Idempotency keys are unique within the relevant tenant/command table.

## Sensitive data

Exact employee addresses, vendor financial data, competitor quote payloads and incident evidence are separately scoped. Generic vendor lists and candidate responses omit compliance detail and quote payloads unless the caller is authorized for that specific surface.
