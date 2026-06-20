from flask import Flask, request, render_template, make_response
import requests as http_client
from pathlib import Path
from datetime import date, timedelta
import os
import threading
import pandas as pd  # kept only for incident.json / altered.json (JSON, not CSV)

app = Flask(__name__)

_go_api_raw = os.environ.get("GO_API_URL", "http://localhost:8081").rstrip("/")
GO_API = _go_api_raw if _go_api_raw.startswith("http") else f"https://{_go_api_raw}"
BASE   = Path(__file__).parent

# ── Risk helpers ───────────────────────────────────────────────────────────────

_RISK_BADGE = {
    "high":   ("bg-red-500 text-white",    "high"),
    "medium": ("bg-yellow-400 text-white", "medium"),
    "low":    ("bg-green-500 text-white",  "low"),
}

def risk_cls_label(level):
    return _RISK_BADGE.get(level, ("bg-gray-200 text-gray-500", "unknown"))

# ── Status / outcome helpers ───────────────────────────────────────────────────

STATUS_CLASSES = {
    "ACTIVE":          "bg-green-50 text-green-700 ring-1 ring-green-200",
    "PENDING_RENEWAL": "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200",
}

OUTCOME_CLASSES = {
    "Passed":              "bg-green-50 text-green-700 ring-1 ring-green-200",
    "Passed Major":        "bg-green-50 text-green-700 ring-1 ring-green-200",
    "Passed Sub":          "bg-green-50 text-green-700 ring-1 ring-green-200",
    "All Orders Resolved": "bg-green-50 text-green-700 ring-1 ring-green-200",
    "Complete":            "bg-green-50 text-green-700 ring-1 ring-green-200",
    "Shutdown":            "bg-red-50 text-red-700 ring-1 ring-red-200",
    "Vol Shut Down":       "bg-red-50 text-red-700 ring-1 ring-red-200",
    "Fail Initial":        "bg-red-50 text-red-700 ring-1 ring-red-200",
    "Fail Sub":            "bg-red-50 text-red-700 ring-1 ring-red-200",
}

def outcome_cls(outcome):
    if outcome in OUTCOME_CLASSES:
        return OUTCOME_CLASSES[outcome]
    if "follow up" in str(outcome).lower() or "dc follow" in str(outcome).lower():
        return "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200"
    return "bg-gray-100 text-gray-500 ring-1 ring-gray-200"


def extract_city(loc):
    parts = str(loc).split()
    return parts[-5].title() if len(parts) >= 5 else None


# ── Elevator cache (loaded in background thread to avoid blocking startup) ────

def _load_elevator_cache():
    """Load all elevators via a single PostgreSQL query (fast) or fall back to Go API."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(db_url)
            cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT
                    e.id,
                    e.location,
                    e.device_type,
                    e.device_status,
                    e.license_status,
                    TO_CHAR(e.license_expiry, 'YYYY-MM-DD')      AS license_expiry,
                    TO_CHAR(li.latest_date,   'YYYY-MM-DD')      AS latest_inspection_date,
                    li.outcome                                    AS latest_inspection_outcome,
                    p.risk_level
                FROM elevators e
                LEFT JOIN LATERAL (
                    SELECT latest_date, outcome
                    FROM   inspections
                    WHERE  elevator_id = e.id
                    ORDER  BY latest_date DESC NULLS LAST
                    LIMIT  1
                ) li ON true
                LEFT JOIN predictions p ON p.elevator_id = e.id
                ORDER BY e.id
            """)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close(); conn.close()
            for r in rows:
                r["_city"] = extract_city(r.get("location", ""))
            return rows
        except Exception:
            pass  # fall through to Go API

    # fallback: paginate Go API
    elevators, page = [], 1
    try:
        while True:
            resp = http_client.get(
                f"{GO_API}/api/elevators",
                params={"page": page, "limit": 500},
                timeout=15,
            )
            if resp.status_code != 200:
                break
            data  = resp.json()
            batch = data.get("elevators", [])
            elevators.extend(batch)
            if len(elevators) >= data.get("total", 0) or not batch:
                break
            page += 1
    except http_client.exceptions.RequestException:
        pass
    for e in elevators:
        e["_city"] = extract_city(e.get("location", ""))
    return elevators


