"""P0 domain foundations for Axiom Fleet and Axiom Network.

This module intentionally keeps the local fallback dependency-free while adding
real, tenant-scoped state machines for the six P0 capability groups:

- master data and effective-dated versions
- route plans, rosters, dispatch and replacements
- safety policies, incidents and corrective actions
- Network regions, approvals, lifecycle, messages and evaluations
- evidence-derived scorecard observations and settlement statements
- granular permission grants

Supabase/Postgres is the production direction. The local tables and route
contracts are additive and do not replace existing Fleet or Network sources of
truth.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from backend_domain import DomainError, new_id, now_iso


MASTER_KINDS = {
    "duty_types",
    "vehicle_groups",
    "taxes",
    "billing_items",
    "labels",
    "feedback_forms",
    "operating_regions",
}

MASTER_PERMISSION = {
    "duty_types": "masters.duty_types.write",
    "vehicle_groups": "masters.vehicle_groups.write",
    "taxes": "masters.taxes.write",
    "billing_items": "masters.billing_items.write",
    "labels": "masters.labels.write",
    "feedback_forms": "masters.feedback_forms.write",
    "operating_regions": "masters.regions.write",
}

P0_PERMISSIONS = {
    "masters.read",
    "masters.write",
    "masters.duty_types.write",
    "masters.vehicle_groups.write",
    "masters.taxes.write",
    "masters.billing_items.write",
    "masters.labels.write",
    "masters.feedback_forms.write",
    "masters.regions.write",
    "route_plans.read",
    "route_plans.write",
    "dispatch.read",
    "dispatch.write",
    "dispatch.respond",
    "tracking.read",
    "replacements.manage",
    "safety.read",
    "safety.incidents.create",
    "safety.incidents.manage",
    "safety.override_close",
    "network.regions.read",
    "network.regions.write",
    "network.vendor_approvals.read",
    "network.vendor_approvals.write",
    "network.lifecycle.write",
    "network.messages.write",
    "network.evaluations.write",
    "network.metrics.write",
    "network.scorecards.write",
    "network.settlements.write",
    "network.disputes.write",
    "network.corrective_actions.write",
    "permissions.read",
    "permissions.write",
    "phase3.analytics.read",
    "phase3.analytics.write",
    "phase3.predictive.read",
    "phase3.predictive.write",
    "phase3.vendor_quality.read",
    "phase3.vendor_quality.write",
    "phase3.simulation.read",
    "phase3.simulation.write",
    "phase3.variance.read",
    "phase3.variance.write",
    "phase3.sustainability.read",
    "phase3.sustainability.write",
    "phase3.regions.read",
    "phase3.regions.write",
}

ROLE_DEFAULTS = {
    "vendor": P0_PERMISSIONS,
    "corporate": {
        "masters.read",
        "masters.write",
        "masters.duty_types.write",
        "masters.vehicle_groups.write",
        "masters.taxes.write",
        "masters.billing_items.write",
        "masters.labels.write",
        "masters.feedback_forms.write",
        "masters.regions.write",
        "route_plans.read",
        "route_plans.write",
        "dispatch.read",
        "dispatch.write",
        "tracking.read",
        "replacements.manage",
        "safety.read",
        "safety.incidents.create",
        "safety.incidents.manage",
        "network.regions.read",
        "network.vendor_approvals.read",
        "network.lifecycle.write",
        "network.messages.write",
        "network.evaluations.write",
        "network.metrics.write",
        "network.scorecards.write",
        "network.settlements.write",
        "network.disputes.write",
        "network.corrective_actions.write",
        "permissions.read",
        "permissions.write",
        "phase3.analytics.read",
        "phase3.analytics.write",
        "phase3.predictive.read",
        "phase3.predictive.write",
        "phase3.vendor_quality.read",
        "phase3.vendor_quality.write",
        "phase3.simulation.read",
        "phase3.simulation.write",
        "phase3.variance.read",
        "phase3.variance.write",
        "phase3.sustainability.read",
        "phase3.sustainability.write",
        "phase3.regions.read",
        "phase3.regions.write",
    },
    "driver": {
        "route_plans.read",
        "dispatch.read",
        "dispatch.respond",
        "safety.read",
        "safety.incidents.create",
        "network.messages.write",
        "phase3.predictive.read",
        "phase3.sustainability.read",
        "phase3.regions.read",
    },
}


def _json(value, fallback):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _text(payload, key, default="", maximum=500):
    # Accept the concise _text(payload, key, 100) form as a maximum length.
    # String third arguments remain defaults, matching the existing backend style.
    if isinstance(default, int) and maximum == 500:
        maximum, default = default, ""
    value = str(payload.get(key, default) or "").strip()
    if len(value) > maximum:
        raise DomainError(400, f"{key} is too long", "validation_error")
    return value


def _int(value, key, default=0):
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise DomainError(400, f"{key} must be an integer", "validation_error") from exc
    if number < 0:
        raise DomainError(400, f"{key} cannot be negative", "validation_error")
    return number


def _limit(query, default=100):
    try:
        return min(max(int(query.get("limit", [default])[0] or default), 1), 500)
    except (TypeError, ValueError):
        return default


def _parse(raw_route):
    parsed = urlsplit(raw_route)
    return parsed.path.rstrip("/") or "/", parse_qs(parsed.query)


def _row(row, json_fields=()):
    if row is None:
        return None
    item = dict(row)
    for field in json_fields:
        if field in item:
            item[field[:-5] if field.endswith("_json") else field] = _json(item.pop(field), {} if field.endswith("_json") else None)
    return item


def _org(user):
    organization_id = user.get("organization_id") if isinstance(user, dict) else user["organization_id"]
    if not organization_id:
        raise DomainError(403, "An organization-linked account is required", "organization_required")
    return organization_id


def _role(user):
    return user.get("role") if isinstance(user, dict) else user["role"]


def _user_id(user):
    return user.get("id") if isinstance(user, dict) else user["id"]


def _staff(user):
    if _role(user) not in {"vendor", "corporate"}:
        raise DomainError(403, "This workflow is restricted to organization operators", "role_forbidden")


def _audit(conn, user, action, entity_type, entity_id, ip, metadata=None):
    conn.execute(
        "INSERT INTO audit_events(id, user_id, action, entity_type, entity_id, metadata_json, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id("audit"), _user_id(user), action, entity_type, entity_id, json.dumps(metadata or {}), ip, now_iso()),
    )


def _emit(conn, user, event_type, entity_type, entity_id, ip, payload=None):
    event_id = new_id("p0evt")
    conn.execute(
        "INSERT INTO p0_events(id, organization_id, event_type, entity_type, entity_id, payload_json, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_id, _org(user), event_type, entity_type, entity_id, json.dumps(payload or {}), _user_id(user), now_iso()),
    )
    _audit(conn, user, event_type, entity_type, entity_id, ip, payload or {})
    return event_id


def _ensure_permission_seed(conn):
    organizations = conn.execute("SELECT id FROM organizations").fetchall()
    for organization in organizations:
        for role, permissions in ROLE_DEFAULTS.items():
            for permission in permissions:
                conn.execute(
                    "INSERT OR IGNORE INTO p0_role_permissions(id, organization_id, role, permission_key, allowed, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (new_id("perm"), organization["id"], role, permission, now_iso(), now_iso()),
                )


def initialize_p0_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS p0_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            actor_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_events_org_time ON p0_events(organization_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS p0_role_permissions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            role TEXT NOT NULL,
            permission_key TEXT NOT NULL,
            allowed INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, role, permission_key)
        );
        CREATE INDEX IF NOT EXISTS idx_p0_permissions_org_role ON p0_role_permissions(organization_id, role, permission_key);

        CREATE TABLE IF NOT EXISTS p0_master_records (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            version INTEGER NOT NULL DEFAULT 1,
            effective_from TEXT,
            effective_to TEXT,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, kind, code)
        );
        CREATE TABLE IF NOT EXISTS p0_master_versions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            master_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            snapshot_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, master_id, version)
        );
        CREATE INDEX IF NOT EXISTS idx_p0_masters_org_kind ON p0_master_records(organization_id, kind, status);

        CREATE TABLE IF NOT EXISTS p0_sites (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL DEFAULT '',
            address_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, code)
        );
        CREATE TABLE IF NOT EXISTS p0_shifts (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            site_id TEXT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            starts_at TEXT NOT NULL,
            ends_at TEXT NOT NULL,
            demand_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, code)
        );

        CREATE TABLE IF NOT EXISTS p0_route_plans (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            site_id TEXT,
            plan_date TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            routing_mode TEXT NOT NULL DEFAULT 'sequence_by_reporting_at',
            constraints_json TEXT NOT NULL DEFAULT '{}',
            feasibility_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            published_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p0_route_stops (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            route_plan_id TEXT NOT NULL,
            duty_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            pickup_json TEXT NOT NULL DEFAULT '{}',
            dropoff_json TEXT NOT NULL DEFAULT '{}',
            reporting_at TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL,
            UNIQUE(route_plan_id, duty_id)
        );
        CREATE TABLE IF NOT EXISTS p0_roster_assignments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            route_plan_id TEXT NOT NULL,
            duty_id TEXT NOT NULL,
            driver_id TEXT,
            vehicle_id TEXT,
            status TEXT NOT NULL DEFAULT 'offered',
            offered_at TEXT NOT NULL,
            response_deadline TEXT,
            responded_at TEXT,
            rejection_reason TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, route_plan_id, duty_id)
        );
        CREATE TABLE IF NOT EXISTS p0_replacements (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            assignment_id TEXT,
            duty_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            replacement_driver_id TEXT,
            replacement_vehicle_id TEXT,
            due_at TEXT,
            resolved_at TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p0_dispatch_events (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            assignment_id TEXT,
            duty_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            actor_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_dispatch_org_status ON p0_roster_assignments(organization_id, status, response_deadline);

        CREATE TABLE IF NOT EXISTS p0_safety_policies (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            rules_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, code, version)
        );
        CREATE TABLE IF NOT EXISTS p0_safety_incidents (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            duty_id TEXT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            owner_id TEXT,
            due_at TEXT,
            root_cause TEXT NOT NULL DEFAULT '',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            opened_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            closed_at TEXT,
            closed_by TEXT
        );
        CREATE TABLE IF NOT EXISTS p0_safety_actions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            incident_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            owner_id TEXT,
            due_at TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            resolution_note TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_incidents_org_status ON p0_safety_incidents(organization_id, status, severity, due_at);

        CREATE TABLE IF NOT EXISTS p0_network_regions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            cities_json TEXT NOT NULL DEFAULT '[]',
            feature_flags_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            version INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, code)
        );
        CREATE TABLE IF NOT EXISTS p0_network_vendor_approvals (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            vendor_profile_id TEXT NOT NULL,
            region_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            evidence_json TEXT NOT NULL DEFAULT '{}',
            expires_at TEXT,
            note TEXT NOT NULL DEFAULT '',
            decided_by TEXT,
            decided_at TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, vendor_profile_id, region_id)
        );
        CREATE TABLE IF NOT EXISTS p0_network_quote_evaluations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            requirement_id TEXT NOT NULL,
            quote_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            commercial_score REAL NOT NULL DEFAULT 0,
            quality_score REAL NOT NULL DEFAULT 0,
            risk_score REAL NOT NULL DEFAULT 0,
            total_score REAL NOT NULL DEFAULT 0,
            sample_size INTEGER NOT NULL DEFAULT 0,
            confidence TEXT NOT NULL DEFAULT 'cold_start',
            comments TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, quote_id, version)
        );
        CREATE TABLE IF NOT EXISTS p0_network_messages (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            thread_key TEXT NOT NULL,
            requirement_id TEXT,
            service_order_id TEXT,
            vendor_profile_id TEXT,
            visibility TEXT NOT NULL DEFAULT 'participants',
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_by TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_network_messages_thread ON p0_network_messages(organization_id, thread_key, created_at);
        CREATE TABLE IF NOT EXISTS p0_network_metric_observations (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            service_order_id TEXT NOT NULL,
            vendor_profile_id TEXT,
            metric_key TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            sample_size INTEGER NOT NULL DEFAULT 0,
            source_event_ids_json TEXT NOT NULL DEFAULT '[]',
            formula_version TEXT NOT NULL DEFAULT 'v1',
            observed_at TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_metric_observations_service ON p0_network_metric_observations(organization_id, service_order_id, metric_key, observed_at);
        CREATE TABLE IF NOT EXISTS p0_network_scorecard_runs (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            service_order_id TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            formula_version TEXT NOT NULL DEFAULT 'v1',
            sample_size INTEGER NOT NULL DEFAULT 0,
            confidence TEXT NOT NULL DEFAULT 'cold_start',
            score REAL NOT NULL DEFAULT 0,
            metrics_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'computed',
            created_by TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, service_order_id, period_start, period_end, formula_version)
        );
        CREATE TABLE IF NOT EXISTS p0_network_corrective_actions (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            vendor_profile_id TEXT,
            service_order_id TEXT,
            scorecard_run_id TEXT,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            owner_id TEXT,
            due_at TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            resolution_note TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p0_network_disputes (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            service_order_id TEXT,
            amount_paise INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            claimant_id TEXT,
            respondent_id TEXT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            resolution_note TEXT NOT NULL DEFAULT '',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p0_network_settlement_statements (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            service_order_id TEXT NOT NULL,
            scorecard_run_id TEXT,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            subtotal_paise INTEGER NOT NULL DEFAULT 0,
            tax_paise INTEGER NOT NULL DEFAULT 0,
            fee_paise INTEGER NOT NULL DEFAULT 0,
            deduction_paise INTEGER NOT NULL DEFAULT 0,
            net_paise INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            reconciliation_json TEXT NOT NULL DEFAULT '{}',
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(organization_id, service_order_id, period_start, period_end)
        );
        CREATE TABLE IF NOT EXISTS p0_network_settlement_lines (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            statement_id TEXT NOT NULL,
            line_type TEXT NOT NULL,
            code TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            quantity REAL NOT NULL DEFAULT 1,
            unit_paise INTEGER NOT NULL DEFAULT 0,
            amount_paise INTEGER NOT NULL DEFAULT 0,
            source_event_ids_json TEXT NOT NULL DEFAULT '[]',
            disputed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_p0_settlements_org_status ON p0_network_settlement_statements(organization_id, status, period_end);
        """
    )

    # Additive lifecycle columns keep existing Network tables compatible.
    for table, columns in {
        "domain_network_requirements": {
            "deadline_at": "TEXT",
            "expires_at": "TEXT",
            "closed_reason": "TEXT NOT NULL DEFAULT ''",
            "approved_at": "TEXT",
            "completed_at": "TEXT",
        },
    }.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    _ensure_permission_seed(conn)


