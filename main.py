"""
Backend entry point.

Run with:
    uvicorn main:app --reload

Exposes:
    POST /api/research-hotels   -> run the LangGraph hotel research workflow
    GET  /                      -> serves the simple frontend
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # must run before app.graph imports anything that reads env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import HotelRequest, HotelResponse
from app.graph import run_hotel_research

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hotel-research-agent")

app = FastAPI(title="AI Hotel Research Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.post("/api/research-hotels", response_model=HotelResponse)
def research_hotels(request: HotelRequest):
    try:
        result = run_hotel_research(
            country=request.country,
            city=request.city,
            preferences=request.preferences or "Any",
            number_of_hotels=request.number_of_hotels or 5,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error while running hotel research graph")
        return HotelResponse(
            success=False,
            message=(
                "Something went wrong while researching hotels. "
                "Please try again in a moment."
            ),
        )

    if not result.get("is_valid", True):
        return HotelResponse(success=False, message=result.get("validation_message"))

    hotels = result.get("hotels") or []
    if not hotels:
        return HotelResponse(
            success=False,
            message=(
                result.get("error")
                or f"Sorry, I couldn't find enough reliable information for "
                f"{request.city}, {request.country}. Please try another city "
                f"or check your spelling."
            ),
        )

    return HotelResponse(
        success=True,
        country=result.get("country"),
        city=result.get("city"),
        hotels=hotels,
        comparison_table_markdown=result.get("comparison_table_markdown"),
        recommendation=result.get("recommendation"),
        final_report_markdown=result.get("final_report"),
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
