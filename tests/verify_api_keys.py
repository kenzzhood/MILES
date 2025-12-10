
import google.generativeai as genai
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("."))
from src import config

print("--- API KEY DIAGNOSTICS ---")

keys = config.GEMINI_API_KEYS
if not keys:
    print("No keys found in config.GEMINI_API_KEYS")
    keys = [config.GEMINI_API_KEY]

print(f"Found {len(keys)} keys.")

for i, key in enumerate(keys):
    masked_key = key[:5] + "..." + key[-5:]
    print(f"\nTesting Key {i} ({masked_key})...")
    
    # 1. Check if key is empty or placeholder
    if "YOUR_GEMINI" in key or not key.strip():
        print(f"❌ Key {i} is invalid (Placeholder/Empty).")
        continue

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("models/gemini-flash-latest")
        response = model.generate_content("Reply with 'OK'.")
        print(f"✅ Key {i} SUCCESS. Response: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Key {i} FAILED.")
        print(f"   Error: {e}")

print("\n--- DIAGNOSTICS COMPLETE ---")

print("\n--- INTEGRATION TEST: ORCHESTRATOR ---")
try:
    from src.orchestrator.gemini_brain import GeminiOrchestrator
    print("Initializing GeminiOrchestrator...")
    brain = GeminiOrchestrator()
    print(f"Brain Keys: {brain.api_keys}")
    
    test_prompt = "hi"
    print(f"Sending prompt: '{test_prompt}'")
    plan = brain.decompose_task(test_prompt)
    
    print("\n[RESULT]")
    print(f"Response: {plan.direct_response[:100]}...")
    
    if "Rate Limit" in plan.direct_response:
        print("❌ FAILURE: Orchestrator still returning Rate Limit message.")
    else:
        print("✅ SUCCESS: Orchestrator returned a valid response.")
        
except Exception as e:
    print(f"❌ CRITICAL FAILURE in Integration Test: {e}")
    import traceback
    traceback.print_exc()

