# Axiom Fleet — PRD implementation status

**Updated:** 19 September 2026  
**Product:** Axiom Fleet  
**Execution model:** Supabase/PostgreSQL/RLS production direction with a dependency-free SQLite fallback for local preview and automated tests.

## Status key

- **[x]** Tested end-to-end in the current local implementation.
- **[~]** Callable and tested locally, with mock providers, a provisional UI, or live-Supabase/project validation still required.
- **[ ]** Not implemented and intentionally left for production hardening or a later product phase.

This document distinguishes functional delivery from infrastructure that cannot be validated in this workspace. Supabase CLI, project credentials, PostgreSQL binaries and external provider credentials were not available, so this report does not claim a live Supabase deployment.

## Current implementation summary

The PRD feature layer is now implemented as callable organization-scoped workflows in `backend_extended.py`, wired before the original domain handlers in `server.py`, mirrored by the Supabase browser adapter, and covered by `deep_feature_smoke_test.py`.

Covered local workflows include:

- Resumable onboarding and tenant provisioning with branch, tax profile, numbering series and progress state.
- Normalized duplicate checks, soft deactivation, effective-dated price-book version snapshots and maker-checker approval.
- Booking approval chains, duty exceptions, maps navigation, masked telephony, SOS, trip shares and incremental polling updates.
- Supplier bill capture, vehicle/fleet costs, supplier and driver payouts, receipts, tax calculation, financial approvals, billing notes, payment links, reconciliation and mock e-invoice cancellation.
- Recurring bookings, multi-stop routes, capacity locks, queued mock jobs, local TOTP/API-key security controls, privacy request fulfillment and employee lifecycle.
- Driver language/quiet-hour preferences, device binding, practice duties and passenger access/trip/rating workflows.
- Alerts, geofences, notification events, payment webhooks with idempotency, associate fleets, offers/bids and settlement ledgers.
- Report exports with expiry, saved views, schedules and drill-downs.
- A mobile-first Driver PWA vertical slice and Expo/React Native foundation with secure mobile sessions, duty lifecycle, location, proof, expenses, offline replay and SOS contracts.
- Consent receipts, retention locks, platform KPIs and feature flags.

The protected Axiom Fleet console now hydrates onboarding state from the backend, provides a working onboarding modal, and exposes Finance controls, Network & partners, Admin health, Security & privacy and Passenger view pages plus a Workflow Center. A usability pass adds progressive disclosure, a three-move Today operating path, role-aware driver navigation, live fleet/duty context and role-specific product tours so daily actions are visible before advanced configuration. Core booking, billing, fleet, customer and driver surfaces remain intact and branded with the supplied logo.

---

# 1. PRD coverage matrix

## A. Identity, tenancy and access control

- [x] Email/password signup and login for vendor, driver and corporate roles.
- [x] Protected private console, httpOnly local session, logout, duplicate-account protection and password-reset non-enumeration.
- [x] Guided resumable organization onboarding with server-side checklist state.
- [x] Tenant provisioning with organization profile, default branch, tax profile and numbering-series settings.
- [~] Supabase Auth profile, organization, branch, membership and invitation model with RLS helpers and RPCs; live project migration and Auth-hook validation remain.
- [~] Granular permissions and organization-scoped policies exist in the local and Supabase foundation; production authorization regression remains.
- [x] Expiring invitation creation and matching-email acceptance, including invited-driver local flow.
- [~] Supabase Auth recovery is wired; email templates and delivery need project configuration.
- [~] Local mock TOTP setup/verification, recovery-code contract and factor audit exist; Google OIDC, mobile OTP/DLT, Supabase Auth MFA enforcement, SSO-enforced platform-admin identity and enterprise SAML remain.
- [~] Local security sessions, API-key hashing/revocation and device records exist; Redis-backed distributed throttling, rotating refresh-token families and production remote revoke remain.
- [~] Local security headers, login throttling, input limits and audit events exist; production WAF, CSRF, HSTS, secret rotation and security review remain.

## B. Vendor masters and pricing

- [x] Organization-scoped customers, drivers, vehicles, suppliers and branches.
- [x] Normalized duplicate detection for customer phone/GSTIN and entity-specific master values.
- [x] Soft deactivation for customer, driver, vehicle and supplier records.
- [~] Document metadata, expiry and mock storage registration exist; real Supabase Storage upload/review remains.
- [x] Booking batch import with row-level imported/error outcomes and source-reference preservation.
- [x] Effective-dated price books, version snapshots, correction history and approval state.
- [~] Price-book editing and approval are API-backed; the full visual version-history editor remains to be expanded.

