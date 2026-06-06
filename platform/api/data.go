package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// ── internal row types (CSV → memory) ────────────────────────────────────────

type elevatorRow struct {
	ID                      int
	Location                string
	DeviceType              string
	DeviceClass             string
	DeviceStatus            string
	UnderReview             bool
	LicenseNumber           string
	LicenseStatus           string
	LicenseExpiry           *string
	LicenseHolder           string
	LicenseHolderAddress    string
	BillingCustomer         string
	BillingAddress          string
	OwnerName               string
	OwnerAddress            string
	AlterationCount         *int
	LatestAlterationType    *string
	LatestAlterationStatus  *string
	LatestInspectionDate    *string
	LatestInspectionType    *string
	LatestInspectionOutcome *string
}

type inspectionRow struct {
	InspectionNumber     int
	ServiceRequestNumber string
	InspectionCustomer   string
	InspectionType       string
	InspectionLocation   string
	EarliestDate         string // ISO 8601 after parsing
	LatestDate           string // ISO 8601 after parsing
	Outcome              string
}

type orderRow struct {
	ElevatingDevicesNumber int
	InspectionNumber       int
	RiskScore              float64
	HasRiskScore           bool // false when RISKSCORE cell was empty; guards mean_risk_score denominator
	Directive              *string
	Description            *string
	Status                 string
	DateIssued             string // ISO 8601 date-only after parsing
	DaysToComply           *int
	ComplianceDate         *string // ISO 8601 after parsing
}

type predictionRow struct {
	PredictedOutcome   string               // predicted_outcome — argmax class name
	Confidence         float64              // confidence — probability of the argmax class
	ClassProbabilities map[string]jsonFloat // prob_* columns — all 13 outcome class probs
	RiskScore          float64              // risk_score — P("Follow up"), used for fleet list risk_level
	RiskLevel          string               // risk_level — high / medium / low
	ModelVersion       string
	AsOfDate           string // prediction_date column, normalised to ISO 8601
}

// ── date normalisation ────────────────────────────────────────────────────────

// Layouts tried in order. The timestamp variant must come before the date-only
// variant so "3/5/2012 14:08" doesn't partially match "1/2/2006".
var dateLayouts = []string{
	"2006-01-02",     // merged_elevator_data Latest_INSPECTION_Date (already ISO 8601)
	"02-Jan-06",      // license.csv LICENSEEXPIRYDATE: "28-Apr-17"
	"1/2/2006 15:04", // order.csv DateofIssue: "3/5/2012 14:08" — time is stripped
	"1/2/2006",       // inspection.csv dates and order.csv ComplianceDate: "1/10/2011"
}

// parseDate converts any recognised date string to ISO 8601 (YYYY-MM-DD).
// Returns nil for empty input; returns the raw string if no layout matches
// (so data is never silently dropped).
func parseDate(s string) *string {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			d := t.Format("2006-01-02")
			return &d
		}
	}
	return &s // unrecognised format — pass through
}

// ── null-coercion helpers ─────────────────────────────────────────────────────

// optStr returns nil for empty/whitespace-only strings.
func optStr(s string) *string {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	return &s
}

// optInt parses a float string (pandas writes "3.0") and returns *int,
// nil for empty strings or NaN.
func optInt(s string) *int {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil || math.IsNaN(f) {
		return nil
	}
	n := int(math.Round(f))
	return &n
}

// mustInt parses a float string to int, returning an error for truly
// unparseable values (used for required key columns).
func mustInt(s string) (int, error) {
	s = strings.TrimSpace(s)
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, err
	}
	return int(math.Round(f)), nil
}

// mustFloat parses a float string, returning 0 for empty or NaN.
func mustFloat(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil || math.IsNaN(f) {
		return 0
	}
	return f
}

// ── CSV primitives ────────────────────────────────────────────────────────────

// colIdx builds a name → column-index map from a header row.
func colIdx(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		m[h] = i
	}
	return m
}

// cell returns the value at a named column, or "" if the column is missing.
func cell(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return row[i]
}

// readCSV opens a CSV file and returns its header row and all data rows.
func readCSV(path string) (headers []string, rows [][]string, err error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true

	headers, err = r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("reading headers: %w", err)
	}

	for {
		rec, readErr := r.Read()
		if errors.Is(readErr, io.EOF) {
			break
		}
		if readErr != nil {
			return nil, nil, fmt.Errorf("reading row: %w", readErr)
		}
		rows = append(rows, rec)
	}
	return headers, rows, nil
}

