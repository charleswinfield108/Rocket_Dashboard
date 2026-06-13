package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"

	"github.com/jackc/pgx/v5"
)

// ── error type ────────────────────────────────────────────────────────────────

type errBody struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

// writeError writes a JSON error body with the given HTTP status code.
// Content-Type is already set by jsonMiddleware.
func (s *server) writeError(w http.ResponseWriter, status int, code, message string) {
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(errBody{Error: code, Message: message}) //nolint:errcheck
}

// writeJSON writes any value as JSON with the given HTTP status code.
func (s *server) writeJSON(w http.ResponseWriter, status int, v any) {
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v) //nolint:errcheck
}

// ── response types (spec §5) ──────────────────────────────────────────────────

// fleetItem is one entry in the GET /api/elevators list (spec §5.1).
type fleetItem struct {
	ID                      int     `json:"id"`
	Location                string  `json:"location"`
	DeviceType              string  `json:"device_type"`
	DeviceStatus            string  `json:"device_status"`
	LicenseStatus           string  `json:"license_status"`
	LicenseExpiry           *string `json:"license_expiry"`
	LatestInspectionDate    *string `json:"latest_inspection_date"`
	LatestInspectionOutcome *string `json:"latest_inspection_outcome"`
	RiskLevel               *string `json:"risk_level"` // null when no prediction row exists
}

type listResponse struct {
	Page      int         `json:"page"`
	Limit     int         `json:"limit"`
	Total     int         `json:"total"`
	Elevators []fleetItem `json:"elevators"`
}

// detailResponse is the GET /api/elevators/{id} body (21 fields per spec).
type detailResponse struct {
	ID                      int     `json:"id"`
	Location                string  `json:"location"`
	DeviceType              string  `json:"device_type"`
	DeviceClass             string  `json:"device_class"`
	DeviceStatus            string  `json:"device_status"`
	UnderReview             bool    `json:"under_review"`
	LicenseNumber           string  `json:"license_number"`
	LicenseStatus           string  `json:"license_status"`
	LicenseExpiry           *string `json:"license_expiry"`
	LicenseHolder           string  `json:"license_holder"`
	LicenseHolderAddress    string  `json:"license_holder_address"`
	BillingCustomer         string  `json:"billing_customer"`
	BillingAddress          string  `json:"billing_address"`
	OwnerName               string  `json:"owner_name"`
	OwnerAddress            string  `json:"owner_address"`
	AlterationCount         *int    `json:"alteration_count"`
	LatestAlterationType    *string `json:"latest_alteration_type"`
	LatestAlterationStatus  *string `json:"latest_alteration_status"`
	LatestInspectionDate    *string `json:"latest_inspection_date"`
	LatestInspectionType    *string `json:"latest_inspection_type"`
	LatestInspectionOutcome *string `json:"latest_inspection_outcome"`
}

// jsonFloat marshals to a JSON number that always contains a decimal point
// (e.g. 22.0 rather than 22), keeping risk_score typed as float on the wire.
type jsonFloat float64

func (f jsonFloat) MarshalJSON() ([]byte, error) {
	s := strconv.FormatFloat(float64(f), 'f', -1, 64)
	if !strings.Contains(s, ".") {
		s += ".0"
	}
	return []byte(s), nil
}

type orderItem struct {
	RiskScore      jsonFloat `json:"risk_score"`
	Directive      *string   `json:"directive"`
	Description    *string   `json:"description"`
	Status         string    `json:"status"`
	DateIssued     string    `json:"date_issued"`
	DaysToComply   *int      `json:"days_to_comply"`
	ComplianceDate *string   `json:"compliance_date"`
}

type inspectionItem struct {
	InspectionNumber     int         `json:"inspection_number"`
	ServiceRequestNumber string      `json:"service_request_number"`
	InspectionCustomer   string      `json:"inspection_customer"`
	InspectionType       string      `json:"inspection_type"`
	Location             string      `json:"location"`
	EarliestDate         string      `json:"earliest_date"`
	LatestDate           string      `json:"latest_date"`
	Outcome              string      `json:"outcome"`
	Orders               []orderItem `json:"orders"`
}

