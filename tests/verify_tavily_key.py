import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config
from tavily import TavilyClient

def test_tavily():
    print(f"Testing Tavily Key: {config.TAVILY_API_KEY[:10]}...")
    try:
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        response = tavily.search(query="test", search_depth="basic", max_results=1)
        print("Success! Tavily returned results.")
        print(response)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_tavily()
