package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"sync"
	"sync/atomic"
	"time"
)

// ── MCP wire types ─────────────────────────────────────────────────────────────

type mcpTool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

type jrpcReq struct {
	JSONRPC string `json:"jsonrpc"`
	ID      int64  `json:"id,omitempty"`
	Method  string `json:"method"`
	Params  any    `json:"params,omitempty"`
}

type jrpcResp struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *jrpcError      `json:"error,omitempty"`
}

type jrpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// ── Interface ─────────────────────────────────────────────────────────────────

// MCPClient is the interface the rest of the API uses to call MCP tools.
// Swappable for a mock in tests.
type MCPClient interface {
	Tools() []mcpTool
	CallTool(ctx context.Context, name string, args map[string]any) (string, error)
	Close()
}

// ── StdioMCPClient ─────────────────────────────────────────────────────────────

// StdioMCPClient launches the Python MCP server as a subprocess and communicates
// via JSON-RPC 2.0 over newline-delimited stdin / stdout.
type StdioMCPClient struct {
	cmd   *exec.Cmd
	stdin io.WriteCloser
	tools []mcpTool

	writeMu sync.Mutex
	pendMu  sync.Mutex
	pending map[int64]chan jrpcResp
	nextID  atomic.Int64
	done    chan struct{}
}

// newStdioMCPClient starts the Python MCP server, performs the MCP initialize
// handshake, discovers all tools, and returns a ready client.
//
// serverDir is the directory containing server.py. python is the Python binary
// (e.g. "python3"). Set MCP_SERVER_DIR / MCP_PYTHON to override defaults.
func newStdioMCPClient(serverDir, python string) (*StdioMCPClient, error) {
	cmd := exec.Command(python, "server.py")
	cmd.Dir = serverDir
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	cmd.Stderr = os.Stderr // Python logs → our stderr

	stdinPipe, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("stdin pipe: %w", err)
	}
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("stdout pipe: %w", err)
	}
	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("starting MCP server: %w", err)
	}

	c := &StdioMCPClient{
		cmd:     cmd,
		stdin:   stdinPipe,
		pending: make(map[int64]chan jrpcResp),
		done:    make(chan struct{}),
	}
	go c.readLoop(stdoutPipe)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := c.initialize(ctx); err != nil {
		cmd.Process.Kill()
		return nil, fmt.Errorf("MCP initialize: %w", err)
	}
	if err := c.discoverTools(ctx); err != nil {
		cmd.Process.Kill()
		return nil, fmt.Errorf("MCP list tools: %w", err)
	}
	log.Printf("MCP: server ready, %d tools available", len(c.tools))
	return c, nil
}

// readLoop runs in a goroutine and dispatches JSON-RPC responses to waiting callers.
func (c *StdioMCPClient) readLoop(r io.Reader) {
	defer close(c.done)
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 4*1024*1024), 4*1024*1024) // 4 MB for large tool results
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		var resp jrpcResp
		if err := json.Unmarshal([]byte(line), &resp); err != nil {
			continue // not a JSON-RPC response (e.g. stray log line)
		}
		if resp.ID == 0 {
			continue // notification — no waiter
		}
		c.pendMu.Lock()
		ch, ok := c.pending[resp.ID]
		if ok {
			delete(c.pending, resp.ID)
		}
		c.pendMu.Unlock()
		if ok {
			ch <- resp
		}
	}
}