_ELEVATORS = _load_elevator_cache()
CITIES     = sorted({e["_city"] for e in _ELEVATORS if e.get("_city")})
STATUSES   = sorted({e["license_status"] for e in _ELEVATORS if e.get("license_status")})


def _ensure_cache():
    global _ELEVATORS, CITIES, STATUSES
    if _ELEVATORS:
        return
    _ELEVATORS = _load_elevator_cache()
    CITIES   = sorted({e["_city"] for e in _ELEVATORS if e.get("_city")})
    STATUSES = sorted({e["license_status"] for e in _ELEVATORS if e.get("license_status")})


# ── Summary statistics (computed once from cache) ─────────────────────────────

def _stats():
    today_str    = date.today().isoformat()
    twelve_str   = (date.today() - timedelta(days=365)).isoformat()
    thirty_str   = (date.today() + timedelta(days=30)).isoformat()
    ninety_str   = (date.today() + timedelta(days=90)).isoformat()

    total    = len(_ELEVATORS)
    active   = sum(1 for e in _ELEVATORS if e.get("license_status") == "ACTIVE")
    inactive = total - active
    expired  = sum(1 for e in _ELEVATORS if e.get("license_expiry") and e["license_expiry"] < today_str)
    overdue  = sum(1 for e in _ELEVATORS
                   if not e.get("latest_inspection_date") or e["latest_inspection_date"] < twelve_str)

    expiring_90 = sum(1 for e in _ELEVATORS
                      if e.get("license_expiry") and today_str <= e["license_expiry"] <= ninety_str)
    expiring_30 = sum(1 for e in _ELEVATORS
                      if e.get("license_expiry") and today_str <= e["license_expiry"] <= thirty_str)
    pending  = sum(1 for e in _ELEVATORS if e.get("license_status") == "PENDING_RENEWAL")

    overdue_with_date = [e["latest_inspection_date"] for e in _ELEVATORS
                         if e.get("latest_inspection_date") and e["latest_inspection_date"] < twelve_str]
    no_record = sum(1 for e in _ELEVATORS if not e.get("latest_inspection_date"))
    oldest    = min(overdue_with_date) if overdue_with_date else None

    sub_overdue = (
        f"Oldest: {oldest} · {no_record:,} never inspected" if oldest
        else f"{no_record:,} elevators never inspected"
    )

    return dict(
        total=total, active=active, inactive=inactive, expired=expired, overdue=overdue,
        sub_all=f"{active:,} Active · {inactive:,} Inactive",
        sub_active=f"{expiring_90:,} licences expiring within 90 days",
        sub_inactive=f"{pending:,} pending renewal",
        sub_overdue=sub_overdue,
        sub_expired=f"{expiring_30:,} more expiring in 30 days",
    )


# ── Table row builder ─────────────────────────────────────────────────────────

def build_rows(elevators):
    today_str  = date.today().isoformat()
    twelve_str = (date.today() - timedelta(days=365)).isoformat()
    rows = []
    for e in elevators:
        eid         = e["id"]
        expiry      = e.get("license_expiry") or ""
        expiry_str  = expiry or "—"
        license_cls = "text-red-600 font-medium" if expiry and expiry < today_str else "text-gray-500"

        insp      = e.get("latest_inspection_date") or ""
        insp_str  = insp or "—"
        insp_cls  = "text-red-600 font-medium" if (not insp or insp < twelve_str) else "text-gray-500"

        status_cls  = STATUS_CLASSES.get(e.get("license_status", ""), "bg-gray-100 text-gray-500 ring-1 ring-gray-200")
        device_type = e.get("device_type") or "—"
        overdue_cls = " border-l-2 border-orange-400 bg-orange-50/30" if (not insp or insp < twelve_str) else ""

        rcls, rlabel = risk_cls_label(e.get("risk_level"))

        rows.append(f"""
      <tr class="hover:bg-gray-50 transition-colors duration-75 cursor-pointer{overdue_cls}"
          hx-get="/elevator/{eid}"
          hx-target="#detail-panel"
          hx-swap="innerHTML">
        <td class="px-5 py-3 font-mono text-xs text-gray-600">{eid}</td>
        <td class="px-5 py-3 text-sm text-gray-700">{e.get('location','')}</td>
        <td class="px-5 py-3 text-sm text-gray-500">{device_type}</td>
        <td class="px-5 py-3">
          <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {status_cls}">{e.get('license_status','')}</span>
        </td>
        <td class="px-5 py-3">
          <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {rcls}">{rlabel}</span>
        </td>
        <td class="px-5 py-3 text-sm font-mono {license_cls}">{expiry_str}</td>
        <td class="px-5 py-3 text-sm font-mono {insp_cls}">{insp_str}</td>
      </tr>""")
    return "".join(rows)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/debug-cache")
