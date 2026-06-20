#!/usr/bin/env python3
"""Populate Render PostgreSQL with Ontario elevator fleet data."""

import json
import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: set DATABASE_URL env var")
    sys.exit(1)

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def parse_ddmonyy(s):
    if not s or (isinstance(s, float)):
        return None
    try:
        return pd.to_datetime(str(s), format="%d-%b-%y").date()
    except Exception:
        return None


def parse_mdyyyy(s):
    if not s or (isinstance(s, float)):
        return None
    try:
        return pd.to_datetime(str(s)).date()
    except Exception:
        return None


def nullable_int(v):
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except (ValueError, TypeError):
        return None


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # ── elevators ──────────────────────────────────────────────────────────────
    print("Loading license.csv...", flush=True)
    lic = pd.read_csv(f"{DATA}/license.csv")

    print("Loading installed.json...", flush=True)
    inst = pd.read_json(f"{DATA}/installed.json")
    inst = inst.rename(columns={"Elevating devices number": "ElevatingDevicesNumber"})

    merged = lic.merge(inst, on="ElevatingDevicesNumber", how="left")

    rows = []
    for _, r in merged.iterrows():
        eid = nullable_int(r["ElevatingDevicesNumber"])
        if eid is None:
            continue
        under = r.get("under review")
        rows.append((
            eid,
            str(r["ElevatingDevicesLicenseNumber"]),
            r.get("LocationoftheElevatingDevice"),
            str(r["LICENSESTATUS"]),
            parse_ddmonyy(r.get("LICENSEEXPIRYDATE")),
            r.get("LICENSEHOLDER"),
            r.get("LICENSEHOLDERADDRESS"),
            r.get("BILLINGCUSTOMER"),
            r.get("BILLINGADDRESS"),
            r.get("Device Type"),
            r.get("Device Class"),
            r.get("DeviceStatus"),
            True if under == "Y" else (False if under == "N" else None),
            r.get("Owner Name"),
            r.get("Owner Address"),
        ))

    execute_values(cur, """
        INSERT INTO elevators
            (id, license_number, location, license_status, license_expiry,
             license_holder, license_holder_address, billing_customer, billing_address,
             device_type, device_class, device_status, under_review, owner_name, owner_address)
        VALUES %s ON CONFLICT DO NOTHING
    """, rows, page_size=1000)
    conn.commit()
    print(f"  elevators: {len(rows)} rows", flush=True)

    cur.execute("SELECT id FROM elevators")
    valid_ids = {row[0] for row in cur.fetchall()}

    # ── inspections ────────────────────────────────────────────────────────────
    print("Loading inspection.csv...", flush=True)
    insp = pd.read_csv(f"{DATA}/inspection.csv")
    rows = []
    for _, r in insp.iterrows():
        eid = nullable_int(r.get("ElevatingDevicesNumber"))
        iid = nullable_int(r.get("InspectionNumber"))
        if eid not in valid_ids or iid is None:
            continue
        rows.append((
            iid, eid,
            str(r["originatingservicerequestnumber"]) if not pd.isna(r.get("originatingservicerequestnumber")) else None,
            r.get("InspectionCustomer"),
            r.get("InspectionType"),
            r.get("InspectionLocation"),
            parse_mdyyyy(r.get("Earliest_INSPECTION_Date")),
            parse_mdyyyy(r.get("Latest_INSPECTION_Date")),
            r.get("InspectionOutcome"),
        ))
    execute_values(cur, """
        INSERT INTO inspections
            (id, elevator_id, service_request_number, customer,
             inspection_type, location, earliest_date, latest_date, outcome)
        VALUES %s ON CONFLICT DO NOTHING
    """, rows, page_size=1000)
    conn.commit()
    print(f"  inspections: {len(rows)} rows", flush=True)

    # ── incidents ──────────────────────────────────────────────────────────────
    print("Loading incident.json...", flush=True)
    incidents = json.load(open(f"{DATA}/incident.json"))
    rows = []
    for r in incidents:
        eid = nullable_int(r.get("elevating devices number"))
        iid = nullable_int(r.get("Incident Number"))
        if eid not in valid_ids or iid is None:
            continue
        rows.append((
            iid, eid,
            nullable_int(r.get("Task Number")),
            r.get("catagory of incident"),
            r.get("Incident Summary"),
            parse_ddmonyy(r.get("Date Of Occurrence")),
            r.get("Time of Occurrence"),
            parse_ddmonyy(r.get("Creation Date")),
            r.get("Specific Root Cause"),
            r.get("Reported occurrence narrative"),
            r.get("Summarized detail of Inspection and tests"),
            r.get("Inspector's Conclusion"),
            r.get("release"),
            nullable_int(r.get("fatal injury")),
            nullable_int(r.get("permanent (serious) injury")),
            nullable_int(r.get("non-permanent (minor) injury")),
            nullable_int(r.get("No Injury")),
            nullable_int(r.get("Fatal Injury Victim")),
            nullable_int(r.get("Concussion Intracranial Inju")),
            nullable_int(r.get("Burns Severe")),
            nullable_int(r.get("Burns Minor")),
            nullable_int(r.get("Whiplash")),
            nullable_int(r.get("Spinal Injury")),
            nullable_int(r.get("Amputation")),
            nullable_int(r.get("Injury Leading Deafness")),
            nullable_int(r.get("Heart Attack")),
            nullable_int(r.get("Fracture Major Bone")),
            nullable_int(r.get("Eye Injury")),
            nullable_int(r.get("Electric Shock Severe")),
            nullable_int(r.get("Electric Shock Minor")),
            nullable_int(r.get("Dislocation Limb")),
            nullable_int(r.get("Bruise Hemorrhage Interna")),
            nullable_int(r.get("Exposure Carcinomatou Poison")),
            nullable_int(r.get("Swelling")),
            nullable_int(r.get("Sprained Twisted Joints Muscle")),
            nullable_int(r.get("Skin Infection Irritation")),
            nullable_int(r.get("Seizure")),
            nullable_int(r.get("Respiratory Infection Irrita")),
            nullable_int(r.get("Poisoning")),
            nullable_int(r.get("Other Internal Injury")),
            nullable_int(r.get("Nausea Dizziness")),
            nullable_int(r.get("Laceration Superficial Cut")),
            nullable_int(r.get("Laceration Deep Cut")),
            nullable_int(r.get("Fracture Nose Fingers Toes")),
            nullable_int(r.get("External Bruise")),
            nullable_int(r.get("Aches Pains")),
        ))
    execute_values(cur, """
        INSERT INTO incidents
            (id, elevator_id, task_number, category, incident_summary,
             date_of_occurrence, time_of_occurrence, creation_date, root_cause,
             narrative, inspection_notes, inspector_conclusion, release,
             severity_fatal, severity_permanent, severity_minor, severity_no_injury,
             injury_fatal_victim, injury_concussion, injury_burns_severe, injury_burns_minor,
             injury_whiplash, injury_spinal, injury_amputation, injury_deafness,
             injury_heart_attack, injury_fracture_major, injury_eye,
             injury_electric_severe, injury_electric_minor, injury_dislocation,
             injury_bruise_internal, injury_exposure_carcinogen, injury_swelling,
             injury_sprained, injury_skin_infection, injury_seizure,
             injury_respiratory, injury_poisoning, injury_other_internal,
             injury_nausea, injury_laceration_superficial, injury_laceration_deep,
             injury_fracture_minor, injury_external_bruise, injury_aches_pains)
        VALUES %s ON CONFLICT DO NOTHING
    """, rows, page_size=500)
    conn.commit()
    print(f"  incidents: {len(rows)} rows", flush=True)

    # ── alterations ────────────────────────────────────────────────────────────
    print("Loading altered.json...", flush=True)
    alterations = json.load(open(f"{DATA}/altered.json"))
    rows = []
    for r in alterations:
        eid = nullable_int(r.get("Elevating Devices Number"))
        aid = nullable_int(r.get("originating service request number"))
        if eid not in valid_ids or aid is None:
            continue
        rows.append((
            aid, eid,
            r.get("Alteration Customer"),
            r.get("Summary"),
            r.get("Alteration  Location"),
            r.get("Alteration Type"),
            r.get("Status of Alteration Request"),
            r.get("Billing Customer"),
        ))
    execute_values(cur, """
        INSERT INTO alterations
            (id, elevator_id, customer, summary, location,
             alteration_type, status, billing_customer)
        VALUES %s ON CONFLICT DO NOTHING
    """, rows, page_size=1000)
    conn.commit()
    print(f"  alterations: {len(rows)} rows", flush=True)

    # ── predictions ────────────────────────────────────────────────────────────
    print("Loading predictions.csv...", flush=True)
    pred = pd.read_csv(f"{DATA}/predictions.csv")
    rows = []
    for _, r in pred.iterrows():
        raw = str(r["elevator_id"])
        eid = nullable_int(raw.replace("EL-", "").lstrip("0") or "0")
        if eid not in valid_ids:
            continue
        rows.append((
            eid,
            r["predicted_outcome"],
            float(r["confidence"]),
            float(r["risk_score"]),
            r["risk_level"],
            str(r["model_version"]),
            parse_mdyyyy(r["prediction_date"]),
            r.get("prob_all_orders_resolved"),
            r.get("prob_complete"),
            r.get("prob_dc_follow_up"),
            r.get("prob_fail_initial"),
            r.get("prob_follow_up"),
            r.get("prob_follow_up_initial"),
            r.get("prob_follow_up_major"),
            r.get("prob_follow_up_sub_major"),
            r.get("prob_other"),
            r.get("prob_passed"),
            r.get("prob_passed_major"),
            r.get("prob_shutdown"),
            r.get("prob_unable_to_inspect"),
        ))
    execute_values(cur, """
        INSERT INTO predictions
            (elevator_id, predicted_outcome, confidence, risk_score, risk_level,
             model_version, prediction_date,
             prob_all_orders_resolved, prob_complete, prob_dc_follow_up,
             prob_fail_initial, prob_follow_up, prob_follow_up_initial,
             prob_follow_up_major, prob_follow_up_sub_major, prob_other,
             prob_passed, prob_passed_major, prob_shutdown, prob_unable_to_inspect)
        VALUES %s ON CONFLICT DO NOTHING
    """, rows, page_size=1000)
    conn.commit()
    print(f"  predictions: {len(rows)} rows", flush=True)

    cur.close()
    conn.close()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
