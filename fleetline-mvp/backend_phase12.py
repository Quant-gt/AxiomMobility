"""Phase 1 and Phase 2 additive foundations for Axiom Fleet.

This module keeps the dependency-free local fallback honest while filling the
operational seams around the existing Fleet/Network/P0 handlers. It provides:

* a unified master registry and import/export/version contract;
* roster/live-board/ETA and bulk operation contracts;
* safety evidence, closure approval and stale-GPS monitoring;
* Network activation gates, replacement workflows, formula-versioned scorecards
  and reconciliation;
* saved views, mobile home data and integration configuration/event contracts.

It deliberately uses the existing domain tables as sources of truth. Production
writes that span multiple aggregates should move behind Supabase RPCs or the
p0-orchestrator Edge Function; the local implementation remains deterministic
and mock-provider backed.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from backend_domain import DEFAULT_PROVIDERS, DomainError, _audit, new_id, now_iso
from backend_p0 import _has_permission, _org, _owned, _role, _row, _text, _user_id


MASTER_REGISTRY_KINDS = {
    "duty_types", "vehicle_groups", "taxes", "billing_items", "documents",
    "labels", "employees", "passengers", "feedback_forms", "branches",
    "operating_regions", "suppliers", "drivers", "vehicles", "rate_cards",
    "sites", "shifts",
}

STAFF_ROLES = {"vendor", "corporate", "platform"}


def _json(value, fallback):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _body_json(payload: dict, key: str, fallback):
    value = payload.get(key)
    return value if isinstance(value, type(fallback)) else fallback


def _parse(raw_route: str):
    parsed = urlsplit(raw_route)
    return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)


def _limit(query, default=100):
    try:
        return min(max(int(query.get("limit", [default])[0] or default), 1), 500)
    except (TypeError, ValueError):
        return default


def _staff(user):
    if _role(user) not in STAFF_ROLES:
        raise DomainError(403, "This workflow is restricted to organization operators", "role_forbidden")


def _require(conn, user, permission: str):
    if not _has_permission(conn, user, permission):
        raise DomainError(403, f"Permission required: {permission}", "permission_denied")


def _phase_audit(conn, user, action, entity_type, entity_id, ip, metadata=None):
    _audit(conn, user, action, entity_type, entity_id, ip, metadata or {})
    conn.execute(
        "INSERT INTO phase12_events(id, organization_id, event_type, entity_type, entity_id, payload_json, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id("phaseevt"), _org(user), action, entity_type, entity_id, json.dumps(metadata or {}), _user_id(user), now_iso()),
    )


def _version(conn, user, entity_type, entity_id, snapshot, change_type, ip):
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS version FROM phase12_versions WHERE organization_id = ? AND entity_type = ? AND entity_id = ?",
        (_org(user), entity_type, entity_id),
    ).fetchone()
    version = int(row["version"] or 0) + 1
    version_id = new_id("phasever")
    conn.execute(
        "INSERT INTO phase12_versions(id, organization_id, entity_type, entity_id, version, change_type, snapshot_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (version_id, _org(user), entity_type, entity_id, version, change_type, json.dumps(snapshot), _user_id(user), now_iso()),
    )
    _phase_audit(conn, user, f"{entity_type}.{change_type}", entity_type, entity_id, ip, {"version": version})
    return {"id": version_id, "version": version, "change_type": change_type, "snapshot": snapshot}


def initialize_phase12_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS phase12_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            actor_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_events_org_time ON phase12_events(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS phase12_versions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            snapshot_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, entity_type, entity_id, version)
        );

        CREATE TABLE IF NOT EXISTS phase12_master_records (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            version INTEGER NOT NULL DEFAULT 1,
            effective_from TEXT,
            effective_to TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, kind, code)
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_masters_org_kind ON phase12_master_records(organization_id, kind, status);

        CREATE TABLE IF NOT EXISTS phase12_roster_versions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            route_plan_id TEXT NOT NULL,
            plan_date TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            assignments_json TEXT NOT NULL DEFAULT '[]',
            constraints_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, route_plan_id, version)
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_rosters_org_date ON phase12_roster_versions(organization_id, plan_date, status);

        CREATE TABLE IF NOT EXISTS phase12_eta_snapshots (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            duty_id TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'mock_maps',
            latitude REAL,
            longitude REAL,
            distance_km REAL NOT NULL DEFAULT 0,
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            eta_at TEXT,
            deviation_minutes INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'estimated',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_eta_duty_time ON phase12_eta_snapshots(organization_id, duty_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS phase12_safety_evidence (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            incident_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            storage_path TEXT NOT NULL DEFAULT '',
            source_event_id TEXT,
            sha256 TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            captured_by TEXT,
            captured_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_evidence_incident ON phase12_safety_evidence(organization_id, incident_id, captured_at DESC);

        CREATE TABLE IF NOT EXISTS phase12_closure_approvals (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            incident_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_by TEXT,
            reviewed_by TEXT,
            review_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            reviewed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS phase12_network_replacements (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            service_order_id TEXT NOT NULL,
            duty_id TEXT,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            replacement_driver_id TEXT,
            replacement_vehicle_id TEXT,
            due_at TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_phase12_network_replacements ON phase12_network_replacements(organization_id, service_order_id, status);

        CREATE TABLE IF NOT EXISTS phase12_scorecard_formulas (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            code TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            weights_json TEXT NOT NULL DEFAULT '{}',
            thresholds_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, code, version)
        );
        CREATE TABLE IF NOT EXISTS phase12_scorecard_disputes (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scorecard_run_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            resolution_note TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS phase12_reconciliations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            service_order_id TEXT NOT NULL,
            scorecard_run_id TEXT,
            statement_id TEXT,
            expected_paise INTEGER NOT NULL DEFAULT 0,
            observed_paise INTEGER NOT NULL DEFAULT 0,
            variance_paise INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'review',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS phase12_permission_bundles (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            permissions_json TEXT NOT NULL DEFAULT '[]',
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, role, version)
        );

        CREATE TABLE IF NOT EXISTS phase12_saved_views (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            name TEXT NOT NULL,
            filters_json TEXT NOT NULL DEFAULT '{}',
            columns_json TEXT NOT NULL DEFAULT '[]',
            sort_json TEXT NOT NULL DEFAULT '{}',
            shared INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, scope, name)
        );

        CREATE TABLE IF NOT EXISTS phase12_bulk_jobs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            idempotency_key TEXT,
            operation TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_ids_json TEXT NOT NULL DEFAULT '[]',
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'queued',
            result_json TEXT NOT NULL DEFAULT '[]',
            created_by TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            UNIQUE(organization_id, idempotency_key)
        );

        CREATE TABLE IF NOT EXISTS phase12_integrations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            provider_type TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'mock',
            status TEXT NOT NULL DEFAULT 'available',
            config_json TEXT NOT NULL DEFAULT '{}',
            last_sync_at TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, provider_type)
        );
        CREATE TABLE IF NOT EXISTS phase12_integration_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT,
            provider_type TEXT NOT NULL,
            event_type TEXT NOT NULL,
            external_id TEXT NOT NULL,
            signature_valid INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'received',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(provider_type, external_id)
        );
        """
    )