def debug_cache():
    import json as _json
    try:
        resp = http_client.get(f"{GO_API}/api/elevators", params={"page": 1, "limit": 1}, timeout=10)
        api_status = resp.status_code
        api_body = resp.text[:200]
    except Exception as e:
        api_status = "ERROR"
        api_body = str(e)
    return _json.dumps({
        "GO_API": GO_API,
        "cache_size": len(_ELEVATORS),
        "api_status": api_status,
        "api_body": api_body,
    }), 200, {"Content-Type": "application/json"}


@app.route("/")
def index():
    _ensure_cache()
    return render_template("index.html", cities=CITIES, statuses=STATUSES, **_stats())


@app.route("/elevators")
def elevators():
    _ensure_cache()
    status       = request.args.get("status",       "All")
    city         = request.args.get("city",         "All")
    current_sort = request.args.get("sort",         "")
    order        = request.args.get("order",        "asc")
    clicked_sort = request.args.get("clicked_sort", "")
    q            = request.args.get("q",            "").strip().lower()

    if clicked_sort:
        if clicked_sort == current_sort:
            order = "desc" if order == "asc" else "asc"
        else:
            order = "asc"
        active_sort = clicked_sort
    else:
        active_sort = current_sort

    # Column name in Go API dict → sort key
    _sort_field = {
        "elevator_id":    "id",
        "license_expiry": "license_expiry",
        "last_inspection":"latest_inspection_date",
        "device_type":    "device_type",
        "license_status": "license_status",
    }

    filtered = _ELEVATORS

    if status and status != "All":
        filtered = [e for e in filtered if e.get("license_status") == status]
    if city and city != "All":
        filtered = [e for e in filtered if e.get("_city") == city]
    if len(q) >= 2:
        filtered = [e for e in filtered
                    if q in str(e.get("id", "")).lower()
                    or q in (e.get("location") or "").lower()]

    if active_sort in _sort_field:
        key = _sort_field[active_sort]
        filtered = sorted(
            filtered,
            key=lambda e: (e.get(key) or "") if key != "id" else e.get(key, 0),
            reverse=(order == "desc"),
        )

    today_str  = date.today().isoformat()
    twelve_str = (date.today() - timedelta(days=365)).isoformat()

    total  = len(_ELEVATORS)
    count  = len(filtered)
    PAGE   = 500
    rows   = build_rows(filtered[:PAGE])

    f_active   = sum(1 for e in filtered if e.get("license_status") == "ACTIVE")
    f_inactive = count - f_active
    f_overdue  = sum(1 for e in filtered
                     if not e.get("latest_inspection_date") or e["latest_inspection_date"] < twelve_str)
    f_expired  = sum(1 for e in filtered if e.get("license_expiry") and e["license_expiry"] < today_str)

    no_results = (
        '<tr><td colspan="7" class="px-5 py-10 text-center text-sm text-gray-400">'
        "No elevators match your filters.</td></tr>"
        if count == 0 else ""
    )

    def sort_icon(col):
        return ("↑" if order == "asc" else "↓") if col == active_sort else "↕"

    def btn_cls(col):
        active = "text-gray-900" if col == active_sort else "text-gray-400"
        return f"flex items-center gap-1 text-xs font-semibold uppercase tracking-wide {active} hover:text-gray-600"

    def sort_btn(col, label):
        return (
            f'<button id="sort-btn-{col}" hx-swap-oob="true" '
            f'class="{btn_cls(col)}" '
            f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
            f'hx-vals=\'{{"clicked_sort": "{col}"}}\'>'
            f'{label} <span>{sort_icon(col)}</span></button>\n'
        )

    fragment = (
        f'<tbody id="tableBody" class="divide-y divide-gray-50">{rows}{no_results}</tbody>\n'
        f'<span id="resultsCount" hx-swap-oob="true" class="text-xs text-gray-400">'
        f'Showing {min(count, PAGE)} of {count} matching ({total} total)</span>\n'
        f'<input id="sort-field" name="sort" type="hidden" value="{active_sort}" hx-swap-oob="true">\n'
        f'<input id="sort-order" name="order" type="hidden" value="{order}" hx-swap-oob="true">\n'
        + sort_btn("elevator_id",    "Elevator ID")
        + sort_btn("license_expiry", "License Expiry")
        + sort_btn("last_inspection","Last Inspection")
        + sort_btn("device_type",    "Type")
        + sort_btn("license_status", "Status")
        + f'<span id="count-val-all"      hx-swap-oob="true">{count}</span>\n'
        + f'<span id="count-val-active"   hx-swap-oob="true">{f_active}</span>\n'
        + f'<span id="count-val-inactive" hx-swap-oob="true">{f_inactive}</span>\n'
        + f'<span id="count-val-overdue"  hx-swap-oob="true">{f_overdue}</span>\n'
        + f'<span id="count-val-expired"  hx-swap-oob="true">{f_expired}</span>'
    )

    resp = make_response(fragment)
    resp.headers["X-Total-Count"]    = total
    resp.headers["X-Filtered-Count"] = count
    return resp


