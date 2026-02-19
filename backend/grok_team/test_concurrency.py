import unittest
import asyncio
import time
from grok_team.agent import Agent
from grok_team.kernel import Kernel

class TestConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus
        await self.kernel.start()

    async def asyncTearDown(self):
        await self.kernel.stop()
    
    async def test_parallel_tool_execution(self):
        agent = Agent("ParallelAgent", self.bus)
        
        # We need to mock `_execute_tool` to simulate delay without actually running tools
        # or use a mock tool that sleeps.
        
        executed_times = []
        
        # Save original
        original_exec = agent._execute_tool
        
        async def mock_exec(tool_call, sender):
            start = time.time()
            await asyncio.sleep(0.5) # Simulate work
            executed_times.append(start)
            agent.add_tool_call_result(tool_call["id"], "Done", "mock_tool")

        agent._execute_tool = mock_exec
        
        # Inject tool calls into a fake step response logic or just call _run_step_loop logic directly?
        # _run_step_loop calls step() then executes tools.
        # Let's mock step() to return multiple tools.
        
        async def mock_step(ctx=None):
            return {
                "role": "assistant",
                "tool_calls": [
                    {"id": "call_1", "function": {"name": "test"}, "type": "function"},
                    {"id": "call_2", "function": {"name": "test"}, "type": "function"},
                    {"id": "call_3", "function": {"name": "test"}, "type": "function"}
                ]
            }
        
        agent.step = mock_step
        
        # Run
        start_time = time.time()
        await agent._run_step_loop(None)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # If sequential: 0.5 * 3 = 1.5s
        # If parallel: around 0.5s + overhead
        
        print(f"Parallel execution took {duration}s")
        self.assertTrue(duration < 1.0, f"Execution took {duration}s, expected < 1.0s (parallel)")
        self.assertEqual(len(agent.messages), 1 + 3) # System + 3 tool results

if __name__ == "__main__":
    unittest.main()
