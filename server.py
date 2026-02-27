from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
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

@app.options("/chat")
async def options_chat():
    return {}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")

    if not user_message:
        return {"error": "No message provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": GEMINI_API_KEY
                },
                json={
                    "contents": [
                        {"parts": [{"text": user_message}]}
                    ]
                }
            )

            result = response.json()
            reply = result["candidates"][0]["content"]["parts"][0]["text"]

            return {"reply": reply}

    except Exception as e:
        return {"error": str(e)}
