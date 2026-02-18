
import aiohttp
from typing import List, Optional, Union, Dict, Any

# Tool Definitions as Dictionaries (compatible with OpenAI function calling)
# Correct format: {"type": "function", "function": {...}}

CHATROOM_SEND_FUNCTION = {
    "name": "chatroom_send",
    "description": "Send a message to other agents in your team. If another agent sends you a message while you are thinking, it will be directly inserted into your context as a function turn. If another agent sends you a message while you are making a function call, the message will be appended to the function response of the tool call that you make.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "description": "Message content to send. Can include tasks, context, or analysis results.",
                "type": "string"
            },
            "to": {
                "description": "Names of the message recipients. Pass 'All' to broadcast a message to the entire group or a specific name like 'Grok' or 'Harper'.",
                "anyOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ]
            }
        },
        "required": ["message", "to"]
    }
}

WAIT_FUNCTION = {
    "name": "wait",
    "description": "Wait for a teammate's message. Use this when you have delegated a task and need the result before proceeding.",
    "parameters": {
        "type": "object",
        "properties": {
            "timeout": {
                "default": 10,
                "description": "The maximum amount of time in seconds to wait.",
                "maximum": 120,
                "minimum": 1,
                "type": "integer"
            }
        }
    }
}


SET_CONVERSATION_TITLE_FUNCTION = {
    "name": "set_conversation_title",
    "description": "Set a concise, descriptive conversation title based on the first user message.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "description": "Short title (3-8 words, no trailing punctuation).",
                "type": "string"
            }
        },
        "required": ["title"]
    }
}

WEB_SEARCH_FUNCTION = {
    "name": "web_search",
    "description": "This action allows you to search the web. You can use search operators like site:reddit.com when needed.",
    "parameters": {
        "properties": {
          "query": {
            "description": "The search query to look up on the web.",
            "type": "string"
          },
          "num_results": {
            "default": 10,
            "description": "The number of results to return. It is optional, default 10, max is 30.",
            "maximum": 30,
            "minimum": 1,
            "type": "integer"
          }
        },
        "required": ["query"],
        "type": "object"
    }
}

ALL_TOOLS = [
    {"type": "function", "function": CHATROOM_SEND_FUNCTION},
    {"type": "function", "function": WAIT_FUNCTION},
    {"type": "function", "function": WEB_SEARCH_FUNCTION},
    {"type": "function", "function": SET_CONVERSATION_TITLE_FUNCTION}
]

# Python Implementations (for execution handling)

def chatroom_send(message: str, to: Union[str, List[str]]):
    """
    Sends a message to other agents.
    The implementation of the actual routing is handled by the Orchestrator,
    this function is primarily a placeholder for the tool call.
    """
    # In a real system, this might enqueue a message.
    # Here, we just return a confirmation that the message was 'sent'.
    # The Orchestrator will intercept the tool call and handle the logic.
    return f"Message sent to {to}: {message[:50]}..."

def wait(timeout: int = 10):
    """
    Waits for a response.
    The Orchestrator handles the actual waiting logic.
    """
    return f"Waited for {timeout} seconds."

async def execute_web_search(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Executes a web search using a local search engine (e.g., SearXNG).
    """
    url = "http://localhost:8080/search"
    # Map 'query' to 'q'. Categories default to 'general'.
    params = {
        "q": query,
        "categories": "general",
        "language": "en-US",
        "pageno": 1,
        "format": "json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                return results[:num_results]
            else:
                # Fallback or error
                raise Exception(f"Search engine returned status {resp.status}")
