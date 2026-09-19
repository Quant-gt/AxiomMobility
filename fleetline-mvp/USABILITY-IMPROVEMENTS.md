# Axiom Fleet usability pass

**Date:** 19 September 2026  
**Goal:** Make the product easier to learn and operate than a feature-dense fleet back office by reducing first-use decisions and making the next action obvious.

## Changes shipped

### 1. Progressive disclosure in the console

The vendor console now keeps the daily operating loop visible first:

1. Overview / Today
2. Duties board
3. Bookings
4. Billing & receipts
5. Drivers & vehicles

Customers, reports, finance controls, network, admin, security, preview surfaces and settings are grouped behind **More tools**. Opening an advanced page automatically reveals that group, so deep functionality remains reachable without overwhelming a first-time operator.

Driver and corporate sessions receive role-aware navigation. Drivers land directly in Driver app mode and see only the relevant field menu; corporate users see their travel and approval workflow first.

### 2. A three-move operating path

The vendor Overview includes a plain-language **Today's operating path**:

1. Capture the next booking.
2. Clear the duty queue.
3. Check field readiness.

Each step is an action, not a documentation link. The intent is to help a new operator complete a useful loop without learning the whole product first.

### 3. Driver-first field experience

Driver app mode is now the default landing surface for driver users and adapts its greeting, initials, city and assigned duty when live session data is available. The primary action remains one large **Start duty** button. Supporting actions are deliberately limited to:

- Route and saved-offline context
- Add expense
- Masked call
- Safety / SOS
- Visible sync queue

### 4. Live operational context

The duties and fleet surfaces prefer current organization data for route, driver, vehicle, capacity, compliance and sync context. Demo fixtures remain only as a graceful empty/local-preview fallback. This keeps the visual experience trustworthy instead of presenting polished but misleading roster values.

The global help action now opens a role-specific three-step product tour for vendors, drivers and corporate users. Each step can open the relevant surface directly.

### 5. Copy and interaction principles

- Prefer task language: “Clear the duty queue” instead of “Manage execution records”.
- Show one recommended next action before exposing configuration.
- Keep advanced workflows available but out of the first-use path.
- Preserve visible status, ownership and recovery state.
- Make offline state explicit instead of showing an indefinite loading spinner.
- Use the same lifecycle vocabulary across vendor and driver views: assigned, accepted, en route, started, completed.

## Recommended walkthroughs

### Vendor, five-minute walkthrough

1. Open the public site and choose **Sign in to command center**.
2. Use the local prototype access shown on the sign-in card, or choose **Create account → Vendor / fleet operator**.
3. Complete the workspace checklist from the Overview.
4. Follow **Today's operating path**: create a booking, open the duties queue and inspect the duty detail drawer.
5. Open **More tools** only when the operator needs pricing, finance, reports or governance.

### Driver, three-minute walkthrough

1. Sign out and choose **Create account → Driver**.
2. Complete the short field profile including licence number.
3. Sign in or accept a fleet invitation.
4. Driver app mode opens directly to the next duty.
5. Select **Start duty**, add an expense, view the sync queue and test the safety action.
6. Disconnect/reconnect to demonstrate queued replay and idempotent sync.

## Still required for production usability

- Replace the web preview with a dedicated Android/iOS driver client.
- Add real Supabase Realtime or an equivalent location stream and a live map surface.
- Add first-class in-product driver invitation and acceptance screens.
- Replace seeded fleet roster/KPI presentation values with fully hydrated role-specific lists.
- Run moderated usability sessions with one vendor dispatcher, one owner and two drivers; measure time-to-first-booking, time-to-allotment, duty-start errors and offline recovery success.
