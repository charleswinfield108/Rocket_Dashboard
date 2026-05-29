from flask import Flask, request, render_template, make_response
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

app = Flask(__name__)

BASE = Path(__file__).parent
DATA = BASE.parent / "data" / "merged_elevator_data.csv"

# One row per elevator — the merged CSV is expanded by alteration records
raw = pd.read_csv(DATA)
raw = raw.drop_duplicates(subset="ElevatingDevicesNumber", keep="first")

df = raw.rename(columns={
    "ElevatingDevicesNumber":       "elevator_id",
    "LocationoftheElevatingDevice": "location",
    "LICENSESTATUS":                "license_status",
    "LICENSEEXPIRYDATE":            "license_expiry",
    "Device Type":                  "device_type",
    "Latest_INSPECTION_Date":       "last_inspection",
})

df["license_expiry"]  = pd.to_datetime(df["license_expiry"],  errors="coerce")
df["last_inspection"] = pd.to_datetime(df["last_inspection"], errors="coerce")

def extract_city(loc):
    parts = str(loc).split()
    return parts[-5].title() if len(parts) >= 5 else None

df["city"] = df["location"].apply(extract_city)

CITIES   = sorted(df["city"].dropna().unique().tolist())
STATUSES = sorted(df["license_status"].unique().tolist())

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


def build_rows(data):
    today     = date.today()
    twelve_mo = today - timedelta(days=365)
    rows = []
    for _, row in data.iterrows():
        expiry      = row["license_expiry"].date() if pd.notna(row["license_expiry"]) else None
        expiry_str  = expiry.strftime("%Y-%m-%d") if expiry else "—"
        license_cls = "text-red-600 font-medium" if expiry and expiry < today else "text-gray-500"

        insp      = row["last_inspection"].date() if pd.notna(row["last_inspection"]) else None
        insp_str  = insp.strftime("%Y-%m-%d") if insp else "—"
        insp_cls  = "text-red-600 font-medium" if (not insp or insp < twelve_mo) else "text-gray-500"

        status_cls  = STATUS_CLASSES.get(row["license_status"], "bg-gray-100 text-gray-500 ring-1 ring-gray-200")
        device_type = row["device_type"] if pd.notna(row["device_type"]) else "—"

        overdue_cls = " border-l-2 border-orange-400 bg-orange-50/30" if (not insp or insp < twelve_mo) else ""
        rows.append(f"""
      <tr class="hover:bg-gray-50 transition-colors duration-75 cursor-pointer{overdue_cls}"
          hx-get="/elevator/{row['elevator_id']}"
          hx-target="#detail-panel"
          hx-swap="innerHTML">
        <td class="px-5 py-3 font-mono text-xs text-gray-600">{row['elevator_id']}</td>
        <td class="px-5 py-3 text-sm text-gray-700">{row['location']}</td>
        <td class="px-5 py-3 text-sm text-gray-500">{device_type}</td>
        <td class="px-5 py-3">
          <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {status_cls}">{row['license_status']}</span>
        </td>
        <td class="px-5 py-3 text-sm font-mono {license_cls}">{expiry_str}</td>
        <td class="px-5 py-3 text-sm font-mono {insp_cls}">{insp_str}</td>
      </tr>""")
    return "".join(rows)


@app.route("/")
def index():
    today       = pd.Timestamp.today().normalize()
    twelve_mo   = today - pd.Timedelta(days=365)
    thirty_days = today + pd.Timedelta(days=30)
    ninety_days = today + pd.Timedelta(days=90)

    df.sort_values("license_expiry", ascending=True, inplace=True)

    total    = len(df)
    active   = int((df["license_status"] == "ACTIVE").sum())
    inactive = int((df["license_status"] != "ACTIVE").sum())
    expired  = int((df["license_expiry"] < today).sum())
    overdue  = int(
        ((df["last_inspection"] < twelve_mo) | df["last_inspection"].isna()).sum()
    )

    expiring_90 = int(
        ((df["license_expiry"] >= today) & (df["license_expiry"] <= ninety_days)).sum()
    )
    pending = int((df["license_status"] == "PENDING_RENEWAL").sum())

    oldest_ts = df.loc[df["last_inspection"] < twelve_mo, "last_inspection"].min()
    no_record = int(df["last_inspection"].isna().sum())
    if pd.notna(oldest_ts):
        sub_overdue = f"Oldest: {oldest_ts.strftime('%Y-%m-%d')} · {no_record:,} never inspected"
    else:
        sub_overdue = f"{no_record:,} elevators never inspected"

    expiring_30 = int(
        ((df["license_expiry"] >= today) & (df["license_expiry"] <= thirty_days)).sum()
    )

    return render_template(
        "index.html",
        cities=CITIES,
        statuses=STATUSES,
        total=total,
        active=active,
        inactive=inactive,
        expired=expired,
        overdue=overdue,
        sub_all=f"{active:,} Active · {inactive:,} Inactive",
        sub_active=f"{expiring_90:,} licences expiring within 90 days",
        sub_inactive=f"{pending:,} pending renewal",
        sub_overdue=sub_overdue,
        sub_expired=f"{expiring_30:,} more expiring in 30 days",
    )


