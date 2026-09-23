# Axiom Fleet MVP

A clickable first slice of the Car Rental Operations Platform described in `technical-prd-car-rental-platform.html`.

## What is implemented

The prototype now has a public/private split:

- Public marketing site is the default view for unauthenticated visitors.
- The public site now covers the full ecosystem input: corporate travel, car-rental operations, passenger and driver apps, offline operations, live tracking, approvals, duty proofs, GST/e-invoice/Tally, payments and collections, reporting, network transactions and white-label readiness.
- Added solution split for **For corporates** and **For car rentals**.
- Added a monthly impact calculator and a walkthrough/contact form.
- Added public pages for About Us, Blogs, NewsRoom, Career, Contact Us and Success Stories.
- Added legal footnote pages for Terms of Service, Privacy Policy, Disclaimer and Refund & Cancellation Policy.
- All public pages use hash routes and share the AXIOM FLEET design system.
- The operations dashboard is hidden behind the login route (`#login` / `#app`).
- Vendor, driver and corporate users can create accounts from the auth surface.
- Email/password login, logout, profile lookup and profile updates are connected to the local backend.
- Sessions use an httpOnly cookie backed by SQLite; the browser no longer treats localStorage as authentication.
- Prototype credentials are seeded for review: `admin@blueorbit.in` / `motion2026`.
- Supabase is the target production backend: Supabase Auth for identity, PostgreSQL/RLS for tenant data, Storage for evidence, Edge Functions for server-side workflows and scheduled jobs for operational automation.
- The local backend remains a development fallback until a Supabase project URL and anon key are configured.
- The Supabase foundation is in `supabase/`; service-role credentials must never be placed in browser code.

The private console focuses on the PRD's MVP release gate, **One Fleet Live**:

- Vendor operations console with responsive layout and shared navigation
- Operations overview with KPI cards, attention queue, live fleet map treatment, run sheet and activity feed
- Duties board with table/kanban views, tabs, search, row details, selection and bulk allotment
- Booking intake with a guided create-booking modal and CSV import flow
- Billing and receipts with invoice list, collection mix, invoice drawer and async-build workflow
- Fleet control with drivers, vehicles, compliance watch and capacity snapshot
- First-class Masters workspace with grouped setup navigation, searchable tenant-scoped registers, mobile-friendly vehicle cards, extended vehicle create/edit fields, supplier and branch registers, duplicate registration protection and CSV vehicle import preview
- Customers and pricing with customer portfolio and effective-dated price-book table
- Reports and analytics with revenue trend, duty performance and SLA exception views
- Finance controls, Network & partners, Admin health, Security & privacy and Passenger view pages backed by the extended API
- Driver app mode preview covering the offline-first contract, sync queue, start duty, expense, masked call and SOS entry points
- Settings surface for workspace profile, operational policies and role/permission summary
- Resumable onboarding modal, a three-move Today operating path and Workflow Center for supplier bills, fleet costs, payouts, report exports, network edges, retention locks, polling updates, security factors and operator KPIs
- Progressive navigation keeps the daily loop visible while grouping advanced tools; driver sessions land directly in the field-mode walkthrough
- Live duty/fleet context now drives route, driver, vehicle, capacity and document views, with demo fixtures only as a graceful fallback
- Role-specific three-step product tour from the help action for vendors, drivers and corporate users
- `USABILITY-IMPROVEMENTS.md` — shipped usability decisions, guided vendor/driver walkthroughs and remaining moderated-test gates
- `MOBILE-APP-STRATEGY.md` — application count, Driver v1 scope, mobile readiness assessment and phased delivery plan
- Extended local workflows for tax calculation, approval chains, duty exceptions, passenger access/rating, alerts/geofences, settlements and financial maker-checker
- P0 control-room surfaces for route planning, dispatch offers/replacements, incident response and policy versioning, with tenant-scoped permission checks and explicit lifecycle actions
- Phase 1/2 control-room extensions for a unified master registry, roster versions, live ETA/GPS health, safety evidence and closure approvals, Network activation/replacement/scorecard reconciliation, permission bundles, saved views and idempotent bulk actions
- Mobile Operations home contracts are shared by the web driver mode, dependency-free Driver PWA and React Native Driver surface; forms use visible sections, sticky actions and offline-safe replay
- Mock-first interactions: navigation, filters, search, drawers, modals, toasts, allotment state changes and CSV export

