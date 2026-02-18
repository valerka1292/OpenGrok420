
from typing import List, Optional, Union

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

ALL_TOOLS = [
    {"type": "function", "function": CHATROOM_SEND_FUNCTION},
    {"type": "function", "function": WAIT_FUNCTION}
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
