import unittest
import asyncio
from grok_team.tools import start_process, read_process_logs, stop_process, PROCESS_REGISTRY, execute_python_run

class TestBackgroundProcess(unittest.IsolatedAsyncioTestCase):
    async def test_background_process_lifecycle(self):
        # Start a process that prints periodically
        code = "import time; print('Start'); time.sleep(0.5); print('Middle'); time.sleep(0.5); print('End')"
        cmd = f"python3 -u -c \"{code}\""
        
        res = await start_process(cmd)
        self.assertIn("PID:", res)
        pid = int(res.split("PID: ")[1])
        
        self.assertIn(pid, PROCESS_REGISTRY)
        
        # Reader needs time to pick up logs
        await asyncio.sleep(0.2)
        logs = await read_process_logs(pid)
        self.assertIn("Start", logs)
        
        await asyncio.sleep(0.6)
        logs = await read_process_logs(pid)
        self.assertIn("Middle", logs)
        
        stop_res = await stop_process(pid)
        self.assertIn("terminated", stop_res)
        
        # Check registry cleanup? We didn't implement cleanup
        # That's fine for MVP
        
    async def test_python_run_async(self):
        res = await execute_python_run("print('hello')")
        self.assertIn("hello", res)

if __name__ == "__main__":
    unittest.main()
