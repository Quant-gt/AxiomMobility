# Axiom Fleet — Regression Test Report

**Test date:** 19 September 2026  
**Build:** `/home/user/fleetline-mvp`  
**Architecture:** Axiom Fleet console + Supabase production foundation + dependency-free SQLite fallback

## Final result

**PASS — 48/48 static, HTTP and interaction-contract checks.**

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

The deep suite now covers onboarding and provisioning, duplicate checks, master deactivation, employee lifecycle, price-book version approval, recurring and multi-stop bookings, capacity locks, multi-level booking approvals, duty exceptions, navigation, masked calling, SOS, supplier bills, fleet costs, payouts, financial approvals, tax calculation, billing notes, public payment links, e-invoice cancellation, receipt allocation, payment webhooks, driver preferences/devices/practice, passenger access/rating, alerts/geofences, polling updates, local TOTP/API-key security, queued jobs, associate network, settlements, report exports/views/schedules, privacy request fulfillment, retention, admin KPIs and feature flags.

Python compilation and JavaScript syntax checks also passed for the backend, extended layer, tests, inline console script and Supabase browser adapter.

## Live local HTTP validation

The live fallback server was restarted on `0.0.0.0:4173` and validated with:

- Root document: HTTP 200, `text/html`.
- Supplied logo: HTTP 200, `image/png`.
- Health route: HTTP 200, JSON.
- Gzip delivery: enabled; current response was 362,680 bytes raw and 81,447 bytes compressed.
- `regression_check.py`: **47/47 passed**.
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
python3 -m py_compile server.py backend_domain.py backend_features.py backend_extended.py domain_engine.py provider_adapters.py
node --check /tmp/axiomfleet-regression.js
node --check /tmp/driver-app.js
node --check supabase/client.js
```

## Known production gates

- Apply and validate the Supabase migration against a real project with Auth and RLS.
- Configure Storage policies, Edge Functions, email templates and provider webhook secrets.
- Replace mock payment, messaging, maps, telephony and e-invoice adapters when credentials and compliance approvals are available.
- Add native driver/passenger clients, Supabase Realtime, Redis-backed distributed throttling, production observability and security review.
- Complete pilot UAT, load/performance, retention-worker and DPDP fulfillment validation.

The correct release description is: **feature-complete local fallback with a Supabase production foundation; not yet a live production deployment.**
