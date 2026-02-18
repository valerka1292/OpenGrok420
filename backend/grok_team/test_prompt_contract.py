import asyncio
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from grok_team.config import LEADER_NAME, ALL_AGENT_NAMES
from grok_team.prompts_loader import get_system_prompt
from grok_team.orchestrator import Orchestrator
import grok_team.agent as agent_module


class PromptContractTest(unittest.TestCase):
    def test_leader_prompt_contains_team_leader_contract_and_tools(self):
        prompt = get_system_prompt(LEADER_NAME, ALL_AGENT_NAMES)
        self.assertIn("you are the team leader", prompt.lower())
        self.assertIn("## Available Tools:", prompt)
        self.assertIn('"name": "chatroom_send"', prompt)
        self.assertIn('"name": "wait"', prompt)

    def test_collaborator_prompt_contains_collaboration_contract(self):
        prompt = get_system_prompt("Harper", ALL_AGENT_NAMES)
        self.assertIn("so that Grok can submit the best possible answer", prompt)
        self.assertIn("Grok is the team leader", prompt)


class WaitFormattingTest(unittest.TestCase):
    def test_wait_formats_messages_like_chat_inserts(self):
        agent_module.OPENAI_API_KEY = agent_module.OPENAI_API_KEY or "test-key"
        orchestrator = Orchestrator()
        leader = orchestrator.agents[LEADER_NAME]
        leader.mailbox.append({"from": "Harper", "content": "Done: searched sources"})

        wait_call = {
            "function": {"arguments": "{\"timeout\": 2}"},
            "id": "wait_1",
        }
        output = asyncio.run(orchestrator._handle_wait_for_leader(leader, wait_call))

        self.assertIn("Chat with Harper: From Harper:", output)
        self.assertIn("Done: searched sources", output)


if __name__ == "__main__":
    unittest.main()
