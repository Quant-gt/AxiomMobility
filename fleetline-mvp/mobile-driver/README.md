# Axiom Fleet Driver mobile client

This directory is the native cross-platform Driver app foundation. It is designed for Expo/React Native and produces Android and iOS builds from one codebase. `eas.json` contains development, internal preview and production build profiles.

## Current vertical slice

- Secure token-based mobile sign-in using `expo-secure-store`.
- Today screen with one-duty-at-a-time workflow and `/api/mobile/home` summary/alert hydration.
- Read-only Phase 3 native data contracts for predictive alerts and sustainability summaries (`src/types.ts` / `src/api.ts`); operator acknowledgement, simulations and regional writes remain on the authenticated web/Edge boundary.
- Assigned, accepted, started and completed duty transitions.
- OTP proof completion.
- Expense capture.
- Foreground and background location tracking while a duty is en route or started.
- Camera receipt/proof capture and signature proof capture.
- Push token registration, assignment/SOS notification handling and masked-call contracts.
- Offline queue persisted with AsyncStorage.
- Exactly-once replay through `/api/sync/replay`.
- Sync center and visible pending-action state.
- Driver profile and notification/location context.

The browser-testable equivalent is available at `/driver-app/` in the local Axiom Fleet server. It uses the same API contracts and is useful before native build tooling is installed.

## Run locally

```bash
npm install
EXPO_PUBLIC_API_URL=http://YOUR-LAN-IP:4173 npm start
```

A real phone cannot call the computer's `localhost`; use the development machine's LAN IP or a deployed HTTPS API. The local fallback now returns an `access_token` for mobile clients and accepts `Authorization: Bearer ...` in addition to the web cookie session.

## Validation completed in this workspace

```bash
npm install
npm run typecheck
npx expo-doctor
npx expo export --platform android --output-dir /tmp/axiom-fleet-export
cd ..
python3 mobile_driver_contract_test.py
python3 mobile_driver_replay_test.py
python3 deep_feature_smoke_test.py
```

The typecheck, Expo Doctor, Android bundle export, contract suite, replay/push HTTP test and deep feature smoke test pass. `node_modules/` and generated exports are local build artifacts and are not required in source control.

## Physical Android run

A connected Android device and Android SDK are required; they are not available in the current environment. On a development machine:

```bash
# from mobile-driver/
EXPO_PUBLIC_API_URL=http://YOUR-LAN-IP:4173 npx expo run:android --device
```

Before launching, start the API on an address reachable from the phone (`0.0.0.0`, same LAN, or deployed HTTPS), allow the Android firewall port, and use the phone's **LAN IP**, never `localhost`. Grant foreground location, background location, camera and notifications when prompted. Confirm the Android foreground-service notification appears only during an active duty.

## Physical test matrix and release gate

1. Sign in, download an assigned duty, accept → en route → started, capture GPS and complete with OTP, photo and signature.
2. Airplane mode: queue status/proof/expense/SOS and location points; reconnect and confirm all replay exactly once.
3. Force-stop/restart: verify the action queue, location buffer and session recover without duplicate events.
4. Weak signal: confirm visible pending state, retry recovery, push receipt and no lost GPS points.
5. Background execution: lock the screen and move during an active duty; verify points arrive. End the duty and verify background tracking stops.
6. Reassign the duty and raise SOS; verify the registered driver/control-room devices receive the correct notifications.
7. Repeat with at least two real drivers and record battery, crash, sync, GPS freshness and proof-completion evidence.

Do not begin Passenger native development until this matrix is passed by a controlled driver pilot. Production push credentials, object storage/signed uploads and a notification worker remain required before store release.
