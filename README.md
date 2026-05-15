# DEMIrobato (DMEPOS Fraud Analysis AI Assistant) - Gemini Chat Server

A FastAPI backend that uses Gemini to analyze healthcare fraud queries. Gemini decides when to call the MCP scraper tools (OIG or SOS) and summarizes the results for investigators.

## What it does

1. Takes a user question via `/chat`
2. Asks Gemini if a tool call is needed (OIG search or SOS search)
3. If yes — calls the MCP API, gets the scraped data, and has Gemini summarize it as a fraud analysis
4. If no — Gemini responds directly

## Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, get a fraud-analysis response |

### Request
```json
{ "message": "Search OIG for ABC Medical Supplies" }
```

### Response
```json
{
  "reply": "...",
  "tool_used": "OIG_search",
  "term": "abc medical supplies"
}
```

## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

Requirements: `fastapi`, `uvicorn`, `httpx`

### Environment Variables

| Variable | Description |
|---|---|
| `API_KEY` | Your Google Gemini API key |
| `API_MCP` | Base URL of the running MCP scraper API (e.g. `https://your-mcp-service.onrender.com`) |


## How Gemini decides what to do

The system prompt currently restricts Gemini strictly to OIG and SOS searches. If a tool is needed, Gemini returns only a JSON object like:

```json
{ "tool": "OIG_search", "term": "abc medical supplies" }
```

The server parses that, calls the MCP scraper, and sends the results back to Gemini for a final fraud-focused summary.

---

> Part of the DMEPOS Healthcare Fraud Analysis tool suite.
