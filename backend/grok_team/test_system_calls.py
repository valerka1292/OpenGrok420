import unittest
import asyncio
from grok_team.event_bus import EventBus
from grok_team.actor import Actor
from grok_team.agent import Agent
from grok_team.kernel import Kernel

class TestSystemCalls(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus
        await self.kernel.start()

    async def asyncTearDown(self):
        await self.kernel.stop()

    async def test_spawn_agent(self):
        # Spawn via Kernel method directly first
        success, msg = await self.kernel.spawn_agent(
            name="TestAgent", 
            system_prompt="You are a test.", 
            agent_cls=Agent,
            temperature=0.9
        )
        self.assertTrue(success)
        self.assertIn("TestAgent", self.kernel.actors)
        
        agent = self.kernel.actors["TestAgent"]
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.temperature, 0.9)
        self.assertEqual(agent.system_prompt, "You are a test.")
        
        # Test duplicate spawn
        success, msg = await self.kernel.spawn_agent(
            name="TestAgent", 
            system_prompt="Dup", 
            agent_cls=Agent
        )
        self.assertFalse(success)

    async def test_spawn_via_system_call_event(self):
        # Create a manager agent to send the system call
        manager = Agent("Manager", self.bus)
        self.kernel.register_actor(manager)
        self.kernel._spawn_actor_task(manager)
        
        # Emit SystemCall
        await self.bus.publish({
            "type": "SystemCall",
            "command": "spawn_agent",
            "args": {
                "name": "DynamicAgent",
                "system_prompt": "Dynamic",
                "temperature": 0.5
            },
            "sender": "Manager",
            "tool_call_id": "call_1"
        })
        
        # Wait for persistence/action
        await asyncio.sleep(0.5) # Time for Kernel to process
        
        self.assertIn("DynamicAgent", self.kernel.actors)
        agent = self.kernel.actors["DynamicAgent"]
        self.assertEqual(agent.temperature, 0.5)

if __name__ == "__main__":
    unittest.main()
