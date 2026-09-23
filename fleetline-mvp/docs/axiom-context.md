# Axiom Fleet context

Last audited: 2026-09-22

```yaml
product_name: Axiom Fleet
product_family: Axiom Fleet
network_name: Axiom Network
network_module_enabled: feature-flagged; local preview enabled for development only
network_mode: closed_b2b_controlled
network_vertical: employee_transport
network_pilot_city: TBD; Bengaluru is the recommended validation city, not yet approved
network_pilot_geography: TBD
network_vendor_approval_required: true
network_public_registration: false
portal_url: local preview at http://localhost:4173
repository_url: https://github.com/Quant-gt/AxiomMobility.git
existing_repository_path: /home/user/fleetline-mvp
existing_frontend_stack: dependency-free HTML/JS console and Driver PWA; Expo React Native Driver app
existing_backend_stack: Python stdlib ThreadingHTTPServer, SQLite local fallback, Supabase REST/RPC adapter
existing_database: SQLite local fallback; Supabase/Postgres production direction
existing_authentication: local cookie plus bearer sessions; Supabase Auth production adapter
existing_mobile_apps: Driver native Expo slice; Driver PWA; no Passenger native app
existing_gps_providers: mock adapter; native Expo location
existing_hrms_integrations: mock/local contract only
existing_finance_integrations: mock/local contract only
current_customer_count: seeded/demo data only
current_vehicle_count: seeded/demo data only
expected_daily_trips: TBD
expected_concurrent_users: TBD
target_countries: [India]
target_cities: TBD
primary_currency: INR
primary_locale: en-IN
primary_timezone: Asia/Kolkata
compliance_scope: [India DPDP Act, applicable transport rules, GDPR where applicable]
```

## Safe assumptions

- Existing local routes and Supabase migration contracts are compatibility surfaces. New Network routes will be additive and versioned through route contracts rather than renaming existing tables.
- Axiom Network is invite-only and tenant-scoped. It is not public registration, a consumer marketplace or anonymous lead resale.
- External maps, messaging, telephony, storage and payment integrations remain mock-first until credentials and provider contracts are supplied.
- The first engineering slice is backend/domain-first: requirement → eligibility/match → structured quote → award → service-order activation → scorecard/settlement evidence.
- No Passenger native implementation starts before the Driver pilot is accepted.

## Blockers requiring product decisions later

- Approved pilot tenant, city and vendor cohort.
- Commercial fee/commission model and legal contracting model.
- Exact HRMS, GPS, map, finance and notification providers.
- Production Supabase project credentials and Edge Function/worker deployment.
- Retention periods and legal approval for address, GPS and incident data.
