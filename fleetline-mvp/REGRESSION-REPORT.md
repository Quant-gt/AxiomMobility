# Axiom Fleet — Regression Test Report

**Test date:** 22 September 2026
**Build:** `/home/user/fleetline-mvp`  
**Architecture:** Axiom Fleet console + Driver PWA + Expo Driver client + Supabase production foundation + dependency-free SQLite fallback

## Final result

**PASS — 83/83 static, HTTP and interaction-contract checks.**

Phase 1/2 and Phase 3 SQLite coverage, provider-boundary tests, frontend JavaScript syntax checks and Supabase contract checks pass. The result is a complete local/mock-first implementation; Supabase project application, browser/WCAG verification and physical Android/pilot gates remain explicitly open.

The following end-to-end local suites also passed after the extended feature layer was integrated:

- `backend_smoke_test.py`
- `domain_engine_test.py`
- `golden_calculation_test.py` (1,000/1,000 generated cases)
- `domain_smoke_test.py`
- `execution_smoke_test.py`
- `provider_adapter_test.py`
- `feature_smoke_test.py`
- `uncovered_smoke_test.py`
- `deep_feature_smoke_test.py`
- `supabase_contract_test.py`
- `mobile_driver_contract_test.py`
- `p0_smoke_test.py`
- `phase12_smoke_test.py`
- `phase3_smoke_test.py` (predictive alerts, graph, simulations, variance, sustainability, regions and tenant isolation)
- `phase3_ev_smoke_test.py` (EV eligibility, charging availability, range, energy cost, passenger-kilometre intensity, avoided emissions and reporting)
- `supabase_contract_test.py` (including Phase 1/2/3 tables, RLS guards and authenticated Edge Function boundaries)
- `regression_check.py` acceptance contracts for loading/recovery, validation, mobile cards, bulk workflows, saved views, command search, audit references and regionalization.
- `docs/ui-acceptance.md` product acceptance contract.

Browser/WCAG 2.2 AA verification and Expo/Android export remain release-gate checks when the corresponding toolchain is available.

The deep suite now covers onboarding and provisioning, duplicate checks, master deactivation, employee lifecycle, price-book version approval, recurring and multi-stop bookings, capacity locks, multi-level booking approvals, duty exceptions, navigation, masked calling, SOS, supplier bills, fleet costs, payouts, financial approvals, tax calculation, billing notes, public payment links, e-invoice cancellation, receipt allocation, payment webhooks, driver preferences/devices/practice, passenger access/rating, alerts/geofences, polling updates, local TOTP/API-key security, queued jobs, associate network, settlements, report exports/views/schedules, privacy request fulfillment, retention, admin KPIs and feature flags. Phase 1/2 adds unified masters/import-export/versioning, rosters, ETA/GPS health, safety evidence and maker-checker closure, Network formula/dispute/reconciliation, saved views, permission bundles, mobile home and HRMS/GPS/maps/messaging/storage boundaries. Phase 3 adds deterministic predictive factors and lifecycle feedback, invite-only vendor-quality graph, idempotent cost/service simulation, reconciliation variance findings, sustainability factors/targets and controlled multi-country localization/FX/tax contracts.

Python compilation and JavaScript syntax checks also passed for the backend, extended layer, tests, inline console script and Supabase browser adapter.

## Live local HTTP validation

The live fallback server was restarted on `0.0.0.0:4173` and validated with:

- Root document: HTTP 200, `text/html`.
- Supplied logo: HTTP 200, `image/png`.
- Health route: HTTP 200, JSON.
- Gzip delivery: enabled; current response was 464,771 bytes raw and 103,351 bytes compressed.
- `regression_check.py`: **83/83 passed**.
- Authenticated live route probe: `/api/auth/me`, `/api/supplier-bills`, `/api/network/edges`, `/api/admin/kpis`, `/api/security/2fa` and `/api/privacy/requests` all returned HTTP 200.

