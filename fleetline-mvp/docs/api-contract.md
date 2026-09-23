# Axiom Network API contract

The governed module is additive under `/api/network/v1`. Existing `/api/network/*` edge, offer, bid and settlement routes remain compatibility routes and are not reinterpreted as the governed MVP.

All routes require an authenticated organization-linked `vendor` or `corporate` session. There is no public vendor registration route. A vendor profile must be created by a buyer tenant from an invite. Production Supabase clients use the same resource names through RLS and security-definer orchestration; the local fallback uses the SQLite handler in `backend_network.py`.

## Feature flag and closed partner directory

- `GET /api/network/v1/feature-flag`
- `POST /api/network/v1/feature-flag` — `{ "enabled": true|false }`
- `GET|POST /api/network/v1/invites`
- `POST /api/network/v1/invites/{id}/accept`
- `POST /api/network/v1/invites/{id}/revoke`
- `GET|POST /api/network/v1/vendor-profiles`

Vendor profile creation requires a buyer-owned `invite_id`. The profile stores cities, service types, vehicle types, capabilities, capacity and compliance evidence.

## Programs and versioned requirements

- `GET|POST /api/network/v1/programs`
- `GET /api/network/v1/programs/{id}`
- `POST /api/network/v1/programs/{id}/activate`
- `POST /api/network/v1/programs/{id}/pause`
- `GET|POST /api/network/v1/programs/{program_id}/requirements`
- `GET /api/network/v1/requirements/{id}`
- `POST /api/network/v1/requirements/{id}/versions`
- `POST /api/network/v1/requirements/{id}/versions/{version}/publish`
- `POST /api/network/v1/requirements/{id}/match`

A match is only valid against a published requirement version. Matching applies deterministic hard filters first—profile state, city, service type, vehicle type, capacity, capabilities and compliance—then stores a versioned, explainable score and exclusion reasons.

## Quotes and buyer comparison

- `GET|POST /api/network/v1/requirements/{id}/quotes`
- `GET|POST /api/network/v1/requirements/{id}/comparisons`
- `GET /api/network/v1/comparisons/{id}`

Quote submissions accept an `idempotency_key`, a `quote` object and `assumptions`. Submitted versions are immutable; a revision creates a new version and supersedes the prior current version. Quote payloads, assumptions and normalized line items remain hidden from buyer list responses until an immutable comparison snapshot is created. Vendors can read only their own quote surface.

## Award, contract, SLA and activation gate

- `GET|POST /api/network/v1/requirements/{id}/awards`
- `GET /api/network/v1/awards/{id}`
- `POST /api/network/v1/awards/{id}/approve`
- `GET /api/network/v1/awards/{id}/checks`
- `POST /api/network/v1/awards/{id}/checks/{check_key}`
- `POST /api/network/v1/contracts/{id}/sign`
- `POST /api/network/v1/awards/{id}/activate`

Awards begin as `pending_approval`. Approval creates a draft contract, SLA rows and blocking checks: `contract_signed`, `vendor_compliance`, `capacity_confirmed` and `dispatch_ready`. Passing a check requires evidence. Activation is rejected until every blocking check passes and the contract is signed.

## Fleet handoff and evidence

- `GET /api/network/v1/service-orders`
- `GET /api/network/v1/service-orders/{id}`
- `GET|POST /api/network/v1/service-orders/{id}/scorecards`
- `GET|POST /api/network/v1/service-orders/{id}/settlements`
- `GET /api/network/v1/events`

Activation creates one Axiom Fleet booking and one Fleet duty, linked by the service order. Network does not become a parallel trip source of truth. Scorecards and settlements require evidence; settlement net is calculated as gross less deductions.

## Idempotency and failure semantics

Mutating command routes accept `idempotency_key` where replay is meaningful. A replay returns the original item with `duplicate: true` rather than creating a second requirement match, quote version, comparison, award, service order, scorecard or settlement. Errors use the existing local JSON format: `{ "ok": false, "error": "...", "code": "..." }`.

Tenant ownership, role checks, quote confidentiality and lifecycle transitions are enforced server-side. Exact employee addresses, vendor financial data and unrelated tenant records are not returned by the Network routes.
