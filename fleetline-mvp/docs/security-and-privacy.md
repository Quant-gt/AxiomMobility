# Network security and privacy baseline

- All `/api/network/v1` routes require an authenticated vendor or corporate organization-linked session.
- Buyer records are scoped by `organization_id`; vendor access is granted only through an eligible buyer-owned vendor profile/candidate link.
- Invite-only partner onboarding is enforced server-side; there is no public vendor registration or anonymous lead resale.
- Driver roles cannot manage Network programs, quotes, awards, contracts or settlements.
- Buyer quote list responses omit payload, assumptions and line-item amounts until the buyer creates an immutable comparison snapshot. Vendors can read only their own quote surface.
- Requirement, quote, comparison, award, contract, SLA, check, service-order, scorecard and settlement transitions are audited and version-snapshotted.
- Passed activation checks, scorecards and settlements require evidence.
- Exact employee addresses, bank details and unrelated tenant data are not copied into generic Network responses.
- Supabase production uses RLS, membership/permission helpers and a security-definer activation RPC. The browser never receives a service-role key.

Before production: perform a formal RLS review, object-storage signed URL review, retention/deletion review, vendor contract/DPA review, threat-led penetration testing and two-fleet pilot acceptance. Provider credentials, real push and production storage are release gates.
