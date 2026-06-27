package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
)

// ── Mock MCP client ───────────────────────────────────────────────────────────

type mockMCPClient struct {
	tools   []mcpTool
	results map[string]string // tool name → JSON result string

	mu    sync.Mutex
	calls []struct {
		name string
		args map[string]any
	}
}

func (m *mockMCPClient) Tools() []mcpTool { return m.tools }

func (m *mockMCPClient) CallTool(_ context.Context, name string, args map[string]any) (string, error) {
	m.mu.Lock()
	m.calls = append(m.calls, struct {
		name string
		args map[string]any
	}{name, args})
	m.mu.Unlock()

	if result, ok := m.results[name]; ok {
		return result, nil
	}
	return "", fmt.Errorf("mock: unknown tool %q", name)
}

func (m *mockMCPClient) Close() {}

func (m *mockMCPClient) toolCalled(name string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, c := range m.calls {
		if c.name == name {
			return true
		}
	}
	return false
}

// ── Fake Ollama server ────────────────────────────────────────────────────────

// fakeOllama serves pre-recorded Ollama /api/chat responses in order.
// Each HTTP call to /api/chat consumes the next response string.
type fakeOllama struct {
	mu        sync.Mutex
	responses []string
	idx       int
}

func (f *fakeOllama) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	io.Copy(io.Discard, r.Body) // drain body
	f.mu.Lock()
	if f.idx >= len(f.responses) {
		f.mu.Unlock()
		http.Error(w, `{"error":"fakeOllama: no more responses"}`, 500)
		return
	}
	resp := f.responses[f.idx]
	f.idx++
	f.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, resp)
}

func ollamaText(content string) string {
	return fmt.Sprintf(`{"message":{"role":"assistant","content":%s}}`, jsonStr(content))
}

func ollamaToolCallResp(toolName string, argsJSON string) string {
	return fmt.Sprintf(
		`{"message":{"role":"assistant","content":"","tool_calls":[{"function":{"name":%s,"arguments":%s}}]}}`,
		jsonStr(toolName), argsJSON,
	)
}

func jsonStr(s string) string {
	b, _ := json.Marshal(s)
	return string(b)
}

// newTestServer wires up a server with the mock MCP client and a fake Ollama,
// returning the test HTTP server and a cleanup function.
func newTestServer(t *testing.T, mock *mockMCPClient, ollama *fakeOllama) *httptest.Server {
	t.Helper()
	ts := httptest.NewServer(ollama)
	t.Cleanup(ts.Close)
	t.Setenv("OLLAMA_URL", ts.URL)
	t.Setenv("OLLAMA_MODEL", "test-model")
	t.Setenv("SYSTEM_PROMPT", "You are REMI, a test assistant.")

	srv := &server{mcp: mock}
	apiTS := httptest.NewServer(srv.routes())
	t.Cleanup(apiTS.Close)
	return apiTS
}

