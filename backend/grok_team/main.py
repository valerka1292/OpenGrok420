
import sys
import os
import asyncio

# Ensure backend acts as a package root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from grok_team.orchestrator import Orchestrator

async def main():
    orchestrator = Orchestrator()
    print("Welcome to Grok Team (Async Version)! Type 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            response = await orchestrator.run(user_input)
            print(f"\nGrok Team: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
