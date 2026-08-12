"""
Pydantic models used across the Hotel Research Agent.

These give us structured, validated data instead of relying on
free-form text from the LLM.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Hotel(BaseModel):
    """A single researched hotel."""

    name: str
    location: str = "Not available"
    rating: str = "Not available"
    price_range: str = "Not available"
    description: str = "Not available"
    facilities: List[str] = Field(default_factory=list)
    room_types: List[str] = Field(default_factory=list)
    nearby_attractions: List[str] = Field(default_factory=list)
    official_website: str = "Not available"
    contact: str = "Not available"
    source_urls: List[str] = Field(default_factory=list)
    best_for: str = "Not available"  # e.g. Luxury, Business, Families


class HotelList(BaseModel):
    """Structured-output wrapper so the LLM returns a clean list of hotels."""

    hotels: List[Hotel] = Field(default_factory=list)


class HotelRequest(BaseModel):
    """Incoming request from the frontend / API."""

    country: str
    city: str
    preferences: Optional[str] = "Any"
    number_of_hotels: int = 5


class HotelResponse(BaseModel):
    """Outgoing structured response from the API."""

    success: bool
    message: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    hotels: List[Hotel] = Field(default_factory=list)
    comparison_table_markdown: Optional[str] = None
    recommendation: Optional[str] = None
    final_report_markdown: Optional[str] = None
