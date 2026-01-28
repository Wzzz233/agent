import requests
import json
import time
import sys

# Configuration
AGENT_URL = "http://localhost:8000/api/v1/agent/chat"
CONVERSATION_ID = f"interactive_test_{int(time.time())}"

def send_message(message: str, conversation_id: str) -> dict:
    """Send a message to the agent and get response."""
    try:
        response = requests.post(
            AGENT_URL,
            json={
                "message": message,
                "conversation_id": conversation_id
            },
            timeout=120  # Longer timeout for complex reasoning
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print("\n[Error]: Cannot connect to Agent. Make sure 'python start_agent.py' is running.")
        return None
    except Exception as e:
        print(f"\n[Error]: {e}")
        return None

def main():
    print("=" * 60)
    print("Interactive Agent Debugger")
    print("=" * 60)
    print(f"Conversation ID: {CONVERSATION_ID}")
    print("Type 'exit' or 'quit' to stop.")
    print("-" * 60)

    chat_history = []

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except KeyboardInterrupt:
            print("\nExiting...")
            break
            
        if user_input.lower() in ['exit', 'quit']:
            break
            
        if not user_input:
            continue
            
        print("\n[Sending to Agent...]")
        
        # Debug history size
        print(f"[Debug] Sending history with {len(chat_history)} messages.")
        
        start_time = time.time()
        
        # Send message WITH history
        try:
            response = requests.post(
                AGENT_URL,
                json={
                    "message": user_input,
                    "conversation_id": CONVERSATION_ID,
                    "history": chat_history
                },
                timeout=120
            )
            response.raise_for_status()
            resp_data = response.json()
        except Exception as e:
            print(f"\n[Error]: {e}")
            resp_data = None
        
        duration = time.time() - start_time
        
        if resp_data:
            print(f"\n[Response Time]: {duration:.2f}s")
            
            # Extract basic info
            agent_text = resp_data.get("response", "")
            thoughts = resp_data.get("thoughts", [])
            
            # Print thoughts/observations (The ReAct trace)
            if thoughts:
                print("\n" + "="*20 + " DEBUG: THOUGHTS & TOOLS " + "="*20)
                for i, thought in enumerate(thoughts):
                    print(f"\n--- Step {i+1} ---")
                    if isinstance(thought, dict):
                        # print json dump for clarity
                        print(json.dumps(thought, indent=2, ensure_ascii=False))
                    else:
                        print(str(thought))
                print("="*65)
            
            # Print final response
            print("\n" + "="*20 + " FINAL RESPONSE " + "="*20)
            print(agent_text)
            print("="*56)
            
            if "error" in resp_data:
                print(f"[Server Error]: {resp_data['error']}")
            
            # Update history for next turn
            # 1. Add the user's message
            chat_history.append({'role': 'user', 'content': user_input})
            
            # 2. Add the observations/thoughts (which include tool results and assistant text)
            if thoughts:
                chat_history.extend(thoughts)
            else:
                # Fallback if thoughts empty (simple response)
                chat_history.append({'role': 'assistant', 'content': agent_text})

if __name__ == "__main__":
    main()
