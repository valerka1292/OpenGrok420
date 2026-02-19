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
    """SSE endpoint: streams NDJSON events from the Kernel EventBus."""

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

        KERNEL.event_bus.subscribe("TaskCompleted", on_event)
        KERNEL.event_bus.subscribe("TaskSubmitted", on_event)
        KERNEL.event_bus.subscribe("TaskFailed", on_event)
        KERNEL.event_bus.subscribe("SystemCall", on_event)
        KERNEL.event_bus.subscribe("ToolUse", on_event) 
        KERNEL.event_bus.subscribe("ArtifactCreated", on_event)
        KERNEL.event_bus.subscribe("MemoryCompressed", on_event)
        KERNEL.event_bus.subscribe("AgentSpawned", on_event)
        KERNEL.event_bus.subscribe("AgentStopped", on_event)

        
        # Inject User Message into Leader
        # We tell the leader this message comes from "User" (or our request_id if we want routing back)
        await KERNEL.actors[LEADER_NAME].inbox.put({
            "type": "TaskSubmitted",
            "from": request_id, 
            "correlation_id": correlation_id,
            "content": req.message
        })
        
        try:
            yield json.dumps({'type': 'conversation', 'conversation_id': conversation.id}, ensure_ascii=False) + '\n'
            yield json.dumps({'type': 'status', 'content': 'Thinking...'}, ensure_ascii=False) + '\n'

            while True:
                # Wait for events with a timeout
                try:
                    event = await asyncio.wait_for(response_queue.get(), timeout=60.0) # 60s timeout for demo
                except asyncio.TimeoutError:
                    yield json.dumps({'type': 'error', 'content': 'Timeout waiting for response'}, ensure_ascii=False) + '\n'
                    break

                event_type = event.get("type")
                sender = event.get("from", event.get("actor", "unknown"))
                
                if event_type == "TaskCompleted":
                    # If this is the final answer addressed to us
                    if sender == LEADER_NAME or event.get("target") == request_id:
                        content = event.get("content")
                        if content:
                             yield json.dumps({'type': 'token', 'content': content}, ensure_ascii=False) + '\n'
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
                        yield json.dumps({
                            'type': 'chatroom_send', 
                            'agent': sender, 
                            'content': content, 
                            'to': target
                        }, ensure_ascii=False) + '\n'
                        
                elif event_type == "SystemCall":
                    yield json.dumps({
                        'type': 'thought', 
                        'agent': sender, 
                        'content': f"System Call: {event.get('command')}"
                    }, ensure_ascii=False) + '\n'

                elif event_type == "ToolUse":
                     args_str = json.dumps(event.get('args', {}), ensure_ascii=False)
                     yield json.dumps({
                         'type': 'tool_use', 
                         'agent': sender, 
                         'tool': event.get('tool'),
                         'query': args_str
                     }, ensure_ascii=False) + '\n'

                elif event_type == "ArtifactCreated":
                     yield json.dumps({
                         'type': 'thought',
                         'agent': sender,
                         'content': f"📦 Created Artifact {event.get('artifact_id')}"
                     }, ensure_ascii=False) + '\n'

                elif event_type == "MemoryCompressed":
                     yield json.dumps({
                         'type': 'thought',
                         'agent': sender,
                         'content': f"🧠 Memory Compressed"
                     }, ensure_ascii=False) + '\n'

                elif event_type == "AgentSpawned":
                     yield json.dumps({
                         'type': 'thought',
                         'agent': "Kernel",
                         'content': f"✨ Spawned Agent: {event.get('actor')}"
                     }, ensure_ascii=False) + '\n'

                elif event_type == "AgentStopped":
                     yield json.dumps({
                         'type': 'thought',
                         'agent': "Kernel",
                         'content': f"💀 Stopped Agent: {event.get('actor')}"
                     }, ensure_ascii=False) + '\n'
                     
                elif event_type == "TaskFailed":
                     yield json.dumps({
                         'type': 'thought', # Display as thought to avoid breaking the chat
                         'agent': sender,
                         'content': f"❌ Error: {event.get('error')}"
                     }, ensure_ascii=False) + '\n'


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
            
            yield json.dumps({'type': 'done'}) + '\n'

        except Exception as e:
            yield json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False) + '\n'
            yield json.dumps({'type': 'done'}) + '\n'
        finally:
            # Cleanup subscription? EventBus implementation above didn't have unsubscribe. 
            # Ideally we should add unsubscribe. 
            # For now, the `on_event` closure will leak if we don't remove it.
            # Post-task: Add unsubscribe to EventBus.
            pass

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