def _has_permission(conn, user, permission):
    role = _role(user)
    if role == "platform":
        return True
    row = conn.execute("SELECT allowed FROM p0_role_permissions WHERE organization_id = ? AND role = ? AND permission_key = ?", (_org(user), role, permission)).fetchone()
    if row is None:
        return permission in ROLE_DEFAULTS.get(role, set())
    return bool(row["allowed"])


def _require_permission(conn, user, permission):
    if not _has_permission(conn, user, permission):
        raise DomainError(403, f"Permission required: {permission}", "permission_denied")


def _owned(conn, table, entity_id, org, message="Record not found"):
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND organization_id = ?", (entity_id, org)).fetchone()
    if row is None:
        raise DomainError(404, message, "not_found")
    return row


def _network_ready(conn, org):
    row = conn.execute("SELECT enabled FROM domain_network_feature_flags WHERE organization_id = ?", (org,)).fetchone()
    if row is not None and not row["enabled"]:
        raise DomainError(403, "Axiom Network is disabled for this workspace", "network_disabled")


def _network_profile(conn, profile_id, org):
    return _owned(conn, "domain_network_vendor_profiles", profile_id, org, "Network vendor profile not found")


def _service_order(conn, service_id, org):
    return _owned(conn, "domain_network_service_orders", service_id, org, "Network service order not found")


def _network_requirement(conn, requirement_id, org):
    return _owned(conn, "domain_network_requirements", requirement_id, org, "Network requirement not found")


def _status_transition(current, target, allowed):
    if current == target:
        return
    if target not in allowed.get(current, set()):
        raise DomainError(409, f"Cannot move from {current} to {target}", "invalid_transition")


def _master_view(row):
    return _row(row, ("config_json",))


def _master_snapshot(row):
    return {
        "id": row["id"],
        "kind": row["kind"],
        "code": row["code"],
        "name": row["name"],
        "status": row["status"],
        "version": row["version"],
        "effective_from": row["effective_from"],
        "effective_to": row["effective_to"],
        "config": _json(row["config_json"], {}),
    }


