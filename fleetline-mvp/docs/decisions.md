# Architecture decisions

## ADR-001 — Preserve the hybrid migration

Keep the current Axiom Fleet web console, local SQLite fallback, Supabase adapter, Driver PWA and native Driver app. Add Network contracts rather than rewriting existing routes.

## ADR-002 — Closed B2B Network

Axiom Network is invite-only and governed. Public registration, consumer marketplace behavior, anonymous lead resale, financial escrow and autonomous awards are disabled by design.

## ADR-003 — Network is not an operational source of truth

Network award/service-order records hand into Axiom Fleet bookings and duties, which remain the source for dispatch, GPS, proof, billing and operational status. Trips are not duplicated in Network tables.

## ADR-004 — Deterministic matching first

Hard eligibility filters precede explainable scoring. No AI/autonomous award logic is introduced in the MVP.

## ADR-005 — Immutable commercial snapshots

Submitted quote versions, normalized quote lines, comparison snapshots and cross-entity award/contract/SLA/check/scorecard/settlement snapshots are append-only. Revisions create versions.

## ADR-006 — Mock-first providers

Maps, communications, storage, finance and vendor partner integrations remain adapters with mock implementations until credentials and contracts are available.

## ADR-007 — Supabase RPC for activation

The production handoff is an atomic security-definer RPC so a Network award cannot partially create a Fleet booking/duty. The local handler mirrors that transaction boundary; migration deployment remains a release gate.
