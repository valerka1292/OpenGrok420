import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from grok_team.agent import Agent
from grok_team.config import ALL_AGENT_NAMES, LEADER_NAME
from grok_team.tools import execute_python_run, execute_web_search


class Orchestrator:
    MAX_LEADER_TURNS = 15
    MAX_PROPAGATION_ROUNDS = 5
    MAX_COLLAB_RECURSION_DEPTH = 10
    MAX_COLLAB_TOOL_CALLS = 6
    HISTORY_PREVIEW_ITEMS = 18

    def __init__(self):
        self.agents: Dict[str, Agent] = {name: Agent(name) for name in ALL_AGENT_NAMES}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def run(self, user_input: str) -> str:
        """Main execution loop (Async)."""
        leader = self.agents[LEADER_NAME]
        leader.add_message("user", user_input)

        current_turn = 0
        while current_turn < self.MAX_LEADER_TURNS:
            current_turn += 1
            print(f"\n--- Turn {current_turn} ---")

            response = await self._run_agent(leader)
            content = response.get("content")
            tool_calls = response.get("tool_calls")

            if content:
                print(f"[Orchestrator Log] {leader.name} says/thinks: {content}")

            if tool_calls:
                is_waiting = any(tc["function"]["name"] == "wait" for tc in tool_calls)

                for tool_call in tool_calls:
                    if tool_call["function"]["name"] != "wait":
                        await self._handle_tool_call(leader, tool_call)

                if is_waiting:
                    await self._process_collaboration_loop()

                    incoming_messages = []
                    while leader.mailbox:
                        msg = leader.mailbox.pop(0)
                        incoming_messages.append(f"Message from {msg['from']}: {msg['content']}")

                    wait_output = "\n\n".join(incoming_messages) if incoming_messages else "No new messages received from the team."

                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "wait":
                            leader.add_tool_call_result(tool_call["id"], wait_output, "wait")
            elif content:
                return content

        return "Error: Maximum turns reached without final answer."

    async def run_stream(
        self,
        user_input: str,
        temperatures: Dict[str, float] = {},
        require_title_tool: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming execution loop. Yields event dicts for SSE transport."""
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

        current_turn = 0
        while current_turn < self.MAX_LEADER_TURNS:
            current_turn += 1

            response = await self._run_agent(leader)
            content = response.get("content")
            tool_calls = response.get("tool_calls")

            if content:
                yield {"type": "thought", "agent": leader.name, "content": content}

            if tool_calls:
                is_waiting = any(tc["function"]["name"] == "wait" for tc in tool_calls)

                for tool_call in tool_calls:
                    if tool_call["function"]["name"] != "wait":
                        async for ev in self._handle_tool_call_stream(leader, tool_call):
                            yield ev

                if is_waiting:
                    yield {"type": "wait", "agent": leader.name}

                    async for ev in self._process_collaboration_loop_stream():
                        yield ev

                    incoming_messages = []
                    while leader.mailbox:
                        msg = leader.mailbox.pop(0)
                        incoming_messages.append(f"Message from {msg['from']}: {msg['content']}")

                    wait_output = "\n\n".join(incoming_messages) if incoming_messages else "No new messages received from the team."

                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "wait":
                            leader.add_tool_call_result(tool_call["id"], wait_output, "wait")

            elif content:
                for i, word in enumerate(content.split(" ")):
                    yield {"type": "token", "content": word if i == 0 else f" {word}"}
                    await asyncio.sleep(0.02)
                yield {"type": "done"}
                return

        yield {"type": "token", "content": "Error: Maximum turns reached without final answer."}
        yield {"type": "done"}

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

            sent_info: List[str] = []
            seen_targets = set()
            for recipient_name in recipients:
                target_names = [n for n in ALL_AGENT_NAMES if n != caller.name] if recipient_name == "All" else [recipient_name]
                for target_name in target_names:
                    if target_name in self.agents and target_name not in seen_targets:
                        self.agents[target_name].mailbox.append({"from": caller.name, "content": message})
                        sent_info.append(target_name)
                        seen_targets.add(target_name)

            if sent_info:
                for name in sent_info:
                    yield {"type": "chatroom_send", "agent": caller.name, "to": name, "content": message[:200]}
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
            yield {"type": "tool_use", "agent": caller.name, "tool": "web_search", "query": query, "num_results": num_results}
            try:
                results = await execute_web_search(query, num_results)
                output = self._format_search_results(results)
                caller.add_tool_call_result(tool_call_id, output, func_name)
            except Exception as e:
                caller.add_tool_call_result(tool_call_id, f"Error performing search: {str(e)}", func_name)

        elif func_name == "python_run":
            code = args.get("code")
            if not isinstance(code, str) or not code.strip():
                caller.add_tool_call_result(tool_call_id, "Error: code must be a non-empty string.", func_name)
                return

            yield {"type": "tool_use", "agent": caller.name, "tool": "python_run"}
            output = await execute_python_run(code)
            caller.add_tool_call_result(tool_call_id, output, func_name)

        elif func_name != "wait":
            caller.add_tool_call_result(tool_call_id, f"Error: Tool {func_name} not found.", func_name)

    async def _process_collaboration_loop_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Parallel collaboration loop that yields SSE events."""
        round_count = 0
        while round_count < self.MAX_PROPAGATION_ROUNDS:
            round_count += 1

            active_agents = [agent for name, agent in self.agents.items() if name != LEADER_NAME and agent.mailbox]
            if not active_agents:
                break

            for agent in active_agents:
                while agent.mailbox:
                    msg = agent.mailbox.pop(0)
                    agent.add_message("system", f"Message from {msg['from']}: {msg['content']}")

            queue: asyncio.Queue = asyncio.Queue()

            async def _run_and_collect(agent: Agent):
                try:
                    async for ev in self._run_agent_step_with_logic_stream(agent):
                        await queue.put(ev)
                except Exception as e:
                    await queue.put({"type": "thought", "agent": agent.name, "content": f"Error: {e}"})

            tasks = [asyncio.create_task(_run_and_collect(a)) for a in active_agents]

            done_tasks = set()
            while len(done_tasks) < len(tasks):
                for task in tasks:
                    if task.done() and task not in done_tasks:
                        done_tasks.add(task)

                while not queue.empty():
                    yield await queue.get()

                if len(done_tasks) < len(tasks):
                    await asyncio.sleep(0.05)

            while not queue.empty():
                yield await queue.get()

    async def _run_agent_step_with_logic_stream(self, agent: Agent, depth: int = 0) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a collaborator's step and yield SSE events."""
        if depth > self.MAX_COLLAB_RECURSION_DEPTH:
            async for ev in self._handle_recursion_limit_stream(agent, depth):
                yield ev
            return

        response = await self._run_agent(agent, extra_system_context=self._build_collaborator_context(agent, depth))
        content = response.get("content")
        tool_calls = response.get("tool_calls")

        if content:
            yield {"type": "thought", "agent": agent.name, "content": content}

        if not tool_calls and content:
            self._deliver_collaborator_content_to_leader(agent, content)

        if tool_calls:
            should_continue = False
            saw_wait = False
            processed_calls = 0
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                if processed_calls >= self.MAX_COLLAB_TOOL_CALLS:
                    agent.add_tool_call_result(
                        tool_call.get("id", "call_unknown"),
                        f"Error: Tool-call budget exceeded ({self.MAX_COLLAB_TOOL_CALLS}) for this collaborator cycle.",
                        func_name,
                    )
                    continue

                processed_calls += 1
                if func_name == "wait":
                    yield {"type": "wait", "agent": agent.name}
                    agent.add_tool_call_result(tool_call["id"], "Waited.", "wait")
                    saw_wait = True
                    continue

                async for ev in self._handle_tool_call_stream(agent, tool_call):
                    yield ev

                if func_name != "chatroom_send":
                    should_continue = True

            if not saw_wait and should_continue:
                async for ev in self._run_agent_step_with_logic_stream(agent, depth + 1):
                    yield ev

    async def _run_agent(self, agent: Agent, extra_system_context: Optional[str] = None, allowed_tool_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run agent step and append response to history."""
        response = await agent.step(extra_system_context=extra_system_context, allowed_tool_names=allowed_tool_names)
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
            if not isinstance(recipients, list):
                recipients = [recipients]

            sent_info = []
            seen_targets = set()
            for recipient_name in recipients:
                target_names = [n for n in ALL_AGENT_NAMES if n != caller.name] if recipient_name == "All" else [recipient_name]
                for target_name in target_names:
                    if target_name in self.agents and target_name not in seen_targets:
                        self.agents[target_name].mailbox.append({"from": caller.name, "content": message})
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
                caller.add_tool_call_result(tool_call_id, self._format_search_results(results), func_name)
            except Exception as e:
                caller.add_tool_call_result(tool_call_id, f"Error performing search: {str(e)}", func_name)

        elif func_name == "python_run":
            code = args.get("code")
            if not isinstance(code, str) or not code.strip():
                caller.add_tool_call_result(tool_call_id, "Error: code must be a non-empty string.", func_name)
                return

            output = await execute_python_run(code)
            caller.add_tool_call_result(tool_call_id, output, func_name)

        elif func_name != "wait":
            caller.add_tool_call_result(tool_call_id, f"Error: Tool {func_name} not found.", func_name)

    async def _process_collaboration_loop(self) -> None:
        """Async propagation loop using parallel collaborator execution."""
        round_count = 0
        while round_count < self.MAX_PROPAGATION_ROUNDS:
            round_count += 1

            active_agents = [agent for name, agent in self.agents.items() if name != LEADER_NAME and agent.mailbox]
            if not active_agents:
                break

            for agent in active_agents:
                while agent.mailbox:
                    msg = agent.mailbox.pop(0)
                    agent.add_message("system", f"Message from {msg['from']}: {msg['content']}")

            tasks = [self._run_agent_step_with_logic(agent) for agent in active_agents]
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        print(f"[Orchestrator Error] Agent execution failed: {res}")

    async def _run_agent_step_with_logic(self, agent: Agent, depth: int = 0) -> Optional[str]:
        """Executes a collaborator's step logic (Think -> Tool -> follow-up)."""
        if depth > self.MAX_COLLAB_RECURSION_DEPTH:
            return await self._handle_recursion_limit(agent, depth)

        response = await self._run_agent(agent, extra_system_context=self._build_collaborator_context(agent, depth))
        content = response.get("content")
        tool_calls = response.get("tool_calls")

        if content:
            print(f"[Orchestrator Log] {agent.name} says/thinks: {content}")

        if not tool_calls and content:
            self._deliver_collaborator_content_to_leader(agent, content)

        if tool_calls:
            should_continue = False
            saw_wait = False
            processed_calls = 0
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]

                if processed_calls >= self.MAX_COLLAB_TOOL_CALLS:
                    agent.add_tool_call_result(
                        tool_call.get("id", "call_unknown"),
                        f"Error: Tool-call budget exceeded ({self.MAX_COLLAB_TOOL_CALLS}) for this collaborator cycle.",
                        func_name,
                    )
                    continue

                processed_calls += 1
                if func_name == "chatroom_send":
                    await self._handle_tool_call(agent, tool_call)
                elif func_name == "wait":
                    agent.add_tool_call_result(tool_call["id"], "Waited.", "wait")
                    saw_wait = True
                else:
                    await self._handle_tool_call(agent, tool_call)
                    should_continue = True

            if not saw_wait and should_continue:
                return await self._run_agent_step_with_logic(agent, depth + 1)
            return None

        return None

    def _deliver_collaborator_content_to_leader(self, agent: Agent, content: str) -> None:
        """Fallback delivery path when collaborator returns plain text without chatroom_send."""
        text = (content or "").strip()
        if not text:
            return
        self.agents[LEADER_NAME].mailbox.append({
            "from": agent.name,
            "content": f"[AUTO-FORWARDED COLLABORATOR RESPONSE] {text}",
        })

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        formatted_results = [
            f"Title: {res.get('title')}\nURL: {res.get('url')}\nContent: {res.get('content')}\n"
            for res in results
        ]
        return "\n---\n".join(formatted_results) if formatted_results else "No results found."

    def _build_agent_history_digest(self, agent: Agent, max_items: int) -> str:
        recent = agent.messages[-max_items:]
        if not recent:
            return "No local history."

        lines: List[str] = []
        for idx, message in enumerate(recent, start=1):
            role = message.get("role", "unknown")
            if role == "tool":
                tool_name = message.get("name", "unknown_tool")
                content = str(message.get("content", ""))
                lines.append(f"{idx}. TOOL_RESULT[{tool_name}]: {content[:300]}")
                continue

            content = str(message.get("content") or "").replace("\n", " ").strip()
            if content:
                lines.append(f"{idx}. {role.upper()}: {content[:220]}")

            tool_calls = message.get("tool_calls") or []
            for tc in tool_calls:
                fn = tc.get("function", {}).get("name", "unknown_tool")
                args = tc.get("function", {}).get("arguments", "")
                lines.append(f"{idx}. TOOL_CALL[{fn}]: {str(args)[:220]}")

        return "\n".join(lines) if lines else "No digestible history entries."

    def _build_collaborator_context(self, agent: Agent, depth: int) -> str:
        history = self._build_agent_history_digest(agent, self.HISTORY_PREVIEW_ITEMS)
        remaining_depth = max(self.MAX_COLLAB_RECURSION_DEPTH - depth, 0)
        return (
            "COLLABORATION EXECUTION POLICY:\n"
            f"- Recursion depth: {depth}/{self.MAX_COLLAB_RECURSION_DEPTH}. Remaining depth budget: {remaining_depth}.\n"
            f"- Tool-call budget in this cycle is limited to {self.MAX_COLLAB_TOOL_CALLS}.\n"
            "- You must avoid endless tool loops. Use at most one additional non-chatroom tool if strictly necessary, then report.\n"
            "- Always give LEADER a concrete deliverable via chatroom_send when you have enough evidence.\n"
            "- Your personal local history follows (messages from agents, your own tool calls/results):\n"
            f"{history}"
        )

    async def _handle_recursion_limit(self, agent: Agent, depth: int) -> str:
        history = self._build_agent_history_digest(agent, self.HISTORY_PREVIEW_ITEMS)
        instruction = (
            "RECURSION LIMIT VIOLATION DETECTED.\n"
            f"You exceeded max recursion depth ({depth}>{self.MAX_COLLAB_RECURSION_DEPTH}).\n"
            "You must now produce a FINAL answer to LEADER.\n"
            "Only tool allowed: chatroom_send. Do not call web_search/python_run/wait anymore.\n"
            "Include what is known, remaining uncertainty, and explicit closure.\n"
            "Your local execution history:\n"
            f"{history}"
        )

        response = await self._run_agent(
            agent,
            extra_system_context=instruction,
            allowed_tool_names=["chatroom_send"],
        )

        content = response.get("content")
        if content:
            print(f"[Orchestrator Log] {agent.name} says/thinks (forced-final): {content}")

        tool_calls = response.get("tool_calls") or []
        sent = False
        for tool_call in tool_calls:
            if tool_call.get("function", {}).get("name") == "chatroom_send":
                await self._handle_tool_call(agent, tool_call)
                sent = True
            else:
                agent.add_tool_call_result(
                    tool_call.get("id", "call_unknown"),
                    "Error: Recursion limit exceeded; only chatroom_send is allowed.",
                    tool_call.get("function", {}).get("name", "unknown_tool"),
                )

        if not sent:
            fallback = (
                f"[FORCED FINAL AFTER RECURSION LIMIT] Agent {agent.name} exceeded recursion depth "
                f"({depth}>{self.MAX_COLLAB_RECURSION_DEPTH}) and did not send chatroom message. "
                "Please treat this as final and proceed with available information."
            )
            self.agents[LEADER_NAME].mailbox.append({"from": agent.name, "content": fallback})

        return "Error: Max recursion depth for collaborator. Forced finalization executed."

    async def _handle_recursion_limit_stream(self, agent: Agent, depth: int) -> AsyncGenerator[Dict[str, Any], None]:
        history = self._build_agent_history_digest(agent, self.HISTORY_PREVIEW_ITEMS)
        warning = (
            f"Recursion depth exceeded ({depth}>{self.MAX_COLLAB_RECURSION_DEPTH}). "
            "Agent switched to forced finalization mode (chatroom_send only)."
        )
        yield {"type": "thought", "agent": agent.name, "content": warning}

        instruction = (
            "RECURSION LIMIT VIOLATION DETECTED.\n"
            f"You exceeded max recursion depth ({depth}>{self.MAX_COLLAB_RECURSION_DEPTH}).\n"
            "You must now produce a FINAL answer to LEADER.\n"
            "Only tool allowed: chatroom_send. Do not call web_search/python_run/wait anymore.\n"
            "Include what is known, remaining uncertainty, and explicit closure.\n"
            "Your local execution history:\n"
            f"{history}"
        )

        response = await self._run_agent(
            agent,
            extra_system_context=instruction,
            allowed_tool_names=["chatroom_send"],
        )

        if response.get("content"):
            yield {"type": "thought", "agent": agent.name, "content": response["content"]}

        tool_calls = response.get("tool_calls") or []
        sent = False
        for tool_call in tool_calls:
            if tool_call.get("function", {}).get("name") == "chatroom_send":
                sent = True
                async for ev in self._handle_tool_call_stream(agent, tool_call):
                    yield ev
            else:
                agent.add_tool_call_result(
                    tool_call.get("id", "call_unknown"),
                    "Error: Recursion limit exceeded; only chatroom_send is allowed.",
                    tool_call.get("function", {}).get("name", "unknown_tool"),
                )

        if not sent:
            fallback = (
                f"[FORCED FINAL AFTER RECURSION LIMIT] Agent {agent.name} exceeded recursion depth "
                f"({depth}>{self.MAX_COLLAB_RECURSION_DEPTH}) and did not send chatroom message. "
                "Please treat this as final and proceed with available information."
            )
            self.agents[LEADER_NAME].mailbox.append({"from": agent.name, "content": fallback})
            yield {"type": "thought", "agent": agent.name, "content": fallback}