@app.route("/elevators")
def elevators():
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

    filtered = df

    if status and status != "All":
        filtered = filtered[filtered["license_status"] == status]
    if city and city != "All":
        filtered = filtered[filtered["city"] == city]
    if len(q) >= 2:
        mask = (
            filtered["elevator_id"].astype(str).str.contains(q, case=False, na=False) |
            filtered["location"].str.contains(q, case=False, na=False)
        )
        filtered = filtered[mask]
    if active_sort in ("elevator_id", "license_expiry", "last_inspection", "device_type", "license_status"):
        filtered = filtered.sort_values(active_sort, ascending=(order != "desc"))

    today_ts  = pd.Timestamp.today().normalize()
    twelve_ts = today_ts - pd.Timedelta(days=365)

    total   = len(df)
    count   = len(filtered)
    PAGE    = 500
    rows    = build_rows(filtered.head(PAGE))

    f_active   = int((filtered["license_status"] == "ACTIVE").sum())
    f_inactive = int((filtered["license_status"] != "ACTIVE").sum())
    f_overdue  = int(
        ((filtered["last_inspection"] < twelve_ts) | filtered["last_inspection"].isna()).sum()
    )
    f_expired  = int((filtered["license_expiry"] < today_ts).sum())

    no_results = (
        '<tr><td colspan="6" class="px-5 py-10 text-center text-sm text-gray-400">'
        "No elevators match your filters.</td></tr>"
        if count == 0 else ""
    )

    def sort_icon(col):
        if col != active_sort:
            return "↕"
        return "↑" if order == "asc" else "↓"

    def btn_cls(col):
        active = "text-gray-900" if col == active_sort else "text-gray-400"
        return f"flex items-center gap-1 text-xs font-semibold uppercase tracking-wide {active} hover:text-gray-600"

    fragment = (
        f'<tbody id="tableBody" class="divide-y divide-gray-50">{rows}{no_results}</tbody>\n'
        f'<span id="resultsCount" hx-swap-oob="true" class="text-xs text-gray-400">'
        f'Showing {min(count, PAGE)} of {count} matching ({total} total)</span>\n'
        f'<input id="sort-field" name="sort" type="hidden" value="{active_sort}" hx-swap-oob="true">\n'
        f'<input id="sort-order" name="order" type="hidden" value="{order}" hx-swap-oob="true">\n'
        f'<button id="sort-btn-elevator_id" hx-swap-oob="true" '
        f'class="{btn_cls("elevator_id")}" '
        f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
        f'hx-vals=\'{{"clicked_sort": "elevator_id"}}\'>'
        f'Elevator ID <span>{sort_icon("elevator_id")}</span></button>\n'
        f'<button id="sort-btn-license_expiry" hx-swap-oob="true" '
        f'class="{btn_cls("license_expiry")}" '
        f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
        f'hx-vals=\'{{"clicked_sort": "license_expiry"}}\'>'
        f'License Expiry <span>{sort_icon("license_expiry")}</span></button>\n'
        f'<button id="sort-btn-last_inspection" hx-swap-oob="true" '
        f'class="{btn_cls("last_inspection")}" '
        f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
        f'hx-vals=\'{{"clicked_sort": "last_inspection"}}\'>'
        f'Last Inspection <span>{sort_icon("last_inspection")}</span></button>\n'
        f'<button id="sort-btn-device_type" hx-swap-oob="true" '
        f'class="{btn_cls("device_type")}" '
        f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
        f'hx-vals=\'{{"clicked_sort": "device_type"}}\'>'
        f'Type <span>{sort_icon("device_type")}</span></button>\n'
        f'<button id="sort-btn-license_status" hx-swap-oob="true" '
        f'class="{btn_cls("license_status")}" '
        f'hx-get="/elevators" hx-target="#tableBody" hx-swap="outerHTML" hx-include="#filters" '
        f'hx-vals=\'{{"clicked_sort": "license_status"}}\'>'
        f'Status <span>{sort_icon("license_status")}</span></button>\n'
        f'<span id="count-val-all" hx-swap-oob="true">{count}</span>\n'
        f'<span id="count-val-active" hx-swap-oob="true">{f_active}</span>\n'
        f'<span id="count-val-inactive" hx-swap-oob="true">{f_inactive}</span>\n'
        f'<span id="count-val-overdue" hx-swap-oob="true">{f_overdue}</span>\n'
        f'<span id="count-val-expired" hx-swap-oob="true">{f_expired}</span>'
    )

    resp = make_response(fragment)
    resp.headers["X-Total-Count"]    = total
    resp.headers["X-Filtered-Count"] = count
    return resp