type inspectionsResponse struct {
	ElevatorID  int              `json:"elevator_id"`
	Count       int              `json:"count"`
	Inspections []inspectionItem `json:"inspections"`
}

type riskResponse struct {
	ElevatorID       int                  `json:"elevator_id"`
	PredictedOutcome string               `json:"predicted_outcome"`
	Confidence       float64              `json:"confidence"`
	RiskScore        jsonFloat            `json:"risk_score"` // P("Follow up") from predictions.csv
	RiskLevel        string               `json:"risk_level"` // high / medium / low
	ClassProbs       map[string]jsonFloat `json:"class_probabilities"`
	OpenOrdersCount  int                  `json:"open_orders_count"`
	MeanRiskScore    *float64             `json:"mean_risk_score"`
	ModelVersion     string               `json:"model_version"`
	AsOfDate         string               `json:"as_of_date"`
}

// ── shared helpers ────────────────────────────────────────────────────────────

// parseID reads the {id} path value and validates it as a positive integer.
// On failure it writes a 400 and returns (0, false).
func (s *server) parseID(w http.ResponseWriter, r *http.Request) (int, bool) {
	raw := r.PathValue("id")
	id, err := strconv.Atoi(raw)
	if err != nil || id <= 0 {
		s.writeError(w, http.StatusBadRequest, "INVALID_PARAMETER",
			"id must be a positive integer, got: "+raw)
		return 0, false
	}
	return id, true
}

// lookupElevator validates {id} and confirms the elevator exists in the DB.
// Returns (id, true) on success; writes 400/404 and returns (0, false) on failure.
func (s *server) lookupElevator(w http.ResponseWriter, r *http.Request) (int, bool) {
	id, ok := s.parseID(w, r)
	if !ok {
		return 0, false
	}
	var exists bool
	if err := s.db.QueryRow(r.Context(),
		`SELECT EXISTS(SELECT 1 FROM elevators WHERE id = $1)`, id,
	).Scan(&exists); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to look up elevator: "+err.Error())
		return 0, false
	}
	if !exists {
		s.writeError(w, http.StatusNotFound, "ELEVATOR_NOT_FOUND",
			"no elevator found with id "+strconv.Itoa(id))
		return 0, false
	}
	return id, true
}

// parseQueryInt parses an optional query-string integer, returning def when empty.
func parseQueryInt(s string, def int) (int, error) {
	if s == "" {
		return def, nil
	}
	return strconv.Atoi(s)
}

// ── handlers ──────────────────────────────────────────────────────────────────

