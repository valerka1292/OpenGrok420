from grok_team.actor import Actor
from grok_team.event_bus import EventBus
import logging
import json
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ShadowAgent(Actor):
    """
    A Shadow Agent observes events but does not participate in the main conversation flow directly.
    It runs in the background.
    """
    def __init__(self, name: str, event_bus: EventBus):
        super().__init__(name, event_bus, start_budget=100) # Shadow agents have high budget for monitoring
        self.observed_events = []

    async def start(self):
        # Shadow agents subscribe to specific topics or global
        # This implementation depends on the concrete class
        self.running = True
        logger.info(f"Shadow Agent '{self.name}' started.")
        try:
            while self.running:
                # Process own inbox (if any direct commands)
                if not self.inbox.empty():
                    message = await self.inbox.get()
                    await self.handle_message(message)
                    self.inbox.task_done()
                else:
                    await asyncio.sleep(0.1)
        finally:
            self.running = False

    async def handle_event(self, event: Dict[str, Any]):
        """Callback for subscribed events."""
        pass

class CriticAgent(ShadowAgent):
    """
    Observes TaskCompleted events and provides a critique.
    """
    def __init__(self, name: str, event_bus: EventBus, client=None, model="gpt-4o", **kwargs):
        super().__init__(name, event_bus)
        self.client = client # OpenAI client
        self.model = model

    async def start(self):
        # Subscribe to TaskCompleted
        self.event_bus.subscribe("TaskCompleted", self.handle_event)
        await super().start()

    async def handle_event(self, event: Dict[str, Any]):
        # Analyze the completion
        content = event.get("content", "")
        sender = event.get("from", "unknown")
        
        if not content or sender == self.name:
            return

        # Simple Critique Logic (Mocked if no client)
        critique = f"Critique of {sender}: Valid response."
        if self.client:
            # We would call LLM here.
            # For MVP, we'll just log a simulated critique to avoid token usage in tests/execution without real keys setup
            pass

        logger.info(f"[{self.name}] Generated critique for {sender}: {critique}")
        
        # Publish Critique Event
        await self.event_bus.publish({
            "type": "ShadowCritique",
            "from": self.name,
            "target_event_id": event.get("id"),
            "content": critique
        })
