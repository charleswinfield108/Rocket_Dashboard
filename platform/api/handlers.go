package main

import (
	"encoding/json"
	"math"
	"net/http"
	"sort"
	"strconv"
	"strings"
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

// lookupElevator validates {id} and confirms it exists in merged_elevator_data.csv.
// On failure it writes 400 or 404 and returns (nil, false).
func (s *server) lookupElevator(w http.ResponseWriter, r *http.Request) (*elevatorRow, bool) {
	id, ok := s.parseID(w, r)
	if !ok {
		return nil, false
	}
	e, found := s.elevators[id]
	if !found {
		s.writeError(w, http.StatusNotFound, "ELEVATOR_NOT_FOUND",
			"no elevator found with id "+strconv.Itoa(id))
		return nil, false
	}
	return e, true
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
func (s *server) handleListElevators(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()

	page, err := parseQueryInt(q.Get("page"), 1)
	if err != nil || page < 1 {
		s.writeError(w, http.StatusBadRequest, "INVALID_PARAMETER",
			"page must be a positive integer")
		return
	}

	limit, err := parseQueryInt(q.Get("limit"), 100)
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

	statusFilter := q.Get("status")

	// Filter: preserve insertion order so pagination is deterministic.
	filtered := make([]int, 0, len(s.elevatorIDs))
	for _, id := range s.elevatorIDs {
		e := s.elevators[id]
		if statusFilter == "" || e.LicenseStatus == statusFilter {
			filtered = append(filtered, id)
		}
	}

	total := len(filtered)
	start := (page - 1) * limit
	if start >= total {
		start = total
	}
	end := start + limit
	if end > total {
		end = total
	}

	items := make([]fleetItem, 0, end-start)
	for _, id := range filtered[start:end] {
		e := s.elevators[id]
		var riskLevel *string
		if pred, ok := s.predictions[e.ID]; ok {
			rl := pred.RiskLevel
			riskLevel = &rl
		}
		items = append(items, fleetItem{
			ID:                      e.ID,
			Location:                e.Location,
			DeviceType:              e.DeviceType,
			DeviceStatus:            e.DeviceStatus,
			LicenseStatus:           e.LicenseStatus,
			LicenseExpiry:           e.LicenseExpiry,
			LatestInspectionDate:    e.LatestInspectionDate,
			LatestInspectionOutcome: e.LatestInspectionOutcome,
			RiskLevel:               riskLevel,
		})
	}

	s.writeJSON(w, http.StatusOK, listResponse{
		Page:      page,
		Limit:     limit,
		Total:     total,
		Elevators: items,
	})
}

// GET /api/elevators/{id}
func (s *server) handleGetElevator(w http.ResponseWriter, r *http.Request) {
	e, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}
	s.writeJSON(w, http.StatusOK, detailResponse{
		ID:                      e.ID,
		Location:                e.Location,
		DeviceType:              e.DeviceType,
		DeviceClass:             e.DeviceClass,
		DeviceStatus:            e.DeviceStatus,
		UnderReview:             e.UnderReview,
		LicenseNumber:           e.LicenseNumber,
		LicenseStatus:           e.LicenseStatus,
		LicenseExpiry:           e.LicenseExpiry,
		LicenseHolder:           e.LicenseHolder,
		LicenseHolderAddress:    e.LicenseHolderAddress,
		BillingCustomer:         e.BillingCustomer,
		BillingAddress:          e.BillingAddress,
		OwnerName:               e.OwnerName,
		OwnerAddress:            e.OwnerAddress,
		AlterationCount:         e.AlterationCount,
		LatestAlterationType:    e.LatestAlterationType,
		LatestAlterationStatus:  e.LatestAlterationStatus,
		LatestInspectionDate:    e.LatestInspectionDate,
		LatestInspectionType:    e.LatestInspectionType,
		LatestInspectionOutcome: e.LatestInspectionOutcome,
	})
}

// GET /api/elevators/{id}/inspections
func (s *server) handleGetInspections(w http.ResponseWriter, r *http.Request) {
	e, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}

	raw := s.inspByElev[e.ID] // nil slice if elevator has no inspections — that's fine

	// Copy so we don't sort the original slice in place.
	sorted := make([]*inspectionRow, len(raw))
	copy(sorted, raw)
	// ISO 8601 dates sort lexicographically, so descending string sort = most-recent first.
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].LatestDate > sorted[j].LatestDate
	})

	items := make([]inspectionItem, 0, len(sorted))
	for _, insp := range sorted {
		rawOrders := s.ordersByInsp[insp.InspectionNumber]
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
			InspectionNumber:     insp.InspectionNumber,
			ServiceRequestNumber: insp.ServiceRequestNumber,
			InspectionCustomer:   insp.InspectionCustomer,
			InspectionType:       insp.InspectionType,
			Location:             insp.InspectionLocation,
			EarliestDate:         insp.EarliestDate,
			LatestDate:           insp.LatestDate,
			Outcome:              insp.Outcome,
			Orders:               orders,
		})
	}

	s.writeJSON(w, http.StatusOK, inspectionsResponse{
		ElevatorID:  e.ID,
		Count:       len(items),
		Inspections: items,
	})
}

