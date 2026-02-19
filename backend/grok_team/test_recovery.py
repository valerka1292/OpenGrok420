import unittest
import asyncio
import os
import shutil
from grok_team.kernel import Kernel
from grok_team.event_logger import EventLogger
from grok_team.agent import Agent

class TestRecovery(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_dir = "data/test_recovery"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
        self.logger = EventLogger(storage_dir=self.test_dir)
        
    async def asyncTearDown(self):
        if os.path.exists(self.test_dir):
           shutil.rmtree(self.test_dir)

    async def test_agent_respawn_on_recovery(self):
        # 1. Create a dummy log with a spawn event
        event = {
            "type": "SystemCall", 
            "command": "spawn_agent", 
            "args": {"name": "Phoenix", "system_prompt": "Rise", "temperature": 0.8},
            "sender": "God"
        }
        await self.logger.log_event(event)
        
        # 2. Start Kernel with this logger
        kernel = Kernel()
        kernel.event_logger = self.logger # Inject logger pointing to data
        
        # 3. Recover
        await kernel.recover_session()
        
        # 4. Verify Phoenix is alive
        self.assertIn("Phoenix", kernel.actors)
        agent = kernel.actors["Phoenix"]
        self.assertEqual(agent.temperature, 0.8)
        
        await kernel.stop()

if __name__ == "__main__":
    unittest.main()
