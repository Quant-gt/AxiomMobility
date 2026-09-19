#!/usr/bin/env python3
"""Static parity guard for the production Supabase foundation and browser adapter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
migration = (ROOT / "supabase/migrations/20260919000000_axiom_fleet_foundation.sql").read_text()
client = (ROOT / "supabase/client.js").read_text()

tables = [
    "onboarding_states", "record_versions", "duplicate_matches", "supplier_bills", "cost_entries",
    "receipt_allocations", "payouts", "financial_actions", "approval_steps", "sla_events",
    "trip_shares", "passenger_ratings", "driver_preferences", "device_bindings", "calls", "sos_events",
    "practice_duties", "alerts", "geofences", "notification_events", "network_edges", "network_offers",
    "network_bids", "settlements", "report_exports", "report_views", "report_schedules", "consents",
    "retention_locks", "webhook_events", "booking_stops", "recurring_bookings", "capacity_locks",
    "billing_notes", "payment_links", "jobs", "auth_factors", "api_keys", "security_events",
]
route_markers = [
    "route === '/api/onboarding'", "route === '/api/tax/calculate'", "route === '/api/updates'",
    "supplier-bills", "driver-payouts", "financial-actions", "networkRoute", "route === '/api/reports/export'",
    "route === '/api/privacy/retention'", "route === '/api/admin/kpis'", "recurringRoute", "stopsRoute",
    "capacityRoute", "billing-notes", "payment-links", "jobRun", "auth_factors", "api_keys",
]
missing_tables = [name for name in tables if f"public.{name}" not in migration]
missing_routes = [marker for marker in route_markers if marker not in client]
assert not missing_tables, f"missing migration tables: {missing_tables}"
assert not missing_routes, f"missing adapter routes: {missing_routes}"
assert "foreach t in array" in migration and "enable row level security" in migration, "extended tables must enable RLS"
assert "drop policy if exists" in migration and "create policy" in migration, "extended policy generation missing"
assert "supabaseDomainRequest" in client and "AxiomSupabaseAdapter" in client, "browser adapter missing"
print(f"PASS Supabase parity contracts: {len(tables)} tables, {len(route_markers)} route families, RLS guard present")
