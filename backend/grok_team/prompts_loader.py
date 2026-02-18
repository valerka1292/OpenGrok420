
import os
from typing import List
from grok_team.config import LEADER_START_PROMPT, AGENTS_START_PROMPT, ALL_PROMPT, LEADER_NAME

def load_file(filepath):
    """Loads content from a text file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def get_system_prompt(agent_name: str, all_agent_names: List[str]) -> str:
    """
    Assembles the system prompt for a specific agent using dynamic placeholders.
    """
    # 1. Determine Prompt Components
    if agent_name == LEADER_NAME:
        header_template = load_file(LEADER_START_PROMPT)
    else:
        header_template = load_file(AGENTS_START_PROMPT)
    
    core_body = load_file(ALL_PROMPT)
    
    # 2. Dynamic Replacement Logic
    
    # Identify collaborators for this agent
    collaborators = [name for name in all_agent_names if name != agent_name]
    
    # Create a string for collaborators, e.g. "Harper, Benjamin, and Lucas"
    if collaborators:
        if len(collaborators) > 1:
            collab_str = ", ".join(collaborators[:-1]) + ", and " + collaborators[-1]
        else:
            collab_str = collaborators[0]
    else:
        collab_str = "no one"

    if agent_name == LEADER_NAME:
        # Leader Prompt Template: "You are [LEADER]... collaborating with {{COLLABORATORS}}."
        header = header_template.replace("[LEADER]", agent_name)
        header = header.replace("{{COLLABORATORS}}", collab_str)
        # Fallback for old templates just in case
        header = header.replace("[AGENT1], [AGENT2], [AGENT3]", collab_str) 
        
    else:
        # Agent Prompt: "You are [AGENT]... collaborating with [LEADER]... {{COLLABORATORS}}."
        # Here {{COLLABORATORS}} refers to peers (excluding leader)
        
        peers = [c for c in collaborators if c != LEADER_NAME]
        
        if peers:
             if len(peers) > 1:
                peers_str = ", ".join(peers[:-1]) + ", and " + peers[-1]
             else:
                peers_str = peers[0]
        else:
            peers_str = ""
            
        header = header_template.replace("[AGENT]", agent_name)
        header = header.replace("[LEADER]", LEADER_NAME)
        header = header.replace("{{COLLABORATORS}}", peers_str)
        # Fallback
        header = header.replace("[AGENT2], [AGENT3]", peers_str)
    
    # 3. Concatenate
    full_prompt = f"{header}\n\n{core_body}"
    
    return full_prompt
