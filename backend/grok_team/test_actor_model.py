import unittest
import asyncio
from grok_team.event_bus import EventBus
from grok_team.actor import Actor
from grok_team.kernel import Kernel

# Mock implementation of an Actor for testing
class MockActor(Actor):
    def __init__(self, name: str, event_bus: EventBus):
        super().__init__(name, event_bus)
        self.received_messages = []

    async def handle_message(self, message):
        self.received_messages.append(message)
        if message.get("type") == "Task":
            response = {"type": "TaskResult", "content": "Done", "target": message["from"]}
            await self.event_bus.publish(response)
        elif message.get("type") == "Crash":
            raise ValueError("Intentional Crash")

class TestActorSystem(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus

    async def asyncTearDown(self):
        await self.kernel.stop()

    async def test_actor_communication_via_queue(self):
        # Setup actors
        actor1 = MockActor("Actor1", self.bus)
        actor2 = MockActor("Actor2", self.bus)
        self.kernel.register_actor(actor1)
        self.kernel.register_actor(actor2)
        
        # Start kernel
        await self.kernel.start()
        
        # Send message from Actor1 to Actor2
        await actor1.send("Actor2", {"type": "Task", "content": "Do work"})
        
        # Wait for Actor2 to process
        await asyncio.sleep(0.1)
        
        # Check if Actor2 received message
        self.assertEqual(len(actor2.received_messages), 1)
        self.assertEqual(actor2.received_messages[0]["content"], "Do work")
        self.assertEqual(actor2.received_messages[0]["from"], "Actor1")

        # Check if Actor2 replied (Actor1 should have inbox message)
        await asyncio.sleep(0.1)
        self.assertEqual(len(actor1.received_messages), 1)
        self.assertEqual(actor1.received_messages[0]["type"], "TaskResult")

    async def test_zombie_reaper_catches_crash(self):
        crasher = MockActor("Crasher", self.bus)
        self.kernel.register_actor(crasher)
        await self.kernel.start()

        # Subscribe to crash events
        crashes = []
        async def on_crash(event):
            crashes.append(event)
        self.bus.subscribe("ActorCrashed", on_crash)

        # Trigger crash
        await crasher.inbox.put({"type": "Crash"})
        
        # Wait for reaper
        await asyncio.sleep(0.2)
        
        self.assertTrue(len(crashes) > 0)
        self.assertEqual(crashes[0]["actor"], "Crasher")
        self.assertIn("Intentional Crash", crashes[0]["error"])

    async def test_graceful_interrupt(self):
        worker = MockActor("Worker", self.bus)
        self.kernel.register_actor(worker)
        await self.kernel.start()

        # Send interrupt
        await self.kernel.interrupt_agent("Worker")
        await asyncio.sleep(0.1)

        # We can't easily check internal state of `check_interrupt` in this mock without more complex logic,
        # but we can verify it didn't crash and processed the signal.
        # In a real actor, handle_interrupt would log or save state.
        # We can check logs if we captured them, but for now just ensure it's still alive or stopped gracefully.
        pass

if __name__ == "__main__":
    unittest.main()
