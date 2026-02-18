
import json
import asyncio
from typing import Dict, List, Any, Optional
from grok_team.config import LEADER_NAME, COLLABORATOR_NAMES, ALL_AGENT_NAMES
from grok_team.agent import Agent

class Orchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {
            name: Agent(name) for name in ALL_AGENT_NAMES
        }
    
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
            
            # Log thought/content if present
            if content:
                print(f"[Orchestrator Log] {leader.name} says/thinks: {content}")

            # Priority to Tools: If tool calls exist, execute them regardless of content.
            if tool_calls:
                is_waiting = any(tc["function"]["name"] == "wait" for tc in tool_calls)
                
                # Handle immediate tools (send)
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] != "wait":
                        self._handle_tool_call(leader, tool_call)
                
                if is_waiting:
                    # Execute 'wait' logic with propagation loop and parallelism
                    wait_results = await self._process_collaboration_loop()
                    
                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "wait":
                            result_str = "\n".join(wait_results) if wait_results else "No new messages."
                            leader.add_tool_call_result(tool_call["id"], result_str, "wait")
            
            elif content:
                # Only return content as Final Answer if NO tools were called.
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

    def _handle_tool_call(self, caller: Agent, tool_call: Dict[str, Any]):
        """Execute chatroom_send/wait logic (Synchronous helper, no I/O)."""
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
                        # Inject as SYSTEM message to distinguish from User
                        self.agents[target_name].mailbox.append({
                            "from": caller.name, 
                            "content": message
                        })
                        sent_info.append(target_name)
            
            caller.add_tool_call_result(tool_call_id, f"Message sent to {', '.join(sent_info)}.", func_name)
            
        elif func_name != "wait":
            caller.add_tool_call_result(tool_call_id, f"Error: Tool {func_name} not found.", func_name)

    async def _process_collaboration_loop(self) -> List[str]:
        """
        Async propagation loop using asyncio.gather for parallel execution.
        """
        collected_responses = [] 
        
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
                    # Use SYSTEM role for teammate messages
                    agent.add_message("system", f"Message from {msg['from']}: {msg['content']}")
            
            # Run active agents in PARALLEL using asyncio.gather
            tasks = [self._run_agent_step_with_logic(agent) for agent in active_agents]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for res in results:
                    if isinstance(res, Exception):
                        print(f"Error executing agent: {res}")
                    elif res:
                        collected_responses.append(res)
        
        return collected_responses

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
                    self._handle_tool_call(agent, tool_call)
                    args = json.loads(tool_call["function"]["arguments"])
                    # If sending to Grok/All, capture as response? 
                    if "Grok" in args.get("to", []) or "All" in args.get("to", []):
                        results.append(f"Message from {agent.name}: {args.get('message')}")
                        
                elif func_name == "wait":
                    # Recursive wait -> just yield control, outer loop handles propagation
                    agent.add_tool_call_result(tool_call["id"], "Waited (Output yielded execution).", "wait")
                else:
                    self._handle_tool_call(agent, tool_call)
            
            return "\n".join(results) if results else None
        
        elif content:
            # If ONLY content, treat it as a response (e.g. answering directly)
            return f"Response from {agent.name}: {content}"
        
        return None