### P0 domain foundation

`backend_p0.py` is an additive local SQLite layer wired before the legacy Network and extended handlers. It provides:

- versioned tenant master records (`duty_types`, `vehicle_groups`, `taxes`, `billing_items`, `labels`, `feedback_forms`, `operating_regions`), list/search/create/edit/archive/restore and audit snapshots;
- sites, shifts, route-plan versions/stops, dispatch assignments, acceptance timers, replacement queue and safe replay keys;
- policy-driven safety incidents, escalation deadlines, evidence/corrective-action records and closure transitions;
- Network regions, invite/vendor approval records, lifecycle governance and evidence-derived scorecard/settlement/dispute contracts;
- tenant permission bundles, explicit deny overrides, authentication checks and cross-tenant ownership enforcement.

The local contract suite is `python3 p0_smoke_test.py`. It covers unauthenticated denial, tenant isolation, duplicate master protection, route-plan publish, assignment acceptance/idempotency, invalid transitions, safety closure, Network region isolation and permission denial.

### Phase 1/2 operational foundation

`backend_phase12.py` is the additive local contract layer for the expanded acceptance scope. It intentionally reuses the canonical Fleet and Network tables rather than creating a second trip ledger:

- `/api/masters/registry` supports all Phase 1 master kinds, search, version history, archive/restore, CSV-shaped import/export and audit events;
- `/api/operations/rosters`, `/api/operations/live-board`, `/api/operations/duties/{id}/eta` and `/api/operations/bulk` provide roster versions, live stale-GPS/deviation signals, deterministic map estimates, tenant-scoped bulk assign/edit/archive and idempotent replay;
- `/api/safety/*` adds evidence attachment registration, hashes, mock object-storage references, stale-location evaluation and maker-checker closure approval;
- `/api/network/v1/*` adds activation gates, replacements, formula-versioned scorecards, disputes and evidence/variance reconciliation;
- `/api/views`, `/api/permissions/bundles`, `/api/mobile/home` and `/api/integrations/*` expose saved views, permission bundles, mobile home data and HRMS/GPS/maps/messaging/storage provider boundaries;
- `phase12_smoke_test.py` validates the new contracts on a fresh database, including tenant isolation, evidence closure and safe idempotent replay.

The UI shows skeleton/retry/empty states, grouped and sticky forms, field-level accessible validation, searchable result/selection counts, mobile-card table equivalents, saved-view reapplication, command search, keyboard shortcuts, audit references and recovery actions. The local fallback remains deterministic when integration credentials are absent. The acceptance contract is documented in `docs/ui-acceptance.md`.

### Phase 3 intelligence moat

`backend_phase3.py` adds the backend-first, additive moat layer without creating a parallel trip ledger:

- deterministic predictive alerts for missed-pickup/ETA/SLA, stale GPS, safety and vendor/service degradation, with model versions, confidence, lead time, factors, source events, acknowledgement, resolution and feedback;
- an invite-only vendor-quality graph over Network profiles, service orders, Fleet duties and scorecards, with explainable dimensions, sample size, confidence, concentration and graph edges;
- idempotent cost/service simulations with stored assumptions, formula versions, vendor mix, demand, distance, wait, capacity/service tradeoffs, currency, FX and emissions output;
- variance findings over invoice calculations, expenses and GPS/rated distance with rule versions, evidence, deduplication, assignment, acknowledgement and resolution;
- sustainability factors, EV eligibility per duty, charging availability and compatibility, reserve/range constraints, localized energy cost, per-duty emissions intensity per passenger-kilometre, baseline/avoided emissions, targets and auditable regional/period reporting;
- controlled country/region profiles with effective localization, timezone, currency, tax, measurement and mock-labelled FX.