func postChat(t *testing.T, apiURL string, body string) chatResponse {
	t.Helper()
	resp, err := http.Post(apiURL+"/api/chat", "application/json", strings.NewReader(body))
	if err != nil {
		t.Fatalf("POST /api/chat: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(resp.Body)
		t.Fatalf("unexpected status %d: %s", resp.StatusCode, raw)
	}
	var cr chatResponse
	if err := json.NewDecoder(resp.Body).Decode(&cr); err != nil {
		t.Fatalf("decoding chatResponse: %v", err)
	}
	return cr
}

// ── Test 1: read-only tool call ───────────────────────────────────────────────

// TestHandleChat_ReadQuery verifies the two-step tool-use loop for a read tool:
//
//	call 1 → LLM returns tool_call for list_tssa_shutdown_elevators
//	MCP executes the tool
//	call 2 → LLM receives the result and returns a text answer
func TestHandleChat_ReadQuery(t *testing.T) {
	mock := &mockMCPClient{
		tools: []mcpTool{
			{Name: "list_tssa_shutdown_elevators", Description: "List elevators under TSSA shutdown order."},
		},
		results: map[string]string{
			"list_tssa_shutdown_elevators": `{"found":true,"count":3,"elevators":[]}`,
		},
	}

	ollama := &fakeOllama{responses: []string{
		// First LLM call: return a tool call
		ollamaToolCallResp("list_tssa_shutdown_elevators", "{}"),
		// Second LLM call (tool result fed back): return the final answer
		ollamaText("There are 3 elevators currently under TSSA shutdown."),
	}}

	apiTS := newTestServer(t, mock, ollama)

	cr := postChat(t, apiTS.URL, `{"message":"How many elevators are on TSSA shutdown?","history":[]}`)

	if cr.Reply != "There are 3 elevators currently under TSSA shutdown." {
		t.Errorf("unexpected reply: %q", cr.Reply)
	}
	if cr.PendingToolCall != nil {
		t.Errorf("expected no pending tool call, got %+v", cr.PendingToolCall)
	}
	if !mock.toolCalled("list_tssa_shutdown_elevators") {
		t.Error("expected list_tssa_shutdown_elevators to be called via MCP")
	}
}

// ── Test 2: schedule_inspection confirm-then-write flow ───────────────────────

// TestHandleChat_ScheduleInspectionConfirmFlow drives the full two-turn
// schedule_inspection gate:
//
//	Turn 1 — user asks to schedule: LLM returns schedule_inspection tool call →
//	          API surfaces confirmation prompt + pending_tool_call; MCP NOT called.
//
//	Turn 2 — user says "yes": API executes schedule_inspection via MCP,
//	          feeds result to LLM, returns natural-language confirmation.
func TestHandleChat_ScheduleInspectionConfirmFlow(t *testing.T) {
	scheduleResult := `{"id":9001,"elevator_id":12345,"inspection_type":"ED-Periodic Inspection","earliest_date":"2026-08-01","outcome":null,"source":"inspections table"}`

	mock := &mockMCPClient{
		tools: []mcpTool{
			{Name: "schedule_inspection", Description: "Schedule a new inspection (destructive)."},
		},
		results: map[string]string{
			"schedule_inspection": scheduleResult,
		},
	}

	schedArgs := `{"elevator_id":12345,"date":"2026-08-01","reason":"Annual safety check","priority":"high"}`

	ollama := &fakeOllama{responses: []string{
		// Turn 1: LLM wants to call schedule_inspection
		ollamaToolCallResp("schedule_inspection", schedArgs),
		// Turn 2: LLM summarises the tool result after confirmed write
		ollamaText("Done! Inspection #9001 has been scheduled for elevator 12345 on 2026-08-01."),
	}}

	apiTS := newTestServer(t, mock, ollama)

	// ── Turn 1: user asks to schedule ──
	turn1Body := `{"message":"Schedule a high-priority inspection for elevator 12345 on 2026-08-01. Reason: Annual safety check.","history":[]}`
	cr1 := postChat(t, apiTS.URL, turn1Body)

	if cr1.PendingToolCall == nil {
		t.Fatal("expected pending_tool_call in turn-1 response, got nil")
	}
	if cr1.PendingToolCall.Tool != "schedule_inspection" {
		t.Errorf("pending tool = %q, want schedule_inspection", cr1.PendingToolCall.Tool)
	}
	if !strings.Contains(cr1.Reply, "yes") || !strings.Contains(cr1.Reply, "cancel") {
		t.Errorf("confirmation message should mention 'yes' and 'cancel', got: %q", cr1.Reply)
	}
	if mock.toolCalled("schedule_inspection") {
		t.Error("schedule_inspection must NOT be called before user confirms")
	}

	// ── Turn 2: user confirms ──
	pendingJSON, _ := json.Marshal(cr1.PendingToolCall)
	turn2Body := fmt.Sprintf(
		`{"message":"yes","history":[{"role":"user","content":"Schedule..."},{"role":"assistant","content":%s}],"pending_tool_call":%s}`,
		jsonStr(cr1.Reply), string(pendingJSON),
	)
	cr2 := postChat(t, apiTS.URL, turn2Body)

	if !mock.toolCalled("schedule_inspection") {
		t.Error("schedule_inspection must be called via MCP after user confirms")
	}
	if cr2.PendingToolCall != nil {
		t.Errorf("expected no pending_tool_call after confirmation, got %+v", cr2.PendingToolCall)
	}
	if !strings.Contains(cr2.Reply, "9001") && !strings.Contains(cr2.Reply, "scheduled") {
		t.Errorf("expected confirmation reply mentioning inspection or ID, got: %q", cr2.Reply)
	}
}

// ── Test 3: cancel aborts without writing ─────────────────────────────────────

func TestHandleChat_ScheduleInspectionCancel(t *testing.T) {
	mock := &mockMCPClient{
		tools:   []mcpTool{{Name: "schedule_inspection"}},
		results: map[string]string{},
	}
	// Ollama is never called during cancellation — fakeOllama has no responses.
	ollama := &fakeOllama{}
	apiTS := newTestServer(t, mock, ollama)

	pending := &pendingToolCall{
		Tool: "schedule_inspection",
		Args: map[string]any{"elevator_id": 12345, "date": "2026-08-01", "reason": "check", "priority": "normal"},
	}
	pendingJSON, _ := json.Marshal(pending)

	body := fmt.Sprintf(
		`{"message":"cancel","history":[],"pending_tool_call":%s}`,
		string(pendingJSON),
	)
	cr := postChat(t, apiTS.URL, body)

	if !strings.Contains(strings.ToLower(cr.Reply), "cancel") {
		t.Errorf("expected cancellation message, got: %q", cr.Reply)
	}
	if mock.toolCalled("schedule_inspection") {
		t.Error("schedule_inspection must NOT be called after cancellation")
	}
	if cr.PendingToolCall != nil {
		t.Errorf("cancelled response must not carry a pending_tool_call")
	}
}

// ── Test 4: direct text answer (no tools needed) ─────────────────────────────

func TestHandleChat_DirectAnswer(t *testing.T) {
	mock := &mockMCPClient{tools: []mcpTool{}}
	ollama := &fakeOllama{responses: []string{
		ollamaText("I am REMI, your elevator operations assistant."),
	}}
	apiTS := newTestServer(t, mock, ollama)

	cr := postChat(t, apiTS.URL, `{"message":"Who are you?","history":[]}`)

	if cr.Reply != "I am REMI, your elevator operations assistant." {
		t.Errorf("unexpected reply: %q", cr.Reply)
	}
	if cr.PendingToolCall != nil {
		t.Errorf("expected no pending_tool_call, got %+v", cr.PendingToolCall)
	}
}
