# Axiom Fleet mobile application strategy

**Decision:** Proceed with mobile development now, starting with one cross-platform Driver application. The first executable vertical slice is available at `/driver-app/` as a mobile-first PWA so the duty loop can be tested immediately; the native client will reuse the same contracts. Keep the vendor, corporate, network and admin experiences in the responsive web console. Add a native Passenger application only if pilot usage proves that scoped web/PWA links are insufficient.

## Application map

| Surface | Form factor | Release decision | Why |
|---|---|---|---|
| Vendor / fleet operator console | Responsive web | Existing product | Dispatch, bookings, fleet, pricing, finance, reports and governance need larger-screen density and shared links. |
| Corporate travel console | Responsive web | Existing product | Booking requests, policy approvals, employee travel and invoice verification are naturally web/SSO workflows. |
| Driver app | One cross-platform native codebase producing Android and iOS builds | **Build now** | Requires background location, offline queue, push notifications, camera/proof capture, low-bandwidth behavior, SOS and device controls. |
| Passenger trip experience | Scoped responsive web/PWA first | Build after driver pilot | A secure trip link is faster to adopt than an app install. Native passenger app is optional and should be evidence-led. |
| Network / associate fleet | Web console | No separate app | Partner offers, bids and settlements belong in the operator workflow; drivers use the same Driver app. |
| Platform admin | Web console | No separate app | Governance, support and tenant controls are desktop-oriented. |

### Count

- **Product surfaces:** 2 core applications now: the web console and the Driver mobile app.
- **Native mobile applications now:** 1 cross-platform Driver app.
- **Store binaries:** 2 deliverables from that one codebase: Android and iOS.
- **Optional later:** 1 Passenger app, only after pilot evidence.
- Vendors, corporates, associate fleets and platform admins should not receive separate native apps in the first release.

## Driver v1 scope

### Authentication and readiness

- Supabase Auth or production mobile session handoff with rotating refresh tokens.
- Vendor invitation acceptance and driver organization association.
- Device registration, revoke, session list and minimum-version check.
- Role-specific onboarding: profile, licence, language, quiet hours, notification consent and location consent.

### Duty loop

1. Sign in and download the next duty manifest.
2. View passenger, route, pickup window, vehicle and policy instructions.
3. Accept duty.
4. Start duty with one primary action.
5. Send location points in the background with visible battery/network state.
6. Record en route, arrived, passenger onboard and completed milestones.
7. Capture OTP, signature, photo, odometer and expenses.
8. Queue every mutation offline with an idempotency key.
9. Replay on reconnect and expose failures clearly.
10. Trigger masked call, trip share or SOS without leaving the duty.

### Navigation model

- One active duty at a time.
- Four bottom-level destinations maximum: Today, Duties, Inbox/Sync and Profile.
- One primary action per duty state.
- No finance, reporting, pricing or admin surfaces in the Driver app.
- Large tap targets, short labels, Hindi/English-ready copy and explicit offline mode.

## Readiness assessment

### Already available in this workspace

- Organization-scoped duty APIs and role checks.
- Driver status transitions, proof, tracking, expenses and SOS routes.
- Offline replay contract with idempotency and conflict-safe results.
- Local device binding and driver preferences.
- Driver manifest/service worker and a role-aware Driver app mode walkthrough.
- Mock maps, telephony, messaging, storage and notification adapters.
- Supabase schema/client parity for the production direction.
- Native Driver scaffold with sign-in, assigned-duty download, lifecycle transitions, durable offline action replay, camera/signature/OTP proof, permission-gated foreground/background location and push-token registration.
- Assignment/reassignment and SOS notification queueing for registered local devices, plus Supabase trigger/RPC contracts in `supabase/migrations/20260919000001_push_dispatch.sql`.
- Repeatable local HTTP replay/push test in `mobile_driver_replay_test.py`.

### Current implementation status — 19 Sep 2026

- **Automated validation:** native TypeScript check, Expo Android bundle export, Expo Doctor, Python contract tests, deep feature smoke and the native-driver replay/push HTTP test all pass.
- **Physical-device validation:** not run here. This environment has no connected Android device, so Android permission prompts, background task execution after app kill, notification delivery, airplane mode, weak signal, battery behavior and LAN API reachability remain open.
- **Production hardening:** media remains URI/metadata based until object storage and signed-upload policy are supplied; push delivery is queued/mock-provider based until Expo/FCM/APNs credentials and a worker/Edge Function are configured.
- **Release gate:** run the physical Android matrix and controlled driver pilot before starting Passenger native work.

### Required before production mobile release

- Replace mock adapters with approved maps, push, telephony and messaging providers, and configure the notification worker/Edge Function.
- Move camera/signature evidence to encrypted object storage with compression, signed URLs, retention and consent controls.
- Add Realtime or a robust location transport alongside the polling fallback, plus battery/network coaching.
- Add crash reporting, analytics, remote config, app version enforcement and staged rollout.
- Complete DPDP notices/consents, data deletion/export behavior and safety review.
- Test Android low-end devices, iOS background behavior, airplane mode, weak signal, app kill/restart and duplicate replay on physical devices.
- Complete a two-fleet pilot before store-wide release.
- Do not begin a Passenger native app until the Driver pilot evidence is accepted.

## Recommended delivery sequence

### Phase 0 — Mobile foundation

Finalize API versioning, mobile session contracts, device/revoke behavior, event names, sync envelopes, permission copy and analytics events.

### Phase 1 — Driver vertical slice

The native slice now covers Today → assigned-duty download → lifecycle → permission-gated GPS → durable offline queue → reconnect replay → OTP/photo/signature proof, push registration and SOS. The local HTTP replay test is the automated gate; physical Android validation is next.

### Phase 2 — Field completeness

Replace mock push/storage adapters, add signed media uploads, navigation handoff, masked-call provider wiring, localization, battery coaching and production observability without changing the driver contract.

### Phase 3 — Pilot hardening

Run two fleets, measure duty-start success, sync recovery, battery use, GPS freshness, proof completion, notification receipt and crash-free sessions. Fix workflows before adding a Passenger app.

## Acceptance targets

- Driver reaches the next duty in under 10 seconds after sign-in.
- Driver starts an assigned duty in under 15 seconds.
- At least 99% of offline operations replay exactly once.
- Location freshness is visible and policy-compliant.
- 90% of test drivers complete the duty loop without dispatcher help.
- Crash-free sessions exceed 99.5% during pilot.
- A Passenger app is approved only if scoped web/PWA usage creates a measurable adoption or support problem.
