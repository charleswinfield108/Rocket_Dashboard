package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// ── Frontend wire types ───────────────────────────────────────────────────────

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// pendingToolCall carries a gated write across the HTTP boundary so the
// frontend can send it back with the user's explicit confirmation on the next turn.
type pendingToolCall struct {
	Tool string         `json:"tool"`
	Args map[string]any `json:"args"`
}

type chatRequest struct {
	Message         string           `json:"message"`
	History         []chatMessage    `json:"history"`
	PendingToolCall *pendingToolCall `json:"pending_tool_call,omitempty"`
}

type chatResponse struct {
	Reply           string           `json:"reply"`
	PendingToolCall *pendingToolCall `json:"pending_tool_call,omitempty"`
}

// ── Ollama internal types ─────────────────────────────────────────────────────

type ollamaToolCall struct {
	Function struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	} `json:"function"`
}

type ollamaMsg struct {
	Role      string           `json:"role"`
	Content   string           `json:"content,omitempty"`
	ToolCalls []ollamaToolCall `json:"tool_calls,omitempty"`
}

type ollamaTool struct {
	Type     string `json:"type"`
	Function struct {
		Name        string          `json:"name"`
		Description string          `json:"description"`
		Parameters  json.RawMessage `json:"parameters"`
	} `json:"function"`
}

// ── Handler ───────────────────────────────────────────────────────────────────

func (s *server) handleChat(w http.ResponseWriter, r *http.Request) {
	var req chatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 90*time.Second)
	defer cancel()

	systemPrompt := loadSystemPrompt()

	// ── Confirmation gate for schedule_inspection ──
	if req.PendingToolCall != nil && req.PendingToolCall.Tool == "schedule_inspection" {
		s.handleConfirmation(w, ctx, req, systemPrompt)
		return
	}

	// ── Normal tool-use loop ──
	msgs := buildMessages(systemPrompt, req.History)
	msgs = append(msgs, ollamaMsg{Role: "user", Content: req.Message})

	var tools []ollamaTool
	if s.mcp != nil {
		tools = mcpToOllamaTools(s.mcp.Tools())
	}

	reply, pending, err := s.runToolLoop(ctx, msgs, tools)
	if err != nil {
		http.Error(w, `{"error":"LLM unavailable"}`, http.StatusServiceUnavailable)
		return
	}
	json.NewEncoder(w).Encode(chatResponse{Reply: reply, PendingToolCall: pending}) //nolint:errcheck
}

// handleConfirmation processes the user's yes/no response for a pending
// schedule_inspection call. The write only runs on an explicit affirmative.
func (s *server) handleConfirmation(w http.ResponseWriter, ctx context.Context, req chatRequest, systemPrompt string) {
	pending := req.PendingToolCall

	switch {
	case isAffirmative(req.Message):
		if s.mcp == nil {
			json.NewEncoder(w).Encode(chatResponse{Reply: "MCP server is not available — cannot schedule the inspection."}) //nolint:errcheck
			return
		}
		result, err := s.mcp.CallTool(ctx, pending.Tool, pending.Args)
		if err != nil {
			json.NewEncoder(w).Encode(chatResponse{Reply: "Failed to schedule inspection: " + err.Error()}) //nolint:errcheck
			return
		}

		// Feed the tool result to the LLM so it produces a natural-language confirmation.
		msgs := buildMessages(systemPrompt, req.History)
		msgs = append(msgs, ollamaMsg{Role: "user", Content: req.Message})
		msgs = append(msgs, ollamaMsg{
			Role: "user",
			Content: fmt.Sprintf(
				"The schedule_inspection tool completed. Result:\n\n%s\n\n"+
					"Confirm to the user what was scheduled in one or two sentences.",
				result,
			),
		})
		reply, _, llmErr := s.callOllama(ctx, msgs, nil)
		if llmErr != nil {
			reply = "Inspection scheduled.\n\nTool result:\n" + result
		}
		json.NewEncoder(w).Encode(chatResponse{Reply: reply}) //nolint:errcheck

	case isCancellation(req.Message):
		json.NewEncoder(w).Encode(chatResponse{Reply: "Inspection scheduling cancelled."}) //nolint:errcheck

	default:
		// Unclear — re-ask, keeping the pending call so the frontend can try again.
		json.NewEncoder(w).Encode(chatResponse{ //nolint:errcheck
			Reply:           "Please respond with **yes** to confirm or **cancel** to abort.",
			PendingToolCall: pending,
		})
	}
}