## C. Bookings and duties

- [x] Booking creation, organization scoping, route/passenger/schedule/duty-type persistence and batch import.
- [x] Assignment, approval chains, driver/vehicle association, status transitions, no-show, reassignment and force-close exceptions.
- [x] Navigation estimates, masked calls, SOS event creation, trip-share tokens and reconciliation route.
- [x] Driver execution with accept/en-route/start/complete milestones, OTP proof, location points, expense capture and idempotent offline replay.
- [x] Incremental `/api/updates` polling contract with cursor and duty/alert events.
- [~] Real-time is implemented as a deterministic polling fallback; WebSocket/realtime channels and mobile reconciliation remain production work.
- [~] Recurring bookings, multi-stop route plans and capacity locks are implemented; complex pricing and availability optimization remain.

## D. Duty slip and calculation engine

- [x] Deterministic integer-paise calculation engine with explainable line items, validation and engine version.
- [x] Local calculation and provider-adapter tests, including tax rounding and idempotent behavior.
- [~] Calculation snapshots and record-version history are persisted; a dedicated correction/version UI remains.
- [x] Generated deterministic 1,000-case golden calculation suite (`golden_calculation_test.py`) plus pilot shadow-billing variance report remains.
- [~] Duty-to-supplier/customer reconciliation endpoint exists; production ledger reconciliation and dispute evidence need live data.

## E. Billing, e-invoicing, receipts and collections

- [x] Invoice generation, issue immutability, payment collection state and dispatch records.
- [x] State-aware GST calculation for intra-state CGST/SGST and inter-state IGST.
- [x] Receipt allocation against an invoice.
- [x] Mock e-invoice IRN/QR issuance and cancellation workflow.
- [x] Payment webhook event storage with provider/external-id idempotency.
- [x] Financial actions with pending review and approve/reject decision records.
- [~] Supabase billing tables, RLS and browser adapter are present; live GST/e-invoice sandbox, Razorpay/Cashfree signatures and tax authority validation remain.
- [~] Collections summary, dispatch and mock payment links exist; aging, automated dunning and reminder scheduling remain.
- [~] Seven-year retention lock records and a queued mock worker exist; an automated retention worker and legal-hold policy enforcement remain.
- [~] Proforma/credit/debit note draft workflows exist; consolidated invoices and production payment-gateway settlement remain.

## F. Purchase, supplier and fleet cost

- [x] Supplier bill capture with bill-number and amount validation metadata.
- [x] Fleet/vehicle cost entries with category, duty/vehicle links and attachment metadata.
- [x] Supplier and driver payout batches enter maker-checker review state.
- [x] Vehicle P&L calculation endpoint and supplier-scorecard endpoint.
- [x] Supplier bill, duty and cost records are organization-scoped in SQLite and Supabase migration.
- [~] Finance controls page and Workflow Center expose bill/cost/payout actions; purchase-ledger detail, fuel/maintenance/toll-specific UI and bill-to-duty reconciliation remain.
- [ ] Payroll, statutory deductions and external HR/payroll settlement.

## G. Corporate console

- [x] Corporate role, employee import, cost-center fields and travel-policy records.
- [x] Multi-level booking approval chains with per-level decisions.
- [x] Corporate invoice verification endpoint and mock HRMS sync contract.
- [x] SLA event creation/resolution and supplier scorecards.
- [~] Current protected console renders a corporate approval view and dedicated finance/admin governance pages; a separate corporate application, policy entitlement engine and live passenger communications remain.
- [ ] Corporate OIDC/SAML SSO, production HRMS integration and auto-acceptance rules.

## H. Driver application

- [x] Driver role and organization association, assigned-duty list, milestones, proof and offline replay.
- [x] Navigation mock adapter, masked calling record, SOS alert, language/quiet-hour preference and device binding.
- [x] Practice/sandbox duty workflow and low-bandwidth driver manifest/service worker.
- [~] Driver view is available in the protected console, is role-aware and opens directly for driver users; a mobile-first PWA vertical slice and Expo/React Native foundation now exist; production Android/iOS push, device limits, background location and store hardening remain.
- [~] Expense capture accepts attachment/photo metadata; production photo upload and review remain.

## I. Passenger experience

- [x] Scoped passenger access links, trip status/history, passenger rating and issue tags.
- [~] The local API, share-token workflow and protected Passenger View are ready; a separately authenticated passenger mobile/web surface and live-location UX remain.
- [ ] Company-email SSO, invite-code authentication, passenger booking requests and quiet-hours notification preference.

