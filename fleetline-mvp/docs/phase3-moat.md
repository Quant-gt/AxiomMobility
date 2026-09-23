# Axiom Fleet Phase 3 · Build the moat

Phase 3 is an additive, backend-first intelligence layer. It does not replace Fleet's canonical duties, bookings, drivers, vehicles, invoices or GPS evidence, and it does not create a second Network trip ledger. All derived rows are tenant-scoped, versioned and auditable.

## Local fallback

`backend_phase3.py` is dependency-free and is initialized after the Phase 1/2 schema in `server.py`. It uses deterministic mock-first calculations and the same replaceable provider boundary as the rest of the local backend.

| Capability | Local route family | Stored evidence / version |
|---|---|---|
| Predictive alerts | `/api/phase3/predictive-alerts` | `model_version`, risk score, confidence, lead time, factors, source event IDs, lifecycle, feedback |
| Vendor-quality graph | `/api/phase3/vendor-quality/graph` | invite-only Network profiles, service orders, duties, scorecards, dimensions, sample size, confidence, concentration, graph edges, `vendor-quality-v1` |
| Cost/service simulation | `/api/phase3/simulations` | idempotency key, assumptions, formula version, baseline/modeled cost, sensitivity, service level, emissions |
| Variance detection | `/api/phase3/variance` | invoice, expense and GPS/rated-distance comparisons, rule version, severity, evidence, deduplication, assignment and resolution |
| Sustainability | `/api/phase3/sustainability` | EV eligibility, passenger capacity/status constraints, charging stations/ports/connectors/power/price, reserve-adjusted range, energy cost, trip emissions, g/passenger-km intensity, baseline/avoided emissions, targets and period/region reports, `factor-v1` / `sustainability-report-v2` |
| Regional operations | `/api/phase3/regions`, `/api/phase3/localization`, `/api/phase3/fx`, `/api/phase3/tax/preview` | controlled region catalog, effective default profile, locale/timezone/currency/tax/measurement, explicit FX source |

### Predictive coverage

The deterministic evaluator evaluates active duties for:

- missing or stale GPS;
- ETA / SLA deviation;
- late-start and missed-pickup risk;
- unresolved safety cases;
- vehicle compliance expiry;
- degraded quality on a linked invite-only Network service order.

An alert is not an autonomous dispatch decision. Operators acknowledge, resolve and give feedback through explicit lifecycle routes.

### Simulation contract

Amounts are integer minor units and the output retains the input assumptions. A scenario may specify demand, distance, duration, vendor mix, fuel/driver/waiting cost, capacity/service penalty, currency and carbon price. Reusing the same tenant and `idempotency_key` returns the stored result rather than mutating another scenario.

### Regional contract

The initial catalog is deliberately controlled: India Maharashtra, India Karnataka, Dubai, Singapore and London. A tenant can activate a catalog profile and configure effective settings or FX rates; arbitrary country codes are rejected. Market rates are not implied: absent a configured rate, the local preview labels the deterministic rate `mock_fx`.

## Supabase production boundary

The production migration is `supabase/migrations/20260925000000_axiom_phase3_moat.sql`. It adds the `phase3_*` tables, controlled catalogs, permissions, tenant RLS policies, audit triggers and indexes. The authenticated Edge boundary is:

- `supabase/functions/phase3-orchestrator/index.ts`
- `supabase/client.js` → `supabasePhase3Request` → `phase3-orchestrator`

The Edge function uses the caller's JWT with the Supabase anon key. It never accepts a service-role key from the browser. The RLS policy model requires both tenant membership and the appropriate `phase3.*` permission; drivers receive only the read contracts needed for field context.

## Validation

```bash
python3 phase3_smoke_test.py
python3 supabase_contract_test.py
python3 -m py_compile server.py backend_phase3.py
```

The browser console exposes the layer as **Axiom intelligence**. It provides operator actions for predictive evaluation, graph recomputation, variance scanning, simulation, emissions calculation and localization selection. The interface remains a read/decision surface; canonical operational mutations continue to use existing Fleet and Network workflows.

## Production gates

Before release, execute the Supabase migration and Edge deployment against a real project, run RLS and authenticated multi-tenant tests, configure approved provider adapters, object storage and push delivery, validate FX/tax/factor governance, perform physical Android testing and complete the two-fleet pilot. Local mock success is not a production approval.
