import unittest
import asyncio
import os
import shutil
from grok_team.event_bus import EventBus
from grok_team.kernel import Kernel
from grok_team.event_logger import EventLogger

class TestEventLogger(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a temporary directory for tests
        self.test_dir = "data/test_sessions"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
        self.kernel = Kernel()
        # Override logger with one pointing to test dir
        self.kernel.event_logger = EventLogger(storage_dir=self.test_dir)
        self.bus = self.kernel.event_bus
        await self.kernel.start() # Subscribes logger

    async def asyncTearDown(self):
        await self.kernel.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    async def test_event_logging(self):
        event = {"type": "TestEvent", "content": "Hello Logger"}
        await self.bus.publish(event)
        
        # Allow async write
        await asyncio.sleep(0.1)
        
        events = self.kernel.event_logger.get_all_events()
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[-1]["type"], "TestEvent")
        self.assertEqual(events[-1]["content"], "Hello Logger")
        self.assertIn("timestamp", events[-1])

if __name__ == "__main__":
    unittest.main()
