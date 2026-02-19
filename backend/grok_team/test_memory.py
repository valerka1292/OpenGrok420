import unittest
import asyncio
from grok_team.agent import Agent
from grok_team.kernel import Kernel
from grok_team.artifact_store import GLOBAL_ARTIFACT_STORE

class TestMemoryAndArtifacts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.kernel = Kernel()
        self.bus = self.kernel.event_bus
        await self.kernel.start()

    async def asyncTearDown(self):
        await self.kernel.stop()

    async def test_large_output_archival(self):
        agent = Agent("Archivist", self.bus)
        
        # Simulate large tool output
        large_content = "A" * 5000
        agent.add_tool_call_result("call_1", large_content, "dummy_tool")
        
        last_msg = agent.messages[-1]
        self.assertIn("[Large Output Stored", last_msg["content"])
        self.assertTrue(len(last_msg["content"]) < 1000) # Should be truncated
        
        # Verify store
        # Extract ID (simple check, or we can check store directly)
        # We assume 1 item in store for this test run
        self.assertEqual(len(GLOBAL_ARTIFACT_STORE._store), 1)
        
    async def test_read_artifact_tool(self):
        # Store something
        art_id = GLOBAL_ARTIFACT_STORE.store("Hello World")
        
        # Use tool via Agent execute (or tool func directly)
        from grok_team.tools import read_artifact
        result = await read_artifact(art_id)
        self.assertIn("Hello World", result)

    async def test_memory_compression_trigger(self):
        # Mock OpenAI? Or just check logic trigger?
        # Since we don't want to call real OpenAI, we might mock `client`.
        # For now, let's just check if `compress_memory` is called (using a flag or mock).
        agent = Agent("Compressor", self.bus)
        
        # Add 25 messages
        for i in range(25):
            agent.add_message("user", f"Msg {i}")
            
        # We need to mock compress_memory or step's internal call
        original_compress = agent.compress_memory
        called = False
        async def mock_compress():
            nonlocal called
            called = True
        
        agent.compress_memory = mock_compress
        
        # Trigger step (which checks memory)
        # We need budget
        agent.budget = 5
        
        # Mock client so step doesn't crash on OpenAI call
        # Or simple: just see if it calls compress BEFORE client call?
        # step() logic: check len -> compress -> cost -> openai
        # So if we mock openai client to fail, we should still see compress called?
        # Or mock client.chat.completions.create
        
        class MockClient:
            class chat:
                class completions:
                    async def create(*args, **kwargs):
                        return type('obj', (object,), {
                            'choices': [type('choice', (object,), {
                                'message': type('msg', (object,), {
                                    'content': 'Response',
                                    'tool_calls': None
                                })()
                            })()]
                        })()
        
        agent.client = MockClient()
        
        await agent.step()
        self.assertTrue(called)

if __name__ == "__main__":
    unittest.main()
