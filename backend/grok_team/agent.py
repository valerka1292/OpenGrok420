
import os
import random
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from grok_team.config import (
    ALL_AGENT_NAMES, 
    LEADER_NAME, 
    OPENAI_API_KEY, 
    OPENAI_BASE_URL, 
    OPENAI_MODEL_NAME
)
from grok_team.prompts_loader import get_system_prompt
from grok_team.tools import ALL_TOOLS
from grok_team.actor import Actor
from grok_team.event_bus import EventBus

logger = logging.getLogger(__name__)

class Agent(Actor):
    def __init__(self, name: str, event_bus: EventBus, system_prompt: Optional[str] = None, temperature: Optional[float] = None, start_budget: int = 10):
        super().__init__(name, event_bus, start_budget)
        
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = get_system_prompt(name, ALL_AGENT_NAMES)
            
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Temperature Setting
        if temperature is not None:
             self.temperature = temperature
        elif self.name == LEADER_NAME:
            self.temperature = 0.6
        else:
            self.temperature = round(random.uniform(0.0, 1.0), 2)
            
        logger.info(f"Agent {self.name} initialized (temp={self.temperature}, budget={self.budget})")

        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.model = OPENAI_MODEL_NAME

    async def handle_message(self, message: Dict[str, Any]):
        """Event handler for the Agent logic."""
        msg_type = message.get("type")
        # Extract correlation ID for tracing
        correlation_id = message.get("correlation_id") or message.get("id")
        
        if msg_type == "TaskSubmitted":
            content = message.get("content")
            sender = message.get("from")
            # Archive user/sender message
            self.add_message("user", f"[Message from {sender}]: {content}" if sender else content)
            
            # Execute step loop (think -> tool -> think ...)
            await self._run_step_loop(sender, correlation_id)
                    
        elif msg_type == "TaskCompleted":
            # Handle reply from another agent
            sender = message.get("from")
            content = message.get("content")
            self.add_message("user", f"[Result from {sender}]: {content}")
            await self._run_step_loop(correlation_id, correlation_id) # Continue thinking with new info and answer request initiator

        elif msg_type == "SystemCallResult":
            # Handle result of spawn/kill etc
            content = message.get("content")
            tool_call_id = message.get("tool_call_id")
            # System calls might need their own correlation tracking via tool_call_id
            if tool_call_id:
                self.add_tool_call_result(tool_call_id, str(content), "system")
                await self._run_step_loop(None, correlation_id)

    async def _run_step_loop(self, initial_sender: Optional[str], correlation_id: Optional[str] = None):
        """Runs the Think -> Act -> Observe loop until final answer or stop."""
        try:
            while True:
                response = await self.step()

                # 1. If we have content, send it to sender (streaming logic replacement)
                if response.get("content") and initial_sender:
                    await self.send(initial_sender, {
                        "type": "TaskCompleted",
                        "from": self.name,
                        "correlation_id": correlation_id,
                        "content": response["content"]
                    })

                # 2. Handle Tool Calls
                tool_calls = response.get("tool_calls")
                if not tool_calls:
                    break

                logger.info(f"[{self.name}] Executing {len(tool_calls)} tools...")
                for tool_call in tool_calls:
                    should_continue = await self._execute_tool(tool_call, correlation_id)
                    if not should_continue:
                        return

        except Exception as e:
            logger.error(f"Agent {self.name} step failed: {e}")
            if initial_sender:
                await self.send(initial_sender, {
                    "type": "TaskFailed",
                    "from": self.name,
                    "correlation_id": correlation_id,
                    "error": str(e)
                })

    async def _execute_tool(self, tool_call: Dict, correlation_id: Optional[str] = None) -> bool:
        func = tool_call["function"]
        name = func["name"]
        args = json.loads(func["arguments"])
        tool_id = tool_call["id"]
        
        # Publish ToolUse event for Kernel monitoring (Loop Detection, etc.)
        await self.event_bus.publish({
            "type": "ToolUse",
            "actor": self.name, # Legacy field
            "from": self.name,
            "correlation_id": correlation_id,
            "tool": name,
            "args": args,
            "tool_call_id": tool_id
        })
        
        from grok_team.tools import execute_web_search, execute_python_run
        
        result = None
        
        try:
            if name == "chatroom_send":
                target = args.get("to")
                msg = args.get("message")
                payload = {
                    "type": "TaskSubmitted", 
                    "content": msg, 
                    "from": self.name,
                    "correlation_id": correlation_id
                }
                if isinstance(target, list):
                    for t in target:
                        await self.send(t, payload)
                else:
                    await self.send(target, payload)
                result = f"Message sent to {target}. Waiting for reply..."
                self.add_tool_call_result(tool_id, result, name)
                return False
                
            elif name == "web_search":
                res = await execute_web_search(args["query"], args.get("num_results", 10))
                result = str(res)
                
            elif name == "read_artifact":
                from grok_team.tools import read_artifact
                result = await read_artifact(args.get("artifact_id"), args.get("start", 0), args.get("length", 4000))

            elif name == "python_run":
                result = await execute_python_run(args["code"])
                
            elif name == "start_process":
                from grok_team.tools import start_process
                result = await start_process(args["command"])
            
            elif name == "read_process_logs":
                from grok_team.tools import read_process_logs
                result = await read_process_logs(args["pid"], args.get("lines", 20))
                
            elif name == "stop_process":
                from grok_team.tools import stop_process
                result = await stop_process(args["pid"])
                
            elif name in ["spawn_agent", "kill_agent", "list_agents", "allocate_budget"]:
                # System calls delegated to Kernel via Bus
                await self.event_bus.publish({
                    "type": "SystemCall",
                    "command": name,
                    "args": args,
                    "tool_call_id": tool_id,
                    "sender": self.name,
                    "from": self.name,
                    "correlation_id": correlation_id
                })
                # Result will arrive as a separate SystemCallResult event and continue loop there.
                return False

            elif name == "set_conversation_title":
                result = "Title set (mock)"

            else:
                result = f"Error: Unknown tool {name}"

        except Exception as e:
            result = f"Error executing {name}: {e}"

        if result is not None:
            self.add_tool_call_result(tool_id, result, name)
            return True

        return True
            
    def add_message(self, role: str, content: str, name: str = None):
        msg = {"role": role, "content": content}
        if name:
            msg["name"] = name
        self.messages.append(msg)
    
    def add_tool_call_result(self, tool_call_id: str, content: str, name: str):
        # Auto-archive large outputs
        if len(content) > 4000:
            from grok_team.artifact_store import GLOBAL_ARTIFACT_STORE
            artifact_id = GLOBAL_ARTIFACT_STORE.store(content)
            logger.info(f"[{self.name}] Stored large tool output as artifact {artifact_id}")
            
            # Publish event
            asyncio.create_task(self.event_bus.publish({
                "type": "ArtifactCreated",
                "actor": self.name,
                "from": self.name,
                "artifact_id": artifact_id,
                "preview": content[:200]
            }))
            
            content = f"[Large Output Stored. Artifact ID: {artifact_id}. Use `read_artifact` to view.]\nPreview:\n{content[:200]}..."

        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })


    def _safe_tail_index(self, min_tail: int) -> int:
        """Find a split index that keeps the latest messages while preserving tool-call pairs."""
        if len(self.messages) <= min_tail + 1:
            return 1

        split_idx = max(1, len(self.messages) - min_tail)
        while split_idx < len(self.messages):
            msg = self.messages[split_idx]
            prev = self.messages[split_idx - 1] if split_idx > 0 else None

            if msg.get("role") == "tool":
                split_idx += 1
                continue

            if prev and prev.get("role") == "assistant" and prev.get("tool_calls"):
                split_idx += 1
                continue

            break

        return min(split_idx, len(self.messages))

    async def compress_memory(self):
        """Compresses history and generates reflection."""
        if len(self.messages) < 15:
            return

        logger.info(f"[{self.name}] Compressing memory...")
        
        # Keep System Prompt (0) and a safe tail that doesn't split tool-call pairs
        preserve_tail = self._safe_tail_index(5)
        to_compress = self.messages[1:preserve_tail]
        keep = self.messages[preserve_tail:]
        
        if not to_compress:
            return

        # Prepare summarization prompt
        text_to_compress = json.dumps(to_compress, indent=2)
        summary_prompt = (
            "Analyze the above conversation history.\n"
            "1. Summarize the key facts and decisions derived so far.\n"
            "2. REFLECTION: What is the current plan? What have we finished? What is next?\n"
            "Output JSON: {\"summary\": \"...\", \"reflection\": \"...\"}"
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a memory manager."},
                    {"role": "user", "content": f"History:\n{text_to_compress}\n\n{summary_prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            summary = result.get("summary", "")
            reflection = result.get("reflection", "")
            
            # Reconstruct history
            new_history = [self.messages[0]] # System Prompt
            new_history.append({"role": "system", "content": f"PREVIOUS CONTEXT (Summarized):\n{summary}"})
            new_history.append({"role": "system", "content": f"REFLECTION (Current Plan):\n{reflection}"})
            new_history.extend(keep)
            
            self.messages = new_history
            logger.info(f"[{self.name}] Memory compressed. History size: {len(self.messages)}")
            
            await self.event_bus.publish({
                "type": "MemoryCompressed",
                "actor": self.name,
                "from": self.name,
                "summary": summary[:100] + "..."
            })
            
        except Exception as e:
            logger.error(f"[{self.name}] Memory compression failed: {e}")

    async def step(self, extra_system_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a step of the agent using the OpenAI API.
        """
        if self.budget <= 0:
            logger.warning(f"[{self.name}] Attempted to step with no budget.")
            return {"role": "assistant", "content": "Error: Budget exhausted."}

        # Check for context limit and compress if needed
        if len(self.messages) > 20:
             await self.compress_memory()

        self.budget -= 1
        logger.info(f"[{self.name}] Thinking... (Budget remaining: {self.budget})")
        
        if len(self.messages) > 40:
             logger.warning(f"[{self.name}] CRITICAL: Context window dangerously full ({len(self.messages)} msgs). Performance may degrade.")

        try:
            request_messages = list(self.messages)
            if extra_system_context:
                request_messages.append({"role": "system", "content": extra_system_context})

            response_obj = await self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=ALL_TOOLS,
                tool_choice="auto",
                stream=False,
                temperature=self.temperature,
                max_tokens=4096
            )
            
            message = response_obj.choices[0].message
            
            # Store response
            msg_data = {"role": "assistant"}
            if message.content:
                msg_data["content"] = message.content
            if message.tool_calls:
                msg_data["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            self.messages.append(msg_data)

            if message.content:
                logger.info(f"[{self.name}] Says: {message.content[:100]}...")

            return msg_data

        except Exception as e:
            logger.error(f"Error calling OpenAI API for agent {self.name}: {e}")
            raise e
