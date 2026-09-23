# Integration matrix

| Integration | Current state | Adapter boundary | Production blocker |
|---|---|---|---|
| Supabase Auth/Postgres | additive Network migration + local parity handler | REST/RPC/RLS; `network_activate_award` RPC; future `network-orchestrator` edge adapter | project credentials, migration/RLS deployment and edge deployment |
| Maps/routing | deterministic mock | `provider_adapters.py` | provider contract/key |
| GPS/telematics | native location + mock | normalized Fleet track point | physical device/provider |
| Push/SMS/email | queued/mock | messaging adapter | credentials/worker |
| Storage | URI/metadata mock | storage adapter | object storage/signed upload |
| HRMS | contract only | sync adapter | customer HRMS choice |
| Finance/ERP | mock/local billing | finance adapter | ERP/contract choice |
| Network vendor systems | invite-only capability profile only | future partner adapter | approved vendor APIs, SLAs and credentials |

Axiom Network does not create a separate operational trip system. Activation writes to the existing Fleet booking/duty boundary. All integrations need scoped credentials, timeout/retry/idempotency, correlation IDs, dead-letter handling and reconciliation before production.
