import unittest
from grok_team.event_bus import EventBus


class TestEventBusUnsubscribe(unittest.IsolatedAsyncioTestCase):
    async def test_unsubscribe_topic_handler(self):
        bus = EventBus()
        calls = []

        async def handler(event):
            calls.append(event)

        bus.subscribe("Ping", handler)
        bus.unsubscribe("Ping", handler)

        await bus.publish({"type": "Ping"})
        self.assertEqual(calls, [])

    async def test_unsubscribe_global_handler(self):
        bus = EventBus()
        calls = []

        async def handler(event):
            calls.append(event)

        bus.subscribe_globally(handler)
        bus.unsubscribe_globally(handler)

        await bus.publish({"type": "Any"})
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
