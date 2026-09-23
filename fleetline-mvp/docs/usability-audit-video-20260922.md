# Internal dashboard walkthrough usability audit

Date: 2026-09-22

Source reviewed: the 4:43 mobile dashboard walkthrough shared by the product owner (`tOf6euYZ0as`). The video was reviewed as a product/interaction reference, not as a claim that the other product's implementation should be copied.

## What the walkthrough shows

The reference dashboard has a simple mobile-first information architecture:

- A persistent organization header and hamburger menu.
- First-class navigation for Dashboard, Operations, Reports, Masters, Network and Location Tracking.
- Masters used as the place for vehicles, employees, pricing, duty types, fuel rules and other reference data.
- Long create/edit forms for vehicles, drivers and employees.
- Searchable/selectable lists for duty types, cities and extra billing items.
- A compact booking entry surface.

The walkthrough also exposes usability problems that should not be copied:

- Large blank/loading areas make the app look broken or slow.
- The red demo-expiry banner occupies valuable mobile space.
- Form sections are visually flat and require excessive scrolling.
- Save/update actions are easy to miss at the end of long forms.
- Small typography and table layouts are difficult to use on a phone.
- List overlays do not consistently show search, selection, count or confirmation state.
- Several screens appear to rely on generic controls rather than workflow-specific validation.

## Axiom comparison

Before this change, Axiom Fleet had stronger operational cards and audit foundations but weaker master-data discoverability:

- Masters was not a first-class navigation item.
- Vehicles were displayed mainly as driver assignments.
- The Vehicles tab on the Fleet page was cosmetic; it did not open a vehicle register.
- There was an Add Driver modal but no equivalent complete Add Vehicle workflow.
- Vehicle records only captured registration, type, make/model, city and status locally.
- Suppliers and branches had APIs but no usable master screens.
- The mobile shell collapsed the desktop sidebar, but did not provide a focused mobile master workflow.

## Changes shipped in this slice

### First-class Masters workspace

- Added a visible Masters item to the protected sidebar.
- Added grouped master navigation for Operations, Commercial, Fleet, People and Locations.
- Added search across master areas.
- Clearly labels connected areas versus areas that are not yet implemented instead of presenting dead links.
- Added setup summary counts from live tenant-scoped data.

### Vehicle register

- Added a real Vehicles master screen.
- Added server-backed search and status filtering.
- Added desktop table and mobile card layouts.
- Added vehicle count, availability, on-duty and compliance-gap summaries.
- Added edit actions and empty/loading-friendly states.
- Added registration, vehicle group, make/model, type, year, city, branch, fuel, seating, luggage, ownership, GPS and status fields.
- Added RC, insurance and PUC expiry dates.
- Added operational notes.
- Added duplicate registration validation per tenant.
- Added additive local SQLite migration for the extended vehicle fields.
- Kept compatibility with `/api/vehicles` and Supabase's existing `vehicle_group`, `year` and `compliance` columns.

### Supplier and branch registers

- Added usable supplier and branch/dispatch-centre registers.
- Added create flows for both.
- Reused the existing tenant-scoped APIs and audit behavior.

### Bulk vehicle import

- Added a small CSV import flow with preview, row limit, required-field validation and per-row success/failure feedback.

## Remaining usability work

This change closes the most visible Masters gap, but it does not complete the whole product. The next usability slices should be:

1. Convert duty types, vehicle groups, taxes and billing items into the same master framework.
2. Add document upload, expiry reminders and renewal actions rather than only date fields.
3. Add full employee/passenger and feedback-form masters.
4. Replace generic long modals with step sections, sticky save actions and inline field errors.
5. Add a mobile operations home with the next decision, urgent exceptions and one-tap actions.
6. Remove or tenant-configure the persistent demo banner outside demo mode.
7. Replace blank loading regions with skeletons, retry states and explicit empty states.
8. Add moderated usability tests with dispatchers, fleet owners and drivers before expanding scope.

## Product interpretation

The video supports the conclusion that user dissatisfaction is likely driven more by **findability, waiting states, form density and unclear next actions** than by the absence of more dashboard metrics. The product should make the daily decision path obvious first, then expose advanced master data through consistent, searchable workflows.
