"""
LangGraph nodes for the Hotel Research Agent.

Architecture:
Tavily -> Web Search
Groq -> Hotel Extraction ONLY

The other steps are deterministic so we don't waste Groq API quota.
"""

import json
import logging
import os
from typing import Dict, List

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# Allow LLM_API_KEY as an alias for GROQ_API_KEY
if os.getenv("LLM_API_KEY") and not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = os.getenv("LLM_API_KEY")

from app.state import HotelResearchState
from app.models import HotelList
from app.tools import web_search_many
from app.prompts import HOTEL_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# ================================================================
# LLM
# ================================================================

def _get_llm():
    """
    Use a smaller/faster Groq model.

    IMPORTANT:
    We only call this once per research request.
    """

    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
    )


# ================================================================
# FORMAT SEARCH RESULTS
# ================================================================

def _format_results_for_prompt(
    results: List[Dict],
    limit: int = 10,
    content_limit: int = 600,
) -> str:
    """
    Keep the search data small enough for Groq.
    """

    lines = []

    for r in results[:limit]:

        title = str(r.get("title", "")).strip()
        url = str(r.get("url", "")).strip()
        content = str(r.get("content", "")).strip()

        lines.append(
            f"TITLE: {title}\n"
            f"URL: {url}\n"
            f"CONTENT: {content[:content_limit]}"
        )

    if not lines:
        return "(no search results)"

    return "\n\n".join(lines)


# ================================================================
# NODE 1 — VALIDATE INPUT
# ================================================================

def validate_input(state: HotelResearchState) -> Dict:
    """
    Validate country, city and number of hotels.
    """

    country = (state.get("country") or "").strip()
    city = (state.get("city") or "").strip()

    number_of_hotels = state.get("number_of_hotels") or 5

    if not country or not city:

        return {
            "is_valid": False,
            "validation_message": (
                "Please provide both a country and a city."
            ),
        }

    try:
        number_of_hotels = int(number_of_hotels)
    except (TypeError, ValueError):
        number_of_hotels = 5

    if not 1 <= number_of_hotels <= 10:
        number_of_hotels = 5

    preferences = (
        state.get("preferences")
        or "Any"
    )

    return {
        "is_valid": True,
        "validation_message": None,
        "country": country,
        "city": city,
        "preferences": preferences,
        "number_of_hotels": number_of_hotels,
        "error": None,
    }


# ================================================================
# NODE 2 — GENERATE SEARCH QUERIES
# ================================================================

def generate_queries(state: HotelResearchState) -> Dict:
    """
    Generate deterministic search queries.

    We intentionally DO NOT call Groq here.
    """

    city = state["city"]
    country = state["country"]

    preference = (
        state.get("preferences")
        or "Any"
    )

    queries = [
        f"best hotels in {city} {country}",
        f"top rated hotels in {city} {country}",
        f"hotels in {city} {country} official website",
    ]

    if preference.lower() != "any":
        queries.append(
            f"{preference} hotels in {city} {country}"
        )

    # Maximum 4 searches to reduce Tavily + processing load.
    queries = queries[:4]

    logger.info(
        "Search queries for %s, %s: %s",
        city,
        country,
        queries,
    )

    return {
        "search_queries": queries
    }


# ================================================================
# NODE 3 — WEB RESEARCH
# ================================================================

def web_research(state: HotelResearchState) -> Dict:
    """
    Search Tavily.
    """

    queries = state.get("search_queries") or []

    if not queries:

        return {
            "search_results": [],
            "error": "No search queries were generated.",
        }

    try:

        results = web_search_many(
            queries,
            max_results_per_query=4,
        )

    except Exception as exc:

        logger.error(
            "Web research failed: %s",
            exc,
        )

        return {
            "search_results": [],
            "error": (
                "Web search failed. "
                "Please check your Tavily API key."
            ),
        }

    if not results:

        return {
            "search_results": [],
            "error": (
                "Web search returned no results. "
                "Please check your TAVILY_API_KEY."
            ),
        }

    # ------------------------------------------------------------
    # Remove duplicate URLs
    # ------------------------------------------------------------

    unique_results = []
    seen_urls = set()

    for result in results:

        url = str(
            result.get("url", "")
        ).strip()

        if url:

            if url in seen_urls:
                continue

            seen_urls.add(url)

        unique_results.append(result)

    logger.info(
        "Web research completed: %d unique results found.",
        len(unique_results),
    )

    return {
        "search_results": unique_results,
        "error": None,
    }


