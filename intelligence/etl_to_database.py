"""
AND-105 Task 3: ETL — flat files → PostgreSQL

Standalone script (not a notebook). Run with:
    python3 intelligence/etl_to_database.py

Connection is configured via environment variables (matching docker-compose.yml):
    DB_HOST     default: localhost
    DB_PORT     default: 5432
    DB_NAME     default: rocketdash
    DB_USER     default: rocketdash
    DB_PASSWORD default: changeme

The database named in DB_NAME must already exist (docker compose up db creates it).
This script creates tables if absent then loads all five source files.
It is idempotent: re-running skips already-inserted rows via ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values

# ── paths ─────────────────────────────────────────────────────────────────────
# Resolved relative to THIS file — works regardless of invocation directory.
HERE = Path(__file__).resolve().parent          # intelligence/
REPO = HERE.parent                              # project root
DATA = REPO / "data"
SQL  = REPO / "platform" / "api" / "migrations" / "001_initial_schema.sql"


# ── connection ────────────────────────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    """Open a psycopg2 connection using environment variables with sane defaults."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "rocketdash"),
        user=os.environ.get("DB_USER", "rocketdash"),
        password=os.environ.get("DB_PASSWORD", "changeme"),
    )


# ── schema bootstrap ──────────────────────────────────────────────────────────

def bootstrap_schema(conn: psycopg2.extensions.connection) -> None:
    """
    Run 001_initial_schema.sql to create tables and indexes if not yet present.
    Checks whether the elevators table already exists before executing — the SQL
    uses plain CREATE TABLE (no IF NOT EXISTS) so re-executing would error.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='elevators'"
        )
        already_exists = cur.fetchone() is not None

    if already_exists:
        print(f"Schema already present — skipping bootstrap ({SQL.name})")
        return

    sql_text = SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()
    print(f"Schema bootstrap complete ({SQL.name})")


# ── type-coercion helpers ─────────────────────────────────────────────────────

def parse_date_dmy(s) -> "datetime.date | None":
    """'dd-Mon-yy' (e.g. '28-Apr-17') → date, or None for blank/unparseable."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d-%b-%y").date()
    except ValueError:
        return None


def parse_date_mdy(s) -> "datetime.date | None":
    """'M/D/YYYY' (e.g. '1/10/2011') → date, or None for blank/unparseable."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        return None


def parse_date_iso(s) -> "datetime.date | None":
    """'YYYY-MM-DD' → date, or None."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time_ampm(s) -> "datetime.time | None":
    """'H:MM:SS AM/PM' (e.g. '2:00:00 PM') → time, or None."""
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%I:%M:%S %p").time()
    except ValueError:
        return None


def opt_str(v) -> "str | None":
    """Return stripped string or None for empty / whitespace-only values."""
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def opt_int(v) -> "int | None":
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def opt_float(v) -> "float | None":
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def to_smallint(v) -> "int | None":
    """JSON float 0.0 / 1.0 / 2.0 / 3.0 → int for SMALLINT columns; None stays None."""
    if v is None:
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


# ── internal utilities ────────────────────────────────────────────────────────

