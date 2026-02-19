import asyncio
import logging
from typing import Dict, Any, Optional

from grok_team.event_bus import EventBus

logger = logging.getLogger(__name__)

class Actor:
    def __init__(self, name: str, event_bus: EventBus, start_budget: int = 10):
        self.name = name
        self.event_bus = event_bus
        self.inbox = asyncio.Queue()
        self.running = False
        self._current_task: Optional[asyncio.Task] = None
        self.budget = start_budget

        # Register inbox with the bus
        self.event_bus.register_actor(self.name, self.inbox)

    async def start(self):
        """Main event loop of the actor."""
        self.running = True
        logger.info(f"Actor '{self.name}' started with budget {self.budget}.")
        try:
            while self.running:
                # Wait for next message
                message = await self.inbox.get()
                
                # Check for control signals
                msg_type = message.get("type")
                
                # 1. High Priority / System Signals (bypass budget check)
                if msg_type == "InterruptSignal":
                    await self._handle_interrupt(message)
                    self.inbox.task_done()
                    continue
                elif msg_type == "PoisonPill":
                    logger.info(f"Actor '{self.name}' received PoisonPill. Stopping.")
                    break
                elif msg_type == "BudgetUpdate":
                    self.budget += int(message.get("amount", 0))
                    logger.info(f"Actor '{self.name}' received budget update. New budget: {self.budget}")
                    self.inbox.task_done()
                    # If we were paused, this continues the loop
                    continue

                # 2. Budget Check for Work Tasks
                if self.budget <= 0:
                    logger.warning(f"Actor '{self.name}' budget exhausted. Pausing task {msg_type}.")
                    # Publish exhaustion event ONLY ONCE per exhaustion state?
                    # For now we publish and then maybe put message back or holding pattern.
                    await self.event_bus.publish({
                        "type": "BudgetExhausted",
                        "actor": self.name,
                        "content": "I have run out of budget. Please allocate more.",
                        "target": "Grok" # Notify Leader
                    })
                    # Re-queue message to head? or just hold it?
                    # Queue doesn't support push-back easily. 
                    # We should probably process it but return error/status? or Wait?
                    # Better: Put it back in a secondary "pending" queue or just wait for budget update.
                    # Simple approach: Wait here until budget > 0?
                    # But we need to process BudgetUpdate messages.
                    # So we cannot block. We must re-queue this message? 
                    # Actually, if we re-queue, we busy-loop.
                    # Let's drop it or handle as "Failed due to budget".
                    # Real OS: Context Switch / Suspend.
                    # User-friendly: "I'm out of budget" response.
                    await self.send(message.get("from"), {
                        "type": "TaskFailed",
                        "error": "BudgetExhausted"
                    })
                    self.inbox.task_done()
                    continue

                # 3. Process Message
                try:
                    await self.handle_message(message)
                except Exception as e:
                    logger.error(f"Actor '{self.name}' failed to handle message {msg_type}: {e}", exc_info=True)
                    raise e 
                
                self.inbox.task_done()
        finally:
            self.running = False
            logger.info(f"Actor '{self.name}' stopped.")

    async def handle_message(self, message: Dict[str, Any]):
        """Override this method to implement actor logic."""
        pass

    async def _handle_interrupt(self, message: Dict[str, Any]):
        """Handle graceful interruption."""
        logger.info(f"Actor '{self.name}' interrupted.")
        # Logic to save state or wrap up partial work could go here.
        # For now, we just log.

    async def send(self, target: str, message: Dict[str, Any]):
        """Convenience method to send a message to another actor."""
        message["target"] = target
        message["from"] = self.name
        await self.event_bus.publish(message)

    def stop(self):
        """Signal the actor to stop gracefully."""
        self.running = False
        self.inbox.put_nowait({"type": "PoisonPill"})
