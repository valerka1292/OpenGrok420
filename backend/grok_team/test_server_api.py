import unittest
import asyncio
import json
from grok_team.server import app, KERNEL
from fastapi.testclient import TestClient

# We need to mock Key Kernel components because they are global in server.py
# Or we can just run the test against the imported app if Kernel is initialized.
# KERNEL is global in server.py. 
# We should clear it before tests.

class TestServerAPI(unittest.TestCase):
    def setUp(self):
        # Reset Kernel states
        KERNEL.actors.clear()
        KERNEL.event_bus._subscribers.clear()
        KERNEL.event_bus._actor_inboxes.clear()
        
    def test_health(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})
        
    def test_events_endpoint(self):
        with TestClient(app) as client:
            # Log a fake event
            asyncio.run(KERNEL.event_logger.log_event({"type": "TestEvent", "content": "hello"}))
            
            response = client.get("/api/events")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("events", data)
            self.assertTrue(len(data["events"]) > 0)
        
    def test_chat_endpoint_structure(self):
        with TestClient(app) as client:
            # Basic check that the endpoint exists and accepts POST
            response = client.post("/api/chat", json={"message": "hello"})
            # It yields a stream, so status code should be 200
            self.assertEqual(response.status_code, 200)

    
if __name__ == "__main__":
    unittest.main()