@app.route("/elevator/<int:elevator_id>")
def elevator_detail(elevator_id):
    row = df[df["elevator_id"] == elevator_id]
    if row.empty:
        return "Elevator not found", 404

    elev = row.iloc[0]

    # --- Inspection history from source file ---
    insp_df = pd.read_csv(BASE.parent / "data" / "inspection.csv")
    insp_df.columns = insp_df.columns.str.strip()
    insp_records = insp_df[insp_df["ElevatingDevicesNumber"] == elevator_id].copy()
    insp_records["Latest_INSPECTION_Date"] = pd.to_datetime(
        insp_records["Latest_INSPECTION_Date"], errors="coerce"
    )
    insp_records = insp_records.sort_values("Latest_INSPECTION_Date", ascending=False)

    insp_rows = ""
    for _, r in insp_records.iterrows():
        dt = r["Latest_INSPECTION_Date"].strftime("%Y-%m-%d") if pd.notna(r["Latest_INSPECTION_Date"]) else "—"
        oc = outcome_cls(r["InspectionOutcome"])
        insp_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 font-mono text-xs text-gray-500">{dt}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r["InspectionType"]}</td>'
            f'<td class="py-1.5 text-xs">'
            f'<span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium {oc}">'
            f'{r["InspectionOutcome"]}</span></td>'
            f'</tr>'
        )

    # --- Incident history from source file ---
    inc_df = pd.read_json(BASE.parent / "data" / "incident.json")
    inc_records = inc_df[inc_df["elevating devices number"] == elevator_id]
    incident_count = len(inc_records)

    inc_rows = ""
    for _, r in inc_records.iterrows():
        dt = r.get("Date Of Occurrence", "—")
        summary = r.get("Incident Summary", "—")
        narrative = r.get("Reported occurrence narrative", "—")
        inc_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 font-mono text-xs text-gray-500">{dt}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{summary}</td>'
            f'<td class="py-1.5 text-xs text-gray-500">{narrative}</td>'
            f'</tr>'
        )

    # --- Alteration history from source file ---
    alt_df = pd.read_json(BASE.parent / "data" / "altered.json")
    alt_records = alt_df[alt_df["Elevating Devices Number"] == elevator_id]
    alteration_count = len(alt_records)

    alt_rows = ""
    for _, r in alt_records.iterrows():
        alt_rows += (
            f'<tr class="border-t border-gray-100">'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r["Alteration Type"]}</td>'
            f'<td class="py-1.5 pr-4 text-xs text-gray-600">{r["Status of Alteration Request"]}</td>'
            f'</tr>'
        )

    device_type = elev["device_type"] if pd.notna(elev["device_type"]) else "—"
    expiry = elev["license_expiry"].strftime("%Y-%m-%d") if pd.notna(elev["license_expiry"]) else "—"

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
    <div><span class="text-gray-400">Type</span><p class="text-gray-700 mt-0.5">{device_type}</p></div>
    <div><span class="text-gray-400">Status</span><p class="text-gray-700 mt-0.5">{elev["license_status"]}</p></div>
    <div class="col-span-2"><span class="text-gray-400">Location</span><p class="text-gray-700 mt-0.5">{elev["location"]}</p></div>
    <div><span class="text-gray-400">Licence Expiry</span><p class="text-gray-700 mt-0.5">{expiry}</p></div>
    <div><span class="text-gray-400">Alterations</span><p class="text-gray-700 mt-0.5">{alteration_count}</p></div>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
      Inspections ({len(insp_records)})
    </p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Date</th>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Type</th>
        <th class="text-left text-xs text-gray-400 pb-1">Outcome</th>
      </tr></thead>
      <tbody>{insp_rows if insp_rows else '<tr><td colspan="3" class="text-xs text-gray-400 py-2">No inspections on record</td></tr>'}</tbody>
    </table>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
      Incidents ({incident_count})
    </p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Date</th>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Summary</th>
        <th class="text-left text-xs text-gray-400 pb-1">Narrative</th>
      </tr></thead>
      <tbody>{inc_rows if inc_rows else '<tr><td colspan="3" class="text-xs text-gray-400 py-2">No incidents on record</td></tr>'}</tbody>
    </table>
  </div>

  <div>
    <p class="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
      Alterations ({alteration_count})
    </p>
    <table class="w-full">
      <thead><tr>
        <th class="text-left text-xs text-gray-400 pb-1 pr-4">Type</th>
        <th class="text-left text-xs text-gray-400 pb-1">Status</th>
      </tr></thead>
      <tbody>{alt_rows if alt_rows else '<tr><td colspan="2" class="text-xs text-gray-400 py-2">No alterations on record</td></tr>'}</tbody>
    </table>
  </div>
</div>
"""
    return html


if __name__ == "__main__":
    app.run(debug=True, port=5000)
