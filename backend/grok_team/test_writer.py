import unittest
import asyncio
from grok_team.history_writer import HistoryWriter
from grok_team.history import SQLiteHistoryStore, StoredMessage
from pathlib import Path

class MockStore:
    def __init__(self):
        self.messages = []
        
    async def add_message(self, cid, msg):
        self.messages.append((cid, msg))

class TestHistoryWriter(unittest.IsolatedAsyncioTestCase):
    async def test_writer(self):
        store = MockStore()
        writer = HistoryWriter(store)
        await writer.start()
        
        msg = StoredMessage(role="user", content="hello")
        await writer.add_message("conv1", msg)
        
        # Give it a moment
        await asyncio.sleep(0.1)
        
        self.assertEqual(len(store.messages), 1)
        self.assertEqual(store.messages[0][0], "conv1")
        
        await writer.stop()

if __name__ == "__main__":
    unittest.main()