# ── Component error fragments ─────────────────────────────────────────────────

def _unavailable_fragment():
    return (
        '<div class="w-80 bg-white rounded-xl border border-amber-200 shadow-sm p-5">'
        '<div class="flex items-start justify-between mb-3">'
        '<p class="text-xs font-semibold uppercase tracking-wide text-amber-600">Service Unavailable</p>'
        '<button onclick="document.getElementById(\'detail-panel\').innerHTML=\'\'" '
        'class="text-gray-400 hover:text-gray-600 text-sm">✕</button>'
        '</div>'
        '<p class="text-sm text-gray-700">Elevator data is temporarily unavailable.</p>'
        '<p class="text-xs text-gray-400 mt-2">The data service is not responding. Try again in a moment.</p>'
        '</div>'
    )


def _not_found_fragment(elevator_id):
    return (
        f'<div class="w-80 bg-white rounded-xl border border-gray-100 shadow-sm p-5">'
        f'<p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Not Found</p>'
        f'<p class="text-sm text-gray-600">No elevator found with ID {elevator_id}.</p>'
        f'</div>'
    )


def _panel_error(label):
    """Error state for always-visible panels (fleet health, alerts)."""
    return (
        f'<div class="rounded-xl border border-amber-100 bg-amber-50 p-4 text-xs text-amber-700">'
        f'<span class="font-semibold">{label}</span> — data service unavailable. '
        f'Ensure the Go API is running on port 8081.</div>'
    )


# ── Elevator detail panel ─────────────────────────────────────────────────────

