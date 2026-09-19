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

## Edge function

`functions/calculate-duty/index.ts` is the production calculation path for the current paise-exact engine. Deploy it after the migration with `supabase functions deploy calculate-duty`; it validates the caller's session and persists the snapshot through `save_duty_calculation`.

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