The private console exposes this as **Axiom intelligence**. The local contract is `python3 phase3_smoke_test.py`; the production migration and authenticated Edge boundary are documented in `docs/phase3-moat.md` and `supabase/`.

## Run locally

The frontend is dependency-free static HTML/CSS/JavaScript. Use the included Python server for the backend API plus gzip delivery of the inline document and cache headers for assets:

```bash
cd fleetline-mvp
python3 server.py
```

Open `http://localhost:4173`.

For a plain static server, `python3 -m http.server 4173 --bind 0.0.0.0` also works, but the auth forms require `server.py` so `/api` requests reach the backend.

## Local backend

`server.py` serves the frontend and exposes the dependency-free local identity plus One Fleet Live domain API on the same origin:

- `GET /api/health` — backend health and storage status.
- `POST /api/auth/signup` — creates vendor, driver or corporate users and stores role-specific profile data.
- `POST /api/auth/login` — validates email/password, sets an opaque httpOnly session cookie for the web prototype and returns a local mobile session access token.
- Mobile clients can send `Authorization: Bearer <access_token>` to the same organization-scoped API routes.
- `GET /api/auth/me` — returns the authenticated user, organization and profile.
- `PATCH /api/auth/me` — updates profile and organization fields.
- `POST /api/auth/logout` — revokes the current session.
- `GET /api/overview` — returns organization-scoped duty and invoice aggregates.
- `GET/POST /api/customers` — customer directory operations.
- `GET/POST /api/drivers` — driver directory operations.
- `GET/POST /api/vehicles` — vehicle directory operations.
- `GET/POST /api/bookings` — booking intake and listing.
- `GET/POST/PATCH /api/duties` — duty creation, status transitions and listing.
- `POST /api/duties/:id/calculate` — persists the paise-exact calculation snapshot.
- `GET/POST/PATCH /api/invoices` — invoice generation and issue state.
- `POST /api/payments` — payment recording and collection state updates.
- `PATCH /api/duties/:id` — organization operator or assigned driver execution milestones with idempotency keys.
- `POST /api/duties/:id/proof` — OTP, signature, photo metadata and duty-slip proof records.
- `POST /api/duties/:id/track` — organization-scoped location points.
- `POST /api/sync/replay` — offline operation replay with per-user idempotency and conflict-safe results.
- `POST /api/duties/:id/expenses` — offline-capable toll, parking, fuel and other expense records.
- `GET/POST /api/branches`, `/api/suppliers`, `/api/price-books` — organization masters and versioned rates.
- `GET/POST /api/employees`, `/api/employees/import`, `/api/policies` — corporate employee and policy workflows.
- `POST /api/bookings/:id/approve|reject|cancel|assign` — booking approvals and assignment actions.
- `POST /api/invoices/:id/e-invoice|dispatch` — mock e-invoice and invoice dispatch adapters.
- `GET /api/reports/summary`, `/api/audit`, `/api/integrations` — operational reporting, audit and provider health.
- `POST /api/tickets`, `/api/privacy/requests`, `PATCH /api/settings` — support, privacy and workspace controls.
- `POST /api/invitations`, `POST /api/invitations/accept` — organization-scoped one-time driver/operator invitations with mock delivery and email matching.
- `POST /api/bookings/import` — row-level booking batch import for CSV-backed frontend intake.
- `POST /api/auth/password-reset` — non-enumerating password-reset request contract backed by the mock messaging adapter locally and Supabase Auth recovery in production mode.
- `GET/PATCH /api/onboarding`, `POST /api/onboarding/provision` — resumable checklist and tenant provisioning.
- `POST /api/duplicates/check` and `PATCH /api/customers|drivers|vehicles|suppliers/:id` — normalized duplicate detection and soft deactivation.
- `POST /api/price-books/:id/versions|approve`, `/api/bookings/:id/approval-chain`, `/api/approval-steps/:id/decision` — versioning and maker-checker approvals.
- `POST /api/duties/:id/navigation|call|sos|trip-share|reconcile` — field exceptions and mock provider workflows.
- `POST /api/supplier-bills`, `/api/costs`, `/api/vehicle-costs`, `/api/supplier-payouts`, `/api/driver-payouts`, `/api/receipts/allocate`, `/api/financial-actions` — finance and supplier controls.
- `POST /api/tax/calculate`, `GET/POST /api/sla`, `GET /api/updates` — state-aware tax, SLA events and polling fallback.
- `GET/POST /api/bookings/recurring`, `/api/bookings/:id/stops`, `/api/capacity/locks` — recurring, multi-stop and availability controls.
- `GET/POST /api/billing-notes`, `/api/payment-links`, `/api/jobs` — notes, collections links and queued mock workers.
- `GET/POST /api/drivers/preferences`, `/api/devices`, `/api/practice-duties`, `/api/passenger/*`, `/api/alerts`, `/api/geofences`, `/api/webhooks/payments` — driver, passenger, alert and integration contracts.
- `/api/security/2fa`, `/api/security/api-keys`, `/api/security/sessions`, `/api/security/events` — local security-factor, API-key, session and audit contracts.
- `/driver-app/` — standalone mobile-first Axiom Fleet Driver PWA vertical slice with sign-in, demo mode, duty lifecycle, offline queue, sync center, proof, expenses, masked call and SOS controls.
- `GET/POST /api/network/*`, `/api/reports/export|views|schedules|drilldown`, `/api/privacy/consents|retention`, `/api/admin/*` — network, reporting, privacy and operator workflows.
- Phase 1/2 routes include `/api/masters/registry`, `/api/operations/live-board`, `/api/mobile/home`, `/api/safety/monitor`, `/api/network/v1/service-orders/*`, `/api/views`, `/api/operations/bulk` and `/api/integrations/catalog|config|sync|events`.

