import asyncio
from typing import Any, Dict, List, Callable, Awaitable
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = defaultdict(list)
        self._actor_inboxes: Dict[str, asyncio.Queue] = {}
        self._global_subscribers: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []

    def register_actor(self, actor_name: str, inbox: asyncio.Queue):
        """Registers an actor's inbox for direct message delivery."""
        self._actor_inboxes[actor_name] = inbox
        logger.info(f"Actor '{actor_name}' registered with EventBus.")

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribes a handler to a specific topic (Pub/Sub pattern)."""
        self._subscribers[topic].append(handler)

    async def publish(self, event: Dict[str, Any]):
        """
        Publishes an event.
        - If 'target' is specified in the event, routes to that actor's inbox.
        - Also distributes to all topic subscribers (e.g., logger, monitor).
        """
        topic = event.get("type", "unknown")
        target = event.get("target")

        # 1. Direct Routing (Inbox Pattern)
        if target and target in self._actor_inboxes:
             await self._actor_inboxes[target].put(event)
        elif target:
             logger.warning(f"EventBus: Target actor '{target}' not found for event {topic}.")

        # 2. Pub/Sub Routing (Observers)
        if topic in self._subscribers:
            for handler in self._subscribers[topic]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in subscriber handler for topic {topic}: {e}")

        # 3. Global/Wildcard subscribers
        for handler in self._global_subscribers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in global subscriber: {e}")

    def subscribe_globally(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """Subscribes a handler to all events."""
        self._global_subscribers.append(handler)