# ================================================================
# NODE 4 — HOTEL EXTRACTION
# ================================================================

def extract_hotels(state: HotelResearchState) -> Dict:
    """
    Extract hotels from Tavily results.

    THIS IS THE ONLY GROQ CALL IN THE WHOLE WORKFLOW.
    """

    results = state.get("search_results") or []

    if not results:

        return {
            "hotels": [],
            "error": (
                "No web search results were available."
            ),
        }

    number_of_hotels = state.get(
        "number_of_hotels",
        5,
    )

    # ------------------------------------------------------------
    # Keep prompt small
    # ------------------------------------------------------------

    search_text = _format_results_for_prompt(
        results,
        limit=10,
        content_limit=600,
    )

    prompt = HOTEL_EXTRACTION_PROMPT.format(
        country=state["country"],
        city=state["city"],
        preferences=state.get(
            "preferences",
            "Any",
        ),
        number_of_hotels=number_of_hotels,
        search_results_text=search_text,
    )

    try:

        llm = _get_llm().with_structured_output(
            HotelList
        )

        parsed: HotelList = llm.invoke(prompt)

        hotels = parsed.hotels

        # --------------------------------------------------------
        # Make sure we don't return more than requested
        # --------------------------------------------------------

        hotels = hotels[:number_of_hotels]

        logger.info(
            "Hotel extraction completed: %d hotels.",
            len(hotels),
        )

        return {
            "hotels": hotels,
            "error": None,
        }

    except Exception as exc:

        logger.error(
            "Hotel extraction failed: %s",
            exc,
        )

        return {
            "hotels": [],
            "error": (
                "Hotel extraction failed. "
                "Groq may have reached its token limit. "
                "Please wait a little and try again."
            ),
        }


# ================================================================
# NODE 5 — VERIFICATION
# ================================================================

def verify_results(state: HotelResearchState) -> Dict:
    """
    Deterministic verification.

    NO GROQ CALL.
    """

    hotels = state.get("hotels") or []

    if not hotels:

        return {
            "hotels": [],
            "verification_notes": [
                "No hotels were available for verification."
            ],
        }

    verified = []

    for hotel in hotels:

        # Basic sanity check.
        if not hotel.name:
            continue

        verified.append(hotel)

    logger.info(
        "Verification completed: %d hotels kept.",
        len(verified),
    )

    return {
        "hotels": verified,
        "verification_notes": [
            "Basic deterministic verification completed."
        ],
    }


# ================================================================
# NODE 6 — RANK HOTELS
# ================================================================

def rank_hotels(state: HotelResearchState) -> Dict:
    """
    Deterministic ranking.

    NO GROQ CALL.
    """

    hotels = state.get("hotels") or []

    if not hotels:

        return {
            "hotels": []
        }

    preference = (
        state.get("preferences")
        or "Any"
    ).lower()

    number_of_hotels = state.get(
        "number_of_hotels",
        5,
    )

    # ------------------------------------------------------------
    # Simple preference-based scoring
    # ------------------------------------------------------------

    def hotel_score(hotel):

        score = 0

        best_for = str(
            hotel.best_for or ""
        ).lower()

        description = str(
            hotel.description or ""
        ).lower()

        combined = (
            best_for
            + " "
            + description
        )

        if preference != "any":

            if preference in combined:
                score += 10

            if preference == "luxury":
                if any(
                    word in combined
                    for word in [
                        "luxury",
                        "luxurious",
                        "premium",
                        "five star",
                        "5-star",
                    ]
                ):
                    score += 5

            elif preference == "business":

                if any(
                    word in combined
                    for word in [
                        "business",
                        "conference",
                        "corporate",
                        "meeting",
                    ]
                ):
                    score += 5

            elif preference == "families":

                if any(
                    word in combined
                    for word in [
                        "family",
                        "families",
                        "kids",
                        "children",
                    ]
                ):
                    score += 5

            elif preference == "budget":

                if any(
                    word in combined
                    for word in [
                        "budget",
                        "affordable",
                        "cheap",
                    ]
                ):
                    score += 5

            elif preference == "couples":

                if any(
                    word in combined
                    for word in [
                        "couples",
                        "romantic",
                        "honeymoon",
                    ]
                ):
                    score += 5

        return score

    hotels = sorted(
        hotels,
        key=hotel_score,
        reverse=True,
    )

    return {
        "hotels": hotels[:number_of_hotels]
    }