// ── loaders ───────────────────────────────────────────────────────────────────

func (s *server) loadData() error {
	if err := s.loadElevators(); err != nil {
		return fmt.Errorf("loading merged_elevator_data.csv: %w", err)
	}
	if err := s.loadInspections(); err != nil {
		return fmt.Errorf("loading inspection.csv: %w", err)
	}
	if err := s.loadOrders(); err != nil {
		return fmt.Errorf("loading order.csv: %w", err)
	}
	s.loadPredictions() // non-fatal; /risk returns 503 when absent
	return nil
}

func (s *server) loadElevators() error {
	path := filepath.Join(s.cfg.dataDir, "merged_elevator_data.csv")
	headers, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIdx(headers)

	s.elevators = make(map[int]*elevatorRow, len(rows))
	s.elevatorIDs = make([]int, 0, len(rows))

	for _, row := range rows {
		id, err := mustInt(cell(row, idx, "ElevatingDevicesNumber"))
		if err != nil {
			continue // skip malformed rows
		}
		e := &elevatorRow{
			ID:                      id,
			Location:                cell(row, idx, "LocationoftheElevatingDevice"),
			DeviceType:              cell(row, idx, "Device Type"),
			DeviceClass:             cell(row, idx, "Device Class"),
			DeviceStatus:            cell(row, idx, "DeviceStatus"),
			UnderReview:             strings.TrimSpace(cell(row, idx, "under review")) == "Y",
			LicenseNumber:           cell(row, idx, "ElevatingDevicesLicenseNumber"),
			LicenseStatus:           cell(row, idx, "LICENSESTATUS"),
			LicenseExpiry:           parseDate(cell(row, idx, "LICENSEEXPIRYDATE")),
			LicenseHolder:           cell(row, idx, "LICENSEHOLDER"),
			LicenseHolderAddress:    cell(row, idx, "LICENSEHOLDERADDRESS"),
			BillingCustomer:         cell(row, idx, "BILLINGCUSTOMER"),
			BillingAddress:          cell(row, idx, "BILLINGADDRESS"),
			OwnerName:               cell(row, idx, "Owner Name"),
			OwnerAddress:            cell(row, idx, "Owner Address"),
			AlterationCount:         optInt(cell(row, idx, "alteration_count")),
			LatestAlterationType:    optStr(cell(row, idx, "latest_alteration_type")),
			LatestAlterationStatus:  optStr(cell(row, idx, "latest_alteration_status")),
			LatestInspectionDate:    parseDate(cell(row, idx, "Latest_INSPECTION_Date")),
			LatestInspectionType:    optStr(cell(row, idx, "InspectionType")),
			LatestInspectionOutcome: optStr(cell(row, idx, "InspectionOutcome")),
		}
		// Guard against duplicate IDs in source data
		if _, seen := s.elevators[id]; !seen {
			s.elevatorIDs = append(s.elevatorIDs, id)
		}
		s.elevators[id] = e
	}
	return nil
}

func (s *server) loadInspections() error {
	path := filepath.Join(s.cfg.dataDir, "inspection.csv")
	headers, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIdx(headers)

	s.inspByElev = make(map[int][]*inspectionRow)

	for _, row := range rows {
		elevID, err := mustInt(cell(row, idx, "ElevatingDevicesNumber"))
		if err != nil {
			continue
		}
		inspNum, err := mustInt(cell(row, idx, "InspectionNumber"))
		if err != nil {
			continue
		}

		insp := &inspectionRow{
			InspectionNumber:     inspNum,
			ServiceRequestNumber: cell(row, idx, "originatingservicerequestnumber"),
			InspectionCustomer:   cell(row, idx, "InspectionCustomer"),
			InspectionType:       cell(row, idx, "InspectionType"),
			InspectionLocation:   cell(row, idx, "InspectionLocation"),
			Outcome:              cell(row, idx, "InspectionOutcome"),
		}
		if d := parseDate(cell(row, idx, "Earliest_INSPECTION_Date")); d != nil {
			insp.EarliestDate = *d
		}
		if d := parseDate(cell(row, idx, "Latest_INSPECTION_Date")); d != nil {
			insp.LatestDate = *d
		}

		s.inspByElev[elevID] = append(s.inspByElev[elevID], insp)
	}
	return nil
}

