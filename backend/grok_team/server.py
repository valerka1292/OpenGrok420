
import sys
import os
import json

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from grok_team.orchestrator import Orchestrator

app = FastAPI(title="Grok Team API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class ChatRequest(BaseModel):
    message: str
    temperatures: dict[str, float] = {}


@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """SSE endpoint: streams NDJSON events from the multi-agent orchestrator."""
    orchestrator = Orchestrator()

    async def event_generator():
        try:
            async for event in orchestrator.run_stream(req.message, req.temperatures):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
