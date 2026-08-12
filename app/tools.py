"""
Web search tool integration.

Kept deliberately separate from the LangGraph nodes so the search
provider can be swapped later (Tavily -> Bing -> SerpAPI -> etc.)
without touching the graph logic.

We use Tavily here because it is purpose-built for LLM/agent search
and has good LangChain support.
"""

import os
import logging
from typing import List, Dict

from dotenv import load_dotenv
from langchain_tavily import TavilySearch

# Load variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


def _get_search_client() -> TavilySearch:
    """Create and return the Tavily search client."""

    api_key = (
        os.getenv("SEARCH_API_KEY")
        or os.getenv("TAVILY_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. "
            "Add it to your .env file."
        )

    # TavilySearch reads TAVILY_API_KEY from the environment.
    os.environ.setdefault("TAVILY_API_KEY", api_key)

    return TavilySearch(
        max_results=5,
        topic="general"
    )


def web_search(
    query: str,
    max_results: int = 5
) -> List[Dict]:
    """
    Run a single web search query and return
    a normalized list of results.
    """

    try:
        client = _get_search_client()

        raw = client.invoke({
            "query": query
        })

        # Handle different response formats
        results = (
            raw.get("results", raw)
            if isinstance(raw, dict)
            else raw
        )

        normalized = []

        for item in results[:max_results]:
            normalized.append({
                "query": query,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            })

        return normalized

    except Exception as exc:
        logger.error(
            "Web search failed for query %r: %s",
            query,
            exc
        )

        return []


def web_search_many(
    queries: List[str],
    max_results_per_query: int = 5
) -> List[Dict]:
    """Run several queries and flatten the results."""

    all_results: List[Dict] = []

    for query in queries:
        all_results.extend(
            web_search(
                query,
                max_results=max_results_per_query
            )
        )

    return all_results