// GET /api/elevators
// Two queries: COUNT for pagination total, then paginated rows with LATERAL
// joins for latest inspection and a LEFT JOIN for risk_level from predictions.
// Status filter uses a parameter guard ($1 = ” skips the filter).
func (s *server) handleListElevators(w http.ResponseWriter, r *http.Request) {
	qp := r.URL.Query()

	page, err := parseQueryInt(qp.Get("page"), 1)
	if err != nil || page < 1 {
		s.writeError(w, http.StatusBadRequest, "INVALID_PARAMETER",
			"page must be a positive integer")
		return
	}

	limit, err := parseQueryInt(qp.Get("limit"), 100)
	if err != nil {
		s.writeError(w, http.StatusBadRequest, "INVALID_PARAMETER",
			"limit must be between 1 and 500")
		return
	}
	if limit < 1 || limit > 500 {
		s.writeError(w, http.StatusBadRequest, "INVALID_PARAMETER",
			"limit must be between 1 and 500, got "+strconv.Itoa(limit))
		return
	}

	statusFilter := qp.Get("status")
	ctx := r.Context()

	const countQ = `
SELECT COUNT(*)::int
FROM elevators
WHERE $1 = '' OR license_status = $1`

	var total int
	if err := s.db.QueryRow(ctx, countQ, statusFilter).Scan(&total); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to count elevators: "+err.Error())
		return
	}

	const listQ = `
SELECT
    e.id,
    COALESCE(e.location, '')                                AS location,
    COALESCE(e.device_type, '')                             AS device_type,
    COALESCE(e.device_status, '')                           AS device_status,
    e.license_status,
    TO_CHAR(e.license_expiry, 'YYYY-MM-DD')                 AS license_expiry,
    TO_CHAR(li.latest_date, 'YYYY-MM-DD')                   AS latest_inspection_date,
    li.outcome                                              AS latest_inspection_outcome,
    p.risk_level
FROM elevators e
LEFT JOIN LATERAL (
    SELECT latest_date, outcome
    FROM inspections
    WHERE elevator_id = e.id
    ORDER BY latest_date DESC NULLS LAST
    LIMIT 1
) li ON true
LEFT JOIN predictions p ON p.elevator_id = e.id
WHERE $1 = '' OR e.license_status = $1
ORDER BY e.id
LIMIT $2 OFFSET $3`

	rows, err := s.db.Query(ctx, listQ, statusFilter, limit, (page-1)*limit)
	if err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query elevators: "+err.Error())
		return
	}
	defer rows.Close()

	items := make([]fleetItem, 0)
	for rows.Next() {
		var (
			id                      int
			location                string
			deviceType              string
			deviceStatus            string
			licenseStatus           string
			licenseExpiry           *string
			latestInspectionDate    *string
			latestInspectionOutcome *string
			riskLevel               *string
		)
		if err := rows.Scan(&id, &location, &deviceType, &deviceStatus,
			&licenseStatus, &licenseExpiry, &latestInspectionDate,
			&latestInspectionOutcome, &riskLevel); err != nil {
			s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
				"failed to scan elevator: "+err.Error())
			return
		}
		items = append(items, fleetItem{
			ID:                      id,
			Location:                location,
			DeviceType:              deviceType,
			DeviceStatus:            deviceStatus,
			LicenseStatus:           licenseStatus,
			LicenseExpiry:           licenseExpiry,
			LatestInspectionDate:    latestInspectionDate,
			LatestInspectionOutcome: latestInspectionOutcome,
			RiskLevel:               riskLevel,
		})
	}
	if err := rows.Err(); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to iterate elevators: "+err.Error())
		return
	}

	s.writeJSON(w, http.StatusOK, listResponse{
		Page:      page,
		Limit:     limit,
		Total:     total,
		Elevators: items,
	})
}

