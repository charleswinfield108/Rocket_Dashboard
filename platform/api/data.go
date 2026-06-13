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

// ── internal row types ────────────────────────────────────────────────────────

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

// ── date normalisation ────────────────────────────────────────────────────────

// Layouts tried in order against order.csv cells. Timestamp variant must come
// before date-only so "3/5/2012 14:08" doesn't partially match "1/2/2006".
var dateLayouts = []string{
	"2006-01-02",     // ISO 8601 fallback
	"1/2/2006 15:04", // DateofIssue: "3/5/2012 14:08" — time stripped on format
	"1/2/2006",       // ComplianceDate: "1/10/2011"
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