def _count(cur, table: str) -> int:
    """Row count for a table. table must be a hardcoded string, not user input."""
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def _get_elevator_ids(conn) -> set:
    """Return the set of integer elevator IDs currently in the elevators table."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM elevators")
        return {row[0] for row in cur.fetchall()}


def _warn(msg: str) -> None:
    print(f"  SKIP: {msg}", file=sys.stderr)


# ── incident column constants ─────────────────────────────────────────────────
# Declared at module level so load_incidents can reference the exact source-key
# order without repeating it twice (once for column list, once for tuple building).

# Maps (source JSON key → DB column name) for all 33 injury indicator columns.
# Order here determines column order in the INSERT and the tuple.
_INCIDENT_INJURY_MAP: tuple[tuple[str, str], ...] = (
    # 4 high-level severity summaries
    ("fatal injury",                   "severity_fatal"),
    ("permanent (serious) injury",     "severity_permanent"),
    ("non-permanent (minor) injury",   "severity_minor"),
    ("No Injury",                      "severity_no_injury"),
    # 29 specific injury-type indicators
    ("Fatal Injury Victim",            "injury_fatal_victim"),
    ("Concussion Intracranial Inju",   "injury_concussion"),
    ("Burns Severe",                   "injury_burns_severe"),
    ("Burns Minor",                    "injury_burns_minor"),
    ("Whiplash",                       "injury_whiplash"),
    ("Spinal Injury",                  "injury_spinal"),
    ("Amputation",                     "injury_amputation"),
    ("Injury Leading Deafness",        "injury_deafness"),
    ("Heart Attack",                   "injury_heart_attack"),
    ("Fracture Major Bone",            "injury_fracture_major"),
    ("Eye Injury",                     "injury_eye"),
    ("Electric Shock Severe",          "injury_electric_severe"),
    ("Electric Shock Minor",           "injury_electric_minor"),
    ("Dislocation Limb",               "injury_dislocation"),
    ("Bruise Hemorrhage Interna",      "injury_bruise_internal"),
    ("Exposure Carcinomatou Poison",   "injury_exposure_carcinogen"),
    ("Swelling",                       "injury_swelling"),
    ("Sprained Twisted Joints Muscle", "injury_sprained"),
    ("Skin Infection Irritation",      "injury_skin_infection"),
    ("Seizure",                        "injury_seizure"),
    ("Respiratory Infection Irrita",   "injury_respiratory"),
    ("Poisoning",                      "injury_poisoning"),
    ("Other Internal Injury",          "injury_other_internal"),
    ("Nausea Dizziness",               "injury_nausea"),
    ("Laceration Superficial Cut",     "injury_laceration_superficial"),
    ("Laceration Deep Cut",            "injury_laceration_deep"),
    ("Fracture Nose Fingers Toes",     "injury_fracture_minor"),
    ("External Bruise",                "injury_external_bruise"),
    ("Aches Pains",                    "injury_aches_pains"),
)

# Prediction probability column names (source CSV header = DB column name).
_PRED_PROB_COLS: tuple[str, ...] = (
    "prob_all_orders_resolved",
    "prob_complete",
    "prob_dc_follow_up",
    "prob_fail_initial",
    "prob_follow_up",
    "prob_follow_up_initial",
    "prob_follow_up_major",
    "prob_follow_up_sub_major",
    "prob_other",
    "prob_passed",
    "prob_passed_major",
    "prob_shutdown",
    "prob_unable_to_inspect",
)


# ── loaders ───────────────────────────────────────────────────────────────────

def load_elevators(conn: psycopg2.extensions.connection) -> dict:
    """
    Load data/license.csv + data/installed.json → elevators table.

    license.csv is the primary source (45,383 rows, all unique IDs).
    installed.json is left-joined to add device attributes (Device Type, Device Class,
    DeviceStatus, under review, Owner Name, Owner Address). All license IDs have a
    matching installed entry; 1,553 installed-only entries are ignored.

    Transforms:
      - LICENSEEXPIRYDATE 'dd-Mon-yy'  → DATE
      - 'under review' 'Y'/'N'         → BOOLEAN  (missing → NULL)

    NOT NULL columns: id, license_number, license_status.
    Rows missing any of these are skipped with a warning.
    """
    with open(DATA / "license.csv", newline="", encoding="utf-8-sig") as f:
        license_rows = list(csv.DictReader(f))

    with open(DATA / "installed.json", encoding="utf-8") as f:
        installed_data = json.load(f)

    # Build installed lookup keyed by integer device number.
    installed_lookup: dict[int, dict] = {}
    for r in installed_data:
        try:
            k = int(r["Elevating devices number"])
            installed_lookup[k] = r
        except (KeyError, ValueError, TypeError):
            pass

    rows = []
    skipped = 0

    for r in license_rows:
        # ── required fields ──────────────────────────────────────────────────
        try:
            eid = int(r["ElevatingDevicesNumber"].strip())
        except (ValueError, KeyError):
            _warn(f"elevators: unparseable ElevatingDevicesNumber — row skipped")
            skipped += 1
            continue

        license_number = opt_str(r.get("ElevatingDevicesLicenseNumber"))
        if not license_number:
            _warn(f"elevators id={eid}: missing ElevatingDevicesLicenseNumber — skipped")
            skipped += 1
            continue

        license_status = opt_str(r.get("LICENSESTATUS"))
        if not license_status:
            _warn(f"elevators id={eid}: missing LICENSESTATUS — skipped")
            skipped += 1
            continue

        # ── installed.json join (left — missing entry leaves device cols NULL) ─
        inst = installed_lookup.get(eid, {})
        ur_raw = inst.get("under review")
        if ur_raw is None:
            under_review = None
        else:
            under_review = str(ur_raw).strip().upper() == "Y"

        rows.append((
            eid,
            license_number,
            opt_str(r.get("LocationoftheElevatingDevice")),
            license_status,
            parse_date_dmy(r.get("LICENSEEXPIRYDATE")),
            opt_str(r.get("LICENSEHOLDER")),
            opt_str(r.get("LICENSEHOLDERADDRESS")),
            opt_str(r.get("BILLINGCUSTOMER")),
            opt_str(r.get("BILLINGADDRESS")),
            opt_str(inst.get("Device Type")),
            opt_str(inst.get("Device Class")),
            opt_str(inst.get("DeviceStatus")),
            under_review,
            opt_str(inst.get("Owner Name")),
            opt_str(inst.get("Owner Address")),
        ))

    sql = """
        INSERT INTO elevators (
            id, license_number, location, license_status, license_expiry,
            license_holder, license_holder_address, billing_customer, billing_address,
            device_type, device_class, device_status, under_review,
            owner_name, owner_address
        ) VALUES %s
        ON CONFLICT (id) DO NOTHING
    """
    with conn.cursor() as cur:
        before = _count(cur, "elevators")
        execute_values(cur, sql, rows, page_size=1000)
        after = _count(cur, "elevators")
    conn.commit()

    inserted = after - before
    conflict_skips = len(rows) - inserted
    return {"inserted": inserted, "skipped": skipped + conflict_skips}


def load_inspections(conn: psycopg2.extensions.connection) -> dict:
    """
    Load data/inspection.csv → inspections table.

    Transforms:
      - Earliest_INSPECTION_Date / Latest_INSPECTION_Date: 'M/D/YYYY' → DATE

    Orphan rows (elevator_id not present in elevators) are skipped.
    NOT NULL: id, elevator_id.
    """
    elevator_ids = _get_elevator_ids(conn)

    with open(DATA / "inspection.csv", newline="", encoding="utf-8-sig") as f:
        source_rows = list(csv.DictReader(f))

    rows = []
    skipped = 0
    orphans = 0

    for r in source_rows:
        try:
            iid = int(r["InspectionNumber"].strip())
        except (ValueError, KeyError):
            _warn(f"inspections: unparseable InspectionNumber — skipped")
            skipped += 1
            continue

        try:
            eid = int(r["ElevatingDevicesNumber"].strip())
        except (ValueError, KeyError):
            _warn(f"inspections id={iid}: unparseable ElevatingDevicesNumber — skipped")
            skipped += 1
            continue

        if eid not in elevator_ids:
            _warn(f"inspections id={iid}: elevator_id={eid} not in elevators (orphan) — skipped")
            orphans += 1
            continue

        rows.append((
            iid,
            eid,
            opt_str(r.get("originatingservicerequestnumber")),
            opt_str(r.get("InspectionCustomer")),
            opt_str(r.get("InspectionType")),
            opt_str(r.get("InspectionLocation")),
            parse_date_mdy(r.get("Earliest_INSPECTION_Date")),
            parse_date_mdy(r.get("Latest_INSPECTION_Date")),
            opt_str(r.get("InspectionOutcome")),
        ))

    sql = """
        INSERT INTO inspections (
            id, elevator_id, service_request_number, customer,
            inspection_type, location, earliest_date, latest_date, outcome
        ) VALUES %s
        ON CONFLICT (id) DO NOTHING
    """
    with conn.cursor() as cur:
        before = _count(cur, "inspections")
        execute_values(cur, sql, rows, page_size=1000)
        after = _count(cur, "inspections")
    conn.commit()

    inserted = after - before
    conflict_skips = len(rows) - inserted
    total_skipped = skipped + orphans + conflict_skips
    if orphans:
        print(f"  inspections: {orphans} orphan rows skipped (elevator not in license.csv)")
    return {"inserted": inserted, "skipped": total_skipped}


def load_incidents(conn: psycopg2.extensions.connection) -> dict:
    """
    Load data/incident.json → incidents table.

    Transforms:
      - 'Date Of Occurrence', 'Creation Date': 'dd-Mon-yy'  → DATE
      - 'Time of Occurrence':                  'H:MM:SS AM/PM' → TIME
      - 33 injury indicator columns:           float (0.0–3.0) → SMALLINT; None → NULL

    The source JSON key "Inspector's Conclusion" contains an apostrophe — accessed
    via r.get() with the exact key string. Orphan rows skipped.
    NOT NULL: id, elevator_id.
    """
    elevator_ids = _get_elevator_ids(conn)

    with open(DATA / "incident.json", encoding="utf-8") as f:
        source_rows = json.load(f)

    # Build the DB column list from constants so INSERT matches tuple order exactly.
    injury_db_cols = ", ".join(db for _, db in _INCIDENT_INJURY_MAP)
    sql = f"""
        INSERT INTO incidents (
            id, elevator_id, task_number, category, incident_summary,
            date_of_occurrence, time_of_occurrence, creation_date,
            root_cause, narrative, inspection_notes, inspector_conclusion, release,
            {injury_db_cols}
        ) VALUES %s
        ON CONFLICT (id) DO NOTHING
    """

    rows = []
    skipped = 0
    orphans = 0

    for r in source_rows:
        # ── required fields ──────────────────────────────────────────────────
        iid = opt_int(r.get("Incident Number"))
        if iid is None:
            _warn("incidents: missing Incident Number — skipped")
            skipped += 1
            continue

        eid = opt_int(r.get("elevating devices number"))
        if eid is None:
            _warn(f"incidents id={iid}: missing elevator_id — skipped")
            skipped += 1
            continue

        if eid not in elevator_ids:
            _warn(f"incidents id={iid}: elevator_id={eid} not in elevators (orphan) — skipped")
            orphans += 1
            continue

        # ── 33 injury columns unpacked in _INCIDENT_INJURY_MAP order ─────────
        injury_vals = tuple(to_smallint(r.get(src)) for src, _ in _INCIDENT_INJURY_MAP)

        rows.append((
            iid,
            eid,
            opt_int(r.get("Task Number")),
            opt_str(r.get("catagory of incident")),
            opt_str(r.get("Incident Summary")),
            parse_date_dmy(r.get("Date Of Occurrence")),
            parse_time_ampm(r.get("Time of Occurrence")),
            parse_date_dmy(r.get("Creation Date")),
            opt_str(r.get("Specific Root Cause")),
            opt_str(r.get("Reported occurrence narrative")),
            opt_str(r.get("Summarized detail of Inspection and tests")),
            opt_str(r.get("Inspector's Conclusion")),
            opt_str(r.get("release")),
            *injury_vals,
        ))

    with conn.cursor() as cur:
        before = _count(cur, "incidents")
        execute_values(cur, sql, rows, page_size=500)
        after = _count(cur, "incidents")
    conn.commit()

    inserted = after - before
    conflict_skips = len(rows) - inserted
    total_skipped = skipped + orphans + conflict_skips
    if orphans:
        print(f"  incidents: {orphans} orphan rows skipped")
    return {"inserted": inserted, "skipped": total_skipped}


def load_alterations(conn: psycopg2.extensions.connection) -> dict:
    """
    Load data/altered.json → alterations table.

    Source key 'Alteration  Location' has a double space — accessed verbatim.
    Two columns confirmed 100% NULL in source ('Inspection number',
    'Alteration contractor name') are omitted from the schema and ignored here.
    Orphan rows skipped. NOT NULL: id, elevator_id.
    """
    elevator_ids = _get_elevator_ids(conn)

    with open(DATA / "altered.json", encoding="utf-8") as f:
        source_rows = json.load(f)

    rows = []
    skipped = 0
    orphans = 0

    for r in source_rows:
        aid = opt_int(r.get("originating service request number"))
        if aid is None:
            _warn("alterations: missing service request number — skipped")
            skipped += 1
            continue

        eid = opt_int(r.get("Elevating Devices Number"))
        if eid is None:
            _warn(f"alterations id={aid}: missing elevator_id — skipped")
            skipped += 1
            continue

        if eid not in elevator_ids:
            _warn(f"alterations id={aid}: elevator_id={eid} not in elevators (orphan) — skipped")
            orphans += 1
            continue

        rows.append((
            aid,
            eid,
            opt_str(r.get("Alteration Customer")),
            opt_str(r.get("Summary")),
            opt_str(r.get("Alteration  Location")),   # double space — verbatim key
            opt_str(r.get("Alteration Type")),
            opt_str(r.get("Status of Alteration Request")),
            opt_str(r.get("Billing Customer")),
        ))

    sql = """
        INSERT INTO alterations (
            id, elevator_id, customer, summary, location,
            alteration_type, status, billing_customer
        ) VALUES %s
        ON CONFLICT (id) DO NOTHING
    """
    with conn.cursor() as cur:
        before = _count(cur, "alterations")
        execute_values(cur, sql, rows, page_size=1000)
        after = _count(cur, "alterations")
    conn.commit()

    inserted = after - before
    conflict_skips = len(rows) - inserted
    total_skipped = skipped + orphans + conflict_skips
    if orphans:
        print(f"  alterations: {orphans} orphan rows skipped")
    return {"inserted": inserted, "skipped": total_skipped}


def load_predictions(conn: psycopg2.extensions.connection) -> dict:
    """
    Load data/predictions.csv → predictions table.

    Transforms:
      - elevator_id: strip 'EL-' prefix → INTEGER  (matches elevators.id)
      - confidence, risk_score, prob_*:  string → float (NUMERIC(8,6) in DB)
      - prediction_date: 'YYYY-MM-DD' → DATE  (already ISO 8601)

    risk_explanation is inserted as NULL; populated in a later task.
    Conflict target is (elevator_id) — one prediction row per elevator.
    Orphan rows skipped. NOT NULL: elevator_id, predicted_outcome, confidence,
    risk_score, risk_level, model_version, prediction_date.
    """
    elevator_ids = _get_elevator_ids(conn)

    with open(DATA / "predictions.csv", newline="", encoding="utf-8-sig") as f:
        source_rows = list(csv.DictReader(f))

    # Build the prob column fragment once so the INSERT string stays readable.
    prob_cols_sql = ", ".join(_PRED_PROB_COLS)
    sql = f"""
        INSERT INTO predictions (
            elevator_id, predicted_outcome, confidence, risk_score, risk_level,
            model_version, prediction_date,
            {prob_cols_sql},
            risk_explanation
        ) VALUES %s
        ON CONFLICT (elevator_id) DO NOTHING
    """

    rows = []
    skipped = 0
    orphans = 0

    for r in source_rows:
        # ── parse elevator_id: "EL-00063692" → 63692 ─────────────────────────
        raw_id = r.get("elevator_id", "").strip()
        if raw_id.startswith("EL-"):
            raw_id = raw_id[3:]
        try:
            eid = int(raw_id)
        except ValueError:
            _warn(f"predictions: unparseable elevator_id '{r.get('elevator_id')}' — skipped")
            skipped += 1
            continue

        if eid not in elevator_ids:
            _warn(f"predictions elevator_id={eid}: not in elevators (orphan) — skipped")
            orphans += 1
            continue

        # ── required NOT NULL fields ──────────────────────────────────────────
        predicted_outcome = opt_str(r.get("predicted_outcome"))
        risk_level        = opt_str(r.get("risk_level"))
        model_version     = opt_str(r.get("model_version"))
        prediction_date   = parse_date_iso(r.get("prediction_date"))
        confidence        = opt_float(r.get("confidence"))
        risk_score        = opt_float(r.get("risk_score"))

        missing = [name for name, val in [
            ("predicted_outcome", predicted_outcome),
            ("risk_level",        risk_level),
            ("model_version",     model_version),
            ("prediction_date",   prediction_date),
            ("confidence",        confidence),
            ("risk_score",        risk_score),
        ] if val is None]

        if missing:
            _warn(f"predictions elevator_id={eid}: missing NOT NULL fields {missing} — skipped")
            skipped += 1
            continue

        rows.append((
            eid,
            predicted_outcome,
            confidence,
            risk_score,
            risk_level,
            model_version,
            prediction_date,
            *(opt_float(r.get(col)) for col in _PRED_PROB_COLS),
            None,   # risk_explanation — populated in Task 6
        ))

    with conn.cursor() as cur:
        before = _count(cur, "predictions")
        execute_values(cur, sql, rows, page_size=1000)
        after = _count(cur, "predictions")
    conn.commit()

    inserted = after - before
    conflict_skips = len(rows) - inserted
    total_skipped = skipped + orphans + conflict_skips
    if orphans:
        print(f"  predictions: {orphans} orphan rows skipped")
    return {"inserted": inserted, "skipped": total_skipped}


# ── summary ───────────────────────────────────────────────────────────────────

def print_summary(results: dict[str, dict], elapsed: float) -> None:
    """Print a per-table row-count and skip summary."""
    print("\n" + "=" * 60)
    print("ETL SUMMARY")
    print("=" * 60)
    for table, stats in results.items():
        inserted = stats.get("inserted", 0)
        skipped  = stats.get("skipped",  0)
        print(f"  {table:<15} inserted={inserted:>7,}  skipped={skipped:>5,}")
    print(f"\n  Total time: {elapsed:.2f}s")
    print("=" * 60)


# ── catalog verification ──────────────────────────────────────────────────────

def verify_tables(conn: psycopg2.extensions.connection) -> None:
    """Confirm all five tables exist and print their row counts."""
    expected = {"elevators", "inspections", "incidents", "alterations", "predictions"}

    with conn.cursor() as cur:
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )
        found = {row[0] for row in cur.fetchall()}

    missing = expected - found
    if missing:
        print(f"!! MISSING TABLES: {sorted(missing)}", file=sys.stderr)
        sys.exit(1)

    print("\nTable row counts (post-load verification):")
    with conn.cursor() as cur:
        for table in sorted(expected):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table:<15} {count:>10,} rows")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("AND-105 Task 3: ETL — flat files → PostgreSQL")
    print(f"  Repo root : {REPO}")
    print(f"  Data dir  : {DATA}")
    print(f"  SQL file  : {SQL}")
    print()

    t0 = time.monotonic()

    conn = get_connection()
    print(
        f"Connected to PostgreSQL at "
        f"{os.environ.get('DB_HOST', 'localhost')}:"
        f"{os.environ.get('DB_PORT', '5432')} "
        f"db={os.environ.get('DB_NAME', 'rocketdash')}"
    )

    bootstrap_schema(conn)

    loaders = [
        ("elevators",   load_elevators),
        ("inspections", load_inspections),
        ("incidents",   load_incidents),
        ("alterations", load_alterations),
        ("predictions", load_predictions),
    ]

    results: dict[str, dict] = {}
    for table, loader in loaders:
        print(f"Loading {table}...")
        results[table] = loader(conn)

    elapsed = time.monotonic() - t0
    print_summary(results, elapsed)
    verify_tables(conn)
    conn.close()


if __name__ == "__main__":
    main()