def _master_snapshot(row):
    return {
        "id": row["id"], "organization_id": row["organization_id"], "kind": row["kind"],
        "code": row["code"], "name": row["name"], "status": row["status"],
        "version": row["version"], "effective_from": row["effective_from"],
        "effective_to": row["effective_to"], "metadata": _json(row["metadata_json"], {}),
    }


def _master_registry(conn, user, method, route, query, payload, ip):
    if route == "/api/masters/registry" and method == "GET":
        _require(conn, user, "masters.read")
        org = _org(user)
        kind = (query.get("kind") or [""])[0]
        q = (query.get("q") or [""])[0].strip().lower()
        sql = "SELECT * FROM phase12_master_records WHERE organization_id = ?"
        args: list[object] = [org]
        if kind:
            sql += " AND kind = ?"; args.append(kind)
        if q:
            sql += " AND (lower(code) LIKE ? OR lower(name) LIKE ?)"; args.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY kind, name LIMIT ?"; args.append(_limit(query))
        rows = conn.execute(sql, args).fetchall()
        return {"ok": True, "items": [_row(row, ("metadata_json",)) for row in rows], "kinds": sorted(MASTER_REGISTRY_KINDS)}
    if route == "/api/masters/registry" and method == "POST":
        _require(conn, user, "masters.write")
        kind = _text(payload, "kind", maximum=60)
        if kind not in MASTER_REGISTRY_KINDS:
            raise DomainError(400, "Unknown master kind", "validation_error")
        code = _text(payload, "code", maximum=100).upper()
        name = _text(payload, "name", maximum=200)
        if not code or not name:
            raise DomainError(400, "kind, code and name are required", "validation_error")
        org = _org(user); now = now_iso(); record_id = new_id("masterreg")
        try:
            conn.execute(
                "INSERT INTO phase12_master_records(id, organization_id, kind, code, name, status, version, effective_from, effective_to, metadata_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
                (record_id, org, kind, code, name, _text(payload, "status", "active", 24), _text(payload, "effective_from", maximum=40) or None, _text(payload, "effective_to", maximum=40) or None, json.dumps(_body_json(payload, "metadata", {})), _user_id(user), now, now),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                raise DomainError(409, "A master with this kind and code already exists", "duplicate_master") from exc
            raise
        row = conn.execute("SELECT * FROM phase12_master_records WHERE id = ?", (record_id,)).fetchone()
        _version(conn, user, "master_registry", record_id, _master_snapshot(row), "created", ip)
        return {"ok": True, "item": _row(row, ("metadata_json",))}
    import_match = re.fullmatch(r"/api/masters/registry/import", route)
    if import_match and method == "POST":
        _require(conn, user, "masters.write")
        records = payload.get("records") if isinstance(payload.get("records"), list) else []
        if not records:
            raise DomainError(400, "records is required", "validation_error")
        results = []
        for index, record in enumerate(records, 1):
            try:
                result = _master_registry(conn, user, "POST", "/api/masters/registry", {}, record if isinstance(record, dict) else {}, ip)
                results.append({"row": index, "status": "imported", "item": result["item"]})
            except DomainError as exc:
                results.append({"row": index, "status": "error", "code": exc.code, "error": str(exc)})
        return {"ok": True, "imported": sum(row["status"] == "imported" for row in results), "failed": sum(row["status"] == "error" for row in results), "rows": results}
    export_match = re.fullmatch(r"/api/masters/registry/export", route)
    if export_match and method == "GET":
        _require(conn, user, "masters.read")
        rows = conn.execute("SELECT kind, code, name, status, version, effective_from, effective_to, metadata_json FROM phase12_master_records WHERE organization_id = ? ORDER BY kind, name", (_org(user),)).fetchall()
        output = io.StringIO(); writer = csv.writer(output); writer.writerow(["kind", "code", "name", "status", "version", "effective_from", "effective_to", "metadata"])
        for row in rows:
            writer.writerow([row["kind"], row["code"], row["name"], row["status"], row["version"], row["effective_from"] or "", row["effective_to"] or "", row["metadata_json"]])
        return {"ok": True, "format": "csv", "filename": f"axiom-master-registry-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.csv", "content": output.getvalue(), "count": len(rows)}
    detail_match = re.fullmatch(r"/api/masters/registry/([^/]+)(?:/(archive|restore))?", route)
    if detail_match:
        record_id, action = detail_match.groups(); org = _org(user)
        row = conn.execute("SELECT * FROM phase12_master_records WHERE id = ? AND organization_id = ?", (record_id, org)).fetchone()
        if not row:
            raise DomainError(404, "Master registry record not found", "not_found")
        if method == "GET":
            versions = conn.execute("SELECT * FROM phase12_versions WHERE organization_id = ? AND entity_type = 'master_registry' AND entity_id = ? ORDER BY version DESC", (org, record_id)).fetchall()
            item = _row(row, ("metadata_json",)); item["versions"] = [_row(version, ("snapshot_json",)) for version in versions]
            return {"ok": True, "item": item}
        _require(conn, user, "masters.write")
        if action and method == "POST":
            target = "archived" if action == "archive" else "active"
            now = now_iso(); conn.execute("UPDATE phase12_master_records SET status = ?, version = version + 1, updated_at = ? WHERE id = ?", (target, now, record_id))
            updated = conn.execute("SELECT * FROM phase12_master_records WHERE id = ?", (record_id,)).fetchone()
            _version(conn, user, "master_registry", record_id, _master_snapshot(updated), target, ip)
            return {"ok": True, "item": _row(updated, ("metadata_json",))}
        if method == "PATCH":
            updates = {}
            for field in ("name", "status", "effective_from", "effective_to"):
                if field in payload: updates[field] = _text(payload, field, maximum=200 if field == "name" else 40)
            if "metadata" in payload: updates["metadata_json"] = json.dumps(_body_json(payload, "metadata", {}))
            if not updates: return {"ok": True, "item": _row(row, ("metadata_json",))}
            updates["version"] = row["version"] + 1; updates["updated_at"] = now_iso()
            values = list(updates.values()) + [record_id, org]
            conn.execute(f"UPDATE phase12_master_records SET {', '.join(f'{field} = ?' for field in updates)} WHERE id = ? AND organization_id = ?", values)
            updated = conn.execute("SELECT * FROM phase12_master_records WHERE id = ?", (record_id,)).fetchone()
            _version(conn, user, "master_registry", record_id, _master_snapshot(updated), "updated", ip)
            return {"ok": True, "item": _row(updated, ("metadata_json",))}
    return None


def _roster_and_live(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/operations/rosters" and method == "GET":
        _require(conn, user, "route_plans.read")
        rows = conn.execute("SELECT * FROM phase12_roster_versions WHERE organization_id = ? ORDER BY plan_date DESC, version DESC LIMIT ?", (org, _limit(query))).fetchall()
        return {"ok": True, "items": [_row(row, ("assignments_json", "constraints_json")) for row in rows]}
    if route == "/api/operations/rosters" and method == "POST":
        _require(conn, user, "route_plans.write")
        route_plan_id = _text(payload, "route_plan_id", maximum=160)
        plan = conn.execute("SELECT * FROM p0_route_plans WHERE id = ? AND organization_id = ?", (route_plan_id, org)).fetchone()
        if not plan: raise DomainError(404, "Route plan not found", "not_found")
        latest = conn.execute("SELECT COALESCE(MAX(version),0) version FROM phase12_roster_versions WHERE organization_id = ? AND route_plan_id = ?", (org, route_plan_id)).fetchone()["version"]
        version = int(latest or 0) + 1; roster_id = new_id("roster"); now = now_iso()
        assignments = payload.get("assignments") if isinstance(payload.get("assignments"), list) else []
        if not assignments:
            assignments = [dict(row) for row in conn.execute("SELECT * FROM p0_roster_assignments WHERE organization_id = ? AND route_plan_id = ? ORDER BY offered_at", (org, route_plan_id)).fetchall()]
        conn.execute("INSERT INTO phase12_roster_versions(id, organization_id, route_plan_id, plan_date, version, status, assignments_json, constraints_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (roster_id, org, route_plan_id, plan["plan_date"], version, _text(payload, "status", "draft", 24), json.dumps(assignments), json.dumps(_body_json(payload, "constraints", {})), _user_id(user), now, now))
        _version(conn, user, "roster", roster_id, {"route_plan_id": route_plan_id, "version": version, "assignments": assignments}, "created", ip)
        return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_roster_versions WHERE id = ?", (roster_id,)).fetchone(), ("assignments_json", "constraints_json"))}
    live_route = route == "/api/operations/live-board" and method == "GET"
    if live_route:
        _require(conn, user, "dispatch.read")
        duties = conn.execute("SELECT d.*, b.booking_reference, b.passenger_name, b.pickup_json, b.dropoff_json, b.scheduled_at FROM domain_duties d LEFT JOIN domain_bookings b ON b.id = d.booking_id WHERE d.organization_id = ? AND d.status NOT IN ('completed','cancelled') ORDER BY COALESCE(d.reporting_at, b.scheduled_at) LIMIT ?", (org, _limit(query))).fetchall()
        items = []
        for duty in duties:
            latest = conn.execute("SELECT * FROM domain_track_points WHERE organization_id = ? AND duty_id = ? ORDER BY recorded_at DESC LIMIT 1", (org, duty["id"])).fetchone()
            assignment = conn.execute("SELECT * FROM p0_roster_assignments WHERE organization_id = ? AND duty_id = ? ORDER BY offered_at DESC LIMIT 1", (org, duty["id"])).fetchone()
            eta = conn.execute("SELECT * FROM phase12_eta_snapshots WHERE organization_id = ? AND duty_id = ? ORDER BY created_at DESC LIMIT 1", (org, duty["id"])).fetchone()
            item = {"duty_id": duty["id"], "booking_reference": duty["booking_reference"], "passenger_name": duty["passenger_name"], "status": duty["status"], "reporting_at": duty["reporting_at"], "scheduled_at": duty["scheduled_at"], "driver_id": duty["driver_id"], "vehicle_id": duty["vehicle_id"], "assignment_status": assignment["status"] if assignment else None, "last_gps": _row(latest) if latest else None, "eta": _row(eta, ("payload_json",)) if eta else None}
            items.append(item)
        return {"ok": True, "items": items, "count": len(items), "updated_at": now_iso()}
    eta_match = re.fullmatch(r"/api/operations/duties/([^/]+)/eta", route)
    if eta_match and method == "POST":
        _require(conn, user, "tracking.read")
        duty_id = eta_match.group(1)
        duty = conn.execute("SELECT d.*, b.pickup_json, b.dropoff_json FROM domain_duties d JOIN domain_bookings b ON b.id = d.booking_id WHERE d.id = ? AND d.organization_id = ?", (duty_id, org)).fetchone()
        if not duty: raise DomainError(404, "Duty not found", "not_found")
        pickup = _json(duty["pickup_json"], {}); dropoff = _json(duty["dropoff_json"], {})
        result = DEFAULT_PROVIDERS.maps.route(pickup=pickup, dropoff=dropoff)
        payload_result = result.payload; eta_at = (datetime.now(timezone.utc) + timedelta(minutes=int(payload_result.get("duration_minutes", 0)))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        snapshot_id = new_id("eta"); conn.execute("INSERT INTO phase12_eta_snapshots(id, organization_id, duty_id, source, latitude, longitude, distance_km, duration_minutes, eta_at, deviation_minutes, status, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (snapshot_id, org, duty_id, result.provider, payload_result.get("points", [{}])[0].get("latitude", payload_result.get("points", [{}])[0].get("lat")), payload_result.get("points", [{}])[0].get("longitude", payload_result.get("points", [{}])[0].get("lng")),  payload_result.get("distance_km", 0), payload_result.get("duration_minutes", 0), eta_at, int(payload.get("deviation_minutes") or 0), _text(payload, "status", "estimated", 24), json.dumps(payload_result), now_iso()))
        return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_eta_snapshots WHERE id = ?", (snapshot_id,)).fetchone(), ("payload_json",))}
    return None


def _safety_phase12(conn, user, method, route, query, payload, ip):
    org = _org(user)
    evidence_match = re.fullmatch(r"/api/safety/incidents/([^/]+)/evidence", route)
    if evidence_match and method in {"GET", "POST"}:
        incident_id = evidence_match.group(1)
        incident = conn.execute("SELECT id FROM p0_safety_incidents WHERE id = ? AND organization_id = ?", (incident_id, org)).fetchone()
        if not incident: raise DomainError(404, "Safety incident not found", "not_found")
        if method == "GET":
            _require(conn, user, "safety.read"); rows = conn.execute("SELECT * FROM phase12_safety_evidence WHERE organization_id = ? AND incident_id = ? ORDER BY captured_at DESC", (org, incident_id)).fetchall(); return {"ok": True, "items": [_row(row, ("metadata_json",)) for row in rows]}
        _require(conn, user, "safety.incidents.manage")
        filename = _text(payload, "filename", maximum=200); content = str(payload.get("content") or ""); raw_hash = _text(payload, "sha256", maximum=128) or hashlib.sha256(content.encode()).hexdigest()
        evidence_id = new_id("evidence"); storage = DEFAULT_PROVIDERS.storage.register_attachment(organization_id=org, entity_type="safety_incident", entity_id=incident_id, filename=filename or "evidence.json", content_type=_text(payload, "content_type", "application/json", 120), size_bytes=len(content.encode()))
        conn.execute("INSERT INTO phase12_safety_evidence(id, organization_id, incident_id, evidence_type, storage_path, source_event_id, sha256, metadata_json, captured_by, captured_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (evidence_id, org, incident_id, _text(payload, "evidence_type", "note", 40), storage.reference, _text(payload, "source_event_id", maximum=160) or None, raw_hash, json.dumps(_body_json(payload, "metadata", {})), _user_id(user), now_iso()))
        _phase_audit(conn, user, "safety.evidence_added", "safety_incident", incident_id, ip, {"evidence_id": evidence_id, "storage_path": storage.reference})
        return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_safety_evidence WHERE id = ?", (evidence_id,)).fetchone(), ("metadata_json",)), "storage": storage.payload}
    monitor_route = route in {"/api/safety/monitor", "/api/safety/monitor/evaluate"}
    if monitor_route and method == "GET":
        _require(conn, user, "safety.read")
        alerts = conn.execute("SELECT * FROM domain_alerts WHERE organization_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT ?", (org, _limit(query))).fetchall()
        incidents = conn.execute("SELECT * FROM p0_safety_incidents WHERE organization_id = ? AND status NOT IN ('closed','resolved') ORDER BY due_at LIMIT ?", (org, _limit(query))).fetchall()
        return {"ok": True, "alerts": [_row(row, ("payload_json",)) for row in alerts], "incidents": [_row(row, ("evidence_json",)) for row in incidents], "updated_at": now_iso()}
    if route == "/api/safety/monitor/evaluate" and method == "POST":
        _require(conn, user, "safety.incidents.manage")
        stale_after = max(30, int(payload.get("stale_after_seconds") or 300)); created = []
        duties = conn.execute("SELECT id, status FROM domain_duties WHERE organization_id = ? AND status IN ('assigned','accepted','en_route','started','paused')", (org,)).fetchall()
        now_dt = datetime.now(timezone.utc)
        for duty in duties:
            track = conn.execute("SELECT recorded_at FROM domain_track_points WHERE organization_id = ? AND duty_id = ? ORDER BY recorded_at DESC LIMIT 1", (org, duty["id"])).fetchone()
            if not track: continue
            try: age = (now_dt - datetime.fromisoformat(track["recorded_at"].replace("Z", "+00:00"))).total_seconds()
            except (TypeError, ValueError): continue
            if age <= stale_after: continue
            existing = conn.execute("SELECT id FROM domain_alerts WHERE organization_id = ? AND entity_type = 'duty' AND entity_id = ? AND alert_type = 'gps_stale' AND status = 'open'", (org, duty["id"])).fetchone()
            if existing: continue
            alert_id = new_id("alert"); alert_payload = {"duty_id": duty["id"], "age_seconds": int(age), "stale_after_seconds": stale_after}
            conn.execute("INSERT INTO domain_alerts(id, organization_id, alert_type, severity, entity_type, entity_id, payload_json, created_at) VALUES (?, ?, 'gps_stale', 'high', 'duty', ?, ?, ?)", (alert_id, org, duty["id"], json.dumps(alert_payload), now_iso()))
            created.append({"id": alert_id, **alert_payload})
        _phase_audit(conn, user, "safety.monitor.evaluated", "safety_monitor", org, ip, {"created": len(created), "stale_after_seconds": stale_after})
        return {"ok": True, "created": created, "count": len(created)}
    approval = re.fullmatch(r"/api/safety/incidents/([^/]+)/closure-approval(?:/([^/]+)/decision)?", route)
    if approval and method in {"GET", "POST"}:
        incident_id, approval_id = approval.groups()
        incident = conn.execute("SELECT * FROM p0_safety_incidents WHERE id = ? AND organization_id = ?", (incident_id, org)).fetchone()
        if not incident: raise DomainError(404, "Safety incident not found", "not_found")
        if method == "GET":
            _require(conn, user, "safety.read"); rows = conn.execute("SELECT * FROM phase12_closure_approvals WHERE organization_id = ? AND incident_id = ? ORDER BY created_at DESC", (org, incident_id)).fetchall(); return {"ok": True, "items": [_row(row) for row in rows]}
        _require(conn, user, "safety.incidents.manage")
        if approval_id:
            row = conn.execute("SELECT * FROM phase12_closure_approvals WHERE id = ? AND organization_id = ? AND incident_id = ?", (approval_id, org, incident_id)).fetchone()
            if not row: raise DomainError(404, "Closure approval not found", "not_found")
            decision = _text(payload, "decision", maximum=24)
            if decision not in {"approved", "rejected"}: raise DomainError(400, "decision must be approved or rejected", "validation_error")
            conn.execute("UPDATE phase12_closure_approvals SET status = ?, reviewed_by = ?, review_note = ?, reviewed_at = ? WHERE id = ?", (decision, _user_id(user), _text(payload, "note", maximum=500), now_iso(), approval_id))
            if decision == "approved":
                open_actions = conn.execute("SELECT COUNT(*) n FROM p0_safety_actions WHERE organization_id = ? AND incident_id = ? AND status NOT IN ('completed','closed','cancelled')", (org, incident_id)).fetchone()["n"]
                if open_actions: raise DomainError(409, "Complete corrective actions before closure approval", "open_corrective_actions")
                if incident["status"] != "resolved": raise DomainError(409, "Only resolved incidents can be closed", "invalid_transition")
                conn.execute("UPDATE p0_safety_incidents SET status = 'closed', closed_at = ?, closed_by = ?, updated_at = ? WHERE id = ?", (now_iso(), _user_id(user), now_iso(), incident_id))
            _phase_audit(conn, user, "safety.closure_approval.decided", "safety_incident", incident_id, ip, {"approval_id": approval_id, "decision": decision})
            return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_closure_approvals WHERE id = ?", (approval_id,)).fetchone()), "incident_status": "closed" if decision == "approved" else incident["status"]}
        approval_id = new_id("closure"); conn.execute("INSERT INTO phase12_closure_approvals(id, organization_id, incident_id, status, requested_by, created_at) VALUES (?, ?, ?, 'pending', ?, ?)", (approval_id, org, incident_id, _user_id(user), now_iso())); _phase_audit(conn, user, "safety.closure_approval.requested", "safety_incident", incident_id, ip, {"approval_id": approval_id}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_closure_approvals WHERE id = ?", (approval_id,)).fetchone())}
    return None


def _network_phase12(conn, user, method, route, query, payload, ip):
    org = _org(user)
    replacement = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/replacements(?:/([^/]+)(?:/(approve|reject|resolve))?)?", route)
    if replacement and method in {"GET", "POST", "PATCH"}:
        service_order_id, replacement_id, action = replacement.groups()
        order = conn.execute("SELECT * FROM domain_network_service_orders WHERE id = ? AND organization_id = ?", (service_order_id, org)).fetchone()
        if not order: raise DomainError(404, "Network service order not found", "not_found")
        if method == "GET":
            _require(conn, user, "network.scorecards.write"); rows = conn.execute("SELECT * FROM phase12_network_replacements WHERE organization_id = ? AND service_order_id = ? ORDER BY created_at DESC", (org, service_order_id)).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]}
        _require(conn, user, "network.scorecards.write")
        if not replacement_id and method == "POST":
            rid = new_id("netreplace"); now = now_iso(); conn.execute("INSERT INTO phase12_network_replacements(id, organization_id, service_order_id, duty_id, reason, status, replacement_driver_id, replacement_vehicle_id, due_at, evidence_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)", (rid, org, service_order_id, _text(payload, "duty_id", maximum=160) or order["fleet_duty_id"], _text(payload, "reason", maximum=500), _text(payload, "replacement_driver_id", maximum=160) or None, _text(payload, "replacement_vehicle_id", maximum=160) or None, _text(payload, "due_at", maximum=40) or None, json.dumps(_body_json(payload, "evidence", {})), _user_id(user), now, now)); _phase_audit(conn, user, "network.replacement.created", "network_service_order", service_order_id, ip, {"replacement_id": rid}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_network_replacements WHERE id = ?", (rid,)).fetchone(), ("evidence_json",))}
        if replacement_id and action and method == "POST":
            row = conn.execute("SELECT * FROM phase12_network_replacements WHERE id = ? AND organization_id = ? AND service_order_id = ?", (replacement_id, org, service_order_id)).fetchone()
            if not row: raise DomainError(404, "Replacement not found", "not_found")
            target = {"approve": "approved", "reject": "rejected", "resolve": "resolved"}[action]
            if row["status"] in {"resolved", "rejected"}: raise DomainError(409, "Replacement is already closed", "invalid_transition")
            now = now_iso(); conn.execute("UPDATE phase12_network_replacements SET status = ?, replacement_driver_id = COALESCE(?, replacement_driver_id), replacement_vehicle_id = COALESCE(?, replacement_vehicle_id), evidence_json = ?, updated_at = ? WHERE id = ?", (target, _text(payload, "replacement_driver_id", maximum=160) or None, _text(payload, "replacement_vehicle_id", maximum=160) or None, json.dumps(_body_json(payload, "evidence", _json(row["evidence_json"], {}))), now, replacement_id)); _phase_audit(conn, user, f"network.replacement.{action}", "network_replacement", replacement_id, ip, {"service_order_id": service_order_id}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_network_replacements WHERE id = ?", (replacement_id,)).fetchone(), ("evidence_json",))}
        if replacement_id and method == "PATCH":
            return _network_phase12(conn, user, "POST", f"/api/network/v1/service-orders/{service_order_id}/replacements/{replacement_id}/resolve", query, payload, ip)
    activation = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/activation", route)
    if activation and method in {"GET", "POST"}:
        service_order_id = activation.group(1); order = conn.execute("SELECT * FROM domain_network_service_orders WHERE id = ? AND organization_id = ?", (service_order_id, org)).fetchone()
        if not order: raise DomainError(404, "Network service order not found", "not_found")
        _require(conn, user, "network.lifecycle.write")
        duty = conn.execute("SELECT * FROM domain_duties WHERE id = ? AND organization_id = ?", (order["fleet_duty_id"], org)).fetchone() if order["fleet_duty_id"] else None
        checks = [
            {"key": "fleet_handoff", "passed": bool(order["fleet_booking_id"] and order["fleet_duty_id"]), "message": "Fleet booking and duty are linked"},
            {"key": "assignment", "passed": bool(duty and duty["driver_id"] and duty["vehicle_id"]), "message": "Driver and vehicle are assigned"},
            {"key": "route_plan", "passed": bool(duty and conn.execute("SELECT 1 FROM p0_route_stops WHERE organization_id = ? AND duty_id = ?", (org, duty["id"])).fetchone()), "message": "Route plan stop exists"},
            {"key": "safety_policy", "passed": bool(conn.execute("SELECT 1 FROM p0_safety_policies WHERE organization_id = ? AND status = 'active'", (org,)).fetchone()), "message": "Active safety policy exists"},
        ]
        ready = all(check["passed"] for check in checks)
        if method == "GET": return {"ok": True, "service_order_id": service_order_id, "ready": ready, "checks": checks}
        if not ready: raise DomainError(409, "Activation checks are incomplete", "activation_blocked")
        conn.execute("UPDATE domain_network_service_orders SET status = 'active' WHERE id = ? AND organization_id = ?", (service_order_id, org)); _phase_audit(conn, user, "network.service_order.activated", "network_service_order", service_order_id, ip, {"checks": checks}); return {"ok": True, "service_order_id": service_order_id, "status": "active", "checks": checks}
    formula = route in {"/api/network/v1/scorecard-formulas", "/api/network/v1/scorecard-formulas/active"}
    if formula and method == "GET":
        _require(conn, user, "network.scorecards.write"); rows = conn.execute("SELECT * FROM phase12_scorecard_formulas WHERE organization_id = ? AND status = 'active' ORDER BY code, version DESC", (org,)).fetchall(); return {"ok": True, "items": [_row(row, ("weights_json", "thresholds_json")) for row in rows]}
    if route == "/api/network/v1/scorecard-formulas" and method == "POST":
        _require(conn, user, "network.scorecards.write"); code = _text(payload, "code", "default", 60); latest = conn.execute("SELECT COALESCE(MAX(version),0) version FROM phase12_scorecard_formulas WHERE organization_id = ? AND code = ?", (org, code)).fetchone()["version"]; fid = new_id("formula"); conn.execute("INSERT INTO phase12_scorecard_formulas(id, organization_id, code, version, status, weights_json, thresholds_json, created_by, created_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?)", (fid, org, code, int(latest or 0) + 1, json.dumps(_body_json(payload, "weights", {"on_time": 0.4, "completion": 0.3, "safety": 0.3})), json.dumps(_body_json(payload, "thresholds", {"pass": 80, "watch": 60})), _user_id(user), now_iso())); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_scorecard_formulas WHERE id = ?", (fid,)).fetchone(), ("weights_json", "thresholds_json"))}
    score_run = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/scorecard", route)
    if score_run and method == "POST":
        _require(conn, user, "network.scorecards.write"); service_order_id = score_run.group(1); order = conn.execute("SELECT id FROM domain_network_service_orders WHERE id = ? AND organization_id = ?", (service_order_id, org)).fetchone();
        if not order: raise DomainError(404, "Network service order not found", "not_found")
        formula_row = conn.execute("SELECT * FROM phase12_scorecard_formulas WHERE organization_id = ? AND status = 'active' ORDER BY version DESC LIMIT 1", (org,)).fetchone()
        weights = _json(formula_row["weights_json"], {}) if formula_row else {"on_time": 0.4, "completion": 0.3, "safety": 0.3}; observations = conn.execute("SELECT * FROM p0_network_metric_observations WHERE organization_id = ? AND service_order_id = ? ORDER BY observed_at", (org, service_order_id)).fetchall(); metrics = {}; source_ids = []
        for observation in observations:
            metrics.setdefault(observation["metric_key"], []).append(float(observation["value"])); source_ids.extend(_json(observation["source_event_ids_json"], []))
        normalized = {key: round(sum(values) / len(values), 2) for key, values in metrics.items() if values}; score = round(sum(normalized.get(key, 0) * float(weight) for key, weight in weights.items()), 2); samples = sum(len(values) for values in metrics.values()); confidence = "high" if samples >= 30 else "medium" if samples >= 10 else "cold_start"; run_id = new_id("score"); today = datetime.now(timezone.utc).date().isoformat(); conn.execute("INSERT INTO p0_network_scorecard_runs(id, organization_id, service_order_id, period_start, period_end, formula_version, sample_size, confidence, score, metrics_json, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'computed', ?, ?)", (run_id, org, service_order_id, payload.get("period_start") or today, payload.get("period_end") or today, f"{formula_row['code']}@{formula_row['version']}" if formula_row else 'default@1', samples, confidence, score, json.dumps({"metrics": normalized, "source_event_ids": sorted(set(source_ids))}), _user_id(user), now_iso())); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_scorecard_runs WHERE id = ?", (run_id,)).fetchone(), ("metrics_json",)), "formula": weights}
    reconciliation = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/reconciliation", route)
    if reconciliation and method in {"GET", "POST"}:
        service_order_id = reconciliation.group(1); _require(conn, user, "network.settlements.write")
        if method == "GET": rows = conn.execute("SELECT * FROM phase12_reconciliations WHERE organization_id = ? AND service_order_id = ? ORDER BY created_at DESC", (org, service_order_id)).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]}
        expected = int(payload.get("expected_paise") or 0); observed = int(payload.get("observed_paise") or 0); variance = observed - expected; rid = new_id("recon"); conn.execute("INSERT INTO phase12_reconciliations(id, organization_id, service_order_id, scorecard_run_id, statement_id, expected_paise, observed_paise, variance_paise, status, evidence_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (rid, org, service_order_id, payload.get("scorecard_run_id"), payload.get("statement_id"), expected, observed, variance, "matched" if variance == 0 else "review", json.dumps(_body_json(payload, "evidence", {})), _user_id(user), now_iso())); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_reconciliations WHERE id = ?", (rid,)).fetchone(), ("evidence_json",))}
    dispute = route == "/api/network/v1/scorecard-disputes" and method in {"GET", "POST"}
    if dispute:
        _require(conn, user, "network.disputes.write")
        if method == "GET": rows = conn.execute("SELECT * FROM phase12_scorecard_disputes WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]}
        did = new_id("scdispute"); conn.execute("INSERT INTO phase12_scorecard_disputes(id, organization_id, scorecard_run_id, reason, evidence_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (did, org, _text(payload, "scorecard_run_id", maximum=160), _text(payload, "reason", maximum=1000), json.dumps(_body_json(payload, "evidence", {})), _user_id(user), now_iso())); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_scorecard_disputes WHERE id = ?", (did,)).fetchone(), ("evidence_json",))}
    return None


def _permissions_views_bulk_integrations(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/permissions/bundles" and method == "GET":
        _require(conn, user, "permissions.read"); rows = conn.execute("SELECT * FROM phase12_permission_bundles WHERE organization_id = ? ORDER BY role, version DESC", (org,)).fetchall(); return {"ok": True, "items": [_row(row, ("permissions_json",)) for row in rows]}
    if route == "/api/permissions/bundles" and method == "POST":
        _require(conn, user, "permissions.write"); role = _text(payload, "role", maximum=40); name = _text(payload, "name", maximum=100); permissions = payload.get("permissions") if isinstance(payload.get("permissions"), list) else []; version = int(conn.execute("SELECT COALESCE(MAX(version),0) version FROM phase12_permission_bundles WHERE organization_id = ? AND role = ?", (org, role)).fetchone()["version"] or 0) + 1; bid = new_id("bundle"); conn.execute("INSERT INTO phase12_permission_bundles(id, organization_id, role, name, description, permissions_json, version, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (bid, org, role, name, _text(payload, "description", maximum=500), json.dumps(permissions), version, _user_id(user), now_iso())); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_permission_bundles WHERE id = ?", (bid,)).fetchone(), ("permissions_json",))}
    if route == "/api/views" and method == "GET":
        rows = conn.execute("SELECT * FROM phase12_saved_views WHERE organization_id = ? ORDER BY scope, name", (org,)).fetchall(); return {"ok": True, "items": [_row(row, ("filters_json", "columns_json", "sort_json")) for row in rows]}
    if route == "/api/views" and method == "POST":
        name = _text(payload, "name", maximum=100); scope = _text(payload, "scope", "operations", 60); view_id = new_id("view12"); now = now_iso(); conn.execute("INSERT INTO phase12_saved_views(id, organization_id, scope, name, filters_json, columns_json, sort_json, shared, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (view_id, org, scope, name, json.dumps(_body_json(payload, "filters", {})), json.dumps(payload.get("columns") if isinstance(payload.get("columns"), list) else []), json.dumps(_body_json(payload, "sort", {})), 1 if payload.get("shared") else 0, _user_id(user), now, now)); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_saved_views WHERE id = ?", (view_id,)).fetchone(), ("filters_json", "columns_json", "sort_json"))}
    view_match = re.fullmatch(r"/api/views/([^/]+)", route)
    if view_match and method == "PATCH":
        view_id = view_match.group(1); row = conn.execute("SELECT * FROM phase12_saved_views WHERE id = ? AND organization_id = ?", (view_id, org)).fetchone();
        if not row: raise DomainError(404, "Saved view not found", "not_found")
        updates = {"name": _text(payload, "name", row["name"], 100), "shared": 1 if payload.get("shared", bool(row["shared"])) else 0, "updated_at": now_iso()}
        if "filters" in payload: updates["filters_json"] = json.dumps(_body_json(payload, "filters", {}))
        if "columns" in payload: updates["columns_json"] = json.dumps(payload["columns"] if isinstance(payload["columns"], list) else [])
        conn.execute(f"UPDATE phase12_saved_views SET {', '.join(f'{key} = ?' for key in updates)} WHERE id = ?", list(updates.values()) + [view_id]); return {"ok": True, "item": _row(conn.execute("SELECT * FROM phase12_saved_views WHERE id = ?", (view_id,)).fetchone(), ("filters_json", "columns_json", "sort_json"))}
    if route == "/api/operations/bulk" and method == "POST":
        _staff(user); ids = payload.get("ids") if isinstance(payload.get("ids"), list) else []; operation = _text(payload, "operation", maximum=50); entity_type = _text(payload, "entity_type", maximum=50); key = _text(payload, "idempotency_key", maximum=160) or None
        if key:
            existing = conn.execute("SELECT * FROM phase12_bulk_jobs WHERE organization_id = ? AND idempotency_key = ?", (org, key)).fetchone()
            if existing: return {"ok": True, "item": _row(existing, ("entity_ids_json", "payload_json", "result_json")), "idempotent": True}
        job_id = new_id("bulk"); results = []
        for entity_id in ids:
            try:
                if entity_type == "master_registry" and operation in {"archive", "restore"}:
                    target = "archived" if operation == "archive" else "active"; cursor = conn.execute("UPDATE phase12_master_records SET status = ?, version = version + 1, updated_at = ? WHERE id = ? AND organization_id = ?", (target, now_iso(), entity_id, org));
                    if cursor.rowcount == 0: raise DomainError(404, "Master not found", "not_found")
                elif entity_type == "master_registry" and operation in {"edit", "bulk_edit"}:
                    target = conn.execute("SELECT * FROM phase12_master_records WHERE id = ? AND organization_id = ?", (entity_id, org)).fetchone()
                    if not target: raise DomainError(404, "Master not found", "not_found")
                    patch = payload.get("patch") if isinstance(payload.get("patch"), dict) else payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
                    allowed = {"name": "name", "status": "status", "effective_from": "effective_from", "effective_to": "effective_to"}
                    updates = {column: patch[key] for key, column in allowed.items() if key in patch and patch[key] is not None}
                    if not updates: raise DomainError(400, "patch must include an editable master field", "validation_error")
                    updates["version"] = int(target["version"] or 1) + 1; updates["updated_at"] = now_iso()
                    conn.execute(f"UPDATE phase12_master_records SET {', '.join(f'{key} = ?' for key in updates)} WHERE id = ? AND organization_id = ?", [*updates.values(), entity_id, org])
                elif entity_type == "incident" and operation == "acknowledge": 
                    cursor = conn.execute("UPDATE p0_safety_incidents SET status = 'acknowledged', updated_at = ? WHERE id = ? AND organization_id = ? AND status = 'open'", (now_iso(), entity_id, org));
                    if cursor.rowcount == 0: raise DomainError(409, "Incident cannot be acknowledged", "invalid_transition")
                elif entity_type == "duty" and operation == "refresh_eta":
                    duty = conn.execute("SELECT d.*, b.pickup_json, b.dropoff_json FROM domain_duties d JOIN domain_bookings b ON b.id = d.booking_id WHERE d.id = ? AND d.organization_id = ?", (entity_id, org)).fetchone()
                    if not duty: raise DomainError(404, "Duty not found", "not_found")
                    route_result = DEFAULT_PROVIDERS.maps.route(pickup=_json(duty["pickup_json"], {}), dropoff=_json(duty["dropoff_json"], {})); route_payload = route_result.payload; eta = (datetime.now(timezone.utc) + timedelta(minutes=int(route_payload.get("duration_minutes", 0)))).replace(microsecond=0).isoformat().replace("+00:00", "Z"); point = (route_payload.get("points") or [{}])[0]
                    conn.execute("INSERT INTO phase12_eta_snapshots(id, organization_id, duty_id, source, latitude, longitude, distance_km, duration_minutes, eta_at, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_id("eta"), org, entity_id, route_result.provider, point.get("latitude", point.get("lat")), point.get("longitude", point.get("lng")), route_payload.get("distance_km", 0), route_payload.get("duration_minutes", 0), eta, json.dumps(route_payload), now_iso()))
                elif entity_type == "duty" and operation in {"edit", "bulk_edit"}:
                    duty = conn.execute("SELECT * FROM domain_duties WHERE id = ? AND organization_id = ?", (entity_id, org)).fetchone()
                    if not duty: raise DomainError(404, "Duty not found", "not_found")
                    patch = payload.get("patch") if isinstance(payload.get("patch"), dict) else payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
                    allowed_statuses = {"draft", "assigned", "accepted", "en_route", "started", "paused", "completed", "cancelled", "archived"}
                    updates = {}
                    if patch.get("status") is not None:
                        status = str(patch["status"]).strip().lower()
                        if status not in allowed_statuses: raise DomainError(400, "Unsupported duty status", "validation_error")
                        updates["status"] = status
                    if patch.get("reporting_at") is not None: updates["reporting_at"] = str(patch["reporting_at"]).strip() or None
                    if not updates: raise DomainError(400, "patch must include status or reporting_at", "validation_error")
                    updates["updated_at"] = now_iso()
                    conn.execute(f"UPDATE domain_duties SET {', '.join(f'{key} = ?' for key in updates)} WHERE id = ? AND organization_id = ?", [*updates.values(), entity_id, org])
                    _phase_audit(conn, user, "duty.bulk_edit", "duty", entity_id, ip, {"fields": sorted(updates.keys())})
                elif entity_type == "duty" and operation in {"archive", "restore"}:
                    target_status = "archived" if operation == "archive" else "draft"
                    cursor = conn.execute("UPDATE domain_duties SET status = ?, updated_at = ? WHERE id = ? AND organization_id = ?", (target_status, now_iso(), entity_id, org))
                    if cursor.rowcount == 0: raise DomainError(404, "Duty not found", "not_found")
                    _phase_audit(conn, user, f"duty.{operation}", "duty", entity_id, ip, {"status": target_status})
                elif entity_type == "duty" and operation in {"assign", "bulk_assign"}:
                    duty = conn.execute("SELECT id FROM domain_duties WHERE id = ? AND organization_id = ?", (entity_id, org)).fetchone()
                    if not duty: raise DomainError(404, "Duty not found", "not_found")
                    driver_id = str(payload.get("driver_id") or "").strip(); vehicle_id = str(payload.get("vehicle_id") or "").strip() or None
                    driver = conn.execute("SELECT id FROM domain_drivers WHERE id = ? AND organization_id = ? AND status NOT IN ('inactive','archived')", (driver_id, org)).fetchone()
                    if not driver: raise DomainError(400, "An active driver is required", "validation_error")
                    if vehicle_id and not conn.execute("SELECT id FROM domain_vehicles WHERE id = ? AND organization_id = ?", (vehicle_id, org)).fetchone(): raise DomainError(400, "Vehicle is not in this tenant", "validation_error")
                    conn.execute("UPDATE domain_duties SET driver_id = ?, vehicle_id = ?, status = 'assigned', updated_at = ? WHERE id = ? AND organization_id = ?", (driver_id, vehicle_id, now_iso(), entity_id, org))
                    _phase_audit(conn, user, "duty.bulk_assign", "duty", entity_id, ip, {"driver_id": driver_id, "vehicle_id": vehicle_id})
                else: raise DomainError(400, "Unsupported bulk operation", "validation_error")
                results.append({"id": entity_id, "status": "updated"})
            except DomainError as exc: results.append({"id": entity_id, "status": "error", "code": exc.code, "error": str(exc)})
        now = now_iso(); conn.execute("INSERT INTO phase12_bulk_jobs(id, organization_id, idempotency_key, operation, entity_type, entity_ids_json, payload_json, status, result_json, created_by, created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)", (job_id, org, key, operation, entity_type, json.dumps(ids), json.dumps(payload), json.dumps(results), _user_id(user), now, now)); return {"ok": True, "item": {"id": job_id, "status": "completed", "results": results}}
    if route == "/api/mobile/home" and method == "GET":
        _require(conn, user, "dispatch.read")
        duty_args = [org]
        duty_sql = "SELECT d.*, b.booking_reference, b.passenger_name, b.pickup_json, b.dropoff_json FROM domain_duties d LEFT JOIN domain_bookings b ON b.id = d.booking_id WHERE d.organization_id = ? AND d.status NOT IN ('completed','cancelled')"
        if _role(user) == "driver":
            duty_sql = "SELECT d.*, b.booking_reference, b.passenger_name, b.pickup_json, b.dropoff_json FROM domain_duties d JOIN domain_drivers dr ON dr.id = d.driver_id AND dr.user_id = ? LEFT JOIN domain_bookings b ON b.id = d.booking_id WHERE d.organization_id = ? AND d.status NOT IN ('completed','cancelled')"
            duty_args = [_user_id(user), org]
        duty_sql += " ORDER BY COALESCE(d.reporting_at, b.scheduled_at) LIMIT 20"
        duties = conn.execute(duty_sql, duty_args).fetchall()
        if _role(user) == "driver":
            duty_ids = [row["id"] for row in duties]
            alerts = conn.execute("SELECT * FROM domain_alerts WHERE organization_id = ? AND status = 'open' AND entity_type = 'duty' AND entity_id IN ({}) ORDER BY created_at DESC LIMIT 5".format(",".join("?" for _ in duty_ids) or "NULL"), [org, *duty_ids]).fetchall()
        else:
            alerts = conn.execute("SELECT * FROM domain_alerts WHERE organization_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT 5", (org,)).fetchall()
        return {"ok": True, "summary": {"open_duties": len(duties), "open_alerts": len(alerts)}, "next_duty": _row(duties[0], ("pickup_json", "dropoff_json")) if duties else None, "duties": [_row(row, ("pickup_json", "dropoff_json")) for row in duties], "alerts": [_row(row, ("payload_json",)) for row in alerts], "updated_at": now_iso()}
    if route == "/api/integrations/catalog" and method == "GET":
        return {"ok": True, "items": [
            {"type": "hrms", "name": "HRMS employee feed", "provider": DEFAULT_PROVIDERS.hrms.name, "mode": "mock", "status": "available", "contract": "/api/integrations/hrms/sync"},
            {"type": "gps", "name": "GPS / telematics", "provider": DEFAULT_PROVIDERS.gps.name, "mode": "mock", "status": "available", "contract": "/api/integrations/events"},
            {"type": "messaging", "name": "SMS, WhatsApp and push", "mode": "mock", "status": "available", "contract": "/api/integrations/events"},
            {"type": "storage", "name": "Evidence object storage", "mode": "mock", "status": "available", "contract": "/api/safety/incidents/{id}/evidence"},
        ]}
    if route == "/api/integrations/config" and method in {"GET", "POST", "PATCH"}:
        if method == "GET": rows = conn.execute("SELECT * FROM phase12_integrations WHERE organization_id = ? ORDER BY provider_type", (org,)).fetchall(); return {"ok": True, "items": [_row(row, ("config_json",)) for row in rows]}
        _staff(user); provider_type = _text(payload, "provider_type", maximum=40); now = now_iso(); config = _body_json(payload, "config", {}); provider_name = _text(payload, "provider_name", provider_type, 100); mode = _text(payload, "mode", "mock", 24); conn.execute("INSERT INTO phase12_integrations(id, organization_id, provider_type, provider_name, mode, status, config_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(organization_id, provider_type) DO UPDATE SET provider_name = excluded.provider_name, mode = excluded.mode, status = excluded.status, config_json = excluded.config_json, updated_at = excluded.updated_at", (new_id("integration"), org, provider_type, provider_name, mode, "configured", json.dumps(config), _user_id(user), now, now)); row = conn.execute("SELECT * FROM phase12_integrations WHERE organization_id = ? AND provider_type = ?", (org, provider_type)).fetchone(); return {"ok": True, "item": _row(row, ("config_json",))}
    if route == "/api/integrations/sync" and method == "POST":
        _staff(user); provider_type = _text(payload, "provider_type", maximum=40); event_id = new_id("integrationevent"); records = payload.get("records") if isinstance(payload.get("records"), list) else []; idempotency_key = _text(payload, "idempotency_key", maximum=160) or None
        if provider_type == "hrms": provider_result = DEFAULT_PROVIDERS.hrms.sync(records=records, idempotency_key=idempotency_key)
        elif provider_type == "gps": provider_result = DEFAULT_PROVIDERS.gps.ingest(positions=records, idempotency_key=idempotency_key)
        else: provider_result = None
        reference = provider_result.reference if provider_result else f"mock_{provider_type}_{uuid.uuid4().hex[:12]}"; result = {"provider_type": provider_type, "provider": provider_result.provider if provider_result else f"mock_{provider_type}", "reference": reference, "status": provider_result.status if provider_result else "queued", "accepted": len(records)}; conn.execute("INSERT INTO phase12_integration_events(id, organization_id, provider_type, event_type, external_id, status, payload_json, created_at) VALUES (?, ?, ?, 'sync_requested', ?, ?, ?, ?)", (event_id, org, provider_type, reference, result["status"], json.dumps(payload), now_iso())); return {"ok": True, "item": result}
    if route == "/api/integrations/events" and method in {"GET", "POST"}:
        if method == "GET": rows = conn.execute("SELECT * FROM phase12_integration_events WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("payload_json",)) for row in rows]}
        provider_type = _text(payload, "provider_type", maximum=40); external_id = _text(payload, "external_id", maximum=160) or new_id("external"); signature_valid = bool(payload.get("signature_valid", True)); conn.execute("INSERT OR IGNORE INTO phase12_integration_events(id, organization_id, provider_type, event_type, external_id, signature_valid, status, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, 'received', ?, ?)", (new_id("integrationevent"), org, provider_type, _text(payload, "event_type", "provider.event", 100), external_id, 1 if signature_valid else 0, json.dumps(payload.get("payload") if isinstance(payload.get("payload"), dict) else payload), now_iso())); return {"ok": True, "status": "received", "signature_valid": signature_valid, "external_id": external_id}
    return None


def handle_phase12(conn, user, method: str, raw_route: str, payload: dict, ip: str):
    route, query = _parse(raw_route)
    if route.startswith("/api/masters/registry"):
        result = _master_registry(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/operations/rosters") or route.startswith("/api/operations/live-board") or route.startswith("/api/operations/duties/") and route.endswith("/eta"):
        result = _roster_and_live(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/safety/incidents/") and ("/evidence" in route or "closure-approval" in route) or route.startswith("/api/safety/monitor"):
        result = _safety_phase12(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/network/v1/service-orders/") or route in {"/api/network/v1/scorecard-formulas", "/api/network/v1/scorecard-formulas/active", "/api/network/v1/scorecard-disputes"}:
        result = _network_phase12(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/permissions/bundles") or route.startswith("/api/views") or route in {"/api/operations/bulk", "/api/mobile/home", "/api/integrations/catalog", "/api/integrations/config", "/api/integrations/sync", "/api/integrations/events"}:
        result = _permissions_views_bulk_integrations(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    return None