func (s *server) loadOrders() error {
	path := filepath.Join(s.cfg.dataDir, "order.csv")
	headers, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIdx(headers)

	s.ordersByInsp = make(map[int][]*orderRow)
	s.ordersByElev = make(map[int][]*orderRow)

	for _, row := range rows {
		elevID, err := mustInt(cell(row, idx, "ElevatingDevicesNumber"))
		if err != nil {
			continue
		}
		// order.csv uses lowercase "inspectionnumber"; inspection.csv uses "InspectionNumber"
		inspNum, err := mustInt(cell(row, idx, "inspectionnumber"))
		if err != nil {
			continue
		}

		rawRS := strings.TrimSpace(cell(row, idx, "RISKSCORE"))
		ord := &orderRow{
			ElevatingDevicesNumber: elevID,
			InspectionNumber:       inspNum,
			RiskScore:              mustFloat(rawRS),
			HasRiskScore:           rawRS != "",
			Directive:              optStr(cell(row, idx, "DIRECTIVE")),
			Description:            optStr(cell(row, idx, "Inspectionsadditionalinformation")),
			Status:                 cell(row, idx, "StatusofInspectionOrder"),
			DaysToComply:           optInt(cell(row, idx, "DaystoComply")),
			ComplianceDate:         parseDate(cell(row, idx, "ComplianceDate")),
		}
		if d := parseDate(cell(row, idx, "DateofIssue")); d != nil {
			ord.DateIssued = *d
		}

		s.ordersByInsp[inspNum] = append(s.ordersByInsp[inspNum], ord)
		s.ordersByElev[elevID] = append(s.ordersByElev[elevID], ord)
	}
	return nil
}

// loadPredictions is non-fatal: if predictions.csv is absent, predictionsLoaded
// stays false and /risk returns 503 at request time.
func (s *server) loadPredictions() {
	path := filepath.Join(s.cfg.dataDir, "predictions.csv")
	headers, rows, err := readCSV(path)
	if err != nil {
		s.predictionsLoaded = false
		return
	}
	idx := colIdx(headers)

	// prob_* column → JSON response class label mapping (spec §5.4).
	probCols := map[string]string{
		"All Orders Resolved": "prob_all_orders_resolved",
		"Complete":            "prob_complete",
		"DC Follow up":        "prob_dc_follow_up",
		"Fail Initial":        "prob_fail_initial",
		"Follow Up Initial":   "prob_follow_up_initial",
		"Follow up":           "prob_follow_up",
		"Follow up Major":     "prob_follow_up_major",
		"Follow up Sub Major": "prob_follow_up_sub_major",
		"Other":               "prob_other",
		"Passed":              "prob_passed",
		"Passed Major":        "prob_passed_major",
		"Shutdown":            "prob_shutdown",
		"Unable to Inspect":   "prob_unable_to_inspect",
	}

	s.predictions = make(map[int]*predictionRow, len(rows))
	for _, row := range rows {
		// elevator_id is stored as "EL-XXXXXXXX"; strip prefix, parse int.
		raw := strings.TrimPrefix(strings.TrimSpace(cell(row, idx, "elevator_id")), "EL-")
		elevID, err := strconv.Atoi(raw)
		if err != nil || elevID <= 0 {
			continue
		}
		probs := make(map[string]jsonFloat, len(probCols))
		for label, col := range probCols {
			probs[label] = jsonFloat(mustFloat(cell(row, idx, col)))
		}
		pred := &predictionRow{
			PredictedOutcome:   strings.TrimSpace(cell(row, idx, "predicted_outcome")),
			Confidence:         mustFloat(cell(row, idx, "confidence")),
			ClassProbabilities: probs,
			RiskScore:          mustFloat(cell(row, idx, "risk_score")),
			RiskLevel:          strings.TrimSpace(cell(row, idx, "risk_level")),
			ModelVersion:       strings.TrimSpace(cell(row, idx, "model_version")),
		}
		if d := parseDate(cell(row, idx, "prediction_date")); d != nil {
			pred.AsOfDate = *d
		}
		s.predictions[elevID] = pred
	}
	s.predictionsLoaded = len(s.predictions) > 0
}
