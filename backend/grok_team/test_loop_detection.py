import unittest
import asyncio
from grok_team.event_bus import EventBus
from grok_team.actor import Actor
from grok_team.kernel import Kernel

class MockAgent(Actor):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.interrupt_count = 0

    async def _handle_interrupt(self, message):
         if "Loop Detected" in message.get("content", ""):
             self.interrupt_count += 1

    async def handle_message(self, message):
        pass

class TestLoopDetection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus
        await self.kernel.start()

    async def asyncTearDown(self):
        await self.kernel.stop()

    async def test_loop_detection(self):
        actor = MockAgent("Looper", self.bus)
        self.kernel.register_actor(actor)
        self.kernel._spawn_actor_task(actor)

        # Simulate 3 identical tool calls
        tool_event = {
            "type": "ToolUse",
            "actor": "Looper",
            "tool": "web_search",
            "args": {"query": "foo"},
            "tool_call_id": "1"
        }

        # 1st call
        await self.bus.publish(tool_event)
        await asyncio.sleep(0.01)
        
        # 2nd call
        await self.bus.publish(tool_event)
        await asyncio.sleep(0.01)

        # 3rd call - Should trigger interrupt
        await self.bus.publish(tool_event)
        await asyncio.sleep(0.1)

        self.assertEqual(actor.interrupt_count, 1)

if __name__ == "__main__":
    unittest.main()
