import unittest
import asyncio
from grok_team.event_bus import EventBus
from grok_team.actor import Actor
from grok_team.kernel import Kernel

class MockActorWithBudget(Actor):
    def __init__(self, name, bus, budget):
        super().__init__(name, bus, start_budget=budget)
        self.processed_count = 0

    async def handle_message(self, message):
        if message.get("type") == "Work":
            # Simulate work cost
            self.budget -= 1 
            self.processed_count += 1

class TestBudgetEconomy(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus
        await self.kernel.start()

    async def asyncTearDown(self):
        await self.kernel.stop()

    async def test_budget_exhaustion(self):
        # Actor with budget 2
        actor = MockActorWithBudget("Worker", self.bus, budget=2)
        self.kernel.register_actor(actor)
        self.kernel._spawn_actor_task(actor)

        # Send 3 work items
        await actor.inbox.put({"type": "Work"})
        await actor.inbox.put({"type": "Work"})
        await actor.inbox.put({"type": "Work"})

        # Wait processing
        await asyncio.sleep(0.1)

        # Should have processed 2 items
        self.assertEqual(actor.processed_count, 2)
        self.assertEqual(actor.budget, 0)
        
        # 3rd item should trigger exhaustion event or remain pending (our implementation drops it or fails it)
        # Check logs or bus for exhaustion event
        # We can subscribe to check
        
    async def test_budget_allocation(self):
        actor = MockActorWithBudget("PoorActor", self.bus, budget=0)
        self.kernel.register_actor(actor)
        self.kernel._spawn_actor_task(actor)

        # Send work (should fail/pause)
        await actor.inbox.put({"type": "Work"})
        await asyncio.sleep(0.1)
        self.assertEqual(actor.processed_count, 0)

        # Allocate budget via Kernel/Bus
        await self.kernel._handle_system_call({
            "command": "allocate_budget", 
            "args": {"agent_name": "PoorActor", "amount": 5}
        })
        
        await asyncio.sleep(0.1)
        # Budget should be 5
        self.assertEqual(actor.budget, 5)
        
        # Resend work (since previous was dropped/failed)
        await actor.inbox.put({"type": "Work"})
        await asyncio.sleep(0.1)
        self.assertEqual(actor.processed_count, 1)

if __name__ == "__main__":
    unittest.main()
