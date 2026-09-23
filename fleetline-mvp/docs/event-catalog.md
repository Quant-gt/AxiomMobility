# Axiom Network event catalog

The local ledger is `domain_network_events`; Supabase uses `network_events` and the shared audit ledger. Event payloads identify the aggregate and retain rule/version/evidence references without copying unrelated tenant data.

| Event | Emitted when |
|---|---|
| `invite.created`, `invite.accepted`, `invite.revoked` | Buyer partner access changes |
| `vendor_profile.created` | An invited supplier profile is approved for the buyer directory |
| `program.created`, `program.activated`, `program.paused` | Program lifecycle changes |
| `requirement.created` | Requirement header and draft version are created |
| `requirement.version_created` | A new draft demand version is added |
| `requirement.published` | A buyer publishes a demand version |
| `matching.completed` | Deterministic hard filters and explainable scoring finish |
| `quote.submitted` | Vendor submits an immutable quote version |
| `comparison.created` | Buyer stores an immutable comparison snapshot |
| `award.created`, `award.approved` | Selection is proposed and then explicitly approved |
| `activation_check.passed`, `activation_check.failed`, `activation_check.waived` | Readiness evidence changes |
| `contract.signed` | Commercial contract moves from draft to signed |
| `service_order.activated` | Approved award passes gates and hands off into Fleet |
| `scorecard.submitted` | Evidence-backed period review is recorded |
| `settlement.created` | Evidence-backed reconciliation draft is created |

Every mutating action also writes the existing Axiom Fleet audit ledger. Version snapshots in `domain_network_record_versions`/`network_record_versions` capture award, contract, SLA, check, service-order, scorecard and settlement changes. Correlation IDs and provider references remain production integration concerns until the worker/edge deployment is configured.