## Implemented feature layer

### Local fallback backend

- `backend_extended.py` owns the extended PRD workflows and initializes its SQLite schema.
- `server.py` imports the extended layer, initializes it before serving, dispatches extended route families before existing handlers, and recognizes all added API prefixes.
- Organization ownership checks, role checks, idempotency behavior, audit events and mock provider references are applied in the local path.
- `/api/updates` provides a cursor-based polling fallback for duty and alert changes.
- `/api/tax/calculate` performs state-aware CGST/SGST versus IGST splitting in paise.
- `/api/sla` supports event creation and resolution.
- Recurring bookings, multi-stop route plans, capacity locks, billing notes, payment links, queued jobs, security factors/API keys, employee lifecycle and public payment-link capture are implemented with auditable local records.

### Phase 1/2 local and production boundary

- `backend_phase12.py` is wired before compatibility handlers and keeps Fleet duties/bookings canonical while adding the unified registry, roster versions, live ETA/GPS health, safety evidence/closure approvals, Network activation/replacement/scorecard/reconciliation, saved views, bulk idempotency, mobile home and provider boundaries.
- `provider_adapters.py` now has deterministic HRMS and GPS/telematics adapters alongside maps, messaging, storage, telephony, payment and e-invoice mocks.
- `supabase/migrations/20260924000000_axiom_phase12_foundations.sql` mirrors the additive tables, permission keys, tenant RLS and audit trigger contracts.
- `supabase/functions/phase12-orchestrator/index.ts` is the authenticated Supabase Edge Function boundary expected by `supabase/client.js`; it covers registry import/export, rosters/ETA/bulk, safety, Network, views, bundles, mobile home and integrations without service-role credentials in browser code.
- The native Driver client hydrates `/api/mobile/home` into its Today screen while retaining offline replay, sticky quick actions and safety controls.

### Phase 3 moat layer

- `backend_phase3.py` is initialized after Phase 1/2 and before compatibility handlers. It keeps Fleet canonical while projecting deterministic alerts, vendor quality, simulations, variance findings, sustainability and localization.
- `phase3_smoke_test.py` passed on a fresh database with two tenant signups, idempotent replay, alert lifecycle/feedback, emissions targets, controlled region rejection, tenant isolation, FX and tax previews.
- `supabase/migrations/20260925000000_axiom_phase3_moat.sql` adds the production tables, controlled region/emission catalogs, permissions, RLS policies and conditional audit triggers.
- `supabase/functions/phase3-orchestrator/index.ts` is the authenticated JWT/anon-key Edge boundary; `supabase/client.js` routes `/api/phase3/*` through it when Supabase is enabled.
- The private console exposes **Axiom intelligence** with evaluation, scan, simulation, emissions and localization actions. Local calculations remain mock-labelled and deterministic until approved providers and factor/FX governance are configured.

### Supabase production direction

`supabase/migrations/20260919000000_axiom_fleet_foundation.sql` now includes extended tenant tables for:

- Onboarding state, record versions and duplicate matches.
- Supplier bills, cost entries, receipt allocations, payouts and financial actions.
- Approval steps, SLA events, trip shares and passenger ratings.
- Driver preferences, devices, calls, SOS events and practice duties.
- Alerts, geofences, notification events and webhook events.
- Network edges/offers/bids/settlements.
- Report exports/views/schedules.
- Consent receipts, retention locks, privacy requests and security events.
- Recurring bookings, booking stops, capacity locks, billing notes, payment links, jobs, auth factors, API keys and security events.

Each extended table has RLS enabled, authenticated grants and organization/member or user-scoped policies. The migration keeps the existing Auth, memberships, core domain tables and RPCs intact.

`supabase/client.js` now supports the onboarding/provisioning path and browser-side adapters for the extended financial, reporting, network, alert, tax, update, retention and admin KPI workflows. It continues to fall back to same-origin local APIs when Supabase is disabled.