// GET /api/elevators/{id}
// All 21 fields come from the DB: elevators table plus three LATERAL subqueries
// for alteration count, latest alteration, and latest inspection.
func (s *server) handleGetElevator(w http.ResponseWriter, r *http.Request) {
	id, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}

	const q = `
SELECT
    e.id,
    COALESCE(e.location, '')                                AS location,
    COALESCE(e.device_type, '')                             AS device_type,
    COALESCE(e.device_class, '')                            AS device_class,
    COALESCE(e.device_status, '')                           AS device_status,
    COALESCE(e.under_review, false)                         AS under_review,
    COALESCE(e.license_number, '')                          AS license_number,
    e.license_status,
    TO_CHAR(e.license_expiry, 'YYYY-MM-DD')                 AS license_expiry,
    COALESCE(e.license_holder, '')                          AS license_holder,
    COALESCE(e.license_holder_address, '')                  AS license_holder_address,
    COALESCE(e.billing_customer, '')                        AS billing_customer,
    COALESCE(e.billing_address, '')                         AS billing_address,
    COALESCE(e.owner_name, '')                              AS owner_name,
    COALESCE(e.owner_address, '')                           AS owner_address,
    NULLIF(ac.cnt, 0)                                       AS alteration_count,
    la.alteration_type                                      AS latest_alteration_type,
    la.status                                               AS latest_alteration_status,
    TO_CHAR(li.latest_date, 'YYYY-MM-DD')                   AS latest_inspection_date,
    li.inspection_type                                      AS latest_inspection_type,
    li.outcome                                              AS latest_inspection_outcome
FROM elevators e
LEFT JOIN LATERAL (
    SELECT COUNT(*)::int AS cnt
    FROM alterations
    WHERE elevator_id = e.id
) ac ON true
LEFT JOIN LATERAL (
    SELECT alteration_type, status
    FROM alterations
    WHERE elevator_id = e.id
    ORDER BY id DESC
    LIMIT 1
) la ON true
LEFT JOIN LATERAL (
    SELECT latest_date, inspection_type, outcome
    FROM inspections
    WHERE elevator_id = e.id
    ORDER BY latest_date DESC NULLS LAST
    LIMIT 1
) li ON true
WHERE e.id = $1`

	var (
		location                string
		deviceType              string
		deviceClass             string
		deviceStatus            string
		underReview             bool
		licenseNumber           string
		licenseStatus           string
		licenseExpiry           *string
		licenseHolder           string
		licenseHolderAddress    string
		billingCustomer         string
		billingAddress          string
		ownerName               string
		ownerAddress            string
		alterationCount         *int
		latestAlterationType    *string
		latestAlterationStatus  *string
		latestInspectionDate    *string
		latestInspectionType    *string
		latestInspectionOutcome *string
	)

	err := s.db.QueryRow(r.Context(), q, id).Scan(
		&id,
		&location,
		&deviceType,
		&deviceClass,
		&deviceStatus,
		&underReview,
		&licenseNumber,
		&licenseStatus,
		&licenseExpiry,
		&licenseHolder,
		&licenseHolderAddress,
		&billingCustomer,
		&billingAddress,
		&ownerName,
		&ownerAddress,
		&alterationCount,
		&latestAlterationType,
		&latestAlterationStatus,
		&latestInspectionDate,
		&latestInspectionType,
		&latestInspectionOutcome,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			s.writeError(w, http.StatusNotFound, "ELEVATOR_NOT_FOUND",
				"no elevator found with id "+strconv.Itoa(id))
			return
		}
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query elevator: "+err.Error())
		return
	}

	s.writeJSON(w, http.StatusOK, detailResponse{
		ID:                      id,
		Location:                location,
		DeviceType:              deviceType,
		DeviceClass:             deviceClass,
		DeviceStatus:            deviceStatus,
		UnderReview:             underReview,
		LicenseNumber:           licenseNumber,
		LicenseStatus:           licenseStatus,
		LicenseExpiry:           licenseExpiry,
		LicenseHolder:           licenseHolder,
		LicenseHolderAddress:    licenseHolderAddress,
		BillingCustomer:         billingCustomer,
		BillingAddress:          billingAddress,
		OwnerName:               ownerName,
		OwnerAddress:            ownerAddress,
		AlterationCount:         alterationCount,
		LatestAlterationType:    latestAlterationType,
		LatestAlterationStatus:  latestAlterationStatus,
		LatestInspectionDate:    latestInspectionDate,
		LatestInspectionType:    latestInspectionType,
		LatestInspectionOutcome: latestInspectionOutcome,
	})
}

// GET /api/elevators/{id}/inspections
// Inspections come from the database. Orders embedded in each inspection
// still come from in-memory order.csv data — order.csv is not in the DB schema.
func (s *server) handleGetInspections(w http.ResponseWriter, r *http.Request) {
	id, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}

	const q = `
SELECT
    i.id                                                    AS inspection_number,
    COALESCE(i.service_request_number, '')                  AS service_request_number,
    COALESCE(i.customer, '')                                AS inspection_customer,
    COALESCE(i.inspection_type, '')                         AS inspection_type,
    COALESCE(i.location, '')                                AS location,
    COALESCE(TO_CHAR(i.earliest_date, 'YYYY-MM-DD'), '')    AS earliest_date,
    COALESCE(TO_CHAR(i.latest_date,   'YYYY-MM-DD'), '')    AS latest_date,
    COALESCE(i.outcome, '')                                 AS outcome
FROM inspections i
WHERE i.elevator_id = $1
ORDER BY i.latest_date DESC NULLS LAST`

	rows, err := s.db.Query(r.Context(), q, id)
	if err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query inspections: "+err.Error())
		return
	}
	defer rows.Close()

	items := make([]inspectionItem, 0)
	for rows.Next() {
		var (
			inspNum  int
			svcReq   string
			customer string
			inspType string
			location string
			earliest string
			latest   string
			outcome  string
		)
		if err := rows.Scan(&inspNum, &svcReq, &customer, &inspType,
			&location, &earliest, &latest, &outcome); err != nil {
			s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
				"failed to scan inspection row: "+err.Error())
			return
		}

		rawOrders := s.ordersByInsp[inspNum]
		orders := make([]orderItem, 0, len(rawOrders)) // non-nil so it marshals to []
		for _, ord := range rawOrders {
			orders = append(orders, orderItem{
				RiskScore:      jsonFloat(ord.RiskScore),
				Directive:      ord.Directive,
				Description:    ord.Description,
				Status:         ord.Status,
				DateIssued:     ord.DateIssued,
				DaysToComply:   ord.DaysToComply,
				ComplianceDate: ord.ComplianceDate,
			})
		}

		items = append(items, inspectionItem{
			InspectionNumber:     inspNum,
			ServiceRequestNumber: svcReq,
			InspectionCustomer:   customer,
			InspectionType:       inspType,
			Location:             location,
			EarliestDate:         earliest,
			LatestDate:           latest,
			Outcome:              outcome,
			Orders:               orders,
		})
	}
	if err := rows.Err(); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to iterate inspection rows: "+err.Error())
		return
	}

	s.writeJSON(w, http.StatusOK, inspectionsResponse{
		ElevatorID:  id,
		Count:       len(items),
		Inspections: items,
	})
}

