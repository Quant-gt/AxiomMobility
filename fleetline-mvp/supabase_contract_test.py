#!/usr/bin/env python3
"""Static parity guard for the production Supabase foundation and browser adapter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
migration = (ROOT / "supabase/migrations/20260919000000_axiom_fleet_foundation.sql").read_text()
network_migration = (ROOT / "supabase/migrations/20260922000000_axiom_network_mvp.sql").read_text()
p0_migration = (ROOT / "supabase/migrations/20260923000000_axiom_p0_foundations.sql").read_text()
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
p0_tables = [
    "p0_role_permissions", "p0_master_records", "p0_master_versions", "p0_sites", "p0_shifts",
    "p0_route_plans", "p0_route_stops", "p0_roster_assignments", "p0_replacements", "p0_safety_policies",
    "p0_safety_incidents", "p0_safety_actions", "p0_network_regions", "p0_network_vendor_approvals",
    "p0_network_quote_evaluations", "p0_network_metric_observations", "p0_network_scorecard_runs",
    "p0_network_disputes", "p0_network_corrective_actions", "p0_network_settlement_statements"
]
p0_routes = [
    "supabaseP0Request", "p0-orchestrator", "p0_master_records", "p0_route_plans",
    "p0_roster_assignments", "p0_safety_incidents", "p0_role_permissions"
]
assert all(f"public.{name}" in p0_migration for name in p0_tables), "P0 Supabase tables missing"
assert all(marker in client for marker in p0_routes), "P0 Supabase browser mappings missing"
assert "p0_audit_row" in p0_migration and "p0_role_permissions" in p0_migration, "P0 audit/permission foundation missing"
assert "network_requirements add column if not exists deadline_at" in p0_migration, "Network lifecycle deadline extension missing"
phase12_migration = (ROOT / "supabase/migrations/20260924000000_axiom_phase12_foundations.sql").read_text()
phase12_function = (ROOT / "supabase/functions/phase12-orchestrator/index.ts").read_text()
phase12_tables = [
    "phase12_events", "phase12_versions", "phase12_master_records", "phase12_roster_versions", "phase12_eta_snapshots",
    "phase12_safety_evidence", "phase12_closure_approvals", "phase12_network_replacements", "phase12_scorecard_formulas",
    "phase12_scorecard_disputes", "phase12_reconciliations", "phase12_permission_bundles", "phase12_saved_views",
    "phase12_bulk_jobs", "phase12_integrations", "phase12_integration_events",
]
phase12_routes = [
    "/api/masters/registry", "/api/mobile/home", "/api/operations/live-board", "/api/operations/bulk",
    "/api/safety/monitor", "/api/network/v1/scorecard-formulas", "/api/views", "/api/permissions/bundles",
    "/api/integrations/catalog",
]
assert all(f"public.{name}" in phase12_migration for name in phase12_tables), "Phase 1/2 Supabase tables missing"
assert all(marker in phase12_function for marker in phase12_routes), "Phase 1/2 Edge Function routes missing"
assert "organization_id is not null" in phase12_migration and "is_platform_user()" in phase12_migration, "Phase 1/2 tenant policy guard missing"
assert "idempotency_key" in phase12_function and "getUser" in phase12_function and "phase12_events" in phase12_function, "Phase 1/2 Edge Function security/idempotency boundary missing"
phase3_migration = (ROOT / "supabase/migrations/20260925000000_axiom_phase3_moat.sql").read_text()
phase3_function = (ROOT / "supabase/functions/phase3-orchestrator/index.ts").read_text()
phase3_tables = [
    "phase3_region_catalog", "phase3_emission_factors", "phase3_events", "phase3_predictive_alerts", "phase3_alert_feedback",
    "phase3_vendor_quality_snapshots", "phase3_vendor_quality_edges", "phase3_simulations", "phase3_variance_findings",
    "phase3_sustainability_trips", "phase3_sustainability_targets", "phase3_charging_stations", "phase3_regions", "phase3_exchange_rates",
]
phase3_routes = [
    "/api/phase3/predictive-alerts", "/api/phase3/vendor-quality/graph", "/api/phase3/simulations",
    "/api/phase3/variance/findings", "/api/phase3/sustainability/summary", "/api/phase3/sustainability/report",
    "/api/phase3/sustainability/trips", "/api/phase3/sustainability/charging-stations", "/api/phase3/sustainability/ev-eligibility",
    "/api/phase3/regions", "/api/phase3/localization", "/api/phase3/fx/convert", "/api/phase3/tax/preview",
]
assert all(f"public.{name}" in phase3_migration for name in phase3_tables), "Phase 3 Supabase tables missing"
assert all(marker in phase3_function for marker in phase3_routes), "Phase 3 Edge Function routes missing"
assert "phase3-orchestrator" in client and "supabasePhase3Request" in client, "Phase 3 browser boundary missing"
assert "has_permission" in phase3_migration and "organization_id is not null" in phase3_migration and "p0_audit_row" in phase3_migration, "Phase 3 RLS/audit guard missing"
assert "idempotency_key" in phase3_function and "getUser" in phase3_function and "predictive-v1" in phase3_function, "Phase 3 security/idempotency/model boundary missing"
assert "ev-eligibility" in phase3_function and "charging_station" in phase3_function and "sustainability-report-v2" in phase3_function, "Phase 3 EV/charging/report parity missing"
assert "ev_eligible" in phase3_migration and "energy_consumption_kwh_per_km" in phase3_migration and "available_ports" in phase3_migration, "Phase 3 additive EV vehicle/charging fields missing"
print(f"PASS Supabase parity contracts: {len(tables)} tables, {len(route_markers)} route families, {len(p0_tables)} P0 tables, {len(phase12_tables)} Phase 1/2 tables, {len(phase3_tables)} Phase 3 tables, RLS guard present")
