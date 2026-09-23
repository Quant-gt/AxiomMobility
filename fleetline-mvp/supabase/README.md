# Axiom Fleet Supabase foundation

This directory contains the Supabase/PostgreSQL foundation selected for the production-oriented backend transition.

## Included

- `migrations/20260919000000_axiom_fleet_foundation.sql`
  - Supabase Auth profile trigger
  - Vendor/corporate organizations and branches
  - Driver profiles
  - Memberships and one-time invitations with acceptance RPCs
  - Permission matrix and RLS helpers
  - Append-only audit event foundation
  - Customers, suppliers, drivers and vehicles
  - Price books
  - Bookings, duties, duty events and duty proofs
  - GPS points and offline sync operations
  - Invoices, invoice lines, expenses and payments
  - Employees, travel policies, booking approvals and organization settings
  - Documents, notifications, support tickets and privacy requests
  - Notifications, integration events, mock e-invoice records and collection actions
  - Core RLS policies, including visibility for billing-provider records
  - Extended tenant-scoped tables for onboarding state, duplicate matches, supplier bills, costs, payouts, financial approvals, approval chains, SLA events, passenger ratings, devices, calls/SOS, alerts/geofences, network offers/bids/settlements, report exports/views/schedules, consent/retention locks, webhook events, recurring bookings, multi-stop routes, capacity locks, billing notes, payment links, queued jobs, auth factors, API keys and security events
  - Idempotent RLS policy generation for the extended tables
  - Organization and driver onboarding RPCs
  - Atomic duty transitions and paise-snapshot persistence RPCs
  - Immutable invoice issue and idempotent payment recording RPCs

- `migrations/20260923000000_axiom_p0_foundations.sql`
  - Versioned tenant master records and master snapshots
  - Sites, shifts, route plans/stops, roster assignments, replacements and dispatch events
  - Safety policies, incidents and corrective actions
  - Closed Network regions, vendor approvals, quote evaluations, messages, metric observations, scorecard runs, corrective actions, disputes and settlement statements/lines
  - Tenant permission overrides integrated into `has_permission`
  - P0-specific indexes, RLS policies and security-definer audit triggers
  - Additive lifecycle columns for Network requirements

- `migrations/20260924000000_axiom_phase12_foundations.sql`
  - Unified Phase 1 master registry and version/audit records for all requested kinds
  - Roster versions, ETA snapshots and operational bulk jobs
  - Safety evidence, storage references, closure approvals and stale-location evaluation records
  - Network activation/replacement records, formula-versioned scorecards, disputes and reconciliation
  - Versioned permission bundles, saved views and provider configuration/event ledgers
  - Permission keys, tenant RLS policies and conditional audit-trigger wiring for every Phase 1/2 table

The P0 and Phase 1/2 browser mappings live in `supabase/client.js`. Reads use tenant-scoped PostgREST collections; cross-aggregate lifecycle commands are sent to authenticated `p0-orchestrator` and `phase12-orchestrator` Edge Function boundaries so publish, activation, evidence closure, scorecard and reconciliation commands can remain atomic in production. The Edge Function deployments and their RPC/transaction implementations are still release gates; this workspace does not claim a live Supabase deployment.

## Edge function

`functions/calculate-duty/index.ts` is the production calculation path for the current paise-exact engine. Deploy it after the migration with `supabase functions deploy calculate-duty`; it validates the caller's session and persists the snapshot through `save_duty_calculation`.

`functions/phase12-orchestrator/index.ts` is the authenticated Phase 1/2 boundary used by `supabase/client.js`. It covers the unified registry (including import/export), rosters/live board/ETA and idempotent bulk refresh, safety evidence/closure approvals, Network activation/replacements/scorecards/reconciliation, saved views, permission bundles, mobile home and provider configuration/events. It uses the caller bearer token and anon key so RLS and `has_permission` remain in force; it does not contain service-role credentials. Deploy it with:

```bash
supabase functions deploy phase12-orchestrator
```

The local SQLite handler remains the fallback when Supabase is not configured. The function's provider responses are mock-mode contracts until project secrets and real provider workers are configured.

## Apply to a Supabase project

1. Create a Supabase project in the intended region.
2. Enable the Auth providers required for the first release.
3. Install the Supabase CLI and authenticate it.
4. Link the local directory to the Supabase project.
5. Apply the migration:

```bash
supabase db push
```

The exact project ref and credentials must be supplied by the project owner; they are intentionally not stored in this repository.

## Auth metadata contract

When creating a user with Supabase Auth, include these metadata keys so the profile trigger can initialize the profile:

```json
{
  "full_name": "Aditi Rao",
  "phone": "+91 90000 00000",
  "account_type": "vendor"
}
```

Allowed account types are `vendor`, `driver` and `corporate`.

After a vendor or corporate user has a valid authenticated session, call the `create_organization` RPC to create the organization, default branch and owner membership atomically. For an independent driver, call `create_driver_profile`. Organization operators can call `create_invitation` to generate a hashed, expiring one-time token; the invited Auth user then calls `accept_invitation` from the matching email account to create the active membership.

## Security notes

- Supabase Auth owns password hashing, access tokens and refresh tokens.
- Application tables are protected with RLS; the client must never send a tenant ID as an authority claim.
- Service-role keys must stay server-side and must never be placed in the browser.
- The migration is a foundation and still needs a Supabase security review before production data is loaded.
- Storage buckets, Edge Functions, email templates, provider secrets, scheduled jobs and production observability still need project-level configuration.
