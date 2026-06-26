# AND-107 AI-Native Requirements

## MCP as Tool Architecture

Use MCP (Model Context Protocol) as the protocol for the chatbot's tools. Build an MCP server and connect the Go API as an MCP client. This gives a single set of tool definitions that serves two consumers:
- The chatbot product (via the Go API)
- Claude Code during development (see MCP in Claude Code below)

## MCP in Claude Code

Configure Claude Code so it can access the same tools the chatbot uses during development. This gives the development tool direct access to the chatbot's data, making development faster and debugging conversational.

**Usage during the sprint:**
- When building or debugging a tool, ask Claude Code to call it directly and show the output.
- When tuning the RAG pipeline, have Claude Code search the knowledge base and show which chunks come back.
- The MCP server becomes part of the development workflow, not just the chatbot's runtime.

**Deliverable:** `docs/mcp-development-workflow.md`

A short reflection describing how using the MCP server through Claude Code helped during development:
- What it was used for
- What it made easier
- Whether it changed how debugging or building was approached

## MCP Security

MCP tools accept input from an LLM, which means they accept input ultimately shaped by user messages. Treat MCP tool inputs the same way as user input in a web API: **validate and sanitize everything**.

Test the MCP server for vulnerabilities. Try to make it execute unintended queries through crafted inputs.

**Deliverable:** `docs/mcp-security-test.md`

Document:
- What was tested
- What was found

## Claude as Test Harness

Use Claude Code or `claude -p` to systematically test the chatbot's responses. Claude (via Pro subscription) is a stronger model than what the chatbot runs on, making it effective for evaluating whether responses are accurate, grounded, and properly cited.

**Deliverable:** `docs/chatbot-evaluation.md`

Document test scenarios and results.

## AI-Assisted PR Review

Continues from Sprint 1. Every pull request requires at least one review before merging. Reviewers may use AI tools but must add their own assessment.
