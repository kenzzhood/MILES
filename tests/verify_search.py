import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.workers.tasks_web_research import perform_web_research

def test_search():
    print("Testing Smart RAG Search (Gemini + Tavily)...")
    # Use a complex prompt to test query extraction and synthesis
    query = "Conduct detailed research on the technologies of holography and Gaussian Splatting. Explain the core differences."
    
    try:
        # Call the function directly (bypassing Celery)
        result = perform_web_research(query)
        print(f"\nOriginal Prompt: {query}")
        print(f"Result Report:\n{result}")
        
        if "Error" in result:
             print("\n❌ Verification Failed with Error.")
        elif len(result) > 100 and ("Holography" in result or "Gaussian" in result):
            print("\n✅ Smart Search Verification Passed: Report generated.")
        else:
            print("\n⚠️ Search returned results but might be too short or irrelevant.")
            
    except Exception as e:
        print(f"\n❌ Search Verification Failed: {e}")

if __name__ == "__main__":
    test_search()
