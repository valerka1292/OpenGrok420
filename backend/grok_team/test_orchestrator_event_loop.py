import os
import sys

import json
import unittest

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from grok_team.config import ALL_AGENT_NAMES, LEADER_NAME
from grok_team.orchestrator import Orchestrator


class FakeAgent:
    def __init__(self, name: str):
        self.name = name
        self.mailbox = []
        self.messages = []
        self.temperature = 0.6

    def add_message(self, role: str, content: str, name: str = None):
        msg = {"role": role, "content": content}
        if name:
            msg["name"] = name
        self.messages.append(msg)

    def add_tool_call_result(self, tool_call_id: str, content: str, name: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })


class ScriptedOrchestrator(Orchestrator):
    def __init__(self, leader_responses):
        self.agents = {name: FakeAgent(name) for name in ALL_AGENT_NAMES}
        self._leader_responses = list(leader_responses)

    async def _run_agent(self, agent, extra_system_context=None, allowed_tool_names=None):
        if agent.name != LEADER_NAME:
            return {"role": "assistant", "content": "noop"}
        if not self._leader_responses:
            return {"role": "assistant", "content": "no scripted response"}
        response = self._leader_responses.pop(0)
        msg_obj = {"role": response["role"]}
        if response.get("content"):
            msg_obj["content"] = response["content"]
        if response.get("tool_calls"):
            msg_obj["tool_calls"] = response["tool_calls"]
        agent.messages.append(msg_obj)
        return response

    async def _handle_tool_call(self, caller, tool_call):
        func_name = tool_call["function"]["name"]
        if func_name == "chatroom_send":
            args = json.loads(tool_call["function"]["arguments"])
            target = args.get("to")
            message = args.get("message", "")
            if target in self.agents:
                self.agents[target].mailbox.append({"from": caller.name, "content": message})
        caller.add_tool_call_result(tool_call.get("id", "id"), "ok", func_name)

    async def _handle_tool_call_stream(self, caller, tool_call):
        await self._handle_tool_call(caller, tool_call)
        yield {"type": "tool_use", "agent": caller.name, "tool": tool_call["function"]["name"]}


class OrchestratorEventLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_continues_after_non_chatroom_tool_call(self):
        orch = ScriptedOrchestrator([
            {
                "role": "assistant",
                "content": "set title first",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "set_conversation_title",
                            "arguments": json.dumps({"title": "Привет"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Привет!"},
        ])

        result = await orch.run("привет")
        self.assertEqual(result, "Привет!")

    async def test_run_stream_continues_after_non_chatroom_tool_call(self):
        orch = ScriptedOrchestrator([
            {
                "role": "assistant",
                "content": "set title first",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "set_conversation_title",
                            "arguments": json.dumps({"title": "Привет"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Привет!"},
        ])

        events = []
        async for event in orch.run_stream("привет", require_title_tool=False):
            events.append(event)

        token_text = "".join(e.get("content", "") for e in events if e.get("type") == "token")
        self.assertIn("Привет!", token_text)
        self.assertEqual(events[-1]["type"], "done")

    async def test_run_resumes_when_agent_reply_arrives(self):
        orch = ScriptedOrchestrator([
            {
                "role": "assistant",
                "content": "delegating",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": "Harper", "message": "Say hi and guess a number"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Harper says hi and number 7."},
        ])

        result = await orch.run("ask one agent to greet and pick a number")
        self.assertEqual(result, "Harper says hi and number 7.")

    async def test_run_stream_resumes_when_agent_reply_arrives(self):
        orch = ScriptedOrchestrator([
            {
                "role": "assistant",
                "content": "delegating",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": "Harper", "message": "Say hi and guess a number"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Harper says hi and number 7."},
        ])

        events = []
        async for event in orch.run_stream("ask one agent to greet and pick a number", require_title_tool=False):
            events.append(event)

        token_text = "".join(e.get("content", "") for e in events if e.get("type") == "token")
        self.assertIn("Harper says hi and number 7.", token_text)
        self.assertEqual(events[-1]["type"], "done")


if __name__ == "__main__":
    unittest.main()
