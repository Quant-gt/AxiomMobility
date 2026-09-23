# Axiom Fleet architecture

## Current architecture

Axiom Fleet is a modular monolith at the local edge with a Supabase/Postgres production target.

```text
Console / Driver PWA / Native Driver
              │
       API route contracts
              │
  Python local domain handlers ── SQLite WAL
              │
  Supabase browser adapter ───── REST/RPC/RLS
              │
  Provider adapters / future workers
```

## P0 operations boundary

`backend_p0.py` is an additive domain layer shared by the console and future Driver/Network clients. It is intentionally placed before compatibility handlers in `server.py` so the existing public/private surfaces and legacy route contracts remain stable. Its local source of truth is SQLite; the production mapping is the additive `p0_*` Supabase schema plus an authenticated `p0-orchestrator` Edge Function for atomic multi-write transitions.

The layer keeps Fleet duties/bookings/drivers/vehicles canonical. Route plans reference those duties rather than creating parallel trips. Safety incidents retain deadlines, evidence and corrective-action state. Network sourcing remains closed and invite-only; region, approval, scorecard and settlement records are tenant scoped and auditable.

## Network module boundary

Axiom Network owns sourcing and governance records only:

- closed tenant programs and operating regions;
- requirement headers and immutable versions;
- invite-controlled vendor profiles;
- eligibility/match runs with hard-filter reasons and explainable scores;
- immutable quotes, normalized quote lines and buyer comparison snapshots;
- controlled awards, contracts, SLAs and activation checks;
- service orders, scorecards, settlements, events and version snapshots.

Axiom Fleet remains the source of truth for:

- organizations, vendors, drivers, vehicles and employees;
- bookings, routes, duties, trips and GPS;
- incidents, notifications, billing evidence and shared audit history.

Activation creates one Fleet booking and one Fleet duty and stores those IDs on the Network service order. Network does not duplicate trip state.

## Local implementation pattern

- `backend_network.py` creates additive `domain_network_*` tables and routes.
- `server.py` dispatches `/api/network/v1/...` before compatibility `/api/network/...` routes.
- Helpers enforce tenant ownership, invite/role access, state transition, quote confidentiality and idempotency.
- Every mutating action writes the shared audit ledger, Network event ledger and relevant immutable version snapshot.
- Existing compatibility routes remain available and are not treated as the governed MVP.

## Supabase implementation pattern

- `20260922000000_axiom_network_mvp.sql` adds UUID tables, tenant foreign keys and RLS.
- `network_activate_award` owns the critical atomic Fleet handoff; complex match/comparison/award orchestration is deliberately an edge/RPC deployment boundary.
- Browser code calls REST/RPC only; no service-role key is shipped to the browser.
- Provider delivery remains adapter/worker territory.

## Reliability and release posture

- Commands accept idempotency keys where replay can create duplicates.
- Submitted quote versions and comparison snapshots are immutable.
- Award, contract, SLA, check, service-order, scorecard and settlement changes are version-snapshotted and audited.
- Activation is blocked until signed-contract and evidence-backed readiness checks pass.
- Supabase deployment, provider credentials, physical-device validation and pilot evidence remain release gates.
