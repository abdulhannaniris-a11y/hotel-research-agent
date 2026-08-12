"""
Assembles the LangGraph workflow:

START
 -> validate_input
 -> generate_queries
 -> web_search
 -> extract_hotels
 -> verify_results
 -> rank_hotels
 -> generate_report
 -> END

If validation fails, or web search / extraction come back empty, the
graph short-circuits straight to generate_report, which produces a
friendly message instead of an empty/broken report.
"""

from langgraph.graph import StateGraph, END

from app.state import HotelResearchState
from app.nodes import (
    validate_input,
    generate_queries,
    web_research,
    extract_hotels,
    verify_results,
    rank_hotels,
    generate_report,
)


def _after_validation(state: HotelResearchState) -> str:
    return "generate_queries" if state.get("is_valid") else "generate_report"


def _after_search(state: HotelResearchState) -> str:
    return "extract_hotels" if state.get("search_results") else "generate_report"


def build_graph():
    graph = StateGraph(HotelResearchState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("generate_queries", generate_queries)
    graph.add_node("web_search", web_research)
    graph.add_node("extract_hotels", extract_hotels)
    graph.add_node("verify_results", verify_results)
    graph.add_node("rank_hotels", rank_hotels)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("validate_input")

    graph.add_conditional_edges(
        "validate_input",
        _after_validation,
        {"generate_queries": "generate_queries", "generate_report": "generate_report"},
    )
    graph.add_edge("generate_queries", "web_search")
    graph.add_conditional_edges(
        "web_search",
        _after_search,
        {"extract_hotels": "extract_hotels", "generate_report": "generate_report"},
    )
    graph.add_edge("extract_hotels", "verify_results")
    graph.add_edge("verify_results", "rank_hotels")
    graph.add_edge("rank_hotels", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


# Compiled once, reused across requests.
hotel_research_graph = build_graph()


def run_hotel_research(country: str, city: str, preferences: str = "Any", number_of_hotels: int = 5) -> dict:
    """Convenience wrapper used by the API layer."""
    initial_state: HotelResearchState = {
        "country": country,
        "city": city,
        "preferences": preferences,
        "number_of_hotels": number_of_hotels,
    }
    return hotel_research_graph.invoke(initial_state)