@app.route("/elevator/<int:elevator_id>")
def elevator_detail(elevator_id):
    try:
        detail_resp = http_client.get(f"{GO_API}/api/elevators/{elevator_id}", timeout=3)
    except http_client.exceptions.RequestException:
        return _unavailable_fragment(), 503

    if detail_resp.status_code == 404:
        return _not_found_fragment(elevator_id), 404
    if detail_resp.status_code != 200:
        return _unavailable_fragment(), 502

    elev = detail_resp.json()

    # Inspection history
    try:
        insp_resp   = http_client.get(f"{GO_API}/api/elevators/{elevator_id}/inspections", timeout=3)
        inspections = insp_resp.json().get("inspections", []) if insp_resp.status_code == 200 else []
    except http_client.exceptions.RequestException:
        inspections = []

    # Risk prediction
    try:
        risk_resp = http_client.get(f"{GO_API}/api/elevators/{elevator_id}/risk", timeout=3)
        risk      = risk_resp.json() if risk_resp.status_code == 200 else None
    except http_client.exceptions.RequestException:
        risk = None

    # ── Build inspection rows ─────────────────────────────────────────────────
    insp_rows = ""
    for insp in inspections:
        dt = insp.get("latest_date") or "—"
        oc = outcome_cls(insp.get("outcome", ""))
        insp_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 font-mono text-xs text-gray-500">{dt}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{insp.get("inspection_type","—")}</td>'
            f'<td class="py-1.5 text-xs">'
            f'<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {oc}">'
            f'{insp.get("outcome","—")}</span></td>'
            f'</tr>'
        )

    # ── Local JSON reads (incidents + alterations not owned by Go API) ────────
    inc_df      = pd.read_json(BASE.parent / "data" / "incident.json")
    inc_records = inc_df[inc_df["elevating devices number"] == elevator_id]

    inc_rows = ""
    for _, r in inc_records.iterrows():
        inc_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 font-mono text-xs text-gray-500">{r.get("Date Of Occurrence","—")}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r.get("Incident Summary","—")}</td>'
            f'<td class="py-1.5 text-xs text-gray-500">{r.get("Reported occurrence narrative","—")}</td>'
            f'</tr>'
        )

    alt_df      = pd.read_json(BASE.parent / "data" / "altered.json")
    alt_records = alt_df[alt_df["Elevating Devices Number"] == elevator_id]

    alt_rows = ""
    for _, r in alt_records.iterrows():
        alt_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r["Alteration Type"]}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r["Status of Alteration Request"]}</td>'
            f'</tr>'
        )

    # ── Risk section HTML ─────────────────────────────────────────────────────
    if risk:
        rs_pct    = f"{round(risk['risk_score'] * 100)}%"
        rcls, _   = risk_cls_label(risk.get("risk_level"))
        rlabel    = risk.get("risk_level", "unknown")
        pred_date = risk.get("as_of_date", "—")
        risk_html = f"""
  <div class="grid grid-cols-3 gap-3 text-xs">
    <div>
      <span class="text-gray-400">Risk Score</span>
      <p class="text-gray-700 font-semibold mt-0.5">{rs_pct}</p>
    </div>
    <div>
      <span class="text-gray-400">Risk Level</span>
      <p class="mt-0.5">
        <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {rcls}">{rlabel}</span>
      </p>
    </div>
    <div>
      <span class="text-gray-400">Prediction Date</span>
      <p class="text-gray-700 mt-0.5">{pred_date}</p>
    </div>
  </div>"""
    else:
        risk_html = '<p class="text-xs text-gray-400">No prediction available</p>'

    html = f"""
<div class="w-96 bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-5">
  <div class="flex items-start justify-between">
    <div>
      <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">Elevator Detail</p>
      <p class="text-lg font-bold text-gray-900 mt-0.5">#{elevator_id}</p>
    </div>
    <button onclick="document.getElementById('detail-panel').innerHTML=''"
        class="text-gray-400 hover:text-gray-600 text-sm">✕</button>
  </div>

  <div class="grid grid-cols-2 gap-3 text-xs">
    <div><span class="text-gray-400">Type</span><p class="text-gray-700 mt-0.5">{elev.get("device_type") or "—"}</p></div>
    <div><span class="text-gray-400">Status</span><p class="text-gray-700 mt-0.5">{elev.get("license_status","—")}</p></div>
    <div class="col-span-2"><span class="text-gray-400">Location</span><p class="text-gray-700 mt-0.5">{elev.get("location","—")}</p></div>
    <div><span class="text-gray-400">Licence Expiry</span><p class="text-gray-700 mt-0.5">{elev.get("license_expiry") or "—"}</p></div>
    <div><span class="text-gray-400">Alterations</span><p class="text-gray-700 mt-0.5">{len(alt_records)}</p></div>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Risk Prediction</p>
    {risk_html}
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Inspections ({len(inspections)})</p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Date</th>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Type</th>
        <th class="text-left text-xs text-gray-400 pb-1">Outcome</th>
      </tr></thead>
      <tbody>{insp_rows or '<tr><td colspan="3" class="text-xs text-gray-400 py-2">No inspections on record</td></tr>'}</tbody>
    </table>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Incidents ({len(inc_records)})</p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Date</th>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Summary</th>
        <th class="text-left text-xs text-gray-400 pb-1">Narrative</th>
      </tr></thead>
      <tbody>{inc_rows or '<tr><td colspan="3" class="text-xs text-gray-400 py-2">No incidents on record</td></tr>'}</tbody>
    </table>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Alterations ({len(alt_records)})</p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Type</th>
        <th class="text-left text-xs text-gray-400 pb-1">Status</th>
      </tr></thead>
      <tbody>{alt_rows or '<tr><td colspan="2" class="text-xs text-gray-400 py-2">No alterations on record</td></tr>'}</tbody>
    </table>
  </div>
</div>
"""
    return html