def _master_routes(conn, user, method, route, query, payload, ip):
    if route == "/api/masters" and method == "GET":
        _require_permission(conn, user, "masters.read")
        counts = {kind: conn.execute("SELECT COUNT(*) n FROM p0_master_records WHERE organization_id = ? AND kind = ? AND status != 'archived'", (_org(user), kind)).fetchone()["n"] for kind in sorted(MASTER_KINDS)}
        return {"ok": True, "counts": counts, "kinds": sorted(MASTER_KINDS)}
    match = re.fullmatch(r"/api/masters/([^/]+)(?:/([^/]+)(?:/(archive|restore))?)?", route)
    if not match:
        return None
    kind, entity_id, action = match.groups()
    if kind not in MASTER_KINDS:
        raise DomainError(404, "Master type not found", "not_found")
    org = _org(user)
    if method == "GET" and not entity_id:
        _require_permission(conn, user, "masters.read")
        q = _text(query, "q", maximum=100) if isinstance(query, dict) else ""
        status_filter = (query.get("status", ["active"])[0] if isinstance(query, dict) else "active")
        sql = "SELECT * FROM p0_master_records WHERE organization_id = ? AND kind = ?"
        args = [org, kind]
        if status_filter != "all":
            sql += " AND status = ?"; args.append(status_filter)
        if q:
            sql += " AND (code LIKE ? OR name LIKE ?)"; args.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY name LIMIT ?"; args.append(_limit(query))
        return {"ok": True, "items": [_master_view(row) for row in conn.execute(sql, args).fetchall()]}
    write_permission = MASTER_PERMISSION[kind]
    if method == "POST" and not entity_id:
        _require_permission(conn, user, write_permission)
        code = _text(payload, "code", maximum=80).upper()
        name = _text(payload, "name", maximum=160)
        if not code or not name:
            raise DomainError(400, "code and name are required", "validation_error")
        if conn.execute("SELECT 1 FROM p0_master_records WHERE organization_id = ? AND kind = ? AND code = ?", (org, kind, code)).fetchone():
            raise DomainError(409, "A master with this code already exists", "duplicate_master")
        now = now_iso(); master_id = new_id("master")
        conn.execute("INSERT INTO p0_master_records(id, organization_id, kind, code, name, status, version, effective_from, effective_to, config_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)", (master_id, org, kind, code, name, _text(payload, "status", "active", 24), _text(payload, "effective_from", maximum=40) or None, _text(payload, "effective_to", maximum=40) or None, json.dumps(payload.get("config") if isinstance(payload.get("config"), dict) else {}), _user_id(user), now, now))
        row = conn.execute("SELECT * FROM p0_master_records WHERE id = ?", (master_id,)).fetchone()
        conn.execute("INSERT INTO p0_master_versions(id, organization_id, master_id, version, change_type, snapshot_json, created_by, created_at) VALUES (?, ?, ?, 1, 'created', ?, ?, ?)", (new_id("masterver"), org, master_id, json.dumps(_master_snapshot(row)), _user_id(user), now))
        _emit(conn, user, "master.created", "master", master_id, ip, {"kind": kind, "code": code})
        return {"ok": True, "item": _master_view(row)}
    if not entity_id:
        raise DomainError(405, "Method not allowed", "method_not_allowed")
    row = _owned(conn, "p0_master_records", entity_id, org, "Master record not found")
    if method == "GET":
        _require_permission(conn, user, "masters.read")
        versions = conn.execute("SELECT * FROM p0_master_versions WHERE organization_id = ? AND master_id = ? ORDER BY version DESC", (org, entity_id)).fetchall()
        result = _master_view(row); result["versions"] = [_row(item, ("snapshot_json",)) for item in versions]; return {"ok": True, "item": result}
    if action in {"archive", "restore"} and method == "POST":
        _require_permission(conn, user, write_permission)
        target = "archived" if action == "archive" else "active"
        now = now_iso(); conn.execute("UPDATE p0_master_records SET status = ?, version = version + 1, updated_at = ? WHERE id = ?", (target, now, entity_id))
        updated = conn.execute("SELECT * FROM p0_master_records WHERE id = ?", (entity_id,)).fetchone()
        conn.execute("INSERT INTO p0_master_versions(id, organization_id, master_id, version, change_type, snapshot_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id("masterver"), org, entity_id, updated["version"], target, json.dumps(_master_snapshot(updated)), _user_id(user), now))
        _emit(conn, user, f"master.{action}d", "master", entity_id, ip, {"kind": kind})
        return {"ok": True, "item": _master_view(updated)}
    if method == "PATCH":
        _require_permission(conn, user, write_permission)
        updates = {}; fields = ("name", "status", "effective_from", "effective_to")
        for field in fields:
            if field in payload:
                updates[field] = _text(payload, field, maximum=160 if field == "name" else 40)
        if "config" in payload:
            updates["config_json"] = json.dumps(payload["config"] if isinstance(payload["config"], dict) else {})
        if not updates:
            return {"ok": True, "item": _master_view(row)}
        version = row["version"] + 1; now = now_iso(); updates["version"] = version; updates["updated_at"] = now
        assignments = ", ".join(f"{key} = ?" for key in updates); values = list(updates.values()) + [entity_id, org]
        conn.execute(f"UPDATE p0_master_records SET {assignments} WHERE id = ? AND organization_id = ?", values)
        updated = conn.execute("SELECT * FROM p0_master_records WHERE id = ?", (entity_id,)).fetchone()
        conn.execute("INSERT INTO p0_master_versions(id, organization_id, master_id, version, change_type, snapshot_json, created_by, created_at) VALUES (?, ?, ?, ?, 'updated', ?, ?, ?)", (new_id("masterver"), org, entity_id, version, json.dumps(_master_snapshot(updated)), _user_id(user), now))
        _emit(conn, user, "master.updated", "master", entity_id, ip, {"kind": kind, "version": version, "fields": list(updates)})
        return {"ok": True, "item": _master_view(updated)}
    raise DomainError(405, "Method not allowed", "method_not_allowed")


def _site_shift_routes(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/operations/sites" and method in {"GET", "POST"}:
        if method == "GET":
            rows = conn.execute("SELECT * FROM p0_sites WHERE organization_id = ? ORDER BY name LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("address_json",)) for row in rows]}
        _require_permission(conn, user, "masters.write")
        code = _text(payload, "code", maximum=40).upper(); name = _text(payload, "name", maximum=160)
        if not code or not name: raise DomainError(400, "code and name are required", "validation_error")
        site_id = new_id("site"); now = now_iso()
        conn.execute("INSERT INTO p0_sites(id, organization_id, code, name, city, address_json, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)", (site_id, org, code, name, _text(payload, "city", maximum=80), json.dumps(payload.get("address") if isinstance(payload.get("address"), dict) else {}), _user_id(user), now, now))
        _emit(conn, user, "site.created", "site", site_id, ip, {"code": code}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_sites WHERE id = ?", (site_id,)).fetchone(), ("address_json",))}
    if route == "/api/operations/shifts" and method in {"GET", "POST"}:
        if method == "GET":
            rows = conn.execute("SELECT * FROM p0_shifts WHERE organization_id = ? ORDER BY starts_at LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("demand_json",)) for row in rows]}
        _require_permission(conn, user, "masters.write")
        code = _text(payload, "code", maximum=40).upper(); name = _text(payload, "name", maximum=160); starts = _text(payload, "starts_at", maximum=40); ends = _text(payload, "ends_at", maximum=40)
        if not code or not name or not starts or not ends: raise DomainError(400, "code, name, starts_at and ends_at are required", "validation_error")
        shift_id = new_id("shift"); now = now_iso()
        conn.execute("INSERT INTO p0_shifts(id, organization_id, site_id, code, name, starts_at, ends_at, demand_json, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)", (shift_id, org, _text(payload, "site_id", maximum=100) or None, code, name, starts, ends, json.dumps(payload.get("demand") if isinstance(payload.get("demand"), dict) else {}), _user_id(user), now, now))
        _emit(conn, user, "shift.created", "shift", shift_id, ip, {"code": code}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_shifts WHERE id = ?", (shift_id,)).fetchone(), ("demand_json",))}
    return None


def _duty_row(conn, duty_id, org):
    row = conn.execute("SELECT * FROM domain_duties WHERE id = ? AND organization_id = ?", (duty_id, org)).fetchone()
    if not row: raise DomainError(404, "Duty not found", "not_found")
    return row


def _booking_for_duty(conn, duty, org):
    row = conn.execute("SELECT * FROM domain_bookings WHERE id = ? AND organization_id = ?", (duty["booking_id"], org)).fetchone()
    if not row: return {"pickup": {}, "dropoff": {}, "passenger_name": ""}
    return {**dict(row), "pickup": _json(row["pickup_json"], {}), "dropoff": _json(row["dropoff_json"], {})}


def _route_detail(conn, plan_id, org):
    plan = _owned(conn, "p0_route_plans", plan_id, org, "Route plan not found")
    stops = conn.execute("SELECT * FROM p0_route_stops WHERE organization_id = ? AND route_plan_id = ? ORDER BY sequence", (org, plan_id)).fetchall()
    assignments = conn.execute("SELECT * FROM p0_roster_assignments WHERE organization_id = ? AND route_plan_id = ? ORDER BY offered_at", (org, plan_id)).fetchall()
    item = _row(plan, ("constraints_json", "feasibility_json")); item["stops"] = [_row(row, ("pickup_json", "dropoff_json")) for row in stops]; item["assignments"] = [_row(row) for row in assignments]; return item


def _operations_routes(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/operations/dispatch-board" and method == "GET":
        _require_permission(conn, user, "dispatch.read")
        rows = conn.execute("SELECT a.*, d.status AS duty_status, b.booking_reference, b.passenger_name, b.scheduled_at FROM p0_roster_assignments a JOIN domain_duties d ON d.id = a.duty_id AND d.organization_id = a.organization_id LEFT JOIN domain_bookings b ON b.id = d.booking_id WHERE a.organization_id = ? ORDER BY COALESCE(a.response_deadline, a.offered_at) LIMIT ?", (org, _limit(query))).fetchall()
        return {"ok": True, "items": [_row(row) for row in rows]}
    plan_match = re.fullmatch(r"/api/operations/route-plans(?:/([^/]+)(?:/(publish))?)?", route)
    if plan_match:
        plan_id, action = plan_match.groups()
        if not plan_id and method == "GET":
            _require_permission(conn, user, "route_plans.read"); rows = conn.execute("SELECT * FROM p0_route_plans WHERE organization_id = ? ORDER BY plan_date DESC, version DESC LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("constraints_json", "feasibility_json")) for row in rows]}
        if not plan_id and method == "POST":
            _require_permission(conn, user, "route_plans.write")
            plan_date = _text(payload, "plan_date", maximum=20) or datetime.now(timezone.utc).date().isoformat()
            duty_ids = payload.get("duty_ids") if isinstance(payload.get("duty_ids"), list) else []
            if not duty_ids:
                duty_rows = conn.execute("SELECT id FROM domain_duties WHERE organization_id = ? AND status NOT IN ('completed','cancelled') ORDER BY reporting_at LIMIT 100", (org,)).fetchall(); duty_ids = [row["id"] for row in duty_rows]
            if not duty_ids: raise DomainError(400, "At least one open duty is required", "validation_error")
            duties = [_duty_row(conn, duty_id, org) for duty_id in duty_ids]
            warnings = []; stops = []
            for index, duty in enumerate(sorted(duties, key=lambda row: row["reporting_at"] or ""), 1):
                booking = _booking_for_duty(conn, duty, org)
                if not duty["reporting_at"]: warnings.append({"duty_id": duty["id"], "code": "missing_reporting_time", "message": "Duty has no reporting time"})
                stops.append((duty, booking, index))
            max_stops = _int(payload.get("max_stops"), "max_stops", 40)
            if len(stops) > max_stops: warnings.append({"code": "stop_capacity_exceeded", "message": f"{len(stops)} stops exceed the configured limit of {max_stops}"})
            feasibility = {"feasible": not any(item.get("code") == "stop_capacity_exceeded" for item in warnings), "warnings": warnings, "method": "ordered_by_reporting_at", "sample_size": len(stops)}
            plan_id = new_id("routeplan"); now = now_iso(); constraints = payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {"max_stops": max_stops}
            conn.execute("INSERT INTO p0_route_plans(id, organization_id, site_id, plan_date, version, status, routing_mode, constraints_json, feasibility_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 'draft', 'sequence_by_reporting_at', ?, ?, ?, ?, ?)", (plan_id, org, _text(payload, "site_id", maximum=100) or None, plan_date, json.dumps(constraints), json.dumps(feasibility), _user_id(user), now, now))
            for duty, booking, sequence in stops:
                conn.execute("INSERT INTO p0_route_stops(id, organization_id, route_plan_id, duty_id, sequence, pickup_json, dropoff_json, reporting_at, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?)", (new_id("routestop"), org, plan_id, duty["id"], sequence, json.dumps(booking.get("pickup", {})), json.dumps(booking.get("dropoff", {})), duty["reporting_at"], now))
            _emit(conn, user, "route_plan.created", "route_plan", plan_id, ip, {"plan_date": plan_date, "stops": len(stops), "feasible": feasibility["feasible"]})
            return {"ok": True, "item": _route_detail(conn, plan_id, org)}
        if plan_id and action == "publish" and method == "POST":
            _require_permission(conn, user, "route_plans.write"); plan = _owned(conn, "p0_route_plans", plan_id, org, "Route plan not found"); _status_transition(plan["status"], "published", {"draft": {"published"}})
            if not _json(plan["feasibility_json"], {}).get("feasible", True) and not payload.get("allow_warnings"): raise DomainError(409, "Route plan is infeasible; resolve warnings or explicitly allow them", "route_infeasible")
            now = now_iso(); conn.execute("UPDATE p0_route_plans SET status = 'published', published_by = ?, updated_at = ? WHERE id = ?", (_user_id(user), now, plan_id)); _emit(conn, user, "route_plan.published", "route_plan", plan_id, ip, {}); return {"ok": True, "item": _route_detail(conn, plan_id, org)}
        if plan_id and method == "GET":
            _require_permission(conn, user, "route_plans.read"); return {"ok": True, "item": _route_detail(conn, plan_id, org)}
    assignment_match = re.fullmatch(r"/api/operations/assignments(?:/([^/]+)(?:/(accept|reject|expire))?)?", route)
    if assignment_match:
        assignment_id, action = assignment_match.groups()
        if not assignment_id and method == "POST":
            _require_permission(conn, user, "dispatch.write")
            plan = _owned(conn, "p0_route_plans", _text(payload, "route_plan_id", 100), org, "Route plan not found")
            duty_id = _text(payload, "duty_id", 100); duty = _duty_row(conn, duty_id, org)
            driver_id = _text(payload, "driver_id", 100) or None; vehicle_id = _text(payload, "vehicle_id", 100) or None
            if driver_id: _owned(conn, "domain_drivers", driver_id, org, "Driver not found")
            if vehicle_id: _owned(conn, "domain_vehicles", vehicle_id, org, "Vehicle not found")
            deadline = _text(payload, "response_deadline", 40) or (datetime.now(timezone.utc) + timedelta(minutes=15)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            now = now_iso(); assignment_id = new_id("assignment")
            conn.execute("INSERT INTO p0_roster_assignments(id, organization_id, route_plan_id, duty_id, driver_id, vehicle_id, status, offered_at, response_deadline, created_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'offered', ?, ?, ?, ?)", (assignment_id, org, plan["id"], duty["id"], driver_id, vehicle_id, now, deadline, _user_id(user), now))
            conn.execute("INSERT INTO p0_dispatch_events(id, organization_id, assignment_id, duty_id, event_type, payload_json, actor_id, created_at) VALUES (?, ?, ?, ?, 'assignment.offered', ?, ?, ?)", (new_id("dispatch"), org, assignment_id, duty["id"], json.dumps({"driver_id": driver_id, "vehicle_id": vehicle_id}), _user_id(user), now))
            _emit(conn, user, "assignment.offered", "assignment", assignment_id, ip, {"duty_id": duty["id"]}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_roster_assignments WHERE id = ?", (assignment_id,)).fetchone())}
        if assignment_id and action and method == "POST":
            assignment = _owned(conn, "p0_roster_assignments", assignment_id, org, "Assignment not found")
            idempotency_key = _text(payload, "idempotency_key", maximum=160) or None
            if idempotency_key:
                replay = conn.execute("SELECT id FROM p0_dispatch_events WHERE organization_id = ? AND assignment_id = ? AND json_extract(payload_json, '$.idempotency_key') = ?", (org, assignment_id, idempotency_key)).fetchone()
                if replay:
                    return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_roster_assignments WHERE id = ?", (assignment_id,)).fetchone()), "idempotent": True}
            if _role(user) == "driver":
                linked = conn.execute("SELECT 1 FROM domain_drivers WHERE id = ? AND user_id = ? AND organization_id = ?", (assignment["driver_id"], _user_id(user), org)).fetchone()
                if not linked: raise DomainError(403, "This assignment is not assigned to the current driver", "permission_denied")
                _require_permission(conn, user, "dispatch.respond")
            else: _require_permission(conn, user, "dispatch.write")
            target = {"accept": "accepted", "reject": "rejected", "expire": "expired"}[action]
            _status_transition(assignment["status"], target, {"offered": {"accepted", "rejected", "expired"}})
            now = now_iso(); reason = _text(payload, "reason", maximum=300)
            conn.execute("UPDATE p0_roster_assignments SET status = ?, responded_at = ?, rejection_reason = ?, updated_at = ? WHERE id = ?", (target, now, reason, now, assignment_id))
            conn.execute("INSERT INTO p0_dispatch_events(id, organization_id, assignment_id, duty_id, event_type, payload_json, actor_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id("dispatch"), org, assignment_id, assignment["duty_id"], f"assignment.{action}", json.dumps({"reason": reason, "idempotency_key": idempotency_key}), _user_id(user), now))
            if target == "accepted": conn.execute("UPDATE domain_duties SET driver_id = ?, vehicle_id = ?, status = 'accepted', updated_at = ? WHERE id = ? AND organization_id = ?", (assignment["driver_id"], assignment["vehicle_id"], now, assignment["duty_id"], org))
            if target in {"rejected", "expired"}:
                conn.execute("INSERT INTO p0_replacements(id, organization_id, assignment_id, duty_id, reason, status, due_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)", (new_id("replacement"), org, assignment_id, assignment["duty_id"], reason or target, assignment["response_deadline"], _user_id(user), now, now))
            _emit(conn, user, f"assignment.{action}", "assignment", assignment_id, ip, {"duty_id": assignment["duty_id"], "status": target}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_roster_assignments WHERE id = ?", (assignment_id,)).fetchone())}
        if assignment_id and method == "GET": _require_permission(conn, user, "dispatch.read"); return {"ok": True, "item": _row(_owned(conn, "p0_roster_assignments", assignment_id, org, "Assignment not found"))}
        if not assignment_id and method == "GET": _require_permission(conn, user, "dispatch.read"); rows = conn.execute("SELECT * FROM p0_roster_assignments WHERE organization_id = ? ORDER BY offered_at DESC LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row) for row in rows]}
    replacement_match = re.fullmatch(r"/api/operations/replacements(?:/([^/]+))?", route)
    if replacement_match and method in {"GET", "POST", "PATCH"}:
        replacement_id = replacement_match.group(1)
        if method == "GET":
            _require_permission(conn, user, "replacements.manage"); sql = "SELECT * FROM p0_replacements WHERE organization_id = ?"; args = [org]
            if replacement_id: sql += " AND id = ?"; args.append(replacement_id)
            sql += " ORDER BY created_at DESC LIMIT ?"; args.append(_limit(query)); rows = conn.execute(sql, args).fetchall(); return {"ok": True, "items": [_row(row) for row in rows]} if not replacement_id else {"ok": True, "item": _row(rows[0]) if rows else None}
        _require_permission(conn, user, "replacements.manage")
        if method == "POST":
            duty_id = _text(payload, "duty_id", 100); _duty_row(conn, duty_id, org); now = now_iso(); replacement_id = new_id("replacement")
            conn.execute("INSERT INTO p0_replacements(id, organization_id, duty_id, reason, status, replacement_driver_id, replacement_vehicle_id, due_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)", (replacement_id, org, duty_id, _text(payload, "reason", "capacity_exception", 300), _text(payload, "replacement_driver_id", 100) or None, _text(payload, "replacement_vehicle_id", 100) or None, _text(payload, "due_at", 40) or None, _user_id(user), now, now)); _emit(conn, user, "replacement.created", "replacement", replacement_id, ip, {"duty_id": duty_id}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_replacements WHERE id = ?", (replacement_id,)).fetchone())}
        replacement = _owned(conn, "p0_replacements", replacement_id, org, "Replacement not found"); status = _text(payload, "status", replacement["status"], 24); now = now_iso(); conn.execute("UPDATE p0_replacements SET status = ?, replacement_driver_id = COALESCE(?, replacement_driver_id), replacement_vehicle_id = COALESCE(?, replacement_vehicle_id), resolved_at = ?, updated_at = ? WHERE id = ?", (status, _text(payload, "replacement_driver_id", 100) or None, _text(payload, "replacement_vehicle_id", 100) or None, now if status == "resolved" else replacement["resolved_at"], now, replacement_id)); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_replacements WHERE id = ?", (replacement_id,)).fetchone())}
    return None


def _safety_routes(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/safety/policies" and method in {"GET", "POST"}:
        if method == "GET":
            _require_permission(conn, user, "safety.read"); rows = conn.execute("SELECT * FROM p0_safety_policies WHERE organization_id = ? AND status = 'active' ORDER BY version DESC", (org,)).fetchall(); return {"ok": True, "items": [_row(row, ("rules_json",)) for row in rows]}
        _require_permission(conn, user, "safety.incidents.manage"); code = _text(payload, "code", "default", 60).lower(); name = _text(payload, "name", "Default safety policy", 160); now = now_iso(); version = (conn.execute("SELECT COALESCE(MAX(version),0) v FROM p0_safety_policies WHERE organization_id = ? AND code = ?", (org, code)).fetchone()["v"] or 0) + 1; policy_id = new_id("safetypolicy")
        conn.execute("INSERT INTO p0_safety_policies(id, organization_id, code, name, version, rules_json, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)", (policy_id, org, code, name, version, json.dumps(payload.get("rules") if isinstance(payload.get("rules"), dict) else {"sos_minutes": 0, "critical_minutes": 5, "high_minutes": 15}), _user_id(user), now, now)); _emit(conn, user, "safety_policy.created", "safety_policy", policy_id, ip, {"version": version}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_safety_policies WHERE id = ?", (policy_id,)).fetchone(), ("rules_json",))}
    if route == "/api/safety/alerts" and method == "POST":
        if _role(user) == "driver": _require_permission(conn, user, "safety.incidents.create")
        else: _require_permission(conn, user, "safety.incidents.manage")
        incident_payload = {**payload, "alert_type": payload.get("alert_type") or "operational_alert", "title": payload.get("title") or payload.get("alert_type") or "Safety alert"}
        return _create_incident(conn, user, incident_payload, ip)
    incident_match = re.fullmatch(r"/api/safety/incidents(?:/([^/]+)(?:/(acknowledge|investigate|contain|resolve|close))?)?", route)
    if incident_match:
        incident_id, action = incident_match.groups()
        if not incident_id and method == "GET":
            _require_permission(conn, user, "safety.read"); rows = conn.execute("SELECT * FROM p0_safety_incidents WHERE organization_id = ? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, opened_at DESC LIMIT ?", (org, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]}
        if not incident_id and method == "POST":
            if _role(user) == "driver": _require_permission(conn, user, "safety.incidents.create")
            else: _require_permission(conn, user, "safety.incidents.manage")
            return _create_incident(conn, user, payload, ip)
        incident = _owned(conn, "p0_safety_incidents", incident_id, org, "Safety incident not found")
        if method == "GET": _require_permission(conn, user, "safety.read"); item = _row(incident, ("evidence_json",)); item["actions"] = [_row(row, ("evidence_json",)) for row in conn.execute("SELECT * FROM p0_safety_actions WHERE organization_id = ? AND incident_id = ? ORDER BY created_at", (org, incident_id)).fetchall()]; return {"ok": True, "item": item}
        if action and method == "POST": return _transition_incident(conn, user, incident, action, payload, ip)
    action_match = re.fullmatch(r"/api/safety/incidents/([^/]+)/actions(?:/([^/]+))?", route)
    if action_match and method in {"GET", "POST", "PATCH"}:
        incident_id, action_id = action_match.groups(); _owned(conn, "p0_safety_incidents", incident_id, org, "Safety incident not found")
        if method == "GET": _require_permission(conn, user, "safety.read"); rows = conn.execute("SELECT * FROM p0_safety_actions WHERE organization_id = ? AND incident_id = ? ORDER BY created_at", (org, incident_id)).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]}
        _require_permission(conn, user, "safety.incidents.manage")
        if method == "POST":
            title = _text(payload, "title", maximum=200)
            if not title: raise DomainError(400, "Action title is required", "validation_error")
            action_id = new_id("safetyaction"); now = now_iso(); conn.execute("INSERT INTO p0_safety_actions(id, organization_id, incident_id, title, status, owner_id, due_at, evidence_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)", (action_id, org, incident_id, title, _text(payload, "owner_id", 100) or None, _text(payload, "due_at", 40) or None, json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}), _user_id(user), now, now)); _emit(conn, user, "safety_action.created", "safety_action", action_id, ip, {"incident_id": incident_id}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_safety_actions WHERE id = ?", (action_id,)).fetchone(), ("evidence_json",))}
        action_row = _owned(conn, "p0_safety_actions", action_id, org, "Safety action not found"); status = _text(payload, "status", action_row["status"], 24); now = now_iso(); conn.execute("UPDATE p0_safety_actions SET status = ?, resolution_note = ?, evidence_json = ?, updated_at = ? WHERE id = ?", (status, _text(payload, "resolution_note", maximum=500), json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"), dict) else _json(action_row["evidence_json"], {})), now, action_id)); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_safety_actions WHERE id = ?", (action_id,)).fetchone(), ("evidence_json",))}
    if route == "/api/safety/evaluate" and method == "POST":
        if _role(user) == "driver": _require_permission(conn, user, "safety.incidents.create")
        else: _require_permission(conn, user, "safety.incidents.manage")
        trigger = bool(payload.get("trigger")) or payload.get("severity") in {"critical", "high"} or payload.get("alert_type") in {"sos", "route_deviation", "missed_pickup"}
        if not trigger: return {"ok": True, "triggered": False, "reason": "No configured safety rule matched"}
        return {"ok": True, "triggered": True, "incident": _create_incident(conn, user, payload, ip)["item"]}
    return None


def _create_incident(conn, user, payload, ip):
    org = _org(user); alert_type = _text(payload, "alert_type", "operational_alert", 60); severity = _text(payload, "severity", "medium", 20).lower()
    if severity not in {"low", "medium", "high", "critical"}: raise DomainError(400, "Invalid incident severity", "validation_error")
    duty_id = _text(payload, "duty_id", 100) or None
    if duty_id:
        _duty_row(conn, duty_id, org)
        if _role(user) == "driver" and not conn.execute("SELECT 1 FROM domain_duties d JOIN domain_drivers dr ON dr.id = d.driver_id WHERE d.id = ? AND dr.user_id = ? AND d.organization_id = ?", (duty_id, _user_id(user), org)).fetchone(): raise DomainError(403, "This incident is not linked to the current duty", "permission_denied")
    due_minutes = {"critical": 5, "high": 15, "medium": 60, "low": 240}[severity]
    due_at = _text(payload, "due_at", 40) or (datetime.now(timezone.utc) + timedelta(minutes=due_minutes)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    incident_id = new_id("incident"); now = now_iso(); conn.execute("INSERT INTO p0_safety_incidents(id, organization_id, duty_id, alert_type, severity, status, title, description, owner_id, due_at, evidence_json, opened_at, updated_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)", (incident_id, org, duty_id, alert_type, severity, _text(payload, "title", alert_type, 200), _text(payload, "description", maximum=1000), _text(payload, "owner_id", 100) or None, due_at, json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}), now, now)); _emit(conn, user, "safety_incident.opened", "safety_incident", incident_id, ip, {"severity": severity, "duty_id": duty_id}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_safety_incidents WHERE id = ?", (incident_id,)).fetchone(), ("evidence_json",))}


def _transition_incident(conn, user, incident, action, payload, ip):
    _require_permission(conn, user, "safety.incidents.manage")
    target = {"acknowledge": "acknowledged", "investigate": "investigating", "contain": "contained", "resolve": "resolved", "close": "closed"}[action]
    allowed = {"open": {"acknowledged", "investigating", "resolved"}, "acknowledged": {"investigating", "contained", "resolved"}, "investigating": {"contained", "resolved"}, "contained": {"resolved"}, "resolved": {"closed"}, "closed": set()}
    _status_transition(incident["status"], target, allowed)
    if target == "closed":
        open_actions = conn.execute("SELECT COUNT(*) n FROM p0_safety_actions WHERE incident_id = ? AND organization_id = ? AND status NOT IN ('completed','closed','cancelled')", (incident["id"], _org(user))).fetchone()["n"]
        if open_actions and not _has_permission(conn, user, "safety.override_close"): raise DomainError(409, "Complete corrective actions before closing the incident", "open_corrective_actions")
    now = now_iso(); resolved = now if target == "resolved" else incident["resolved_at"]; closed = now if target == "closed" else incident["closed_at"]; root = _text(payload, "root_cause", maximum=500) or incident["root_cause"]
    conn.execute("UPDATE p0_safety_incidents SET status = ?, root_cause = ?, updated_at = ?, resolved_at = ?, closed_at = ?, closed_by = ? WHERE id = ?", (target, root, now, resolved, closed, _user_id(user) if target == "closed" else incident["closed_by"], incident["id"]))
    _emit(conn, user, f"safety_incident.{action}d", "safety_incident", incident["id"], ip, {"status": target}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_safety_incidents WHERE id = ?", (incident["id"],)).fetchone(), ("evidence_json",))}


def _network_region_routes(conn, user, method, route, query, payload, ip):
    # The legacy Network handler owns the feature-flag mutation itself so an
    # operator can re-enable a paused module; P0 only owns additive controls.
    if route == "/api/network/v1/feature-flag":
        return None
    org = _org(user); _network_ready(conn, org)
    region_match = re.fullmatch(r"/api/network/v1/regions(?:/([^/]+))?", route)
    if region_match:
        region_id = region_match.group(1)
        if method == "GET":
            _require_permission(conn, user, "network.regions.read"); sql = "SELECT * FROM p0_network_regions WHERE organization_id = ?"; args = [org]
            if region_id: sql += " AND id = ?"; args.append(region_id)
            sql += " ORDER BY name LIMIT ?"; args.append(_limit(query)); rows = conn.execute(sql, args).fetchall(); result = [_row(row, ("cities_json", "feature_flags_json")) for row in rows]; return {"ok": True, "items": result} if not region_id else {"ok": True, "item": result[0] if result else None}
        _require_permission(conn, user, "network.regions.write")
        if method == "POST" and not region_id:
            code = _text(payload, "code", maximum=40).upper(); name = _text(payload, "name", maximum=160)
            if not code or not name: raise DomainError(400, "code and name are required", "validation_error")
            rid = new_id("networkregion"); now = now_iso(); conn.execute("INSERT INTO p0_network_regions(id, organization_id, code, name, cities_json, feature_flags_json, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)", (rid, org, code, name, json.dumps(payload.get("cities") if isinstance(payload.get("cities"), list) else []), json.dumps(payload.get("feature_flags") if isinstance(payload.get("feature_flags"), dict) else {}), _user_id(user), now, now)); _emit(conn, user, "network_region.created", "network_region", rid, ip, {"code": code}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_regions WHERE id = ?", (rid,)).fetchone(), ("cities_json", "feature_flags_json"))}
        if method == "PATCH" and region_id:
            row = _owned(conn, "p0_network_regions", region_id, org, "Network region not found"); updates = {key: payload[key] for key in ("name", "status") if key in payload};
            if "cities" in payload: updates["cities_json"] = json.dumps(payload["cities"] if isinstance(payload["cities"], list) else [])
            if "feature_flags" in payload: updates["feature_flags_json"] = json.dumps(payload["feature_flags"] if isinstance(payload["feature_flags"], dict) else {})
            if updates:
                updates["version"] = row["version"] + 1; updates["updated_at"] = now_iso(); assignments = ", ".join(f"{key} = ?" for key in updates); conn.execute(f"UPDATE p0_network_regions SET {assignments} WHERE id = ? AND organization_id = ?", list(updates.values()) + [region_id, org])
            return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_regions WHERE id = ?", (region_id,)).fetchone(), ("cities_json", "feature_flags_json"))}
    approval_match = re.fullmatch(r"/api/network/v1/vendor-approvals(?:/([^/]+))?", route)
    if approval_match and method in {"GET", "POST", "PATCH"}:
        approval_id = approval_match.group(1)
        if method == "GET":
            _require_permission(conn, user, "network.vendor_approvals.read"); sql = "SELECT a.*, r.code AS region_code, r.name AS region_name, v.vendor_name FROM p0_network_vendor_approvals a JOIN p0_network_regions r ON r.id = a.region_id LEFT JOIN domain_network_vendor_profiles v ON v.id = a.vendor_profile_id WHERE a.organization_id = ?"; args = [org]
            if approval_id: sql += " AND a.id = ?"; args.append(approval_id)
            sql += " ORDER BY a.created_at DESC LIMIT ?"; args.append(_limit(query)); rows = conn.execute(sql, args).fetchall(); return {"ok": True, "items": [_row(row, ("evidence_json",)) for row in rows]} if not approval_id else {"ok": True, "item": _row(rows[0], ("evidence_json",)) if rows else None}
        if method == "POST":
            _require_permission(conn, user, "network.vendor_approvals.write"); profile = _network_profile(conn, _text(payload, "vendor_profile_id", 100), org); region = _owned(conn, "p0_network_regions", _text(payload, "region_id", 100), org, "Network region not found"); aid = new_id("vendorapproval"); now = now_iso(); conn.execute("INSERT INTO p0_network_vendor_approvals(id, organization_id, vendor_profile_id, region_id, status, evidence_json, expires_at, note, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)", (aid, org, profile["id"], region["id"], json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}), _text(payload, "expires_at", 40) or None, _text(payload, "note", maximum=500), _user_id(user), now, now)); _emit(conn, user, "vendor_approval.created", "vendor_approval", aid, ip, {"vendor_profile_id": profile["id"], "region_id": region["id"]}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_vendor_approvals WHERE id = ?", (aid,)).fetchone(), ("evidence_json",))}
        _require_permission(conn, user, "network.vendor_approvals.write"); approval = _owned(conn, "p0_network_vendor_approvals", approval_id, org, "Vendor approval not found"); target = _text(payload, "status", approval["status"], 24); allowed = {"pending": {"approved", "probation", "rejected", "suspended"}, "probation": {"approved", "suspended", "offboarded"}, "approved": {"probation", "suspended", "offboarded"}, "suspended": {"approved", "offboarded"}, "rejected": {"pending"}, "offboarded": set()}; _status_transition(approval["status"], target, allowed); now = now_iso(); conn.execute("UPDATE p0_network_vendor_approvals SET status = ?, note = ?, decided_by = ?, decided_at = ?, updated_at = ? WHERE id = ?", (target, _text(payload, "note", maximum=500), _user_id(user), now, now, approval_id)); _emit(conn, user, "vendor_approval.transitioned", "vendor_approval", approval_id, ip, {"status": target}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_vendor_approvals WHERE id = ?", (approval_id,)).fetchone(), ("evidence_json",))}
    return None


def _network_lifecycle_routes(conn, user, method, route, query, payload, ip):
    org = _org(user); _network_ready(conn, org)
    life_match = re.fullmatch(r"/api/network/v1/requirements/([^/]+)/lifecycle", route)
    if life_match and method in {"GET", "POST"}:
        requirement = _network_requirement(conn, life_match.group(1), org)
        if method == "GET": return {"ok": True, "item": _row(requirement), "allowed": {"draft": ["submitted", "cancelled"], "submitted": ["under_review", "cancelled"], "under_review": ["vendors_invited", "cancelled"], "vendors_invited": ["quoting", "cancelled"], "quoting": ["matching", "quote_closed", "expired", "cancelled"], "matching": ["quote_closed", "negotiation", "award_pending", "cancelled"], "quote_closed": ["comparison_ready", "negotiation", "expired"], "comparison_ready": ["award_pending", "negotiation", "cancelled"], "negotiation": ["comparison_ready", "award_pending", "cancelled"], "award_pending": ["awarded", "cancelled"], "awarded": ["contract_pending", "cancelled"], "contract_pending": ["activated", "cancelled"], "activated": ["live", "suspended"], "live": ["completed", "suspended"], "suspended": ["live", "cancelled"], "completed": [], "cancelled": [], "expired": [], "published": ["matching", "quoting", "cancelled", "expired"], "matched": ["quoting", "award_pending"], "quoted": ["comparison_ready", "award_pending"], "award_pending": ["awarded", "cancelled"]}.get(requirement["status"], [])}
        _require_permission(conn, user, "network.lifecycle.write"); target = _text(payload, "status", maximum=30); allowed = {"draft": {"submitted", "cancelled"}, "submitted": {"under_review", "cancelled"}, "under_review": {"vendors_invited", "cancelled"}, "vendors_invited": {"quoting", "cancelled"}, "quoting": {"matching", "quote_closed", "expired", "cancelled"}, "matching": {"quote_closed", "negotiation", "award_pending", "cancelled"}, "quote_closed": {"comparison_ready", "negotiation", "expired"}, "comparison_ready": {"award_pending", "negotiation", "cancelled"}, "negotiation": {"comparison_ready", "award_pending", "cancelled"}, "award_pending": {"awarded", "cancelled"}, "awarded": {"contract_pending", "cancelled"}, "contract_pending": {"activated", "cancelled"}, "activated": {"live", "suspended"}, "live": {"completed", "suspended"}, "suspended": {"live", "cancelled"}, "published": {"matching", "quoting", "cancelled", "expired"}, "matched": {"quoting", "award_pending"}, "quoted": {"comparison_ready", "award_pending"}}; _status_transition(requirement["status"], target, allowed); now = now_iso(); deadline = _text(payload, "deadline_at", 40) or requirement["deadline_at"]; expires = _text(payload, "expires_at", 40) or requirement["expires_at"]; conn.execute("UPDATE domain_network_requirements SET status = ?, deadline_at = ?, expires_at = ?, closed_reason = ?, approved_at = ?, completed_at = ?, updated_at = ? WHERE id = ? AND organization_id = ?", (target, deadline, expires, _text(payload, "closed_reason", maximum=300), now if target in {"under_review", "award_pending", "awarded"} else requirement["approved_at"], now if target == "completed" else requirement["completed_at"], now, requirement["id"], org)); _emit(conn, user, "network_requirement.transitioned", "requirement", requirement["id"], ip, {"from": requirement["status"], "to": target}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM domain_network_requirements WHERE id = ?", (requirement["id"],)).fetchone())}
    if route == "/api/network/v1/deadlines/process" and method == "POST":
        _require_permission(conn, user, "network.lifecycle.write"); now = _text(payload, "now", 40) or now_iso(); rows = conn.execute("SELECT * FROM domain_network_requirements WHERE organization_id = ? AND status IN ('draft','submitted','under_review','vendors_invited','quoting','matching','published','matched','quoted') AND ((deadline_at IS NOT NULL AND deadline_at < ?) OR (expires_at IS NOT NULL AND expires_at < ?))", (org, now, now)).fetchall(); expired=[]
        for row in rows: conn.execute("UPDATE domain_network_requirements SET status = 'expired', closed_reason = 'deadline_or_expiry', updated_at = ? WHERE id = ?", (now, row["id"])); _emit(conn, user, "network_requirement.expired", "requirement", row["id"], ip, {"reason": "deadline_or_expiry"}); expired.append(row["id"])
        return {"ok": True, "expired_requirement_ids": expired, "count": len(expired), "processed_at": now}
    evaluation_match = re.fullmatch(r"/api/network/v1/requirements/([^/]+)/evaluations(?:/([^/]+))?", route)
    if evaluation_match and method in {"GET", "POST"}:
        requirement_id, evaluation_id = evaluation_match.groups(); _network_requirement(conn, requirement_id, org)
        if method == "GET":
            _require_permission(conn, user, "network.evaluations.write"); rows = conn.execute("SELECT * FROM p0_network_quote_evaluations WHERE organization_id = ? AND requirement_id = ? ORDER BY total_score DESC", (org, requirement_id)).fetchall(); return {"ok": True, "items": [_row(row) for row in rows]}
        _require_permission(conn, user, "network.evaluations.write"); quote_id = _text(payload, "quote_id", 100); quote = _owned(conn, "domain_network_quotes", quote_id, org, "Network quote not found"); version = _int(payload.get("version"), "version", 1); commercial = float(payload.get("commercial_score") or 0); quality = float(payload.get("quality_score") or 0); risk = float(payload.get("risk_score") or 0); total = round(commercial * .4 + quality * .4 + risk * .2, 4); eid = new_id("quoteeval"); now = now_iso(); conn.execute("INSERT INTO p0_network_quote_evaluations(id, organization_id, requirement_id, quote_id, version, commercial_score, quality_score, risk_score, total_score, sample_size, confidence, comments, status, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?)", (eid, org, requirement_id, quote_id, version, commercial, quality, risk, total, _int(payload.get("sample_size"), "sample_size", 0), _text(payload, "confidence", "cold_start", 24), _text(payload, "comments", maximum=1000), _user_id(user), now, now)); _emit(conn, user, "network_quote.evaluated", "quote_evaluation", eid, ip, {"quote_id": quote_id, "total_score": total}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_quote_evaluations WHERE id = ?", (eid,)).fetchone())}
    return None


def _network_collaboration_routes(conn, user, method, route, query, payload, ip):
    org = _org(user); _network_ready(conn, org)
    if route == "/api/network/v1/messages" and method in {"GET", "POST"}:
        if method == "GET":
            _require_permission(conn, user, "network.messages.write"); thread = query.get("thread_key", [""])[0]; sql = "SELECT * FROM p0_network_messages WHERE organization_id = ?"; args = [org]
            if thread: sql += " AND thread_key = ?"; args.append(thread)
            sql += " ORDER BY created_at ASC LIMIT ?"; args.append(_limit(query)); return {"ok": True, "items": [_row(row) for row in conn.execute(sql, args).fetchall()]}
        _require_permission(conn, user, "network.messages.write"); thread = _text(payload, "thread_key", 120); body = _text(payload, "body", maximum=4000)
        if not thread or not body: raise DomainError(400, "thread_key and body are required", "validation_error")
        mid = new_id("networkmsg"); now = now_iso(); conn.execute("INSERT INTO p0_network_messages(id, organization_id, thread_key, requirement_id, service_order_id, vendor_profile_id, visibility, body, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (mid, org, thread, _text(payload, "requirement_id", 100) or None, _text(payload, "service_order_id", 100) or None, _text(payload, "vendor_profile_id", 100) or None, _text(payload, "visibility", "participants", 24), body, _user_id(user), now)); _emit(conn, user, "network_message.created", "network_message", mid, ip, {"thread_key": thread}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_messages WHERE id = ?", (mid,)).fetchone())}
    observation_match = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/metric-observations", route)
    if observation_match and method in {"GET", "POST"}:
        service_id = observation_match.group(1); order = _service_order(conn, service_id, org)
        if method == "GET":
            rows = conn.execute("SELECT * FROM p0_network_metric_observations WHERE organization_id = ? AND service_order_id = ? ORDER BY observed_at DESC LIMIT ?", (org, service_id, _limit(query))).fetchall(); return {"ok": True, "items": [_row(row, ("source_event_ids_json",)) for row in rows]}
        _require_permission(conn, user, "network.metrics.write"); metric = _text(payload, "metric_key", 80); oid = new_id("metricobs"); now = now_iso(); value = float(payload.get("value") or 0); sample = _int(payload.get("sample_size"), "sample_size", 0); conn.execute("INSERT INTO p0_network_metric_observations(id, organization_id, service_order_id, vendor_profile_id, metric_key, value, unit, sample_size, source_event_ids_json, formula_version, observed_at, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (oid, org, order["id"], _text(payload, "vendor_profile_id", 100) or order["vendor_profile_id"], metric, value, _text(payload, "unit", 80), sample, json.dumps(payload.get("source_event_ids") if isinstance(payload.get("source_event_ids"), list) else []), _text(payload, "formula_version", "v1", 40), _text(payload, "observed_at", 40) or now, _user_id(user), now)); _emit(conn, user, "metric_observation.created", "metric_observation", oid, ip, {"service_order_id": service_id, "metric_key": metric}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_metric_observations WHERE id = ?", (oid,)).fetchone(), ("source_event_ids_json",))}
    return None


def _scorecard_settlement_routes(conn, user, method, route, query, payload, ip):
    org = _org(user); _network_ready(conn, org)
    score_match = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/scorecard-runs", route)
    if score_match and method in {"GET", "POST"}:
        service_id = score_match.group(1); _service_order(conn, service_id, org)
        if method == "GET":
            _require_permission(conn, user, "network.scorecards.write"); rows = conn.execute("SELECT * FROM p0_network_scorecard_runs WHERE organization_id = ? AND service_order_id = ? ORDER BY created_at DESC", (org, service_id)).fetchall(); return {"ok": True, "items": [_row(row, ("metrics_json",)) for row in rows]}
        _require_permission(conn, user, "network.scorecards.write"); start = _text(payload, "period_start", 40); end = _text(payload, "period_end", 40)
        if not start or not end: raise DomainError(400, "period_start and period_end are required", "validation_error")
        observations = conn.execute("SELECT metric_key, AVG(value) value, SUM(sample_size) sample_size, MAX(formula_version) formula_version FROM p0_network_metric_observations WHERE organization_id = ? AND service_order_id = ? AND observed_at >= ? AND observed_at <= ? GROUP BY metric_key", (org, service_id, start, end)).fetchall()
        sample = sum(int(row["sample_size"] or 0) for row in observations); confidence = "high" if sample >= 30 else "medium" if sample >= 10 else "low" if sample > 0 else "cold_start"; metrics = {row["metric_key"]: {"value": round(float(row["value"] or 0), 4), "sample_size": int(row["sample_size"] or 0)} for row in observations}; score = round(sum(item["value"] for item in metrics.values()) / len(metrics), 4) if metrics else 0; formula = _text(payload, "formula_version", "v1", 40); sid = new_id("scorecardrun"); now = now_iso()
        conn.execute("INSERT INTO p0_network_scorecard_runs(id, organization_id, service_order_id, period_start, period_end, formula_version, sample_size, confidence, score, metrics_json, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (sid, org, service_id, start, end, formula, sample, confidence, score, json.dumps(metrics), _user_id(user), now)); _emit(conn, user, "scorecard.computed", "scorecard_run", sid, ip, {"service_order_id": service_id, "confidence": confidence, "sample_size": sample}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_scorecard_runs WHERE id = ?", (sid,)).fetchone(), ("metrics_json",))}
    statement_match = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/settlement-statements(?:/([^/]+)/(approve))?", route)
    if statement_match and method in {"GET", "POST"}:
        service_id, statement_id, action = statement_match.groups(); _service_order(conn, service_id, org)
        if method == "GET":
            _require_permission(conn, user, "network.settlements.write"); rows = conn.execute("SELECT * FROM p0_network_settlement_statements WHERE organization_id = ? AND service_order_id = ? ORDER BY period_end DESC", (org, service_id)).fetchall(); result=[]
            for row in rows:
                item=_row(row,("reconciliation_json",)); item["lines"]=[_row(line,("source_event_ids_json",)) for line in conn.execute("SELECT * FROM p0_network_settlement_lines WHERE organization_id = ? AND statement_id = ? ORDER BY created_at", (org,row["id"])).fetchall()]; result.append(item)
            return {"ok": True, "items": result}
        if action == "approve" and method == "POST":
            _require_permission(conn, user, "network.settlements.write"); statement = _owned(conn, "p0_network_settlement_statements", statement_id, org, "Settlement statement not found"); _status_transition(statement["status"], "approved", {"draft": {"submitted", "disputed", "approved"}, "submitted": {"approved", "disputed"}, "disputed": {"approved"}}); conn.execute("UPDATE p0_network_settlement_statements SET status = 'approved', updated_at = ? WHERE id = ?", (now_iso(), statement_id)); _emit(conn, user, "settlement.approved", "settlement_statement", statement_id, ip, {}); return {"ok": True, "item": _row(conn.execute("SELECT * FROM p0_network_settlement_statements WHERE id = ?", (statement_id,)).fetchone(), ("reconciliation_json",))}
        if method == "POST" and not statement_id:
            _require_permission(conn, user, "network.settlements.write"); start = _text(payload, "period_start", 40); end = _text(payload, "period_end", 40); lines = payload.get("lines") if isinstance(payload.get("lines"), list) else []
            if not start or not end or not lines: raise DomainError(400, "period_start, period_end and lines are required", "validation_error")
            existing = conn.execute("SELECT * FROM p0_network_settlement_statements WHERE organization_id = ? AND service_order_id = ? AND period_start = ? AND period_end = ?", (org, service_id, start, end)).fetchone()
            if existing: return {"ok": True, "duplicate": True, "item": _row(existing, ("reconciliation_json",))}
            subtotal=tax=fee=deduction=0; statement_id=new_id("settlementstmt"); now=now_iso(); normalized=[]
            for line in lines:
                amount=_int(line.get("amount_paise"), "amount_paise", 0); line_type=str(line.get("line_type") or "charge"); subtotal += amount if line_type == "charge" else 0; tax += amount if line_type == "tax" else 0; fee += amount if line_type == "fee" else 0; deduction += amount if line_type == "deduction" else 0; normalized.append((new_id("settlementline"), org, statement_id, line_type, str(line.get("code") or "line"), str(line.get("description") or ""), float(line.get("quantity") or 1), _int(line.get("unit_paise"), "unit_paise", 0), amount, json.dumps(line.get("source_event_ids") if isinstance(line.get("source_event_ids"), list) else []), 1 if line.get("disputed") else 0, now))
            net=subtotal+tax+fee-deduction; reconciliation=payload.get("reconciliation") if isinstance(payload.get("reconciliation"),dict) else {}; conn.execute("INSERT INTO p0_network_settlement_statements(id, organization_id, service_order_id, scorecard_run_id, period_start, period_end, subtotal_paise, tax_paise, fee_paise, deduction_paise, net_paise, status, reconciliation_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)", (statement_id, org, service_id, _text(payload,"scorecard_run_id",100) or None, start, end, subtotal, tax, fee, deduction, net, json.dumps(reconciliation), _user_id(user), now, now)); conn.executemany("INSERT INTO p0_network_settlement_lines(id, organization_id, statement_id, line_type, code, description, quantity, unit_paise, amount_paise, source_event_ids_json, disputed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", normalized); _emit(conn, user, "settlement_statement.created", "settlement_statement", statement_id, ip, {"service_order_id": service_id, "net_paise": net}); item=_row(conn.execute("SELECT * FROM p0_network_settlement_statements WHERE id = ?", (statement_id,)).fetchone(), ("reconciliation_json",)); item["lines"]=[_row(conn.execute("SELECT * FROM p0_network_settlement_lines WHERE statement_id = ?", (statement_id,)).fetchall()[i], ("source_event_ids_json",)) for i in range(len(normalized))]; return {"ok": True, "item": item}
    dispute_match = re.fullmatch(r"/api/network/v1/disputes(?:/([^/]+)(?:/(acknowledge|resolve|reject))?)?", route)
    if dispute_match and method in {"GET", "POST"}:
        dispute_id, action = dispute_match.groups()
        if method == "GET":
            _require_permission(conn,user,"network.disputes.write"); sql="SELECT * FROM p0_network_disputes WHERE organization_id = ?"; args=[org]
            if dispute_id: sql+=" AND id = ?"; args.append(dispute_id)
            sql+=" ORDER BY created_at DESC LIMIT ?"; args.append(_limit(query)); rows=conn.execute(sql,args).fetchall(); return {"ok":True,"items":[_row(row,("evidence_json",)) for row in rows]}
        _require_permission(conn,user,"network.disputes.write")
        if method == "POST" and not dispute_id:
            did=new_id("dispute"); now=now_iso(); conn.execute("INSERT INTO p0_network_disputes(id, organization_id, entity_type, entity_id, service_order_id, amount_paise, reason, status, claimant_id, respondent_id, evidence_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)", (did,org,_text(payload,"entity_type", "settlement",50),_text(payload,"entity_id",100),_text(payload,"service_order_id",100) or None,_int(payload.get("amount_paise"),"amount_paise",0),_text(payload,"reason",maximum=1000),_text(payload,"claimant_id",100) or _user_id(user),_text(payload,"respondent_id",100) or None,json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"),dict) else {}),_user_id(user),now,now)); _emit(conn,user,"dispute.created","dispute",did,ip,{}); return {"ok":True,"item":_row(conn.execute("SELECT * FROM p0_network_disputes WHERE id = ?",(did,)).fetchone(),("evidence_json",))}
        dispute=_owned(conn,"p0_network_disputes",dispute_id,org,"Dispute not found"); target={"acknowledge":"investigating","resolve":"resolved","reject":"rejected"}[action]; _status_transition(dispute["status"],target,{"open":{"investigating","resolved","rejected"},"investigating":{"resolved","rejected"}}); now=now_iso(); conn.execute("UPDATE p0_network_disputes SET status=?, resolution_note=?, updated_at=? WHERE id=?",(target,_text(payload,"resolution_note",maximum=1000),now,dispute_id)); return {"ok":True,"item":_row(conn.execute("SELECT * FROM p0_network_disputes WHERE id = ?",(dispute_id,)).fetchone(),("evidence_json",))}
    action_match = re.fullmatch(r"/api/network/v1/corrective-actions(?:/([^/]+))?", route)
    if action_match and method in {"GET", "POST", "PATCH"}:
        aid=action_match.group(1)
        if method=="GET":
            _require_permission(conn,user,"network.corrective_actions.write"); sql="SELECT * FROM p0_network_corrective_actions WHERE organization_id=?"; args=[org]
            if aid: sql+=" AND id=?"; args.append(aid)
            sql+=" ORDER BY created_at DESC LIMIT ?"; args.append(_limit(query)); rows=conn.execute(sql,args).fetchall(); return {"ok":True,"items":[_row(row,("evidence_json",)) for row in rows]}
        _require_permission(conn,user,"network.corrective_actions.write")
        if method=="POST":
            title=_text(payload,"title",maximum=200)
            if not title: raise DomainError(400,"title is required","validation_error")
            aid=new_id("corrective"); now=now_iso(); conn.execute("INSERT INTO p0_network_corrective_actions(id, organization_id, vendor_profile_id, service_order_id, scorecard_run_id, title, status, owner_id, due_at, evidence_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)",(aid,org,_text(payload,"vendor_profile_id",100) or None,_text(payload,"service_order_id",100) or None,_text(payload,"scorecard_run_id",100) or None,title,_text(payload,"owner_id",100) or None,_text(payload,"due_at",40) or None,json.dumps(payload.get("evidence") if isinstance(payload.get("evidence"),dict) else {}),_user_id(user),now,now)); _emit(conn,user,"corrective_action.created","corrective_action",aid,ip,{}); return {"ok":True,"item":_row(conn.execute("SELECT * FROM p0_network_corrective_actions WHERE id=?",(aid,)).fetchone(),("evidence_json",))}
        action=_owned(conn,"p0_network_corrective_actions",aid,org,"Corrective action not found"); status=_text(payload,"status",action["status"],24); now=now_iso(); conn.execute("UPDATE p0_network_corrective_actions SET status=?, resolution_note=?, updated_at=? WHERE id=?",(status,_text(payload,"resolution_note",maximum=1000),now,aid)); return {"ok":True,"item":_row(conn.execute("SELECT * FROM p0_network_corrective_actions WHERE id=?",(aid,)).fetchone(),("evidence_json",))}
    readiness_match = re.fullmatch(r"/api/network/v1/service-orders/([^/]+)/readiness", route)
    if readiness_match and method == "GET":
        _require_permission(conn,user,"network.scorecards.write"); order=_service_order(conn,readiness_match.group(1),org); checks=[]; duty=None
        if order["fleet_duty_id"]: duty=conn.execute("SELECT * FROM domain_duties WHERE id=? AND organization_id=?",(order["fleet_duty_id"],org)).fetchone()
        checks.append({"key":"fleet_handoff","passed":bool(order["fleet_booking_id"] and order["fleet_duty_id"]),"message":"Fleet booking and duty linked" if order["fleet_booking_id"] and order["fleet_duty_id"] else "Fleet handoff is missing"})
        checks.append({"key":"assignment","passed":bool(duty and duty["driver_id"] and duty["vehicle_id"]),"message":"Driver and vehicle assigned" if duty and duty["driver_id"] and duty["vehicle_id"] else "Driver and vehicle assignment is missing"})
        route_ok=bool(duty and conn.execute("SELECT 1 FROM p0_route_stops WHERE organization_id=? AND duty_id=?",(org,duty["id"])).fetchone()); checks.append({"key":"route_plan","passed":route_ok,"message":"Route plan stop exists" if route_ok else "Publish a route plan stop before activation"})
        approval=conn.execute("SELECT 1 FROM p0_network_vendor_approvals WHERE organization_id=? AND vendor_profile_id=? AND status='approved'",(org,order["vendor_profile_id"])).fetchone(); checks.append({"key":"vendor_approval","passed":bool(approval),"message":"Vendor is region-approved" if approval else "Vendor approval is missing"})
        policy=conn.execute("SELECT 1 FROM p0_safety_policies WHERE organization_id=? AND status='active'",(org,)).fetchone(); checks.append({"key":"safety_policy","passed":bool(policy),"message":"Active safety policy configured" if policy else "Create an active safety policy"})
        return {"ok":True,"service_order_id":order["id"],"ready":all(check["passed"] for check in checks),"checks":checks}
    return None


def _permission_routes(conn, user, method, route, query, payload, ip):
    org = _org(user)
    if route == "/api/permissions" and method == "GET":
        _require_permission(conn, user, "permissions.read"); rows=conn.execute("SELECT role, permission_key, allowed FROM p0_role_permissions WHERE organization_id=? ORDER BY role, permission_key",(org,)).fetchall(); return {"ok":True,"items":[_row(row) for row in rows],"permissions":sorted(P0_PERMISSIONS)}
    if route == "/api/permissions/check" and method == "POST":
        permission=_text(payload,"permission",120); return {"ok":True,"permission":permission,"allowed":_has_permission(conn,user,permission),"role":_role(user)}
    grant_match=re.fullmatch(r"/api/permissions/grants(?:/([^/]+))?",route)
    if grant_match and method in {"POST","PATCH"}:
        _require_permission(conn,user,"permissions.write"); role=_text(payload,"role",30); permission=_text(payload,"permission",120); allowed=1 if bool(payload.get("allowed",True)) else 0
        if role not in ROLE_DEFAULTS or permission not in P0_PERMISSIONS: raise DomainError(400,"Unknown role or permission","validation_error")
        now=now_iso(); conn.execute("INSERT INTO p0_role_permissions(id,organization_id,role,permission_key,allowed,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(organization_id,role,permission_key) DO UPDATE SET allowed=excluded.allowed,updated_at=excluded.updated_at",(new_id("perm"),org,role,permission,allowed,now,now)); _emit(conn,user,"permission.updated","permission",permission,ip,{"role":role,"allowed":bool(allowed)}); return {"ok":True,"role":role,"permission":permission,"allowed":bool(allowed)}
    return None


def handle_p0(conn, user, method: str, raw_route: str, payload: dict, ip: str):
    _ensure_permission_seed(conn)
    route, query = _parse(raw_route)
    if route.startswith("/api/masters"):
        result = _master_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/operations/"):
        result = _site_shift_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
        result = _operations_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/safety/"):
        result = _safety_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/network/v1/") and _role(user) == "driver":
        # Let the compatibility Network boundary emit its role_forbidden
        # contract before organization resolution for independent drivers.
        return None
    if route == "/api/network/v1/feature-flag":
        return None
    if route.startswith("/api/network/v1/"): 
        # Return None for existing Network routes so backend_network.py keeps
        # its compatibility behavior and quote/award source of truth.
        result = _network_region_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
        result = _network_lifecycle_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
        result = _network_collaboration_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
        result = _scorecard_settlement_routes(conn, user, method, route, query, payload, ip)
        if result is not None: return result
    if route.startswith("/api/permissions"):
        return _permission_routes(conn, user, method, route, query, payload, ip)
    return None
