import unittest
import asyncio
from grok_team.kernel import Kernel
from grok_team.shadow_agent import CriticAgent

class TestShadowAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        await self.kernel.start()
        
    async def asyncTearDown(self):
        await self.kernel.stop()
        
    async def test_critic_agent(self):
        # 1. Spawn Critic
        await self.kernel.spawn_agent("Critic", "You are a critic", agent_cls=CriticAgent)
        
        # 2. Publish a TaskCompleted event
        event = {
            "type": "TaskCompleted",
            "from": "Worker",
            "content": "I did the job.",
            "id": "task_1"
        }
        await self.kernel.event_bus.publish(event)
        
        # 3. Wait for Critic to react (it runs in background via subscription)
        await asyncio.sleep(0.2)
        
        # 4. Check if ShadowCritique event was published
        # We can't easily check EventBus "history" unless we log it or subscribe.
        # Let's verify by subscribing a test handler.
        
        critiques = []
        async def on_critique(e):
            critiques.append(e)
            
        self.kernel.event_bus.subscribe("ShadowCritique", on_critique)
        
        # Re-publish to catch it
        await self.kernel.event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        self.assertTrue(len(critiques) > 0)
        self.assertEqual(critiques[0]["from"], "Critic")
        self.assertIn("Valid response", critiques[0]["content"])

if __name__ == "__main__":
    unittest.main()
