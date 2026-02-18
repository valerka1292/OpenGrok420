
import os


from dotenv import load_dotenv

load_dotenv()



# Agent Names
LEADER_NAME = "Grok"
COLLABORATOR_NAMES = ["Harper", "Benjamin", "Lucas"]
ALL_AGENT_NAMES = [LEADER_NAME] + COLLABORATOR_NAMES

# Prompt Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

LEADER_START_PROMPT = os.path.join(PROMPTS_DIR, "leader_start.txt")
AGENTS_START_PROMPT = os.path.join(PROMPTS_DIR, "agents_start.txt")
ALL_PROMPT = os.path.join(PROMPTS_DIR, "all.txt")
TOOLS_PROMPT = os.path.join(PROMPTS_DIR, "tools.txt")

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4-turbo-preview")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set. Please set it in your environment or .env file.")
