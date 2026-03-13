import os, re

from crewai.tools import tool
from tavily import TavilyClient

@tool
def web_search_tool(query: str):
    """Search the web for news articles using the given query and return cleaned results with title, url, and markdown content."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not set. Cannot perform search."

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=5,
            include_raw_content=True,
        )
    except Exception as e:
        return f"Error: search request failed — {e}. Do not retry this query."

    results = response.get("results")
    if not results:
        return "No articles found for this query."

    cleaned_chunks = []

    for result in results:
        try:
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("raw_content") or result.get("content") or ""

            cleaned = re.sub(r"\n{3,}", "\n\n", content).strip()
            cleaned = re.sub(r"\\{2,}", "", cleaned)

            # Truncate to 1500 words to prevent LLM context overflow
            words = cleaned.split()
            if len(words) > 1500:
                cleaned = " ".join(words[:1500])

            cleaned_chunks.append({"title": title, "url": url, "markdown": cleaned})
        except Exception:
            continue

    if not cleaned_chunks:
        return "No valid articles found after processing."

    return cleaned_chunks