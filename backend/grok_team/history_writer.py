import asyncio
import logging
from typing import Any, List
from grok_team.history import SQLiteHistoryStore, StoredMessage

logger = logging.getLogger(__name__)

class HistoryWriter:
    """
    Background worker for writing to SQLite history.
    Decouples the API from database locks.
    """
    def __init__(self, store: SQLiteHistoryStore):
        self.store = store
        self.queue = None
        self.running = False
        self._task = None

    async def start(self):
        self.running = True
        self.queue = asyncio.Queue()
        self._task = asyncio.create_task(self._process_queue())
        logger.info("HistoryWriter started.")

    async def stop(self):
        self.running = False
        if self._task and self.queue:
            await self.queue.join() # Wait for pending writes
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HistoryWriter stopped.")

    async def add_message(self, conversation_id: str, message: StoredMessage):
        """Enqueue a message for writing."""
        if self.queue is None:
             logger.warning("HistoryWriter not started. Dropping message.")
             return
        await self.queue.put(("add_message", (conversation_id, message)))

    async def _process_queue(self):
        while self.running:
            try:
                item = await self.queue.get()
                op, args = item
                
                if op == "add_message":
                    conversation_id, message = args
                    try:
                        await self.store.add_message(conversation_id, message)
                    except Exception as e:
                        logger.error(f"HistoryWriter failed to write message: {e}")
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"HistoryWriter loop error: {e}")
