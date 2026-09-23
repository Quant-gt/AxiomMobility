# Axiom Fleet UI acceptance contract

The local web surface treats the following as product behavior, not backlog copy. The same boundary is intended for the Supabase-backed surface.

## Operator interaction

- Every operational screen exposes one visually dominant primary action; secondary actions use neutral or soft treatments.
- Initial hydration shows skeleton cards. A failed hydration state preserves the local shell and provides Retry. Empty collections explain the next action.
- Long forms are grouped by purpose, use a sticky modal footer or settings save bar, and keep the save action available while the form scrolls.
- Required fields validate beside the field, set `aria-invalid="true"`, connect the error with `aria-describedby`, focus the first invalid field, and clear the error when corrected.
- Searchable registers expose a live result count, active filter/query and selected-record count.
- Every rendered data table is decorated with header labels and becomes a stacked mobile card at the small-screen breakpoint.
- Duties support bulk assign, bulk status edit and bulk archive. Versioned master records support bulk edit and archive/restore. Bulk jobs are idempotent and tenant-scoped.
- Planning and operations views can be saved to `/api/views` and reapplied from the Saved view selector.
- `Ctrl/Cmd+K` opens the command palette; arrow keys, Enter and Escape are supported.
- Mutation success toasts display an audit reference when the API returns one. Failure toasts expose Retry/recovery behavior.

## Regionalization and accessibility

- Currency, locale, timezone, date formatting, tax/GST/VAT label, distance unit and effective operating region come from the tenant's active Phase 3 localization profile. No operational calculation relies on an Indian rupee default.
- Dialogs expose modal semantics, labelled close controls, focus entry, live validation and keyboard Escape handling. Icon-only controls have accessible labels; decorative SVGs are hidden from assistive technology.
- Static source checks cover the contracts above. Browser/WCAG 2.2 AA verification, screen-reader passes and keyboard-only acceptance remain release-gate checks when a real browser harness is available.

## Sustainability intelligence

- Vehicle records hold additive EV eligibility, battery/range, consumption, connector, power, charging status and localized energy-price fields.
- `POST /api/phase3/sustainability/ev-eligibility` evaluates operational status, passenger capacity, reserve-adjusted required range, remaining range, compatible charging availability, energy, localized cost, baseline emissions, avoided emissions and emissions per passenger-kilometre.
- Charging stations support tenant-scoped CRUD, region/status filtering, connector types, active ports, power and energy price, with audit references on mutations.
- Sustainability trips persist factor-versioned energy, cost, emissions, passenger-kilometre intensity, baseline comparison, avoided emissions, range and charging evidence.
- Period/region reports expose EV share, energy, cost, emissions intensity, baseline/avoided emissions, targets, recommendations, `factor-v1` and `sustainability-report-v2`, plus a report audit reference.

## Release gates

The SQLite fallback is dependency-free and mock-first. Production still requires Supabase migration/RLS execution, Edge runtime validation, authentication and provider configuration, physical Android testing, real push credentials, object storage, and the two-fleet pilot.
