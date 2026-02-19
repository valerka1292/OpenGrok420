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
from pydantic import BaseModel, Field, ConfigDict

from grok_team.kernel import Kernel
from grok_team.agent import Agent
from grok_team.config import ALL_AGENT_NAMES, LEADER_NAME
from grok_team.history import SQLiteHistoryStore, StoredMessage

app = FastAPI(title="Grok Team API")
KERNEL = Kernel()

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

from grok_team.history_writer import HistoryWriter

HISTORY_PATH = Path(os.getenv('HISTORY_STORE_PATH', 'backend/data/history.db'))
history_store = SQLiteHistoryStore(HISTORY_PATH)
history_writer = HistoryWriter(history_store)
history_lock = asyncio.Lock()

@app.on_event('startup')
async def startup_event():
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    await history_store.initialize()
    await history_writer.start()
    
    # Initialize Agents
    for name in ALL_AGENT_NAMES:
        # Check if already exists to avoid dupes on reload
        if name not in KERNEL.actors:
            agent = Agent(name, KERNEL.event_bus)
            KERNEL.register_actor(agent)
            
    await KERNEL.start()

@app.on_event('shutdown')
async def shutdown_event():
    await KERNEL.stop()
    await history_writer.stop()



class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    message: str
    temperatures: dict[str, float] = Field(default_factory=dict)
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
    """SSE endpoint: streams JSON payloads over Server-Sent Events from the Kernel EventBus."""

    async with history_lock:
        conversation = await history_store.get_or_create(req.conversation_id)
        # We might need to restore agent state from DB here in a real unified system
        # For now, we assume agents are running in memory (Note: this is not stateless between requests in this simple integration)
        # But we DO need to log the user message
        # Use background writer
        await history_writer.add_message(conversation.id, StoredMessage(role='user', content=req.message))

    # Identify a "reply channel" for this request
    request_id = f"req_{int(time.time()*1000)}"
    correlation_id = request_id

    # Apply per-agent temperatures from the client request.
    for agent_name, value in req.temperatures.items():
        agent = KERNEL.actors.get(agent_name)
        if agent is None:
            continue
        try:
            agent.temperature = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            continue
    
    def _sse(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    async def event_generator():
        assistant_tokens: list[str] = [] 
        assistant_thoughts: list[dict] = []
        start = time.perf_counter()
        
        # Queue to capture events for this specific request
        response_queue = asyncio.Queue()
        
        async def on_event(event):
            # We filter for events relevant to this request via correlation_id
            if event.get("correlation_id") == correlation_id:
                 await response_queue.put(event)
            # Fallback for legacy or direct targets (if target matches request_id)
            elif event.get("target") == request_id:
                 await response_queue.put(event)

        topics = [
            "TaskCompleted",
            "TaskSubmitted",
            "TaskFailed",
            "SystemCall",
            "ToolUse",
            "ArtifactCreated",
            "MemoryCompressed",
            "AgentSpawned",
            "AgentStopped",
        ]
        for topic in topics:
            KERNEL.event_bus.subscribe(topic, on_event)

        
        # Inject User Message into Leader
        # We tell the leader this message comes from "User" (or our request_id if we want routing back)
        await KERNEL.actors[LEADER_NAME].inbox.put({
            "type": "TaskSubmitted",
            "from": request_id, 
            "correlation_id": correlation_id,
            "content": req.message
        })
        
        try:
            yield _sse({'type': 'conversation', 'conversation_id': conversation.id})
            yield _sse({'type': 'status', 'content': 'Thinking...'})

            while True:
                # Wait for events with a timeout
                try:
                    event = await asyncio.wait_for(response_queue.get(), timeout=60.0) # 60s timeout for demo
                except asyncio.TimeoutError:
                    yield _sse({'type': 'error', 'content': 'Timeout waiting for response'})
                    break

                event_type = event.get("type")
                sender = event.get("from", event.get("actor", "unknown"))
                
                if event_type == "TaskCompleted":
                    # If this is the final answer addressed to us
                    if sender == LEADER_NAME or event.get("target") == request_id:
                        content = event.get("content")
                        if content:
                             yield _sse({'type': 'token', 'content': content})
                             assistant_tokens.append(content)
                             # Break only if it's the final answer from Leader?
                             # With Agent OS, we might get multiple completions. 
                             # For now, we assume Leader's completion is final.
                             if sender == LEADER_NAME:
                                 break 
                             
                elif event_type == "TaskSubmitted":
                    # Thought/Delegation -> chatroom_send
                    content = event.get("content")
                    target = event.get("target", "unknown")
                    if sender != request_id:
                        event_payload = {
                            'type': 'chatroom_send',
                            'agent': sender,
                            'content': content,
                            'to': target,
                        }
                        assistant_thoughts.append(event_payload)
                        yield _sse(event_payload)
                        
                elif event_type == "SystemCall":
                    event_payload = {'type': 'thought', 'agent': sender, 'content': f"System Call: {event.get('command')}"}
                    assistant_thoughts.append(event_payload)
                    yield _sse(event_payload)

                elif event_type == "ToolUse":
                     args_str = json.dumps(event.get('args', {}), ensure_ascii=False)
                     event_payload = {'type': 'tool_use', 'agent': sender, 'tool': event.get('tool'), 'query': args_str}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)

                elif event_type == "ArtifactCreated":
                     event_payload = {'type': 'thought', 'agent': sender, 'content': f"📦 Created Artifact {event.get('artifact_id')}"}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)

                elif event_type == "MemoryCompressed":
                     event_payload = {'type': 'thought', 'agent': sender, 'content': '🧠 Memory Compressed'}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)

                elif event_type == "AgentSpawned":
                     event_payload = {'type': 'thought', 'agent': 'Kernel', 'content': f"✨ Spawned Agent: {event.get('actor')}"}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)

                elif event_type == "AgentStopped":
                     event_payload = {'type': 'thought', 'agent': 'Kernel', 'content': f"💀 Stopped Agent: {event.get('actor')}"}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)
                     
                elif event_type == "TaskFailed":
                     event_payload = {'type': 'thought', 'agent': sender, 'content': f"❌ Error: {event.get('error')}"}
                     assistant_thoughts.append(event_payload)
                     yield _sse(event_payload)


            # Done
            duration = round(time.perf_counter() - start, 2)
            final_text = "".join(assistant_tokens)
            
            if final_text:
                # Use background writer (no lock needed)
                await history_writer.add_message(conversation.id, StoredMessage(
                    role='assistant',
                    content=final_text,
                    thoughts=assistant_thoughts,
                    duration=duration,
                ))
            
            yield _sse({'type': 'done'})

        except Exception as e:
            yield _sse({'type': 'error', 'content': str(e)})
            yield _sse({'type': 'done'})
        finally:
            for topic in topics:
                KERNEL.event_bus.unsubscribe(topic, on_event)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@app.get('/api/events')
async def get_events(limit: int = 100):
    """Retrieve recent system events from the log."""
    events = KERNEL.event_logger.get_all_events()
    # Return last N events
    return {"events": events[-limit:]}

@app.get('/api/health')
async def health():
    return {'status': 'ok'}
