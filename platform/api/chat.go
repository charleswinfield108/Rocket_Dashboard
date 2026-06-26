package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"os"
)

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatRequest struct {
	Message string        `json:"message"`
	History []chatMessage `json:"history"`
}

type chatResponse struct {
	Reply string `json:"reply"`
}

func (s *server) handleChat(w http.ResponseWriter, r *http.Request) {
	var req chatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid request body"}`, http.StatusBadRequest)
		return
	}

	systemPrompt := loadSystemPrompt()

	// Build messages for Ollama: system + history + new user message
	messages := []chatMessage{
		{Role: "system", Content: systemPrompt},
	}
	messages = append(messages, req.History...)
	messages = append(messages, chatMessage{Role: "user", Content: req.Message})

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
		"messages": messages,
		"stream":   false,
	}
	body, _ := json.Marshal(payload)

	resp, err := http.Post(ollamaURL+"/api/chat", "application/json", bytes.NewReader(body))
	if err != nil {
		http.Error(w, `{"error":"could not reach Ollama"}`, http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)

	var ollamaResp struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	}
	if err := json.Unmarshal(raw, &ollamaResp); err != nil || ollamaResp.Message.Content == "" {
		http.Error(w, `{"error":"unexpected response from Ollama"}`, http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(chatResponse{Reply: ollamaResp.Message.Content})
}

func loadSystemPrompt() string {
	// Try file path relative to binary location, then fall back to env var
	paths := []string{
		"prompts/system_prompt.md",
		"platform/api/prompts/system_prompt.md",
		"/app/prompts/system_prompt.md",
	}
	for _, p := range paths {
		if data, err := os.ReadFile(p); err == nil {
			return string(data)
		}
	}
	if v := os.Getenv("SYSTEM_PROMPT"); v != "" {
		return v
	}
	return "You are REMI, a helpful elevator operations assistant. Answer questions about elevator operations, inspections, and compliance."
}
