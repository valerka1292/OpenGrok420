

import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from grok_team.config import LEADER_NAME, COLLABORATOR_NAMES, ALL_AGENT_NAMES
from grok_team.agent import Agent
from grok_team.tools import execute_web_search

class Orchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {
            name: Agent(name) for name in ALL_AGENT_NAMES
        }
        self._event_queue: asyncio.Queue = asyncio.Queue()
    
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
                is_waiting = any(tc["function"]["name"] == "wait" for tc in tool_calls)
                
                # Handle immediate tools (send/search)
                for tool_call in tool_calls:
                    if tool_call["function"]["name"] != "wait":
                        await self._handle_tool_call(leader, tool_call)
                
                if is_waiting:
                    # Execute 'wait' logic: Run collaborators
                    await self._process_collaboration_loop()
                    
                    # Read Leader Mailbox
                    incoming_messages = []
                    while leader.mailbox:
                        msg = leader.mailbox.pop(0)
                        incoming_messages.append(f"Message from {msg['from']}: {msg['content']}")
                    
                    if incoming_messages:
                        wait_output = "\n\n".join(incoming_messages)
                    else:
                        wait_output = "No new messages received from the team."

                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "wait":
                            leader.add_tool_call_result(tool_call["id"], wait_output, "wait")
            
            elif content:
                return content
        
        return "Error: Maximum turns reached without final answer."

    # ──────────────────────────────────────────────
    # Streaming variant  (yields SSE event dicts)
    # ──────────────────────────────────────────────

    async def run_stream(self, user_input: str, temperatures: Dict[str, float] = {}, require_title_tool: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming execution loop. Yields event dicts for the SSE transport.
        Event types: status, thought, tool_use, chatroom_send, wait, token, done.
        """
        # Update temperature for specific agents if provided
        for name, temp in temperatures.items():
            if name in self.agents:
                self.agents[name].temperature = temp
                print(f"[Orchestrator] Set {name} temperature to {temp}")
        
        leader = self.agents[LEADER_NAME]
        if require_title_tool:
            leader.add_message(
                "system",
                "Before solving the task, call set_conversation_title exactly once with a concise Russian title for this dialog.",
            )
        leader.add_message("user", user_input)

        yield {"type": "status", "content": "Agents thinking..."}

        max_turns = 15
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1

            # Run Leader
            response = await self._run_agent(leader)
            content = response.get("content")
            tool_calls = response.get("tool_calls")

            if content:
                yield {"type": "thought", "agent": leader.name, "content": content}

            if tool_calls:
                is_waiting = any(tc["function"]["name"] == "wait" for tc in tool_calls)

                # Handle immediate tools (send/search) with events
                for tool_call in tool_calls:
                    fn = tool_call["function"]["name"]
                    if fn != "wait":
                        async for ev in self._handle_tool_call_stream(leader, tool_call):
                            yield ev

                if is_waiting:
                    # Yield wait event for the leader
                    yield {"type": "wait", "agent": leader.name}

                    # Run collaborators & collect their events
                    async for ev in self._process_collaboration_loop_stream():
                        yield ev

                    # Read Leader Mailbox
                    incoming_messages = []
                    while leader.mailbox:
                        msg = leader.mailbox.pop(0)
                        incoming_messages.append(f"Message from {msg['from']}: {msg['content']}")

                    wait_output = "\n\n".join(incoming_messages) if incoming_messages else "No new messages received from the team."

                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "wait":
                            leader.add_tool_call_result(tool_call["id"], wait_output, "wait")

            elif content:
                # Final answer — stream it token-by-token (word-level)
                words = content.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else " " + word
                    yield {"type": "token", "content": token}
                    await asyncio.sleep(0.02)  # Small delay for typing effect
                yield {"type": "done"}
                return

        yield {"type": "token", "content": "Error: Maximum turns reached without final answer."}
        yield {"type": "done"}

    # ── Streaming tool-call handler ──

    async def _handle_tool_call_stream(self, caller: Agent, tool_call: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute tool and yield corresponding SSE events."""
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
            if not isinstance(message, str) or not message.strip():
                caller.add_tool_call_result(tool_call_id, "Error: message must be a non-empty string.", func_name)
                return
            if not isinstance(recipients, list):
                recipients = [recipients]

            sent_info = []
            seen_targets = set()
            for recipient_name in recipients:
                target_names = (
                    [n for n in ALL_AGENT_NAMES if n != caller.name]
                    if recipient_name == "All"
                    else [recipient_name]
                )
                for target_name in target_names:
                    if target_name in self.agents and target_name not in seen_targets:
                        self.agents[target_name].mailbox.append({
                            "from": caller.name,
                            "content": message,
                        })
                        sent_info.append(target_name)
                        seen_targets.add(target_name)

            if sent_info:
                # Yield chatroom_send event for each recipient
                for name in sent_info:
                    yield {
                        "type": "chatroom_send",
                        "agent": caller.name,
                        "to": name,
                        "content": message[:200],
                    }
                caller.add_tool_call_result(tool_call_id, f"Message sent to {', '.join(sent_info)}.", func_name)
            else:
                caller.add_tool_call_result(tool_call_id, f"Error: No valid recipients found in {recipients}.", func_name)

        elif func_name == "set_conversation_title":
            title = str(args.get("title", "")).strip()
            if not title:
                caller.add_tool_call_result(tool_call_id, "Error: title must be non-empty.", func_name)
                return
            safe_title = title[:120]
            yield {"type": "conversation_title", "title": safe_title}
            caller.add_tool_call_result(tool_call_id, f"Conversation title set: {safe_title}", func_name)

        elif func_name == "web_search":
            query = args.get("query")
            num_results = args.get("num_results", 10)

            yield {
                "type": "tool_use",
                "agent": caller.name,
                "tool": "web_search",
                "query": query,
                "num_results": num_results,
            }

            try:
                results = await execute_web_search(query, num_results)
                formatted_results = []
                for res in results:
                    formatted_results.append(
                        f"Title: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n"
                    )
                output = "\n---\n".join(formatted_results) if formatted_results else "No results found."
                caller.add_tool_call_result(tool_call_id, output, func_name)
            except Exception as e:
                caller.add_tool_call_result(tool_call_id, f"Error performing search: {str(e)}", func_name)

        elif func_name != "wait":
            caller.add_tool_call_result(tool_call_id, f"Error: Tool {func_name} not found.", func_name)

    # ── Streaming collaboration loop ──

    async def _process_collaboration_loop_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Parallel collaboration loop that yields SSE events.
        Agents run in parallel via asyncio.gather; their events are collected through a queue.
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
                    agent.add_message("system", f"Message from {msg['from']}: {msg['content']}")

            # Collect events from parallel execution via queue
            queue: asyncio.Queue = asyncio.Queue()

            async def _run_and_collect(agent: Agent):
                try:
                    async for ev in self._run_agent_step_with_logic_stream(agent):
                        await queue.put(ev)
                except Exception as e:
                    await queue.put({"type": "thought", "agent": agent.name, "content": f"Error: {e}"})

            tasks = [asyncio.create_task(_run_and_collect(a)) for a in active_agents]

            # Drain queue while tasks are running
            done_tasks = set()
            while len(done_tasks) < len(tasks):
                # Check for completed tasks
                for t in tasks:
                    if t.done() and t not in done_tasks:
                        done_tasks.add(t)

                # Drain everything available
                while not queue.empty():
                    yield await queue.get()

                if len(done_tasks) < len(tasks):
                    await asyncio.sleep(0.05)

            # Final drain
            while not queue.empty():
                yield await queue.get()

    async def _run_agent_step_with_logic_stream(self, agent: Agent, depth=0) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a collaborator's step and yield SSE events.
        """
        if depth > 2:
            yield {"type": "thought", "agent": agent.name, "content": "Max recursion depth reached."}
            return

        response = await self._run_agent(agent)
        content = response.get("content")
        tool_calls = response.get("tool_calls")

        if content:
            yield {"type": "thought", "agent": agent.name, "content": content}

        if tool_calls:
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                if func_name == "chatroom_send":
                    async for ev in self._handle_tool_call_stream(agent, tool_call):
                        yield ev
                elif func_name == "wait":
                    yield {"type": "wait", "agent": agent.name}
                    agent.add_tool_call_result(tool_call["id"], "Waited.", "wait")
                else:
                    async for ev in self._handle_tool_call_stream(agent, tool_call):
                        yield ev

    # ── Original (non-streaming) helpers ──

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
            if not isinstance(message, str) or not message.strip():
                caller.add_tool_call_result(tool_call_id, "Error: message must be a non-empty string.", func_name)
                return
            if not isinstance(recipients, list): recipients = [recipients]

            sent_info = []
            seen_targets = set()
            for recipient_name in recipients:
                target_names = [n for n in ALL_AGENT_NAMES if n != caller.name] if recipient_name == "All" else [recipient_name]
                for target_name in target_names:
                    if target_name in self.agents and target_name not in seen_targets:
                        # Inject as SYSTEM message
                        self.agents[target_name].mailbox.append({
                            "from": caller.name, 
                            "content": message
                        })
                        sent_info.append(target_name)
                        seen_targets.add(target_name)
            
            if not sent_info:
                caller.add_tool_call_result(tool_call_id, f"Error: No valid recipients found in {recipients}.", func_name)
            else:
                caller.add_tool_call_result(tool_call_id, f"Message sent to {', '.join(sent_info)}.", func_name)
            
        elif func_name == "set_conversation_title":
            title = str(args.get("title", "")).strip()
            if not title:
                caller.add_tool_call_result(tool_call_id, "Error: title must be non-empty.", func_name)
                return
            caller.add_tool_call_result(tool_call_id, f"Conversation title set: {title[:120]}", func_name)

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
                    agent.add_message("system", f"Message from {msg['from']}: {msg['content']}")
            
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
