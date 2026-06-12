-- =============================================================================
-- AND-105 Task 2: Initial schema — five core tables
-- =============================================================================
-- Run from: psql -U <user> -d <dbname> -f 001_initial_schema.sql
-- Dependency order: elevators must exist before any child table is created.
--
-- ORPHAN POLICY: FKs are strict (REFERENCES elevators ON DELETE RESTRICT).
-- The data migration will filter orphans out with:
--   WHERE elevator_id IN (SELECT id FROM elevators)
-- Orphan counts from source data inspection:
--   inspections:  145 / 40 954  (0.35%)
--   predictions:  145 / 40 954  (0.35%)
--   incidents:      1 /  2 446  (0.04%)
--   alterations:    9 / 31 619  (0.03%)
-- =============================================================================

-- ── elevators ─────────────────────────────────────────────────────────────────
-- Sources: data/license.csv (license identity) + data/installed.json (device attrs)
-- Natural PK: ElevatingDevicesNumber is 45,383-row unique, 0 nulls — confirmed.
CREATE TABLE elevators (
    -- identity (license.csv)
    id                    INTEGER      PRIMARY KEY,   -- ElevatingDevicesNumber
    license_number        TEXT         NOT NULL UNIQUE,  -- ElevatingDevicesLicenseNumber
    location              TEXT,                       -- LocationoftheElevatingDevice
    license_status        TEXT         NOT NULL,      -- LICENSESTATUS
    license_expiry        DATE,                       -- LICENSEEXPIRYDATE (dd-Mon-yy → date)
    license_holder        TEXT,                       -- LICENSEHOLDER
    license_holder_address TEXT,                      -- LICENSEHOLDERADDRESS
    billing_customer      TEXT,                       -- BILLINGCUSTOMER
    billing_address       TEXT,                       -- BILLINGADDRESS
    -- device attributes (installed.json, joined on same id)
    device_type           TEXT,                       -- Device Type
    device_class          TEXT,                       -- Device Class
    device_status         TEXT,                       -- DeviceStatus
    under_review          BOOLEAN,                    -- under review ('Y'/'N' → boolean)
    owner_name            TEXT,                       -- Owner Name
    owner_address         TEXT                        -- Owner Address
    -- OMITTED: LICENSEHOLDERACCOUNTNUMBER, BILLINGACCOUNT, Owner Account Number
    --          All rows contain only the literal string "data redacted" / "redacted".
);

-- ── inspections ───────────────────────────────────────────────────────────────
-- Source: data/inspection.csv
-- Natural PK: InspectionNumber is 143,181-row unique, 0 nulls — confirmed.
CREATE TABLE inspections (
    id                    INTEGER      PRIMARY KEY,   -- InspectionNumber
    elevator_id           INTEGER      NOT NULL
                              REFERENCES elevators(id) ON DELETE RESTRICT,
    service_request_number TEXT,                      -- originatingservicerequestnumber
    customer              TEXT,                       -- InspectionCustomer
    inspection_type       TEXT,                       -- InspectionType
    location              TEXT,                       -- InspectionLocation (0.1% null)
    earliest_date         DATE,                       -- Earliest_INSPECTION_Date (M/D/YYYY → date)
    latest_date           DATE,                       -- Latest_INSPECTION_Date  (M/D/YYYY → date)
    outcome               TEXT                        -- InspectionOutcome
);

-- ── incidents ─────────────────────────────────────────────────────────────────
-- Source: data/incident.json
-- Natural PK: Incident Number is 2,446-row unique, 0 nulls — confirmed.
-- The 29 specific injury-type columns and 4 severity summary columns are
-- SMALLINT (values observed: 0–3 representing victim counts).
-- All 33 injury columns share the same 56.6% null pattern, indicating they
-- come from a separate data-entry form that was not filled in for all records.
CREATE TABLE incidents (
    id                        INTEGER  PRIMARY KEY,   -- Incident Number
    elevator_id               INTEGER  NOT NULL
                                  REFERENCES elevators(id) ON DELETE RESTRICT,
    task_number               INTEGER,                -- Task Number
    category                  TEXT,                   -- catagory of incident [sic]
    incident_summary          TEXT,                   -- Incident Summary
    date_of_occurrence        DATE,                   -- Date Of Occurrence (dd-Mon-yy → date)
    time_of_occurrence        TIME,                   -- Time of Occurrence
    creation_date             DATE,                   -- Creation Date (dd-Mon-yy → date)
    root_cause                TEXT,                   -- Specific Root Cause (35.1% null)
    narrative                 TEXT,                   -- Reported occurrence narrative
    inspection_notes          TEXT,                   -- Summarized detail of Inspection and tests (89.4% null)
    inspector_conclusion      TEXT,                   -- Inspector's Conclusion (89.4% null)
    release                   TEXT,                   -- release (all rows = 'yes')
    -- severity summary columns (56.6% null as a group)
    severity_fatal            SMALLINT,               -- fatal injury
    severity_permanent        SMALLINT,               -- permanent (serious) injury
    severity_minor            SMALLINT,               -- non-permanent (minor) injury
    severity_no_injury        SMALLINT,               -- No Injury
    -- specific injury-type indicators (56.6% null as a group; values 0–3)
    injury_fatal_victim       SMALLINT,               -- Fatal Injury Victim
    injury_concussion         SMALLINT,               -- Concussion Intracranial Inju
    injury_burns_severe       SMALLINT,               -- Burns Severe
    injury_burns_minor        SMALLINT,               -- Burns Minor
    injury_whiplash           SMALLINT,               -- Whiplash
    injury_spinal             SMALLINT,               -- Spinal Injury
    injury_amputation         SMALLINT,               -- Amputation
    injury_deafness           SMALLINT,               -- Injury Leading Deafness
    injury_heart_attack       SMALLINT,               -- Heart Attack
    injury_fracture_major     SMALLINT,               -- Fracture Major Bone
    injury_eye                SMALLINT,               -- Eye Injury
    injury_electric_severe    SMALLINT,               -- Electric Shock Severe
    injury_electric_minor     SMALLINT,               -- Electric Shock Minor
    injury_dislocation        SMALLINT,               -- Dislocation Limb
    injury_bruise_internal    SMALLINT,               -- Bruise Hemorrhage Interna
    injury_exposure_carcinogen SMALLINT,              -- Exposure Carcinomatou Poison
    injury_swelling           SMALLINT,               -- Swelling
    injury_sprained           SMALLINT,               -- Sprained Twisted Joints Muscle
    injury_skin_infection     SMALLINT,               -- Skin Infection Irritation
    injury_seizure            SMALLINT,               -- Seizure
    injury_respiratory        SMALLINT,               -- Respiratory Infection Irrita
    injury_poisoning          SMALLINT,               -- Poisoning
    injury_other_internal     SMALLINT,               -- Other Internal Injury
    injury_nausea             SMALLINT,               -- Nausea Dizziness
    injury_laceration_superficial SMALLINT,           -- Laceration Superficial Cut
    injury_laceration_deep    SMALLINT,               -- Laceration Deep Cut
    injury_fracture_minor     SMALLINT,               -- Fracture Nose Fingers Toes
    injury_external_bruise    SMALLINT,               -- External Bruise
    injury_aches_pains        SMALLINT                -- Aches Pains
);

