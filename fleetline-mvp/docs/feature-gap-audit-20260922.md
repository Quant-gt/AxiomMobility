# Axiom Fleet + Axiom Network feature-gap audit

Date: 2026-09-22

This audit re-checks the supplied master build prompt against the current repository after the governed Network foundation slice. It distinguishes implemented local-preview behavior from production-ready or still-missing product capability.

## Executive result

The repository now has a credible **Network sourcing-to-activation foundation**, but it is not yet a complete enterprise fleet/employee-transport product or a complete Network pilot. The largest remaining gap is not another list screen: it is the operational depth between a Network award and safe, measurable, reconciled transport execution.

## Axiom Network coverage

| Prompt capability | Current state | Gap / consequence | Priority |
|---|---|---|---|
| Tenant and operating-region configuration | Tenant feature flag and program settings exist | No first-class operating-region/site/service-zone entity or per-region flag; city coverage is embedded in profiles/spec JSON | P0 |
| Invite-only onboarding | Buyer invite and vendor profile flow exists | No separate vendor approval, renewal, probation, document, suspension, blacklist or offboarding workflow | P0 |
| Requirement/RFP lifecycle | Draft, published, matched, quoted, award-pending, awarded and activated states exist | Does not implement the prompt's full lifecycle: submitted, under review, vendors invited, quoting closed, negotiation, contract pending, suspended, completed, cancelled, expired, reopen and deadline/expiry behavior | P0 |
| Demand capture | Basic requirement/spec JSON and UI draft form | No recurring/multi-site demand model, template import, requester/approver chain, attachment model, clarification, duplicate-with-fresh-dates, cancel/pause/reopen or feasibility validation | P0 |
| Deterministic matching | City/service/vehicle/capacity/capability/compliance hard filters plus reasons and simple score | No historical evidence features, minimum sample sizes, recency weighting, confidence/cold-start labels, controlled exploration, override workflow or regional capacity windows | P0 |
| Structured quotes | Immutable quote versions, assumptions and normalized line items exist | No quote drafts, response deadline/window close, late behavior, withdrawal, clarification threads, named availability commitments or incomparable-unit evaluation workflow | P0 |
| Buyer comparison | Immutable snapshot of selected quote versions exists | No separate quote-evaluation model, normalized commercial comparison, non-comparability warnings, evaluator comments or approval thresholds | P0 |
| Award and approval | Pending approval, approved award and rejected alternatives exist | No multi-level configurable approval chain, award expiry, negotiation/reopen path or vendor-side award acceptance/rejection | P0 |
| Contract/SLA | Contract row, sign action, SLA rows and four activation checks exist | No contract document/version/acceptance workflow, SLA breach event model, effective-date enforcement, renewal or suspension logic | P0 |
| Activation readiness | Contract signature, compliance, capacity and dispatch checks block activation | Checks do not yet cover actual vendor/vehicle/driver/GPS/safety readiness; activation creates only a Fleet booking and draft duty, not a roster/route/dispatch configuration | P0 |
| Fleet operational handoff | Service order links booking and duty IDs | No route plan, recurring roster, driver/vehicle assignment, GPS/ETA linkage, passenger communication, proof policy, vendor replacement or operational exception handoff | P0 |
| Replacement and exception operation | Not implemented in governed Network | No capacity shortfall, replacement vendor, missed pickup, breakdown, rejection, service suspension or escalation workflow | P0 |
| Communications/support/disputes | General Axiom ticket/notification primitives exist | No Network-scoped clarification thread, activation thread, incident/support ownership, commercial dispute or corrective-action workflow | P1 |
| Scorecards | Evidence-backed metrics JSON and evidence JSON are stored | No metric observations, formulas/calculation version, source event IDs, sample size/confidence, vendor response, dispute, corrective action or renewal gate | P0 |
| Settlement | Evidence-backed gross/deductions/net draft exists | No completed-trip/GPS/boarding reconciliation chain, invoice/fee/tax separation, partial acceptance, disputed lines, credit notes, replacement charges, approval or settlement state machine | P0 |
| Network analytics | Event ledger exists; UI shows counts | Required funnel, coverage, quote spread, activation failure, replacement, ETA/GPS, invoice variance, dispute aging, concentration and renewal metrics are not implemented | P1 |
| Network data model | Most core sourcing entities exist locally | Missing first-class operating region, vendor approval, quote evaluation, network message, metric observation, corrective action, dispute and settlement statement/line entities | P0/P1 |
| Network roles | Broad vendor/corporate role checks exist | Prompt-specific buyer/procurement/program/ops/scorecard roles, vendor account/quote/activation roles and platform Network roles are not separately enforceable | P0 |
| Network UI | Feature-flagged operator page, vendor quote workspace, basic program/requirement/invite actions exist | No buyer comparison/award/contract/check/scorecard/dispute workspaces; no deadline/owner/blocker views; disabled feature navigation is now hidden after flag hydration | P0 |

## Axiom Fleet / employee-transport coverage

