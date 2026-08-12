# AI Hotel Research Agent

A simple AI agent that researches real hotels for a given country/city using
live web search, built with **LangChain**, **LangGraph**, **Tavily search**,
and **Claude (Anthropic)**, served through a **FastAPI** backend and a
lightweight HTML/CSS/JS frontend.

The agent never invents hotels, ratings, or prices — every field is either
backed by a search result or explicitly marked `Not available`.

---

## 1. Project Structure

```text
hotel-research-agent/
│
├── app/
│   ├── __init__.py
│   ├── graph.py       # LangGraph workflow assembly
│   ├── state.py        # Shared state passed between graph nodes
│   ├── nodes.py         # The 7 workflow nodes (validate -> ... -> report)
│   ├── tools.py          # Web search tool (Tavily), isolated from graph logic
│   ├── prompts.py         # All LLM prompt templates
│   └── models.py           # Pydantic schemas (Hotel, requests/responses)
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .env                 # Your real keys (not committed)
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── main.py               # FastAPI app entry point
```

---

## 2. Setup Instructions

### Step 1 — Create a virtual environment

```bash
cd hotel-research-agent
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```text
LLM_API_KEY=your_groq_api_key
SEARCH_API_KEY=your_tavily_api_key
```

* **LLM_API_KEY** — a [Groq API key](https://console.groq.com/keys), used
  via `langchain-groq` (`ChatGroq`, model `llama-3.3-70b-versatile`) for
  query generation, extraction, verification, ranking, and the final
  recommendation. Swap the model name in `app/nodes.py` (`_get_llm`) if you
  prefer a different Groq-hosted model.
* **SEARCH_API_KEY** — a [Tavily](https://tavily.com) API key (free tier
  available), used for live web search.

`.env` is already listed in `.gitignore`, so your keys are never committed.

---

## 3. Running Locally

```bash
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser. The FastAPI app serves
both the API and the static frontend, so there's nothing else to start.

---

## 4. Using the App

1. Enter a **Country** and **City** (e.g. `Pakistan` / `Lahore`).
2. Optionally set the number of hotels (1–10) and a preference (Luxury,
   Budget, Family-friendly, Business, Near city center, Near airport, or Any).
3. Click **Research Hotels**.
4. The agent will search the web, extract and verify hotel details, rank
   them against your preference, and display:
   * Individual hotel cards (rating, price, facilities, nearby attractions,
     official website, sources)
   * A comparison table
   * A short AI recommendation

### Example request/response

Request:

```json
{
  "country": "Pakistan",
  "city": "Lahore",
  "preferences": "Luxury",
  "number_of_hotels": 5
}
```

Response (abridged):

```json
{
  "success": true,
  "country": "Pakistan",
  "city": "Lahore",
  "hotels": [
    {
      "name": "Pearl Continental Hotel Lahore",
      "location": "Lahore, Pakistan",
      "rating": "4.5/5",
      "price_range": "Not available",
      "description": "A well-known 5-star hotel in Lahore ...",
      "facilities": ["Swimming Pool", "Free Wi-Fi", "Restaurant"],
      "nearby_attractions": ["Lahore Zoo"],
      "official_website": "https://www.pchotels.com/lahore",
      "source_urls": ["https://..."],
      "best_for": "Luxury"
    }
  ],
  "comparison_table_markdown": "| Hotel | Rating | ... |",
  "recommendation": "Based on the available information, Pearl Continental ...",
  "final_report_markdown": "## Hotels in Lahore, Pakistan\n\n### 1. ..."
}
```

---

## 5. Testing

Manual test matrix (also see `Phase 8` in the original spec):

| Case | Expected result |
|---|---|
| `Pakistan` / `Lahore` | Report with real hotels |
| `UAE` / `Dubai` | Report with real hotels |
| `Turkey` / `Istanbul` | Report with real hotels |
| Empty city | Friendly validation message, no crash |
| Nonsense city (e.g. `Xzqplor`) | "Couldn't find enough reliable information" message |
| `SEARCH_API_KEY` missing/invalid | Friendly error, no stack trace shown to user |
| Anthropic key missing/invalid | Friendly error, no stack trace shown to user |

You can also test the API directly:

```bash
curl -X POST http://127.0.0.1:8000/api/research-hotels \
  -H "Content-Type: application/json" \
  -d '{"country":"Japan","city":"Tokyo","preferences":"Business","number_of_hotels":5}'
```

---

## 6. The LangGraph Workflow

```text
START
  → validate_input      Checks country/city are present and reasonable
  → generate_queries     Claude generates 4–6 targeted search queries
  → web_search            Tavily runs each query, results are flattened
  → extract_hotels         Claude extracts a structured hotel list from
                            search snippets only (no invented data)
  → verify_results          Claude re-checks each field against the
                              source snippets; unsupported fields become
                              "Not available"; duplicates are merged
  → rank_hotels               Claude labels each hotel's best-fit
                                traveler type and reorders by preference
  → generate_report             Builds the markdown report, comparison
                                  table, and a sourced recommendation
  → END
```

If `validate_input` fails, or `web_search` returns nothing, the graph
short-circuits straight to `generate_report`, which returns a clear,
user-friendly message instead of a broken or empty report — this is
implemented with LangGraph conditional edges in `app/graph.py`.

State is a single `HotelResearchState` `TypedDict` (see `app/state.py`)
that flows through every node; each node returns only the fields it
updates, and LangGraph merges them in.

---

## 7. The LangChain Tools

* **`app/tools.py`** wraps `langchain-tavily`'s `TavilySearch` tool behind a
  plain `web_search(query)` / `web_search_many(queries)` function. This
  keeps the search *provider* decoupled from the graph — swapping Tavily
  for Bing/SerpAPI/another provider later only means editing this one file.
* **Structured output**: `app/nodes.py` uses
  `ChatAnthropic(...).with_structured_output(HotelList)` (a Pydantic model
  in `app/models.py`) so extraction, verification, and ranking all return
  validated JSON instead of free-form text that would need fragile parsing.

---

## 8. Design Rules Followed

* Never fabricates hotel names, ratings, or prices — unverifiable fields
  are explicitly marked `Not available`.
* Prefers official hotel websites and reputable sources; every hotel
  carries its `source_urls`.
* Duplicate hotels are merged during verification.
* API keys are never hard-coded or exposed to the frontend; they're only
  read server-side from `.env`.
* Errors are caught at every layer (search, LLM, network) and turned into
  plain, non-technical messages — no stack traces reach the user.

---

## 9. Extending Later

The modular structure (`tools.py` for search, `nodes.py` for logic,
`prompts.py` for wording, `graph.py` for orchestration) is designed so you
can add, without restructuring:

* Booking links / real-time availability
* Price comparison across sources
* Google Maps integration for `nearby_attractions`
* Restaurant / flight / attraction research agents alongside this one
* A `save_search` endpoint + simple user accounts
* PDF export of `final_report_markdown`
