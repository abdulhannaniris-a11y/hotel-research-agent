"""
Shared state object that flows through every node of the LangGraph.

LangGraph passes this dict-like object from node to node, and each
node returns a partial update that gets merged into it.
"""

from typing import List, Optional, TypedDict
from app.models import Hotel


class HotelResearchState(TypedDict, total=False):
    # --- input ---
    country: str
    city: str
    preferences: str
    number_of_hotels: int

    # --- validation ---
    is_valid: bool
    validation_message: Optional[str]

    # --- research ---
    search_queries: List[str]
    search_results: List[dict]  # raw {query, url, title, content} chunks

    # --- extraction / processing ---
    hotels: List[Hotel]
    verification_notes: List[str]

    # --- output ---
    comparison_table_markdown: str
    recommendation: str
    final_report: str

    # --- error handling ---
    error: Optional[str]