# ── Fleet health panel (Component 3) ─────────────────────────────────────────

def _fleet_stats_from_db():
    """Query fleet stats directly from PostgreSQL. Returns dict matching Go API shape."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            (SELECT COUNT(*)                FROM elevators)    AS total_elevators,
            (SELECT COUNT(*)                FROM inspections)  AS total_inspections,
            (SELECT COUNT(*) FROM inspections
             WHERE outcome IN ('Passed','Passed Major','Passed Sub',
                               'All Orders Resolved','Complete'))  AS passed_inspections,
            (SELECT COUNT(*) FROM predictions WHERE risk_level = 'high')   AS high_risk,
            (SELECT COUNT(*) FROM predictions WHERE risk_level = 'medium') AS medium_risk,
            (SELECT COUNT(*) FROM predictions WHERE risk_level = 'low')    AS low_risk,
            (SELECT COUNT(*) FROM elevators e
             WHERE NOT EXISTS (SELECT 1 FROM predictions p WHERE p.elevator_id = e.id)) AS unscored
    """)
    row = dict(cur.fetchone())
    cur.close(); conn.close()
    total = row["total_inspections"] or 1
    return {
        "total_elevators":      int(row["total_elevators"]),
        "total_inspections":    int(row["total_inspections"]),
        "inspection_pass_rate": round(int(row["passed_inspections"]) / total, 4),
        "risk_levels": {
            "high":     int(row["high_risk"]),
            "medium":   int(row["medium_risk"]),
            "low":      int(row["low_risk"]),
            "unscored": int(row["unscored"]),
        },
    }


@app.route("/fleet-health")
def fleet_health():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            s = _fleet_stats_from_db()
        except Exception:
            return _panel_error("Fleet Health"), 503
    else:
        try:
            resp = http_client.get(f"{GO_API}/api/fleet/stats", timeout=10)
            if resp.status_code != 200:
                return _panel_error("Fleet Health"), 502
            s = resp.json()
        except http_client.exceptions.RequestException:
            return _panel_error("Fleet Health"), 503

    rl   = s.get("risk_levels") or {}
    high = rl.get("high", 0)
    med  = rl.get("medium", 0)
    low  = rl.get("low", 0)
    uns  = rl.get("unscored", 0)
    pr   = s.get("inspection_pass_rate", 0)

    risk_html = (
        f'<div class="flex items-center gap-1.5">'
        f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500 text-white">{high:,} high</span>'
        f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-400 text-white">{med:,} medium</span>'
        f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500 text-white">{low:,} low</span>'
        f'<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-500">{uns:,} unscored</span>'
        f'</div>'
    ) if rl else '<p class="text-xs text-gray-400">Risk predictions not available</p>'

    return f"""
<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
  <div class="flex items-center justify-between mb-4">
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">Fleet Health</p>
    <span class="text-xs text-gray-300">from /api/fleet/stats</span>
  </div>
  <div class="grid grid-cols-3 gap-6">
    <div>
      <p class="text-xs text-gray-400 mb-1">Total Elevators</p>
      <p class="text-2xl font-bold text-gray-900">{s.get("total_elevators",0):,}</p>
    </div>
    <div>
      <p class="text-xs text-gray-400 mb-1">Inspection Pass Rate</p>
      <p class="text-2xl font-bold text-gray-900">{round(pr * 100)}%</p>
      <p class="text-xs text-gray-400 mt-0.5">{s.get("total_inspections",0):,} total inspections</p>
    </div>
    <div>
      <p class="text-xs text-gray-400 mb-2">Risk Distribution</p>
      {risk_html}
    </div>
  </div>
</div>
"""


