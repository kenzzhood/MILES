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

    if config.TAVILY_API_KEY == "YOUR_TAVILY_API_KEY_HERE":
        return "Error: Please set your TAVILY_API_KEY in src/config.py"

    try:
        # 1. Configure Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)

        # 2. Extract a clean search query
        # The user might say "Conduct detailed research on X...", we just want "X".
        extraction_prompt = f"""
        Extract a specific, effective search query from this user request.
        Return ONLY the query, nothing else.
        User Request: "{user_prompt}"
        """
        extraction_response = model.generate_content(extraction_prompt)
        search_query = extraction_response.text.strip()
        print(f"RAG_Search: Refined query to '{search_query}'")

        # 3. Perform Search with Tavily
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
        # We use 'advanced' depth if available, or 'basic'. 
        # 'search_depth="advanced"' gives better results but costs 2 credits. 
        # Let's stick to basic for the free tier efficiency, or let the user decide later.
        search_result = tavily.search(query=search_query, search_depth="basic", max_results=5)
        
        results = search_result.get("results", [])
        if not results:
            return f"I couldn't find any results for '{search_query}'."

        # 4. Synthesize Report with Gemini
        # We feed the raw results back to the LLM to write the final answer.
        
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
        
        report_response = model.generate_content(synthesis_prompt)
        final_report = report_response.text.strip()
        
        print(f"FINISHED RAG_Search: Generated report ({len(final_report)} chars)")
        return final_report

    except Exception as exc:
        print(f"RAG_Search error: {exc}")
        return f"I encountered an error during research: {exc}"

