import sys
import os
import json
import asyncio
import time
from pathlib import Path

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from grok_team.orchestrator import Orchestrator
from grok_team.history import SQLiteHistoryStore, StoredMessage

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

HISTORY_PATH = Path(os.getenv('HISTORY_STORE_PATH', 'backend/data/history.db'))
history_store = SQLiteHistoryStore(HISTORY_PATH)
history_lock = asyncio.Lock()

@app.on_event('startup')
async def startup_event():
    await history_store.initialize()



class ChatRequest(BaseModel):
    message: str
    temperatures: dict[str, float] = {}
    conversation_id: str | None = None


class ConversationCreateRequest(BaseModel):
    title: str = Field(default='Новый диалог', min_length=1, max_length=120)


@app.get('/api/conversations')
async def list_conversations(query: str = ''):
    async with history_lock:
        if query.strip():
            return {'items': await history_store.search_summaries(query)}
        return {'items': await history_store.list_summaries()}


@app.post('/api/conversations')
async def create_conversation(req: ConversationCreateRequest):
    async with history_lock:
        conv = await history_store.create(req.title)
        return conv.to_dict()


@app.get('/api/conversations/{conversation_id}')
async def get_conversation(conversation_id: str):
    async with history_lock:
        conv = await history_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail='Conversation not found')
        return conv.to_dict()


@app.delete('/api/conversations/{conversation_id}')
async def delete_conversation(conversation_id: str):
    async with history_lock:
        deleted = await history_store.delete(conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail='Conversation not found')
        return {'status': 'deleted'}


@app.post('/api/chat')
async def chat_stream(req: ChatRequest):
    """SSE endpoint: streams NDJSON events from the multi-agent orchestrator."""
    orchestrator = Orchestrator()

    async with history_lock:
        conversation = await history_store.get_or_create(req.conversation_id)
        was_new_conversation = len(conversation.messages) == 0
        previous_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation.messages
            if msg.role in {"user", "assistant"}
        ]
        await history_store.add_message(conversation.id, StoredMessage(role='user', content=req.message))

    orchestrator.restore_leader_history(previous_messages)

    async def event_generator():
        assistant_tokens: list[str] = []
        assistant_thoughts: list[dict] = []
        start = time.perf_counter()
        conversation_saved = False

        try:
            yield json.dumps({'type': 'conversation', 'conversation_id': conversation.id}, ensure_ascii=False) + '\n'
            async for event in orchestrator.run_stream(req.message, req.temperatures, require_title_tool=was_new_conversation):
                event_type = event.get('type')
                if event_type in {'thought', 'tool_use', 'chatroom_send', 'status'}:
                    assistant_thoughts.append(event)
                elif event_type == 'token' and event.get('content'):
                    assistant_tokens.append(str(event.get('content')))
                elif event_type == 'conversation_title' and event.get('title'):
                    async with history_lock:
                        await history_store.update_title(conversation.id, str(event.get('title')))

                if event_type == 'done' and not conversation_saved:
                    assistant_text = ''.join(assistant_tokens).strip()
                    if assistant_text:
                        duration = round(time.perf_counter() - start, 2)
                        async with history_lock:
                            await history_store.add_message(conversation.id, StoredMessage(
                                role='assistant',
                                content=assistant_text,
                                thoughts=assistant_thoughts,
                                duration=duration,
                            ))
                    conversation_saved = True

                yield json.dumps(event, ensure_ascii=False) + '\n'
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