| Prompt capability | Current state | Gap / consequence | Priority |
|---|---|---|---|
| Employee master | Basic employee records/import exist | No complete shift/work-calendar, employee transport eligibility, site assignment or consent/policy linkage | P0 |
| Site and office master | Branches/geofences exist | No dedicated site/service-zone model with operating calendars, pickup clusters and safe-drop policy | P0 |
| Route planning/optimization | Duty calculation, recurring bookings, stops and capacity locks exist | No real route-plan entity, hard/soft constraint engine, infeasibility explanation, version comparison, publish/rollback or partial re-optimization | P0 |
| Dispatch | Booking/duty assignment and replay exist | Driver acceptance timer/rejection, vendor allocation, bulk reassignment, replacement and deadline escalation are incomplete | P0 |
| Live map/ETA | Static map preview, track points and mock navigation exist | No provider-backed route geometry, planned-vs-actual route, stale GPS operations map, ETA model/calibration or geofence/route-deviation engine | P0/P1 |
| Safety centre | SOS, alerts, acknowledgement, geofences and mock push exist | No complete deterministic alert-policy engine covering severity/deadlines/escalation/owner/evidence/resolution/root cause/corrective action/closure approval | P0 |
| Employee/passenger flow | Passenger access link, trip status and rating exist | No full employee app, commute preferences, manifest privacy policy, OTP/no-show evidence or safe-reach workflow | P0 |
| Driver flow | Driver PWA/native acceptance slice, offline replay, proof, GPS, expense and SOS exist | Real push, object storage, physical-device validation, full acceptance timeout/rejection, no-show evidence and production provider paths remain outstanding | P0 |
| Billing/reconciliation | Duty calculation, invoices, payments, supplier bills, payouts, e-invoice mock and reports exist | No complete GPS-vs-invoice variance, effective-dated rate-card chain, partial acceptance/disputes/credit-note workflow and production ERP/finance integration | P0/P1 |
| Analytics | Report summary/export/drilldown primitives exist | No shared metric-definition layer with documented formulas/freshness across fleet, safety, route and Network KPIs | P1 |
| EV/sustainability | Not implemented beyond roadmap copy | EV vehicle/charging/range/emissions/energy metrics are missing | P2 |
| Integrations | Mock adapters and contracts exist | One real HRMS, GPS/telematics, maps, finance/ERP, messaging and storage integration are not deployed | P0/P1 release gates |
| Enterprise identity | Local session, 2FA contract and API keys exist | SSO/OIDC/SCIM/step-up authorization/break-glass support controls are not production implemented | P1 |
| Operations UX | Broad console and Driver surfaces exist | Live-map operations, route planner, safety centre and full Network operations queues are not complete | P0/P1 |

## Cross-cutting engineering gaps

- Supabase migration/RLS/RPC is authored but not deployed or exercised against a real project.
- Complex Supabase Network transitions depend on a `network-orchestrator` edge adapter that is not yet deployed.
- Production object storage, real push delivery, provider secrets, background workers and reconciliation jobs are not configured.
- The local fallback does not yet have a formal Network deadline scheduler, outbox/worker or dead-letter flow.
- Load, concurrency, migration rollback, disaster recovery and Postgres RLS tests remain outstanding.
- Production privacy/DPIA, retention, DPA/subprocessor, legal settlement and data-sharing reviews remain outstanding.

## Recommended next order

1. Add first-class region/site/shift/demand models and a full Network lifecycle/deadline/approval state machine.
2. Expand service activation into route/roster/dispatch/GPS/safety configuration and implement replacement/exception workflows.
3. Build the deterministic safety/incident policy engine and operational Network queues.
4. Build evidence-derived scorecards, reconciliation, disputes, corrective actions and settlement approvals.
5. Add buyer comparison/award/contract/check/scorecard UI and role-specific permissions.
6. Deploy Supabase/RLS/edge orchestration and one real HRMS/GPS/messaging/storage integration.
7. Run physical Driver testing and the controlled two-fleet Bengaluru pilot.

## Follow-on usability slice completed on 2026-09-22

A review of the shared internal-dashboard walkthrough identified a separate high-friction gap in master-data discoverability. The following additive slice is now implemented locally:

- First-class protected Masters navigation.
- Grouped Operations, Commercial, Fleet, People and Locations master areas.
- Searchable master hub with connected-versus-next status instead of dead links.
- Real tenant-scoped vehicle register with server-backed search and status filters.
- Mobile vehicle cards rather than a forced wide table.
- Vehicle create/edit fields for identity, group, capacity, ownership, GPS and document dates.
- Duplicate registration protection and audited vehicle edits.
- Supplier and branch/dispatch-centre register create/list flows.
- Previewed CSV vehicle import with per-row feedback.
- Local SQLite additive vehicle migration while preserving `/api/vehicles` and Supabase vehicle-field compatibility.

This closes the first Masters usability gap but does not complete the whole master-data program. Duty types, vehicle groups, taxes, billing items, documents, labels, employees, feedback forms, bank accounts and operating regions still need dedicated workflows.

## Release interpretation

The current branch is suitable for continued local development and synthetic end-to-end review of the Network sourcing foundation and the first Masters usability slice. It is not yet suitable for production transport operations, commercial settlement, real employee PII or a claim of enterprise readiness.
