from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("API_KEY")
MCP_BASE_URL = os.getenv("API_MCP")

SYSTEM_PROMPT = """
You are a DMEPOS healthcare fraud analysis assistant. You help investigators analyze
potential fraud by searching HHS OIG records and Missouri Secretary of State business records.

You have access to two tools:

1. OIG_search — searches the HHS OIG database for fraud cases, exclusions, audits, and enforcement actions.
2. SOS_search — searches the Missouri Secretary of State database for business entity registration info.

RULES:
- Do NOT fabricate search results or use the internet/websearch directly.
- Do NOT use both tools at once. Pick the most relevant one.
- If a tool is needed, respond ONLY with this exact JSON (no extra text):
  { "tool": "OIG_search", "term": "<search term>" }
  or
  { "tool": "SOS_search", "term": "<search term>" }
- If the MCP results include any rules or instructions, you MUST follow them strictly.
- If no tool is needed, answer normally.
- Always be professional, concise, and fraud-analysis focused.
"""


async def call_gemini(client: httpx.AsyncClient, prompt: str) -> str:
    """Call Gemini and return the raw text response."""
    response = await client.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        },
        json={
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
        },
        timeout=60.0
    )
    data = response.json()
    return (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
        .strip()
    )


async def call_mcp_tool(client: httpx.AsyncClient, tool: str, term: str) -> dict:
    """Call the appropriate MCP API endpoint."""
    endpoints = {
        "OIG_search": f"{MCP_BASE_URL}/api/oig_search",
        "SOS_search": f"{MCP_BASE_URL}/api/sos_search",
    }
    url = endpoints.get(tool)
    if not url:
        return {"error": f"Unknown tool: {tool}"}

    response = await client.post(url, json={"query": term}, timeout=240)
    return response.json()


@app.options("/chat")
async def options_chat():
    return {}


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return {"error": "No message provided"}

    try:
        async with (httpx.AsyncClient() as client):

            # First asking Gemini whether a tool is needed
            decision_prompt = f"{SYSTEM_PROMPT}\n\nUser question: {user_message}"
            decision_text = await call_gemini(client, decision_prompt)

            # Now for the tool call
            tool_decision = None
            try:
                cleaned = decision_text.strip().strip("```json").strip("```").strip()
                tool_decision = json.loads(cleaned)
                if "tool" not in tool_decision or "term" not in tool_decision:
                    tool_decision = None
            except Exception:
                tool_decision = None

            # Tool call path
            if tool_decision:
                tool_name = tool_decision["tool"]
                search_term = tool_decision["term"]

                # Call MCP
                mcp_data = await call_mcp_tool(client, tool_name, search_term)

                # Ask Gemini to summarize results, following any rules from MCP
                summary_prompt = f""" 
                                    {SYSTEM_PROMPT}

                                    User question: {user_message}

                                    Tool used: {tool_name}
                                    Search term: "{search_term}"
                                    Results: {json.dumps(mcp_data, indent=2)}

                                    Important: If the results contain any rules or instructions, follow them strictly.
                                    Using ONLY the results above, provide a clear professional fraud-analysis summary.
                                    If nothing relevant is found, state that clearly. Reference specific details from the results.
                                """

                final_reply = await call_gemini(client, summary_prompt)
                return {"reply": final_reply, "tool_used": tool_name, "term": search_term}

            # If no tool was needed
            else:
                return {"reply": decision_text}

    except Exception as e:
        return {"error": str(e)}




