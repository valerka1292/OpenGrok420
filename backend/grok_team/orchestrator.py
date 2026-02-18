
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from grok_team.config import LEADER_NAME, COLLABORATOR_NAMES, ALL_AGENT_NAMES
from grok_team.agent import Agent
from grok_team.tools import execute_web_search

class Orchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {
            name: Agent(name) for name in ALL_AGENT_NAMES
        }

    def _format_chat_message(self, sender: str, content: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"Chat with {sender}: From {sender}: [{timestamp}] {content}"
    
    async def run(self, user_input: str) -> str:
        """
        Main execution loop (Async).
        """
        leader = self.agents[LEADER_NAME]
        leader.add_message("user", user_input)
        
        max_turns = 15 
        current_turn = 0
        
        while current_turn < max_turns:
            current_turn += 1
            print(f"\n--- Turn {current_turn} ---")
            
            # Run Leader
            response = await self._run_agent(leader)
            
            content = response.get("content")
            tool_calls = response.get("tool_calls")
            
            if content:
                print(f"[Orchestrator Log] {leader.name} says/thinks: {content}")

            # Priority to Tools
            if tool_calls:
                wait_calls = [tc for tc in tool_calls if tc["function"]["name"] == "wait"]
                
                # Handle immediate tools (send/search)
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] != "wait":
                        await self._handle_tool_call(leader, tool_call)
                
                if wait_calls:
                    for wait_call in wait_calls:
                        wait_output = await self._handle_wait_for_leader(leader, wait_call)
                        leader.add_tool_call_result(wait_call["id"], wait_output, "wait")
            
            elif content:
                return content
        
        return "Error: Maximum turns reached without final answer."

    async def _run_agent(self, agent: Agent) -> Dict[str, Any]:
        """Run agent step and update history (Async)."""
        response = await agent.step()
        msg_obj = {"role": response["role"]}
        if response.get("content"):
            msg_obj["content"] = response["content"]
        if response.get("tool_calls"):
             msg_obj["tool_calls"] = response["tool_calls"]
        agent.messages.append(msg_obj)
        return response

    async def _handle_tool_call(self, caller: Agent, tool_call: Dict[str, Any]):
        """Execute tool logic (Async)."""
        func_name = tool_call["function"]["name"]
        args_str = tool_call["function"]["arguments"]
        tool_call_id = tool_call.get("id", "call_unknown")
        
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            caller.add_tool_call_result(tool_call_id, "Error: Invalid JSON.", func_name)
            return

        if func_name == "chatroom_send":
            message = args.get("message")
            recipients = args.get("to")
            if not isinstance(recipients, list): recipients = [recipients]
            
            sent_info = []
            for recipient_name in recipients:
                target_names = [n for n in ALL_AGENT_NAMES if n != caller.name] if recipient_name == "All" else [recipient_name]
                for target_name in target_names:
                    if target_name in self.agents:
                        self.agents[target_name].mailbox.append({
                            "from": caller.name, 
                            "content": message
                        })
                        sent_info.append(target_name)
            
            if not sent_info:
                caller.add_tool_call_result(tool_call_id, f"Error: No valid recipients found in {recipients}.", func_name)
            else:
                caller.add_tool_call_result(tool_call_id, f"Message sent to {', '.join(sent_info)}.", func_name)
            
        elif func_name == "web_search":
            query = args.get("query")
            num_results = args.get("num_results", 10)
            
            try:
                results = await execute_web_search(query, num_results)
                
                # Format results for the agent
                formatted_results = []
                for res in results:
                    formatted_results.append(f"Title: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n")
                
                output = "\n---\n".join(formatted_results) if formatted_results else "No results found."
                caller.add_tool_call_result(tool_call_id, output, func_name)
            except Exception as e:
                caller.add_tool_call_result(tool_call_id, f"Error performing search: {str(e)}", func_name)

        elif func_name != "wait":
            caller.add_tool_call_result(tool_call_id, f"Error: Tool {func_name} not found.", func_name)

    async def _handle_wait_for_leader(self, leader: Agent, wait_tool_call: Dict[str, Any]) -> str:
        """Runs collaboration rounds until leader receives messages or wait timeout elapses."""
        timeout_s = 10
        try:
            args = json.loads(wait_tool_call["function"].get("arguments", "{}") or "{}")
            parsed_timeout = int(args.get("timeout", 10))
            timeout_s = max(1, min(parsed_timeout, 120))
        except (ValueError, TypeError, json.JSONDecodeError):
            timeout_s = 10

        elapsed = 0
        poll_interval_s = 1

        while elapsed < timeout_s and not leader.mailbox:
            await self._process_collaboration_loop()
            if leader.mailbox:
                break
            await asyncio.sleep(poll_interval_s)
            elapsed += poll_interval_s

        incoming_messages = []
        while leader.mailbox:
            msg = leader.mailbox.pop(0)
            incoming_messages.append(self._format_chat_message(msg["from"], msg["content"]))

        if incoming_messages:
            return "\n\n".join(incoming_messages)
        return "No new messages received from the team."



    async def _process_collaboration_loop(self) -> None:
        """
        Async propagation loop using asyncio.gather for parallel execution.
        Populates mailboxes but returns nothing (Leader reads mailbox separately).
        """
        max_propagation_rounds = 5
        round_count = 0
        
        while round_count < max_propagation_rounds:
            round_count += 1
            
            active_agents = [
                agent for name, agent in self.agents.items() 
                if name != LEADER_NAME and agent.mailbox
            ]
            
            if not active_agents:
                break 
            
            # Consume messages
            for agent in active_agents:
                while agent.mailbox:
                    msg = agent.mailbox.pop(0)
                    agent.add_message("system", self._format_chat_message(msg["from"], msg["content"]))
            
            # Run active agents in PARALLEL
            tasks = [self._run_agent_step_with_logic(agent) for agent in active_agents]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        print(f"[Orchestrator Error] Agent execution failed: {res}")
        
        return None

    async def _run_agent_step_with_logic(self, agent: Agent, depth=0) -> Optional[str]:
        """
        Executes a Collaborator's step logic (Think -> Output/Tool) Asynchronously.
        """
        if depth > 2: 
            return "Error: Max recursion depth for collaborator."
            
        response = await self._run_agent(agent)
        
        content = response.get("content")
        tool_calls = response.get("tool_calls")
        
        if content:
             print(f"[Orchestrator Log] {agent.name} says/thinks: {content}")
        
        if tool_calls:
            results = []
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                
                if func_name == "chatroom_send":
                    await self._handle_tool_call(agent, tool_call)
                    # No need to return anything, message is enqueued
                elif func_name == "wait":
                    agent.add_tool_call_result(tool_call["id"], "Waited.", "wait")
                else:
                    await self._handle_tool_call(agent, tool_call)
            return None
        
        return None
