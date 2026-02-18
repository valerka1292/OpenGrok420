import os
import sys

import asyncio
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
        self._leader_pending_targets = set()

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
        await Orchestrator._handle_tool_call(self, caller, tool_call)

    async def _handle_tool_call_stream(self, caller, tool_call):
        async for ev in Orchestrator._handle_tool_call_stream(self, caller, tool_call):
            yield ev


class DelayedCollaborationOrchestrator(Orchestrator):
    def __init__(self, leader_responses):
        self.agents = {name: FakeAgent(name) for name in ALL_AGENT_NAMES}
        self._leader_responses = list(leader_responses)
        self._leader_pending_targets = set()

    async def _run_agent(self, agent, extra_system_context=None, allowed_tool_names=None):
        if agent.name == LEADER_NAME:
            response = self._leader_responses.pop(0)
        elif agent.name == "Harper":
            response = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "h1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": LEADER_NAME, "message": "Harper done"}),
                        },
                    }
                ],
            }
        elif agent.name == "Benjamin":
            await asyncio.sleep(0.05)
            response = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "b1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": LEADER_NAME, "message": "Benjamin done"}),
                        },
                    }
                ],
            }
        else:
            response = {"role": "assistant", "content": "noop"}

        msg_obj = {"role": response["role"]}
        if response.get("content"):
            msg_obj["content"] = response["content"]
        if response.get("tool_calls"):
            msg_obj["tool_calls"] = response["tool_calls"]
        agent.messages.append(msg_obj)
        return response


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


    async def test_non_leader_chatroom_send_can_reach_peer_agent(self):
        orch = ScriptedOrchestrator([])
        harper = orch.agents["Harper"]

        await orch._handle_tool_call(
            harper,
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "chatroom_send",
                    "arguments": json.dumps({"to": "Benjamin", "message": "please validate"}),
                },
            },
        )

        self.assertEqual(len(orch.agents["Benjamin"].mailbox), 1)
        self.assertEqual(orch.agents["Benjamin"].mailbox[0]["from"], "Harper")

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

    async def test_leader_wait_message_is_not_final_with_pending_agents(self):
        orch = DelayedCollaborationOrchestrator([
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "l1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": ["Harper", "Benjamin"], "message": "greet and guess"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Принято. Ожидаю ответ от Бенджамина."},
            {"role": "assistant", "content": "Готово, получил ответы от всех."},
        ])

        result = await orch.run("попроси двух агентов")
        self.assertEqual(result, "Готово, получил ответы от всех.")

    async def test_stream_leader_wait_message_is_not_final_with_pending_agents(self):
        orch = DelayedCollaborationOrchestrator([
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "l1",
                        "type": "function",
                        "function": {
                            "name": "chatroom_send",
                            "arguments": json.dumps({"to": ["Harper", "Benjamin"], "message": "greet and guess"}),
                        },
                    }
                ],
            },
            {"role": "assistant", "content": "Принято. Ожидаю ответ от Бенджамина."},
            {"role": "assistant", "content": "Готово, получил ответы от всех."},
        ])

        events = []
        async for event in orch.run_stream("попроси двух агентов", require_title_tool=False):
            events.append(event)

        token_text = "".join(e.get("content", "") for e in events if e.get("type") == "token")
        self.assertIn("Готово, получил ответы от всех.", token_text)


    async def test_leader_does_not_resend_to_same_pending_agent(self):
        orch = ScriptedOrchestrator([])
        leader = orch.agents[LEADER_NAME]

        await orch._handle_tool_call(
            leader,
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "chatroom_send",
                    "arguments": json.dumps({"to": "Benjamin", "message": "first"}),
                },
            },
        )
        await orch._handle_tool_call(
            leader,
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "chatroom_send",
                    "arguments": json.dumps({"to": "Benjamin", "message": "duplicate"}),
                },
            },
        )

        self.assertEqual(len(orch.agents["Benjamin"].mailbox), 1)

    async def test_wait_tool_noop_without_args(self):
        orch = ScriptedOrchestrator([])
        leader = orch.agents[LEADER_NAME]
        await orch._handle_tool_call(
            leader,
            {
                "id": "call_wait",
                "type": "function",
                "function": {
                    "name": "wait",
                    "arguments": "{}",
                },
            },
        )

        last = leader.messages[-1]
        self.assertEqual(last["role"], "tool")
        self.assertEqual(last["name"], "wait")
        self.assertEqual(last["content"], "")


if __name__ == "__main__":
    unittest.main()