Data is stored in `data/axiom_fleet.sqlite3` by default. Set `AXIOM_DB_PATH` to use another database location and `PORT` to change the server port. The schema stores organizations, users, role profiles, sessions, audit events, One Fleet Live records and the extended feature ledger. The backend seeds the existing demo vendor account and an operational booking → duty → calculation → invoice loop on first start. Use `deep_feature_smoke_test.py` to validate the extended workflows in a temporary database.

## Supabase target

The production-oriented database/auth foundation is now prepared in `supabase/`:

- `supabase/migrations/20260919000000_axiom_fleet_foundation.sql` — PostgreSQL schema, core and extended tenant tables, RLS policies, permissions and onboarding RPCs.
- `supabase/client.js` — browser adapter used when Supabase configuration is enabled; it covers Auth, profile onboarding, organization-scoped overview, domain collection reads, core RPC writes and the extended finance/reporting/network/privacy/admin workflows.
- `supabase/functions/calculate-duty/index.ts` — authenticated Edge Function for the paise-exact production calculation path.
- `supabase/functions/phase12-orchestrator/index.ts` — authenticated Phase 1/2 boundary for tenant-scoped reads, lifecycle writes, idempotent bulk work and provider events.
- `supabase/config.example.js` — public URL/anon-key configuration template.
- `supabase/README.md` — setup, Auth metadata and security instructions.

Copy `supabase/config.example.js` to `supabase/config.js`, add the Supabase project URL and anon key, apply the migration with `supabase db push`, then restart `server.py`. Until configured, the frontend continues to use the local backend fallback.

## Assumptions and production gates

- The current delivery is a **feature-complete local fallback and Supabase production foundation**, not a claim that a live Supabase project or external provider is configured.
- Seeded operational data and mock provider responses keep the local preview dependency-free while the domain and extended APIs are exercised end to end.
- Local identity remains a development fallback: email/password, SQLite, opaque cookie sessions and an in-process login-failure guard. Production direction remains Supabase Auth plus PostgreSQL/RLS.
- Google OIDC, mobile OTP, TOTP/2FA, SSO/SAML, email verification, native passenger/driver clients and real provider credentials still require project-level delivery.
- The PRD's recommended production stack remains the target: PostgreSQL tenant isolation, Redis-backed sessions/rate limits, async jobs, object storage, mobile SQLite sync, observability and service-level APIs.

## Recommended production handoff sequence