// GET /api/elevators/{id}/risk
func (s *server) handleGetRisk(w http.ResponseWriter, r *http.Request) {
	// 400/404 first — unknown elevator is never a predictions problem.
	e, ok := s.lookupElevator(w, r)
	if !ok {
		return
	}

	if !s.predictionsLoaded {
		s.writeError(w, http.StatusServiceUnavailable, "PREDICTIONS_UNAVAILABLE",
			"predictions are not yet available; predictions.csv will be generated in Task 6")
		return
	}
	pred, found := s.predictions[e.ID]
	if !found {
		s.writeError(w, http.StatusServiceUnavailable, "PREDICTIONS_UNAVAILABLE",
			"no prediction row available for elevator "+strconv.Itoa(e.ID))
		return
	}

	// open_orders_count: count of OPEN orders.
	// mean_risk_score: mean over orders that have a non-empty RISKSCORE cell only;
	// empty cells must not contribute to the denominator (they coerce to 0.0 and
	// dilute the mean — elevator 10 has 7 empty out of 24 rows).
	orders := s.ordersByElev[e.ID]
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
		ElevatorID:       e.ID,
		PredictedOutcome: pred.PredictedOutcome,
		Confidence:       pred.Confidence,
		RiskScore:        jsonFloat(pred.RiskScore),
		RiskLevel:        pred.RiskLevel,
		ClassProbs:       pred.ClassProbabilities,
		OpenOrdersCount:  openCount,
		MeanRiskScore:    meanRisk,
		ModelVersion:     pred.ModelVersion,
		AsOfDate:         pred.AsOfDate,
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

// passOutcomes is the set of InspectionOutcome values counted as a pass.
var passOutcomes = map[string]bool{
	"Passed":               true,
	"Passed Major":         true,
	"Passed Sub":           true,
	"Complete":             true,
	"Complete Enforcement": true,
	"All Orders Resolved":  true,
}

// GET /api/fleet-stats
func (s *server) handleFleetStats(w http.ResponseWriter, r *http.Request) {
	// Equipment-type counts — from already-loaded elevator data.
	equipTypes := make(map[string]int)
	for _, e := range s.elevators {
		if e.DeviceType != "" {
			equipTypes[e.DeviceType]++
		}
	}

	// Inspection pass rate — read inspection.csv at request time.
	inspPath := s.cfg.dataDir + "/inspection.csv"
	inspHeaders, inspRows, err := readCSV(inspPath)
	if err != nil {
		s.writeError(w, 500, "INTERNAL_ERROR", "failed to read inspection data")
		return
	}
	idx := colIdx(inspHeaders)
	totalInsp := len(inspRows)
	passed := 0
	for _, row := range inspRows {
		outcome := strings.TrimSpace(cell(row, idx, "InspectionOutcome"))
		if passOutcomes[outcome] {
			passed++
		}
	}
	var passRate jsonFloat
	if totalInsp > 0 {
		passRate = jsonFloat(math.Round(float64(passed)/float64(totalInsp)*10000) / 10000)
	}

	// Risk-level counts — from in-memory predictions (nil when not loaded).
	var riskCounts *riskLevelCounts
	if s.predictionsLoaded {
		counts := riskLevelCounts{}
		for _, pred := range s.predictions {
			switch pred.RiskLevel {
			case "high":
				counts.High++
			case "medium":
				counts.Medium++
			case "low":
				counts.Low++
			}
		}
		scored := 0
		for id := range s.elevators {
			if _, ok := s.predictions[id]; ok {
				scored++
			}
		}
		counts.Unscored = len(s.elevators) - scored
		riskCounts = &counts
	}

	s.writeJSON(w, http.StatusOK, fleetStatsResponse{
		TotalElevators:     len(s.elevators),
		InspectionPassRate: passRate,
		TotalInspections:   totalInsp,
		RiskLevels:         riskCounts,
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

// GET /api/fleet-alerts
func (s *server) handleFleetAlerts(w http.ResponseWriter, r *http.Request) {
	if !s.predictionsLoaded {
		s.writeError(w, http.StatusServiceUnavailable, "PREDICTIONS_UNAVAILABLE",
			"predictions are not yet available")
		return
	}

	alerts := make([]alertItem, 0)

	for elevID, pred := range s.predictions {
		if pred.RiskLevel != "high" {
			continue
		}

		// Find the most-recent inspection row for this elevator.
		inspections := s.inspByElev[elevID]
		if len(inspections) == 0 {
			continue // no inspection record — skip
		}
		latest := inspections[0]
		for _, insp := range inspections[1:] {
			if insp.LatestDate > latest.LatestDate {
				latest = insp
			}
		}

		// Only alert if the most-recent outcome is not a pass.
		if passOutcomes[latest.Outcome] {
			continue
		}

		e := s.elevators[elevID]
		var lastDate *string
		if latest.LatestDate != "" {
			d := latest.LatestDate
			lastDate = &d
		}
		equipType := ""
		if e != nil {
			equipType = e.DeviceType
		}
		alerts = append(alerts, alertItem{
			ElevatorID:            elevID,
			RiskScore:             jsonFloat(pred.RiskScore),
			RiskLevel:             pred.RiskLevel,
			LastInspectionDate:    lastDate,
			LastInspectionOutcome: latest.Outcome,
			EquipmentType:         equipType,
		})
	}

	// Sort descending by risk_score.
	sort.Slice(alerts, func(i, j int) bool {
		return alerts[i].RiskScore > alerts[j].RiskScore
	})

	s.writeJSON(w, http.StatusOK, alerts)
}
