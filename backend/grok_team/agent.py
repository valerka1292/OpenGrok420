
import os
import random
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

class Agent:
    def __init__(self, name: str):
        self.name = name
        self.system_prompt = get_system_prompt(name, ALL_AGENT_NAMES)
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.mailbox = []  # Queue for incoming messages from other agents

        # Temperature Setting
        if self.name == LEADER_NAME:
            self.temperature = 0.6  # Slightly higher for creative delegation
        else:
            self.temperature = round(random.uniform(0.0, 1.0), 2) # Random (0-1) for creativity
            
        print(f"[System] Agent {self.name} initialized with temperature: {self.temperature}")

        # Initialize OpenAI Client asynchronously
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.model = OPENAI_MODEL_NAME

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
            "content": content
        })

    async def step(
        self,
        extra_system_context: Optional[str] = None,
        allowed_tool_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a step of the agent using the OpenAI API with Streaming (Async).
        Returns the response message (either text or tool call).
        """
        print(f"\n[{self.name}] Thinking (temp={self.temperature})...")

        try:
            request_messages = list(self.messages)
            if extra_system_context:
                request_messages.append({"role": "system", "content": extra_system_context})

            tools = ALL_TOOLS
            if allowed_tool_names is not None:
                allowed = set(allowed_tool_names)
                tools = [tool for tool in ALL_TOOLS if tool.get("function", {}).get("name") in allowed]

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=request_messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
                temperature=self.temperature,
                max_tokens=4096
            )
            
            accumulated_content = ""
            current_tool_calls = {}
            
            print(f"[{self.name} Output]: ", end="", flush=True)

            async for chunk in stream:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Handle Reasoning Content
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                     print(reasoning, end="", flush=True)
                
                if delta.content:
                    print(delta.content, end="", flush=True)
                    accumulated_content += delta.content
                
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {"name": "", "arguments": ""}
                            }
                        
                        if tc.id:
                            current_tool_calls[idx]["id"] = tc.id
                        if tc.type:
                            current_tool_calls[idx]["type"] = tc.type
                        if tc.function:
                            if tc.function.name:
                                current_tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                current_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            print()
            
            response = {
                "role": "assistant",
                "content": accumulated_content if accumulated_content else None,
            }
            
            if current_tool_calls:
                response["tool_calls"] = []
                for idx in sorted(current_tool_calls.keys()):
                    response["tool_calls"].append(current_tool_calls[idx])
            
            return response

        except Exception as e:
            print(f"\nError calling OpenAI API for agent {self.name}: {e}")
            return {
                "role": "assistant",
                "content": f"I encountered an error while thinking: {str(e)}"
            }