1. Apply the Supabase migration to a non-production project and validate Auth, PostgREST, RLS and the browser adapter.
2. Deploy `phase12-orchestrator` and `calculate-duty`, configure Supabase Storage, email templates and provider secrets without exposing service-role credentials.
3. Expand Workflow Center actions into dedicated supplier, finance, network, passenger and admin screens.
4. Add Realtime plus polling fallback, signed provider webhooks, Redis throttling and production security headers.
5. Run the generated calculation corpus, shadow billing, financial reconciliation, load tests and two-fleet UAT.
6. Build native driver/passenger clients and complete DPDP retention/export/deletion evidence.
7. Only then switch production traffic from the SQLite fallback to the Supabase-backed deployment.

## Important files

- `index.html` — complete clickable prototype; all styling and behavior are inline to keep preview resilient.
- `axiom-fleet-logo.png` — cropped, transparent official Axiom Fleet logo, resized and compressed for the reduced brand treatment.
- `server.py` — dependency-free local fallback backend/API and optimized static server with SQLite, httpOnly sessions, audit events, gzip delivery and cache headers.
- `backend_smoke_test.py` — end-to-end signup/login/profile/logout test for vendor, driver and corporate accounts.
- `domain_engine.py` — paise-exact, explainable duty calculation engine.
- `golden_calculation_test.py` — deterministic generated 1,000-case calculation golden suite.
- `backend_domain.py` — local One Fleet Live domain store for customers, bookings, duties, execution, proof, tracking, expenses, invoices and payments.
- `backend_features.py` — local feature services for branches, suppliers, price books, corporate approvals, notifications, reports, support and privacy.
- `domain_smoke_test.py` — end-to-end booking → duty → calculation → invoice → payment test.
- `execution_smoke_test.py` — driver assignment, execution milestones, offline replay/idempotency, OTP proof and location tracking test.
- `provider_adapters.py` — mock-first payment, messaging, telephony, maps, e-invoice and storage contracts.
- `provider_adapter_test.py` — deterministic mock provider contract tests.
- `feature_smoke_test.py` — branches, suppliers, pricing, employees, policies, approvals, documents, notifications, invitations, tickets, privacy, reports and settings test.
- `uncovered_smoke_test.py` — focused booking-import and password-reset request coverage.
- `deep_feature_smoke_test.py` — broad extended PRD workflow coverage across onboarding, finance, approvals, driver/passenger, alerts, network, reports, privacy and admin.
- `supabase_contract_test.py` — static parity guard for extended Supabase tables, RLS generation and browser route families.
- `p0_smoke_test.py` — isolated P0 domain, transition, idempotency, authorization-negative and tenant-isolation test.
- `supabase/migrations/20260923000000_axiom_p0_foundations.sql` — production-direction P0 tables, indexes, tenant RLS, permission grants and row-level audit triggers.
- `backend_phase12.py` — additive Phase 1/2 local handler for masters, rosters, ETA, safety evidence, Network scorecards, saved views, bulk actions and integrations.
- `phase12_smoke_test.py` — fresh-database Phase 1/2 tenant, lifecycle, evidence, adapter and idempotency smoke suite.
- `supabase/migrations/20260924000000_axiom_phase12_foundations.sql` — Phase 1/2 PostgreSQL tables, permission keys, RLS policies and audit-trigger wiring.
- `openapi.yaml` — published contract for the implemented same-origin API.
- `PRD-GAPS-AND-IMPROVEMENT-PLAN.md` — current feature coverage matrix and production gates.
- `supabase/` — Supabase/PostgreSQL foundation, extended RLS migration, browser adapter and setup documentation.
- `driver-sw.js` and `driver-manifest.json` — dependency-free offline shell for the driver surface.
- `regression_check.py` — repeatable static regression suite for routes, assets, auth contracts and accessibility baselines.
- `REGRESSION-REPORT.md` — latest regression scope and results.
- `data/axiom_fleet.sqlite3` — on-demand local persisted identity database; it is intentionally not stored in the project tree or used for production data.
- `.gitignore` — keeps local database/WAL files and Python caches out of source control.
- `README.md` — scope, assumptions and production handoff sequence.
