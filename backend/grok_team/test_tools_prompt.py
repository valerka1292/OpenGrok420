import unittest

from grok_team.tools import generate_tools_prompt, get_tools_for_agent


class TestDynamicToolPrompt(unittest.TestCase):
    def test_non_leader_tools_exclude_system_calls(self):
        names = [tool["function"]["name"] for tool in get_tools_for_agent(is_leader=False)]
        self.assertNotIn("spawn_agent", names)
        self.assertNotIn("kill_agent", names)
        self.assertNotIn("list_agents", names)
        self.assertNotIn("allocate_budget", names)
        self.assertIn("python_run", names)

    def test_leader_prompt_mentions_tools(self):
        prompt = generate_tools_prompt(is_leader=True)
        self.assertIn('"name": "spawn_agent"', prompt)
        self.assertIn('"name": "read_artifact"', prompt)


if __name__ == "__main__":
    unittest.main()