# ================================================================
# NODE 7 — REPORT
# ================================================================

def generate_report(state: HotelResearchState) -> Dict:
    """
    Generate the final report.

    NO GROQ CALL.
    """

    hotels = state.get("hotels") or []

    city = state["city"]
    country = state["country"]

    if not hotels:

        error_message = state.get("error")

        if error_message:

            message = (
                f"I couldn't complete the hotel research "
                f"for {city}, {country}. "
                f"{error_message}"
            )

        else:

            message = (
                f"I couldn't find reliable hotel information "
                f"for {city}, {country}. "
                f"Please try another search."
            )

        return {
            "final_report": message,
            "comparison_table_markdown": "",
            "recommendation": message,
        }

    # ============================================================
    # HOTEL REPORT
    # ============================================================

    report_lines = [
        f"## Hotels in {city}, {country}\n"
    ]

    for index, hotel in enumerate(
        hotels,
        start=1,
    ):

        report_lines.append(
            f"### {index}. {hotel.name}\n"
        )

        report_lines.append(
            f"**Rating:** {hotel.rating}\n"
        )

        report_lines.append(
            f"**Location:** {hotel.location}\n"
        )

        report_lines.append(
            f"**Price:** {hotel.price_range}\n"
        )

        report_lines.append(
            f"**Best For:** {hotel.best_for}\n"
        )

        report_lines.append(
            f"**About:** {hotel.description}\n"
        )

        if hotel.facilities:

            report_lines.append(
                "**Facilities:**"
            )

            for facility in hotel.facilities:

                report_lines.append(
                    f"- {facility}"
                )

            report_lines.append("")

        if hotel.nearby_attractions:

            report_lines.append(
                "**Nearby:**"
            )

            for attraction in (
                hotel.nearby_attractions
            ):

                report_lines.append(
                    f"- {attraction}"
                )

            report_lines.append("")

        report_lines.append(
            f"**Official Website:** "
            f"{hotel.official_website}\n"
        )

        if hotel.source_urls:

            report_lines.append(
                "**Sources:**"
            )

            for source in hotel.source_urls:

                report_lines.append(
                    f"- {source}"
                )

        report_lines.append(
            "\n---\n"
        )

    # ============================================================
    # COMPARISON TABLE
    # ============================================================

    table_lines = [
        "| Hotel | Rating | Price | Location | Best For |",
        "|---|---|---|---|---|",
    ]

    for hotel in hotels:

        table_lines.append(
            f"| {hotel.name} | "
            f"{hotel.rating} | "
            f"{hotel.price_range} | "
            f"{hotel.location} | "
            f"{hotel.best_for} |"
        )

    comparison_table = "\n".join(
        table_lines
    )

    # ============================================================
    # SIMPLE RECOMMENDATION
    # ============================================================

    preference = (
        state.get("preferences")
        or "Any"
    )

    first_hotel = hotels[0]

    recommendation = (
        f"Based on the available web research, "
        f"**{first_hotel.name}** is the top result for "
        f"{city}, {country}."
    )

    if preference.lower() != "any":

        recommendation += (
            f" It was selected with your "
            f"**{preference}** preference in mind."
        )

    recommendation += (
        " Review the listed sources before making "
        "a booking because prices and availability "
        "can change."
    )

    # ============================================================
    # FINAL REPORT
    # ============================================================

    final_report = (
        "\n".join(report_lines)
        + "\n## Comparison\n\n"
        + comparison_table
        + "\n\n## Recommendation\n\n"
        + recommendation
    )

    return {
        "final_report": final_report,
        "comparison_table_markdown": comparison_table,
        "recommendation": recommendation,
    }