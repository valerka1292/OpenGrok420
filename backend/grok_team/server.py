import sys
import os
import json
import uuid
import asyncio
from datetime import datetime, timezone

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from grok_team.orchestrator import Orchestrator

app = FastAPI(title="Grok Team API")

extra_origins = [
    origin.strip()
    for origin in os.getenv('FRONTEND_ORIGINS', '').split(',')
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173', 'http://127.0.0.1:5173',
        'http://localhost:5174', 'http://127.0.0.1:5174',
        'http://localhost:5175', 'http://127.0.0.1:5175',
        *extra_origins,
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: str
    duration: float | None = None


class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ChatStore:
    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _make_title(message: str) -> str:
        cleaned = " ".join(message.strip().split())
        if not cleaned:
            return "Новый диалог"
        return cleaned[:56] + ('…' if len(cleaned) > 56 else '')

    async def create_session(self, first_message: str = "") -> ChatSession:
        async with self._lock:
            now = self._now_iso()
            session = ChatSession(
                id=str(uuid.uuid4()),
                title=self._make_title(first_message),
                created_at=now,
                updated_at=now,
                messages=[],
            )
            self._sessions[session.id] = session
            return session

    async def list_sessions(self) -> list[SessionSummary]:
        async with self._lock:
            sessions = sorted(self._sessions.values(), key=lambda s: s.updated_at, reverse=True)
            return [
                SessionSummary(
                    id=s.id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=len(s.messages),
                )
                for s in sessions
            ]

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with self._lock:
            return self._sessions.get(session_id)

    async def append_message(self, session_id: str, role: str, content: str, duration: float | None = None):
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            now = self._now_iso()
            session.messages.append(ChatMessage(role=role, content=content, created_at=now, duration=duration))
            if role == 'user' and len(session.messages) <= 1:
                session.title = self._make_title(content)
            session.updated_at = now


chat_store = ChatStore()


class ChatRequest(BaseModel):
    message: str
    temperatures: dict[str, float] = {}
    session_id: str | None = None


@app.get('/api/sessions', response_model=list[SessionSummary])
async def list_sessions():
    return await chat_store.list_sessions()


@app.post('/api/sessions', response_model=SessionSummary)
async def create_session():
    created = await chat_store.create_session()
    return SessionSummary(
        id=created.id,
        title=created.title,
        created_at=created.created_at,
        updated_at=created.updated_at,
        message_count=0,
    )


@app.get('/api/sessions/{session_id}', response_model=ChatSession)
async def get_session(session_id: str):
    session = await chat_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    return session


@app.post('/api/chat')
async def chat_stream(req: ChatRequest):
    """SSE endpoint: streams NDJSON events from the multi-agent orchestrator."""
    session = await chat_store.get_session(req.session_id) if req.session_id else None
    if not session:
        session = await chat_store.create_session(req.message)

    await chat_store.append_message(session.id, 'user', req.message)

    orchestrator = Orchestrator()
    history = [
        {'role': msg.role, 'content': msg.content}
        for msg in session.messages[:-1]
        if msg.role in ('user', 'assistant')
    ]

    async def event_generator():
        started = datetime.now(timezone.utc)
        accumulated_response: list[str] = []

        yield json.dumps({'type': 'session', 'session_id': session.id}, ensure_ascii=False) + '\n'

        try:
            async for event in orchestrator.run_stream(req.message, req.temperatures, history=history):
                if event.get('type') == 'token':
                    accumulated_response.append(str(event.get('content', '')))
                yield json.dumps(event, ensure_ascii=False) + '\n'

            response_text = ''.join(accumulated_response).strip()
            if response_text:
                duration = (datetime.now(timezone.utc) - started).total_seconds()
                await chat_store.append_message(session.id, 'assistant', response_text, duration=duration)
        except Exception as e:
            yield json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False) + '\n'
            yield json.dumps({'type': 'done'}) + '\n'

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@app.get('/api/health')
async def health():
    return {'status': 'ok'}