## J. Tracking, alerts and communications

- [x] GPS points, alert records, geofences, notification event history and payment webhook records.
- [x] Mock maps, telephony, messaging, e-invoice and storage adapters with deterministic provider references.
- [~] Polling fallback is wired; Supabase Realtime/WebSockets, FCM/APNs, DLT SMS, WhatsApp BSP, email delivery receipts and provider circuit breakers remain.
- [~] Call consent, masked number and SOS records are persisted locally; real telephony recording/retention needs provider and legal configuration.

## K. Reports and analytics

- [x] Tenant-scoped summaries, CSV export records with seven-day expiry, saved views, schedules and source-row drill-down.
- [x] Operations report, vehicle P&L, supplier scorecards and platform KPI endpoints.
- [~] Supabase report export/view/schedule tables and adapter are included; local queued jobs and Workflow Center are available, while production workers, presigned downloads, cursor pagination and reporting read replicas remain.
- [ ] Full report builder, 100K-row async export and performance-tested analytics warehouse.

## L. Platform admin

- [x] Platform KPI counts and tenant/client registry endpoints for local operators.
- [x] Feature flag read/write contract and support ticket foundation.
- [~] Local operator permissions and audit trails exist; separate staff SSO, admin application, support impersonation banner, subscription/usage/dues and cross-tenant registries remain.

## M. Associate network and settlements

- [x] Associate fleet edges with accept flow, duty offers, bids and settlement ledger net calculation.
- [~] Supabase network tables and tenant RLS are included; selective rate-card sharing, trust scoring, evidence-locked disputes and settlement statements remain.
- [~] Dedicated Network & partners page and Workflow Center expose the local network creation path; trust scoring, disputes and settlement statements remain.

## N. Production infrastructure and integrations

- [x] Dependency-free local executable backend, mock adapters, deterministic smoke suites and Supabase browser adapter fallback.
- [~] Supabase PostgreSQL migration now includes core and extended tables, indexes, RLS and the browser adapter routes; it has not been applied to a live project in this workspace.
- [ ] React/TypeScript production app migration, Node/NestJS/Go service, Redis, S3, queues, TimescaleDB/ClickHouse, CloudFront/WAF, DR region, PITR, OpenTelemetry/Sentry and CI/CD.
- [x] OpenAPI contract is published for the implemented routes, with idempotency contracts on execution/provider mutations; universal cursor pagination and API version policy remain.

## O. Privacy, security and quality gates

- [x] Consent receipts, retention locks, privacy request foundation, organization audit events and mock webhook idempotency.
- [~] Supabase RLS, tenant boundaries and financial/retention tables are scaffolded; live security review and threat-model sign-off remain.
- [ ] PII field encryption, DPDP automated export/deletion fulfillment, legal-hold worker, breach runbook, penetration test, SBOM/dependency scanning and SOC 2/ISO evidence.
- [x] Static/HTTP regression is green; backend, domain, execution, feature, uncovered, golden, Supabase-contract and deep-feature suites pass.
- [~] Browser/source validation is complete; two-fleet pilot UAT, load/p95 testing, mobile cold-start testing and 80% coverage reporting remain.

---

# 2. Remaining production work, in delivery order

1. Apply the Supabase migration to a non-production project and run the full API/browser adapter suite against real Auth, PostgREST and RLS.
2. Replace the placeholder Supabase config with project URL/anon key through deployment secrets; keep service-role credentials server-side.
3. [completed locally] Expand the protected console into Finance controls, Network & partners, Passenger view, Admin health and Security & privacy pages; continue adding role-specific production UX during pilot.
4. Add Supabase Realtime plus polling fallback, Storage upload policies, Edge Function deployment and provider webhook signature verification.
5. Finish the calculation corpus, shadow billing and financial reconciliation with pilot records.
6. Add production authentication options, Redis throttling, device management, CSRF/HSTS/WAF and security review.
7. Build the one cross-platform native Driver client first; keep Passenger as a scoped web/PWA link until pilot evidence justifies a second native app, then run a two-fleet pilot with UAT, performance and recovery evidence.

## Definition of feature-ready local scope

The local product is feature-ready for continued pilot integration when a vendor can onboard, create a booking, approve/allot a duty, execute it with offline replay and proof, generate/collect an invoice, record supplier costs/payouts, export reports, and retain auditable privacy/network/alert evidence. That scope is now callable and tested.

It should be described as a **feature-complete local fallback with a Supabase production foundation**, not as a live production deployment, until the Supabase project, external providers, native clients and security/pilot gates above are completed.