A live Supabase project has not been connected or migration-tested because project URL, anon key and project credentials were not supplied. That is an environment gate, not a local implementation failure.

### Console exposure

- Onboarding progress is hydrated from `/api/onboarding` and can be completed from a server-persisted modal.
- The Overview quick actions now include a Workflow Center.
- Dedicated Finance controls, Network & partners, Admin health, Security & privacy and Passenger view pages hydrate from extended APIs.
- Progressive navigation keeps Overview, Duties, Bookings, Billing and Fleet visible while grouping advanced tools behind More tools; driver sessions land in Driver app mode.
- Overview now presents a three-move Today operating path: capture booking, clear duty queue and check field readiness.
- Driver app mode adapts to the signed-in driver, assigned-duty data and local sync queue; the help button opens a role-specific three-step product tour.
- `/driver-app/` now exposes a mobile-first Driver PWA vertical slice with sign-in/demo mode, duty lifecycle, offline queue, sync center, proof, expenses, masked call and SOS controls.
- `mobile-driver/` contains the Expo/React Native foundation for the same Driver flow, with secure mobile tokens, foreground location, notifications, offline replay and Android/iOS build configuration.
- Duties and fleet surfaces now hydrate route, driver, vehicle, capacity and document context from live organization data before falling back to demo fixtures.
- Workflow Center actions invoke supplier-bill, fleet-cost, driver-payout, report-export, network-edge, retention, updates, security and KPI endpoints using the current organization session.
- Existing Axiom Fleet public pages, protected route guard, logo, seeded demo account and private console navigation remain intact.

## Optimization and delivery checks

- Supplied transparent Axiom Fleet logo remains in six expected surfaces.
- Logo asset is 640×184 and 65,271 bytes, below the 100 KB target.
- Local static assets and script references resolve.
- Gzip compression and cache headers remain active.
- Static form labels, route templates, hash routing and authentication bindings remain green.

## Validation commands

```bash
python3 regression_check.py
python3 uncovered_smoke_test.py
python3 backend_smoke_test.py
python3 domain_engine_test.py
python3 golden_calculation_test.py
python3 domain_smoke_test.py
python3 execution_smoke_test.py
python3 provider_adapter_test.py
python3 feature_smoke_test.py
python3 deep_feature_smoke_test.py
python3 supabase_contract_test.py
python3 mobile_driver_contract_test.py
python3 p0_smoke_test.py
python3 phase12_smoke_test.py
python3 phase3_smoke_test.py
python3 -m py_compile server.py backend_domain.py backend_features.py backend_extended.py backend_p0.py backend_phase12.py backend_phase3.py domain_engine.py provider_adapters.py
npm run typecheck  # from mobile-driver/
npx expo export --platform android --output-dir /tmp/axiom-fleet-export  # from mobile-driver/
node --check /tmp/axiomfleet-regression.js
node --check /tmp/driver-app.js
node --check supabase/client.js
npx esbuild supabase/functions/phase12-orchestrator/index.ts --bundle --external:https://* --outfile=/tmp/phase12-orchestrator.js && node --check /tmp/phase12-orchestrator.js
npx esbuild supabase/functions/phase3-orchestrator/index.ts --bundle --external:https://* --outfile=/tmp/phase3-orchestrator.js && node --check /tmp/phase3-orchestrator.js
```

## Known production gates

- Apply and validate the Supabase migration against a real project with Auth and RLS.
- Configure Storage policies, Edge Functions, email templates and provider webhook secrets.
- Replace mock payment, messaging, maps, telephony and e-invoice adapters when credentials and compliance approvals are available.
- Add native driver/passenger clients, Supabase Realtime, Redis-backed distributed throttling, production observability and security review.
- Complete pilot UAT, load/performance, retention-worker and DPDP fulfillment validation.

The correct release description is: **feature-complete local fallback with a Supabase production foundation; not yet a live production deployment.**