// GET /api/elevators/{id}/risk
// Predictions come from the database. Orders (open_orders_count, mean_risk_score)
// still come from in-memory order.csv data — order.csv is not in the DB schema.
func (s *server) handleGetRisk(w http.ResponseWriter, r *http.Request) {
	// 400/404 first — unknown elevator is never a predictions problem.
	id, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}

	const q = `
SELECT
    predicted_outcome,
    confidence::float8,
    risk_score::float8,
    risk_level,
    model_version,
    TO_CHAR(prediction_date, 'YYYY-MM-DD')  AS as_of_date,
    prob_all_orders_resolved::float8,
    prob_complete::float8,
    prob_dc_follow_up::float8,
    prob_fail_initial::float8,
    prob_follow_up::float8,
    prob_follow_up_initial::float8,
    prob_follow_up_major::float8,
    prob_follow_up_sub_major::float8,
    prob_other::float8,
    prob_passed::float8,
    prob_passed_major::float8,
    prob_shutdown::float8,
    prob_unable_to_inspect::float8
FROM predictions
WHERE elevator_id = $1`

	var (
		predictedOutcome  string
		confidence        float64
		riskScore         float64
		riskLevel         string
		modelVersion      string
		asOfDate          string
		pAllOrders        float64
		pComplete         float64
		pDCFollowUp       float64
		pFailInitial      float64
		pFollowUp         float64
		pFollowUpInitial  float64
		pFollowUpMajor    float64
		pFollowUpSubMajor float64
		pOther            float64
		pPassed           float64
		pPassedMajor      float64
		pShutdown         float64
		pUnableToInspect  float64
	)

	err := s.db.QueryRow(r.Context(), q, id).Scan(
		&predictedOutcome,
		&confidence,
		&riskScore,
		&riskLevel,
		&modelVersion,
		&asOfDate,
		&pAllOrders,
		&pComplete,
		&pDCFollowUp,
		&pFailInitial,
		&pFollowUp,
		&pFollowUpInitial,
		&pFollowUpMajor,
		&pFollowUpSubMajor,
		&pOther,
		&pPassed,
		&pPassedMajor,
		&pShutdown,
		&pUnableToInspect,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			s.writeError(w, http.StatusServiceUnavailable, "PREDICTIONS_UNAVAILABLE",
				"no prediction row available for elevator "+strconv.Itoa(id))
			return
		}
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query predictions: "+err.Error())
		return
	}

	// open_orders_count: count of OPEN orders.
	// mean_risk_score: mean over orders that have a non-empty RISKSCORE cell only;
	// empty cells must not contribute to the denominator (they coerce to 0.0 and
	// dilute the mean — elevator 10 has 7 empty out of 24 rows).
	orders := s.ordersByElev[id]
	openCount := 0
	var riskSum float64
	var riskCount int
	for _, ord := range orders {
		if ord.Status == "OPEN" {
			openCount++
		}
		if ord.HasRiskScore {
			riskSum += ord.RiskScore
			riskCount++
		}
	}
	var meanRisk *float64
	if riskCount > 0 {
		v := riskSum / float64(riskCount)
		meanRisk = &v
	}

	s.writeJSON(w, http.StatusOK, riskResponse{
		ElevatorID:       id,
		PredictedOutcome: predictedOutcome,
		Confidence:       confidence,
		RiskScore:        jsonFloat(riskScore),
		RiskLevel:        riskLevel,
		ClassProbs: map[string]jsonFloat{
			"All Orders Resolved": jsonFloat(pAllOrders),
			"Complete":            jsonFloat(pComplete),
			"DC Follow up":        jsonFloat(pDCFollowUp),
			"Fail Initial":        jsonFloat(pFailInitial),
			"Follow Up Initial":   jsonFloat(pFollowUpInitial),
			"Follow up":           jsonFloat(pFollowUp),
			"Follow up Major":     jsonFloat(pFollowUpMajor),
			"Follow up Sub Major": jsonFloat(pFollowUpSubMajor),
			"Other":               jsonFloat(pOther),
			"Passed":              jsonFloat(pPassed),
			"Passed Major":        jsonFloat(pPassedMajor),
			"Shutdown":            jsonFloat(pShutdown),
			"Unable to Inspect":   jsonFloat(pUnableToInspect),
		},
		OpenOrdersCount: openCount,
		MeanRiskScore:   meanRisk,
		ModelVersion:    modelVersion,
		AsOfDate:        asOfDate,
	})
}