// runToolLoop drives the LLM + MCP tool execution loop.
//
// Each iteration calls the LLM. If it returns tool calls, they are executed and
// their results appended before the next call. The loop exits when the LLM
// returns a plain text answer.
//
// Exception: schedule_inspection is gated — instead of executing the write, the
// loop returns a confirmation prompt and a non-nil pending that the caller must
// surface to the user before the write can proceed.
func (s *server) runToolLoop(ctx context.Context, msgs []ollamaMsg, tools []ollamaTool) (reply string, pending *pendingToolCall, err error) {
	const maxIter = 8
	for i := 0; i < maxIter; i++ {
		content, toolCalls, err := s.callOllama(ctx, msgs, tools)
		if err != nil {
			return "", nil, err
		}

		if len(toolCalls) == 0 {
			return content, nil, nil
		}

		msgs = append(msgs, ollamaMsg{Role: "assistant", ToolCalls: toolCalls})

		for _, tc := range toolCalls {
			if tc.Function.Name == "schedule_inspection" {
				args := parseToolArgs(tc.Function.Arguments)
				p := &pendingToolCall{Tool: "schedule_inspection", Args: args}
				return formatConfirmation(args), p, nil
			}

			// All other tools are read-only; execute immediately.
			args := parseToolArgs(tc.Function.Arguments)
			result := ""
			if s.mcp != nil {
				toolCtx, cancel := context.WithTimeout(ctx, 45*time.Second)
				r, callErr := s.mcp.CallTool(toolCtx, tc.Function.Name, args)
				cancel()
				if callErr != nil {
					result = fmt.Sprintf(`{"error":%q}`, callErr.Error())
				} else {
					result = r
				}
			}
			msgs = append(msgs, ollamaMsg{Role: "tool", Content: result})
		}
	}
	return "", nil, fmt.Errorf("tool loop exceeded %d iterations", maxIter)
}

// callOllama sends one request to Ollama /api/chat. tools may be nil.
func (s *server) callOllama(ctx context.Context, msgs []ollamaMsg, tools []ollamaTool) (string, []ollamaToolCall, error) {
	ollamaURL := os.Getenv("OLLAMA_URL")
	if ollamaURL == "" {
		ollamaURL = "http://localhost:11434"
	}
	model := os.Getenv("OLLAMA_MODEL")
	if model == "" {
		model = "gemma2:2b"
	}

	payload := map[string]any{
		"model":    model,
		"messages": msgs,
		"stream":   false,
	}
	if len(tools) > 0 {
		payload["tools"] = tools
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, ollamaURL+"/api/chat", bytes.NewReader(body))
	if err != nil {
		return "", nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", nil, fmt.Errorf("could not reach Ollama: %w", err)
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)

	var or struct {
		Message struct {
			Content   string           `json:"content"`
			ToolCalls []ollamaToolCall `json:"tool_calls"`
		} `json:"message"`
	}
	if err := json.Unmarshal(raw, &or); err != nil {
		return "", nil, fmt.Errorf("unexpected Ollama response: %w", err)
	}
	return or.Message.Content, or.Message.ToolCalls, nil
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func buildMessages(systemPrompt string, history []chatMessage) []ollamaMsg {
	msgs := make([]ollamaMsg, 0, 1+len(history))
	msgs = append(msgs, ollamaMsg{Role: "system", Content: systemPrompt})
	for _, h := range history {
		msgs = append(msgs, ollamaMsg{Role: h.Role, Content: h.Content})
	}
	return msgs
}

func mcpToOllamaTools(mcpTools []mcpTool) []ollamaTool {
	out := make([]ollamaTool, 0, len(mcpTools))
	for _, t := range mcpTools {
		var ot ollamaTool
		ot.Type = "function"
		ot.Function.Name = t.Name
		ot.Function.Description = t.Description
		ot.Function.Parameters = t.InputSchema
		out = append(out, ot)
	}
	return out
}

func formatConfirmation(args map[string]any) string {
	priority := args["priority"]
	if priority == nil {
		priority = "normal"
	}
	return fmt.Sprintf(
		"REMI wants to schedule an inspection:\n\n"+
			"• Elevator ID: %v\n"+
			"• Date: %v\n"+
			"• Priority: %v\n"+
			"• Reason: %v\n\n"+
			"⚠️  This will INSERT a new row into the inspections table.\n"+
			"Type **yes** to confirm or **cancel** to abort.",
		args["elevator_id"], args["date"], priority, args["reason"],
	)
}

func isAffirmative(msg string) bool {
	s := strings.ToLower(strings.TrimSpace(msg))
	for _, w := range []string{"yes", "y", "confirm", "ok", "sure", "go", "proceed", "do it", "confirmed", "go ahead", "yep", "yeah"} {
		if s == w {
			return true
		}
	}
	return strings.HasPrefix(s, "yes,") || strings.HasPrefix(s, "yes ")
}

func isCancellation(msg string) bool {
	s := strings.ToLower(strings.TrimSpace(msg))
	for _, w := range []string{"no", "n", "cancel", "abort", "stop", "never mind", "nevermind", "nope", "nah"} {
		if s == w {
			return true
		}
	}
	return strings.HasPrefix(s, "no,") || strings.HasPrefix(s, "cancel ")
}

func loadSystemPrompt() string {
	for _, p := range []string{
		"prompts/system_prompt.md",
		"platform/api/prompts/system_prompt.md",
		"/app/prompts/system_prompt.md",
	} {
		if data, err := os.ReadFile(p); err == nil {
			return string(data)
		}
	}
	if v := os.Getenv("SYSTEM_PROMPT"); v != "" {
		return v
	}
	return "You are REMI, a helpful elevator operations assistant."
}
