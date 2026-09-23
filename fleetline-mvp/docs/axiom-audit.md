# Axiom Fleet audit

Last audited: 2026-09-22

## Repository and runtime

- `server.py` serves the responsive console, APIs and static assets using Python stdlib only.
- `backend_domain.py` owns core customer, driver, vehicle, booking, duty, proof, tracking, expense, invoice and replay contracts.
- `backend_features.py` owns the feature-layer masters, onboarding, notifications, approvals and related workflows.
- `backend_extended.py` owns extended operational, finance, security, passenger, network-edge and reporting contracts.
- `supabase/migrations/` mirrors the production direction with Postgres tables, RLS and RPCs.
- `supabase/client.js` routes protected browser requests to Supabase REST/RPC.
- `mobile-driver/` contains the Expo Driver app with bearer auth, offline queue, background location, camera/signature proof and push registration.
- `driver-app/` is the dependency-free Driver PWA contract surface.

## Existing strengths

- Tenant/organization scoping and role checks exist in the local fallback.
- Core duty state transitions, proof, location, expenses and idempotent replay exist.
- Supabase RLS/RPC foundation exists.
- Local and Supabase device binding/push-token contracts exist.
- Assignment/SOS push queueing and replay tests exist.
- Static server caching, ETags, SQLite WAL and mobile request timeouts are implemented.
- Test coverage includes regression, smoke, domain, provider, native contract and replay/push checks.

## Important gaps against the master prompt

1. Existing Network support is a shallow edge/offer/bid/settlement flow, not a governed RFP-to-service-order lifecycle.
2. No versioned transport requirements, quote line items, comparison snapshots, awards, contracts, SLAs or activation checks exist in the local domain.
3. Existing `domain_network_*` and Supabase `network_*` models do not enforce vendor eligibility, quote immutability, tenant/program visibility or service-order handoff.
4. No explainable matching run or hard-filter result model exists.
5. Network scorecards and settlement records lack evidence linkage and metric definitions.
6. Employee, shift, site and fixed-route foundations are partial; full transport demand integration remains future work.
7. Media remains URI/metadata based in the native proof flow.
8. Push delivery remains queued/mock-provider based pending production credentials and a worker/Edge Function.
9. Supabase migration has not been deployed from this environment.
10. A physical Android device and controlled Driver pilot are unavailable here.

## Recommended next slice

Implement the controlled Axiom Network MVP as additive domain contracts in local SQLite and Supabase:

```text
program → requirement/version → vendor eligibility → match run/candidates
→ immutable structured quotes → comparison snapshot → approved award
→ contract/SLA → service-order activation into a duty/route configuration
→ evidence-backed scorecard and settlement statement
```

Do not remove existing edge/offer routes; retain them as compatibility aliases and document the migration path.