-- ── alterations ───────────────────────────────────────────────────────────────
-- Source: data/altered.json
-- Natural PK: originating service request number is 31,619-row unique, 0 nulls.
-- OMITTED: 'Inspection number' (100% NULL in source) and
--          'Alteration contractor name' (100% NULL in source).
CREATE TABLE alterations (
    id                    INTEGER      PRIMARY KEY,   -- originating service request number
    elevator_id           INTEGER      NOT NULL
                              REFERENCES elevators(id) ON DELETE RESTRICT,
    customer              TEXT,                       -- Alteration Customer
    summary               TEXT,                       -- Summary
    location              TEXT,                       -- Alteration  Location (note: extra space in key)
    alteration_type       TEXT,                       -- Alteration Type
    status                TEXT,                       -- Status of Alteration Request
    billing_customer      TEXT                        -- Billing Customer
);

-- ── predictions ───────────────────────────────────────────────────────────────
-- Source: data/predictions.csv
-- PK: elevator_id is both the natural identifier and the FK to elevators.
-- One prediction row per elevator (40,954 rows, all unique).
-- elevator_id in source is "EL-XXXXXXXX"; strip prefix and parse as integer
-- before insert — the integer value equals ElevatingDevicesNumber.
-- risk_explanation is intentionally NULL here; populated by a later task.
CREATE TABLE predictions (
    elevator_id               INTEGER      PRIMARY KEY
                                  REFERENCES elevators(id) ON DELETE RESTRICT,
    predicted_outcome         TEXT         NOT NULL,  -- predicted_outcome
    confidence                NUMERIC(8,6) NOT NULL,  -- confidence
    risk_score                NUMERIC(8,6) NOT NULL,  -- risk_score (P("Follow up"))
    risk_level                TEXT         NOT NULL,  -- risk_level: high / medium / low
    model_version             TEXT         NOT NULL,  -- model_version
    prediction_date           DATE         NOT NULL,  -- prediction_date (ISO 8601 → date)
    -- per-class probabilities (13 outcome classes)
    prob_all_orders_resolved  NUMERIC(8,6),
    prob_complete             NUMERIC(8,6),
    prob_dc_follow_up         NUMERIC(8,6),
    prob_fail_initial         NUMERIC(8,6),
    prob_follow_up            NUMERIC(8,6),
    prob_follow_up_initial    NUMERIC(8,6),
    prob_follow_up_major      NUMERIC(8,6),
    prob_follow_up_sub_major  NUMERIC(8,6),
    prob_other                NUMERIC(8,6),
    prob_passed               NUMERIC(8,6),
    prob_passed_major         NUMERIC(8,6),
    prob_shutdown             NUMERIC(8,6),
    prob_unable_to_inspect    NUMERIC(8,6),
    risk_explanation          TEXT                    -- NULL now; populated in a later task
);

-- =============================================================================
-- Indexes
-- Based on actual query patterns in platform/api/handlers.go:
--   handleListElevators:  filters by license_status
--   handleFleetAlerts:    filters predictions by risk_level = 'high', sorts by risk_score DESC
--   handleGetInspections: fetches all inspections for one elevator, sorts by latest_date DESC
--   handleFleetStats:     full-table scan of inspections grouped by outcome
-- =============================================================================

-- FK columns (always index to avoid seq-scan on join)
CREATE INDEX ON inspections(elevator_id);
CREATE INDEX ON incidents(elevator_id);
CREATE INDEX ON alterations(elevator_id);

-- Covering index for the "inspections for elevator sorted recent-first" query
CREATE INDEX ON inspections(elevator_id, latest_date DESC);

-- Fleet pass-rate aggregation
CREATE INDEX ON inspections(outcome);

-- License status filter on the elevator list
CREATE INDEX ON elevators(license_status);

-- Fleet-alerts: filter high-risk, sort by risk_score
CREATE INDEX ON predictions(risk_level);
CREATE INDEX ON predictions(risk_score DESC);