// rpc sends a JSON-RPC request and waits for the matching response.
func (c *StdioMCPClient) rpc(ctx context.Context, method string, params any) (*jrpcResp, error) {
	id := c.nextID.Add(1)

	// Register the response channel BEFORE sending to avoid a race.
	ch := make(chan jrpcResp, 1)
	c.pendMu.Lock()
	c.pending[id] = ch
	c.pendMu.Unlock()

	data, err := json.Marshal(jrpcReq{JSONRPC: "2.0", ID: id, Method: method, Params: params})
	if err != nil {
		c.pendMu.Lock()
		delete(c.pending, id)
		c.pendMu.Unlock()
		return nil, err
	}

	c.writeMu.Lock()
	_, err = fmt.Fprintf(c.stdin, "%s\n", data)
	c.writeMu.Unlock()
	if err != nil {
		c.pendMu.Lock()
		delete(c.pending, id)
		c.pendMu.Unlock()
		return nil, err
	}

	select {
	case resp := <-ch:
		if resp.Error != nil {
			return nil, fmt.Errorf("MCP %s error %d: %s", method, resp.Error.Code, resp.Error.Message)
		}
		return &resp, nil
	case <-ctx.Done():
		c.pendMu.Lock()
		delete(c.pending, id)
		c.pendMu.Unlock()
		return nil, ctx.Err()
	case <-c.done:
		return nil, fmt.Errorf("MCP server exited unexpectedly")
	}
}

// notify sends a JSON-RPC notification (no response expected).
func (c *StdioMCPClient) notify(method string, params any) {
	data, _ := json.Marshal(jrpcReq{JSONRPC: "2.0", Method: method, Params: params})
	c.writeMu.Lock()
	fmt.Fprintf(c.stdin, "%s\n", data)
	c.writeMu.Unlock()
}

func (c *StdioMCPClient) initialize(ctx context.Context) error {
	_, err := c.rpc(ctx, "initialize", map[string]any{
		"protocolVersion": "2024-11-05",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "rocket-elevators-api", "version": "1.0"},
	})
	if err != nil {
		return err
	}
	c.notify("notifications/initialized", nil)
	return nil
}

func (c *StdioMCPClient) discoverTools(ctx context.Context) error {
	resp, err := c.rpc(ctx, "tools/list", map[string]any{})
	if err != nil {
		return err
	}
	var result struct {
		Tools []mcpTool `json:"tools"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return fmt.Errorf("parsing tools/list result: %w", err)
	}
	c.tools = result.Tools
	return nil
}

// Tools returns the list of tools discovered at startup.
func (c *StdioMCPClient) Tools() []mcpTool { return c.tools }

// CallTool calls a named MCP tool and returns the text content of the first result item.
func (c *StdioMCPClient) CallTool(ctx context.Context, name string, args map[string]any) (string, error) {
	if args == nil {
		args = map[string]any{}
	}
	resp, err := c.rpc(ctx, "tools/call", map[string]any{
		"name":      name,
		"arguments": args,
	})
	if err != nil {
		return "", err
	}

	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		return "", fmt.Errorf("parsing tools/call result: %w", err)
	}
	if len(result.Content) == 0 {
		return "", nil
	}
	if result.IsError {
		return "", fmt.Errorf("tool %q error: %s", name, result.Content[0].Text)
	}
	return result.Content[0].Text, nil
}

// Close shuts down the MCP server subprocess.
func (c *StdioMCPClient) Close() {
	c.stdin.Close()
	c.cmd.Wait()
}

// mcpServerDir returns the directory containing server.py.
// Override with MCP_SERVER_DIR env var (required in Docker / Render).
// Defaults to ../mcp relative to the process working directory (platform/api/).
func mcpServerDir() string {
	if d := os.Getenv("MCP_SERVER_DIR"); d != "" {
		return d
	}
	return "../mcp"
}

// mcpPython returns the Python binary to use when starting the MCP server.
// Override with MCP_PYTHON env var (e.g. "python" on Windows or a venv path).
func mcpPython() string {
	if p := os.Getenv("MCP_PYTHON"); p != "" {
		return p
	}
	return "python3"
}

// parseToolArgs deserialises json.RawMessage arguments that may arrive as either
// a JSON object or a double-encoded JSON string (some models serialise this way).
func parseToolArgs(raw json.RawMessage) map[string]any {
	if len(raw) == 0 {
		return nil
	}
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err == nil {
		return m
	}
	var s string
	if err := json.Unmarshal(raw, &s); err == nil {
		var m2 map[string]any
		if json.Unmarshal([]byte(s), &m2) == nil {
			return m2
		}
	}
	return nil
}
