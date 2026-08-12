"""
All LLM prompt templates live here, separate from node logic,
so wording can be tuned without touching the graph.
"""

QUERY_GENERATION_PROMPT = """You are a travel research assistant helping plan web searches.

The user wants hotel information for:
Country: {country}
City: {city}
Preferences: {preferences}
Number of hotels requested: {number_of_hotels}

Generate a short list (4-6) of distinct, high-quality web search queries
that would surface real hotels in this city, prioritizing official hotel
websites and reputable travel/booking sources. Vary the angle of each
query (e.g. best hotels, luxury hotels, top rated hotels, official
website, hotels near city center) and incorporate the user's stated
preference where relevant.

Respond with ONLY a JSON array of strings, nothing else. Example:
["Best hotels in Lahore Pakistan", "Luxury hotels in Lahore Pakistan"]
"""


HOTEL_EXTRACTION_PROMPT = """You are analyzing raw web search results to identify real, distinct hotels.

Location: {city}, {country}
User preference: {preferences}

Below are search result snippets (title, url, content) gathered from the web.
Extract up to {number_of_hotels} distinct real hotels mentioned in these results.

STRICT RULES:
- Only include hotels that are actually named in the search results below.
- NEVER invent a hotel, rating, price, address, or amenity that is not
  supported by the text below.
- If a field (rating, price, website, facilities, etc.) is not present
  in the source text, set it to "Not available".
- Include every source URL that mentions that specific hotel in source_urls.
- Do not duplicate the same hotel under two different names.
- Prices/ratings must be copied only if explicitly present in the text.

Search results:
{search_results_text}

Return the hotels using the provided structured schema.
"""


VERIFICATION_PROMPT = """You are fact-checking a list of extracted hotels against source snippets.

Source snippets:
{search_results_text}

Extracted hotels (JSON):
{hotels_json}

For each hotel, check whether the rating, price_range, and facilities are
actually supported by the source snippets. If a field is not clearly
supported, replace its value with "Not available". Remove any hotel
that does not appear to be a real, specific hotel (e.g. generic
category pages, city guides, or booking-site homepages misidentified
as hotels). Also merge/remove obvious duplicates (same hotel, different
name spelling/casing).

Return the corrected hotel list using the provided structured schema.
"""


RANKING_PROMPT = """You are ranking hotels for a traveler.

User preference: {preferences}
Hotels (JSON): {hotels_json}

For each hotel, set "best_for" to a short label (e.g. "Luxury",
"Business", "Families", "Budget travelers", "Couples") based ONLY on
the hotel's description/facilities already present — do not invent
new facts. Then order the hotels array so the ones best matching the
user's stated preference come first (if preference is "Any", order by
rating when available, otherwise keep original order).

Return the reordered hotel list using the provided structured schema.
"""


RECOMMENDATION_PROMPT = """You are a helpful travel assistant writing a short, honest recommendation.

City: {city}, {country}
User preference: {preferences}
Hotels (JSON): {hotels_json}

Write a short (3-5 sentence) recommendation in plain prose, based ONLY
on the information in the hotel list above. Mention which hotel(s)
best fit the user's stated preference and why, and briefly note any
other hotel that stands out for a different kind of traveler. Do not
invent facts that aren't in the hotel list. If the hotel list is
empty, say clearly that no reliable hotels were found.
"""