// ── fleet-stats ───────────────────────────────────────────────────────────────

type riskLevelCounts struct {
	High     int `json:"high"`
	Medium   int `json:"medium"`
	Low      int `json:"low"`
	Unscored int `json:"unscored"`
}

type fleetStatsResponse struct {
	TotalElevators     int              `json:"total_elevators"`
	InspectionPassRate jsonFloat        `json:"inspection_pass_rate"`
	TotalInspections   int              `json:"total_inspections"`
	RiskLevels         *riskLevelCounts `json:"risk_levels"`
	EquipmentTypes     map[string]int   `json:"equipment_types"`
}

// GET /api/fleet/stats
// Three DB queries replace: in-memory map iteration (equipment types),
// per-request inspection.csv re-read (pass rate), and dual in-memory map
// cross-reference (risk levels + unscored). passOutcomes set kept in sync
// with the SQL IN clause below.
func (s *server) handleFleetStats(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	// Query 1: equipment-type distribution + total elevator count.
	const equipQ = `
SELECT COALESCE(device_type, ''), COUNT(*)::int
FROM elevators
GROUP BY device_type`

	equipRows, err := s.db.Query(ctx, equipQ)
	if err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query equipment types: "+err.Error())
		return
	}
	defer equipRows.Close()

	equipTypes := make(map[string]int)
	totalElevators := 0
	for equipRows.Next() {
		var dt string
		var cnt int
		if err := equipRows.Scan(&dt, &cnt); err != nil {
			s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
				"failed to scan equipment type: "+err.Error())
			return
		}
		if dt != "" {
			equipTypes[dt] = cnt
		}
		totalElevators += cnt
	}
	if err := equipRows.Err(); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to iterate equipment types: "+err.Error())
		return
	}
	equipRows.Close()

	// Query 2: inspection pass rate + total (replaces per-request CSV re-read).
	// ROUND to 4 dp with NUMERIC arithmetic, cast to float8 for jsonFloat scan.
	// Pass outcomes must match passOutcomes map above exactly.
	const inspQ = `
SELECT
    COUNT(*)::int                                                           AS total_inspections,
    ROUND(
        COUNT(*) FILTER (WHERE outcome IN (
            'Passed', 'Passed Major', 'Passed Sub',
            'Complete', 'Complete Enforcement', 'All Orders Resolved'
        ))::numeric / NULLIF(COUNT(*), 0)::numeric,
        4
    )::float8                                                               AS pass_rate
FROM inspections`

	var totalInsp int
	var passRate float64
	if err := s.db.QueryRow(ctx, inspQ).Scan(&totalInsp, &passRate); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query inspection stats: "+err.Error())
		return
	}

	// Query 3: risk-level counts + unscored.
	const riskQ = `
SELECT
    COUNT(*) FILTER (WHERE risk_level = 'high')::int   AS high,
    COUNT(*) FILTER (WHERE risk_level = 'medium')::int AS medium,
    COUNT(*) FILTER (WHERE risk_level = 'low')::int    AS low,
    (SELECT COUNT(*)::int FROM elevators)
        - COUNT(DISTINCT elevator_id)::int             AS unscored
FROM predictions`

	counts := riskLevelCounts{}
	if err := s.db.QueryRow(ctx, riskQ).Scan(
		&counts.High, &counts.Medium, &counts.Low, &counts.Unscored,
	); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query risk levels: "+err.Error())
		return
	}

	s.writeJSON(w, http.StatusOK, fleetStatsResponse{
		TotalElevators:     totalElevators,
		InspectionPassRate: jsonFloat(passRate),
		TotalInspections:   totalInsp,
		RiskLevels:         &counts,
		EquipmentTypes:     equipTypes,
	})
}

