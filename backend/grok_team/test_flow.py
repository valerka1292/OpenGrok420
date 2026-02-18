
import sys
import os
import json
import asyncio

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from grok_team.orchestrator import Orchestrator

async def test_flow_async():
    print("Testing Grok Team Flow (Async)...")
    orchestrator = Orchestrator()
    
    # Updated prompt to force search tool usage
    user_input = "Search for 'latest AI news' using the web_search tool. Limit to 5 results." 
    
    print(f"User Input: {user_input}")
    try:
        final_response = await orchestrator.run(user_input)
        print(f"\nFinal Response: {final_response}")
        print("\nSUCCESS: Async Flow executed without errors.")
    except Exception as e:
        print(f"\nFAILURE: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_flow_async())
