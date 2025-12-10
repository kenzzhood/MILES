"""
Specialist Worker: RAG Web Research

This worker uses:
1.  **Gemini** to refine the user's search query.
2.  **Tavily** to perform high-quality web searches.
3.  **Gemini** to synthesize the results into a professional report.
"""

from __future__ import annotations

import google.generativeai as genai
from tavily import TavilyClient

from .celery_app import celery_app
from .. import config


@celery_app.task(name="tasks.perform_web_research")
def perform_web_research(user_prompt: str) -> str:
    """
    Perform "Smart" Web Research.
    
    Flow:
    User Prompt -> [Gemini] -> Clean Query -> [Tavily] -> Results -> [Gemini] -> Final Report
    """

    print(f"STARTING RAG_Search: Processing '{user_prompt}'")
    
    # 1. Setup API Keys
    api_keys = getattr(config, "GEMINI_API_KEYS", None) or [config.GEMINI_API_KEY]
    current_key_index = 0
    
    def configure_gemini(index):
        key = api_keys[index]
        genai.configure(api_key=key)
        return genai.GenerativeModel(config.GEMINI_MODEL_NAME)

    model = configure_gemini(current_key_index)

    # Helper for Retry Logic
    def generate_with_retry(prompt, is_extraction=False):
        nonlocal current_key_index, model
        max_retries = len(api_keys) + 1
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                return response
            except Exception as e:
                is_rate_limit = "429" in str(e) or "ResourceExhausted" in str(e) or "QuotaExceeded" in str(e)
                if is_rate_limit:
                    print(f"RAG_Search: Rate Limit (429) on Key {current_key_index}. Rotating...")
                    if len(api_keys) > 1:
                        current_key_index = (current_key_index + 1) % len(api_keys)
                        model = configure_gemini(current_key_index)
                        continue # Retry
                raise e # Re-raise if not rate limit or no keys left
        return None

    try:
        # 2. Extract a clean search query
        extraction_prompt = f"""
        Extract a specific, effective search query from this user request.
        Return ONLY the query, nothing else.
        User Request: "{user_prompt}"
        """
        
        extraction_response = generate_with_retry(extraction_prompt, is_extraction=True)
        
        # Safety Check
        if not extraction_response or not extraction_response.parts:
            print(f"RAG_Search: Gemini blocked query extraction.")
            search_query = user_prompt
        else:
            search_query = extraction_response.text.strip()
            
        print(f"RAG_Search: Refined query to '{search_query}'")

        # 3. Perform Search with Tavily
        if config.TAVILY_API_KEY == "YOUR_TAVILY_API_KEY_HERE":
             return "Error: Please set your TAVILY_API_KEY in src/config.py"
             
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        search_result = tavily.search(query=search_query, search_depth="basic", max_results=5)
        
        results = search_result.get("results", [])
        if not results:
            return f"I couldn't find any results for '{search_query}'."

        # 4. Synthesize Report with Gemini
        context_text = "\n\n".join([
            f"Source: {res.get('title', 'Unknown')}\nURL: {res.get('url', 'Unknown')}\nContent: {res.get('content', '')}"
            for res in results
        ])

        synthesis_prompt = f"""
        You are an expert research assistant.
        Based on the following search results, write a comprehensive and well-structured answer to the user's original request.
        
        **User Request:** "{user_prompt}"
        
        **Search Results:**
        {context_text}
        
        **Instructions:**
        - Synthesize the information into a coherent report.
        - Use markdown formatting (headers, bullet points).
        - Cite sources where appropriate (e.g., "[Source Name]").
        - If the results don't fully answer the request, state what is missing.
        - Be professional and concise.
        """
        
        report_response = generate_with_retry(synthesis_prompt)
        
        if not report_response or not report_response.parts:
             final_report = "I found results but couldn't summarize them due to safety/auth errors. Links:\n" + "\n".join([f"- {r.get('url')}" for r in results])
        else:
             final_report = report_response.text.strip()
        
        print(f"FINISHED RAG_Search: Generated report ({len(final_report)} chars)")
        return final_report

    except Exception as exc:
        print(f"RAG_Search error: {exc}")
        return f"I encountered an error during research: {exc}"

