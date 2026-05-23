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

        rows.append(f"""
      <tr class="hover:bg-gray-50 transition-colors duration-75">
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
    if q:
        mask = (
            filtered["elevator_id"].astype(str).str.contains(q, case=False, na=False) |
            filtered["location"].str.contains(q, case=False, na=False) |
            filtered["license_status"].str.contains(q, case=False, na=False) |
            filtered["device_type"].astype(str).str.contains(q, case=False, na=False)
        )
        filtered = filtered[mask]
    if active_sort in ("elevator_id", "license_expiry", "last_inspection"):
        filtered = filtered.sort_values(active_sort, ascending=(order != "desc"))

    total = len(df)
    count = len(filtered)
    rows  = build_rows(filtered)

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
        f'Showing {count} of {total} elevators</span>\n'
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
        f'License Expiry <span>{sort_icon("license_expiry")}</span></button>'
    )

    resp = make_response(fragment)
    resp.headers["X-Total-Count"]    = total
    resp.headers["X-Filtered-Count"] = count
    return resp


if __name__ == "__main__":
    app.run(debug=True, port=5000)