# ── Alerts section (Component 4) ─────────────────────────────────────────────

def _fleet_alerts_from_db(limit=20):
    """Query high-risk alerts directly from PostgreSQL."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            p.elevator_id,
            p.risk_score,
            TO_CHAR(li.latest_date, 'YYYY-MM-DD') AS last_inspection_date,
            li.outcome                             AS last_inspection_outcome,
            e.device_type                          AS equipment_type
        FROM predictions p
        JOIN elevators e ON e.id = p.elevator_id
        LEFT JOIN LATERAL (
            SELECT latest_date, outcome
            FROM   inspections
            WHERE  elevator_id = p.elevator_id
            ORDER  BY latest_date DESC NULLS LAST
            LIMIT  1
        ) li ON true
        WHERE p.risk_level = 'high'
        ORDER BY p.risk_score DESC
        LIMIT %s
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


@app.route("/fleet-alerts")
def fleet_alerts():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            alerts = _fleet_alerts_from_db()
        except Exception:
            return _panel_error("Alerts"), 503
    else:
        try:
            resp = http_client.get(f"{GO_API}/api/fleet/alerts", timeout=10)
            if resp.status_code == 503:
                return _panel_error("Alerts"), 503
            if resp.status_code != 200:
                return _panel_error("Alerts"), 502
            alerts = resp.json()
        except http_client.exceptions.RequestException:
            return _panel_error("Alerts"), 503

    if not alerts:
        return (
            '<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5">'
            '<p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Alerts</p>'
            '<p class="text-sm text-gray-400">No elevators currently flagged.</p>'
            '</div>'
        )

    rows = ""
    for a in alerts:
        rs_pct = f"{round(a['risk_score'] * 100)}%"
        rows += (
            f'<tr class="border-t border-gray-50 hover:bg-gray-50">'
            f'<td class="px-4 py-2 font-mono text-xs text-gray-600">{a["elevator_id"]}</td>'
            f'<td class="px-4 py-2 text-xs font-semibold text-red-600">{rs_pct}</td>'
            f'<td class="px-4 py-2 font-mono text-xs text-gray-500">{a.get("last_inspection_date","—")}</td>'
            f'<td class="px-4 py-2 text-xs text-gray-600">{a.get("last_inspection_outcome","—")}</td>'
            f'<td class="px-4 py-2 text-xs text-gray-500">{a.get("equipment_type","—")}</td>'
            f'</tr>'
        )

    return f"""
<div class="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
  <div class="flex items-center justify-between mb-4">
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">
      Alerts
      <span class="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded bg-red-500 text-white text-xs font-bold">{len(alerts)}</span>
    </p>
    <span class="text-xs text-gray-300">high risk · failed most-recent inspection</span>
  </div>
  <div class="overflow-x-auto">
    <table class="w-full">
      <thead>
        <tr>
          <th class="px-4 pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Elevator</th>
          <th class="px-4 pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Risk</th>
          <th class="px-4 pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Last Inspection</th>
          <th class="px-4 pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Outcome</th>
          <th class="px-4 pb-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Type</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
"""


@app.route("/api/chat", methods=["POST"])
def chat_proxy():
    """Proxy chat requests from the browser to the Go API (which calls Ollama)."""
    try:
        resp = http_client.post(
            f"{GO_API}/api/chat",
            json=request.get_json(),
            timeout=60,
        )
        return resp.content, resp.status_code, {"Content-Type": "application/json"}
    except http_client.exceptions.RequestException as e:
        return {"error": "chat service unavailable"}, 503


if __name__ == "__main__":
    app.run(debug=True, port=5000)