// ── fleet-alerts ──────────────────────────────────────────────────────────────

type alertItem struct {
	ElevatorID            int       `json:"elevator_id"`
	RiskScore             jsonFloat `json:"risk_score"`
	RiskLevel             string    `json:"risk_level"`
	LastInspectionDate    *string   `json:"last_inspection_date"`
	LastInspectionOutcome string    `json:"last_inspection_outcome"`
	EquipmentType         string    `json:"equipment_type"`
}

// GET /api/fleet/alerts
// INNER JOIN LATERAL finds the single most-recent inspection per high-risk
// elevator; the WHERE on li.outcome replicates the CSV passOutcomes filter.
// INNER (not LEFT) JOIN on LATERAL means elevators with zero inspections are
// automatically excluded — matching the CSV handler's explicit len==0 continue.
func (s *server) handleFleetAlerts(w http.ResponseWriter, r *http.Request) {
	const q = `
SELECT
    p.elevator_id,
    p.risk_score::float8,
    p.risk_level,
    TO_CHAR(li.latest_date, 'YYYY-MM-DD')   AS last_inspection_date,
    COALESCE(li.outcome, '')                AS last_inspection_outcome,
    COALESCE(e.device_type, '')             AS equipment_type
FROM predictions p
JOIN elevators e ON e.id = p.elevator_id
JOIN LATERAL (
    SELECT latest_date, outcome
    FROM inspections
    WHERE elevator_id = p.elevator_id
    ORDER BY latest_date DESC NULLS LAST
    LIMIT 1
) li ON true
WHERE p.risk_level = 'high'
  AND li.outcome NOT IN (
      'Passed', 'Passed Major', 'Passed Sub',
      'Complete', 'Complete Enforcement', 'All Orders Resolved'
  )
ORDER BY p.risk_score DESC`

	rows, err := s.db.Query(r.Context(), q)
	if err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to query fleet alerts: "+err.Error())
		return
	}
	defer rows.Close()

	alerts := make([]alertItem, 0)
	for rows.Next() {
		var (
			elevID    int
			riskScore float64
			riskLevel string
			lastDate  *string
			lastOut   string
			equipType string
		)
		if err := rows.Scan(&elevID, &riskScore, &riskLevel,
			&lastDate, &lastOut, &equipType); err != nil {
			s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
				"failed to scan alert row: "+err.Error())
			return
		}
		alerts = append(alerts, alertItem{
			ElevatorID:            elevID,
			RiskScore:             jsonFloat(riskScore),
			RiskLevel:             riskLevel,
			LastInspectionDate:    lastDate,
			LastInspectionOutcome: lastOut,
			EquipmentType:         equipType,
		})
	}
	if err := rows.Err(); err != nil {
		s.writeError(w, http.StatusInternalServerError, "INTERNAL_ERROR",
			"failed to iterate alert rows: "+err.Error())
		return
	}

	s.writeJSON(w, http.StatusOK, alerts)
}
