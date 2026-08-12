const form = document.getElementById("research-form");
const submitBtn = document.getElementById("submit-btn");
const statusSection = document.getElementById("status");
const statusList = document.getElementById("status-list");
const errorBox = document.getElementById("error-box");
const resultsSection = document.getElementById("results");
const resultsHeading = document.getElementById("results-heading");
const hotelCardsEl = document.getElementById("hotel-cards");
const comparisonTableEl = document.getElementById("comparison-table");
const recommendationEl = document.getElementById("recommendation");

const LOADING_STEPS = [
  "🔎 Searching the web...",
  "🤖 Analyzing hotel information...",
  "🔍 Verifying hotel details...",
  "📊 Comparing results...",
  "✨ Preparing your hotel report..."
];

let stepTimer = null;

/* =========================
   UI HELPERS
========================= */

function resetUI() {
  errorBox.hidden = true;
  errorBox.textContent = "";

  resultsSection.hidden = true;

  hotelCardsEl.innerHTML = "";
  comparisonTableEl.innerHTML = "";
  recommendationEl.textContent = "";
}

function startLoadingAnimation() {
  statusSection.hidden = false;

  statusList.innerHTML = LOADING_STEPS
    .map((step, index) => `<li id="step-${index}">${step}</li>`)
    .join("");

  let currentStep = 0;

  document
    .getElementById("step-0")
    ?.classList.add("active");

  stepTimer = setInterval(() => {
    document
      .getElementById(`step-${currentStep}`)
      ?.classList.remove("active");

    currentStep = Math.min(
      currentStep + 1,
      LOADING_STEPS.length - 1
    );

    document
      .getElementById(`step-${currentStep}`)
      ?.classList.add("active");
  }, 1400);
}

function stopLoadingAnimation() {
  if (stepTimer) {
    clearInterval(stepTimer);
    stepTimer = null;
  }

  statusSection.hidden = true;
}

/* =========================
   SECURITY
========================= */

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function safeUrl(value) {
  if (!value || value === "Not available") {
    return null;
  }

  try {
    const url = new URL(value);

    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.href;
    }

    return null;
  } catch {
    return null;
  }
}

/* =========================
   HOTEL HELPERS
========================= */

function displayValue(value) {
  if (
    value === undefined ||
    value === null ||
    value === "" ||
    value === "Not available"
  ) {
    return "Not available";
  }

  return escapeHtml(String(value));
}

function renderRating(rating) {
  if (
    rating === undefined ||
    rating === null ||
    rating === "" ||
    rating === "Not available"
  ) {
    return "Not available";
  }

  return `⭐ ${escapeHtml(String(rating))}`;
}

function renderFacilities(facilities) {
  if (!Array.isArray(facilities) || facilities.length === 0) {
    return "";
  }

  const validFacilities = facilities
    .filter(
      (facility) =>
        facility &&
        facility !== "Not available"
    )
    .slice(0, 10);

  if (validFacilities.length === 0) {
    return "";
  }

  return `
    <div class="chip-row">
      ${validFacilities
        .map(
          (facility) =>
            `<span class="chip">✓ ${escapeHtml(facility)}</span>`
        )
        .join("")}
    </div>
  `;
}

function renderAttractions(attractions) {
  if (!Array.isArray(attractions) || attractions.length === 0) {
    return "";
  }

  const validAttractions = attractions
    .filter(
      (item) =>
        item &&
        item !== "Not available"
    )
    .slice(0, 6);

  if (validAttractions.length === 0) {
    return "";
  }

  return `
    <p class="desc">
      <strong>📍 Nearby:</strong>
      ${validAttractions
        .map((item) => escapeHtml(item))
        .join(", ")}
    </p>
  `;
}

function renderWebsite(website) {
  const url = safeUrl(website);

  if (!url) {
    return `<span>🌐 Website: Not available</span>`;
  }

  return `
    <a
      href="${escapeHtml(url)}"
      target="_blank"
      rel="noopener noreferrer"
    >
      🌐 Visit Official Website →
    </a>
  `;
}

function renderSources(sourceUrls) {
  if (!Array.isArray(sourceUrls) || sourceUrls.length === 0) {
    return "";
  }

  const validUrls = sourceUrls
    .map(safeUrl)
    .filter(Boolean)
    .slice(0, 5);

  if (validUrls.length === 0) {
    return "";
  }

  return `
    <div class="source-links">
      <strong>🔗 Sources:</strong>
      ${validUrls
        .map(
          (url, index) => `
            <a
              href="${escapeHtml(url)}"
              target="_blank"
              rel="noopener noreferrer"
            >
              Source ${index + 1}
            </a>
          `
        )
        .join(" · ")}
    </div>
  `;
}

/* =========================
   HOTEL CARD
========================= */

function renderHotelCard(hotel, index) {
  const name =
    hotel?.name || "Hotel name unavailable";

  const rating = renderRating(hotel?.rating);

  const price = displayValue(
    hotel?.price_range
  );

  const location = displayValue(
    hotel?.location
  );

  const bestFor = displayValue(
    hotel?.best_for
  );

  const description =
    hotel?.description &&
    hotel.description !== "Not available"
      ? escapeHtml(hotel.description)
      : "No detailed description was available from the researched sources.";

  const facilities =
    renderFacilities(hotel?.facilities);

  const attractions =
    renderAttractions(
      hotel?.nearby_attractions
    );

  const website =
    renderWebsite(
      hotel?.official_website
    );

  const sources =
    renderSources(
      hotel?.source_urls
    );

  return `
    <article class="hotel-card">

      <span class="rank-tag">
        #${index + 1}
      </span>

      <h4>
        ${escapeHtml(name)}
      </h4>

      <div class="hotel-meta">

        <span>
          <strong>Rating:</strong>
          ${rating}
        </span>

        <span>
          <strong>Price:</strong>
          ${price}
        </span>

        <span>
          <strong>Location:</strong>
          📍 ${location}
        </span>

        <span>
          <strong>Best for:</strong>
          🎯 ${bestFor}
        </span>

      </div>

      <p class="desc">
        ${description}
      </p>

      ${
        facilities
          ? `
            <div>
              <strong>🏨 Facilities</strong>
              ${facilities}
            </div>
          `
          : ""
      }

      ${attractions}

      <div class="links">

        ${website}

        ${sources}

      </div>

    </article>
  `;
}

/* =========================
   COMPARISON TABLE
========================= */

function renderComparisonTable(hotels) {
  if (!Array.isArray(hotels) || hotels.length === 0) {
    return `
      <p class="desc">
        No hotels available for comparison.
      </p>
    `;
  }

  const rows = hotels
    .map(
      (hotel) => `
        <tr>

          <td>
            <strong>
              ${escapeHtml(
                hotel?.name ||
                "Not available"
              )}
            </strong>
          </td>

          <td>
            ${renderRating(hotel?.rating)}
          </td>

          <td>
            ${displayValue(
              hotel?.price_range
            )}
          </td>

          <td>
            ${displayValue(
              hotel?.location
            )}
          </td>

          <td>
            ${displayValue(
              hotel?.best_for
            )}
          </td>

        </tr>
      `
    )
    .join("");

  return `
    <table class="compare">

      <thead>
        <tr>
          <th>Hotel</th>
          <th>Rating</th>
          <th>Price</th>
          <th>Location</th>
          <th>Best For</th>
        </tr>
      </thead>

      <tbody>
        ${rows}
      </tbody>

    </table>
  `;
}

/* =========================
   FORM SUBMISSION
========================= */

form.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    resetUI();
    startLoadingAnimation();

    submitBtn.disabled = true;
    submitBtn.textContent =
      "Researching hotels...";

    const payload = {
      country:
        document
          .getElementById("country")
          .value
          .trim(),

      city:
        document
          .getElementById("city")
          .value
          .trim(),

      preferences:
        document
          .getElementById("preferences")
          .value,

      number_of_hotels:
        parseInt(
          document
            .getElementById(
              "number_of_hotels"
            )
            .value,
          10
        ) || 5
    };

    /* =========================
       BASIC VALIDATION
    ========================= */

    if (!payload.country || !payload.city) {
      stopLoadingAnimation();

      errorBox.hidden = false;
      errorBox.textContent =
        "Please enter both a country and city.";

      submitBtn.disabled = false;
      submitBtn.textContent =
        "Research Hotels";

      return;
    }

    try {
      const response =
        await fetch(
          "/api/research-hotels",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify(payload)
          }
        );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          "The server returned an invalid response."
        );
      }

      stopLoadingAnimation();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.message ||
          "Hotel research failed."
        );
      }

      /* =========================
         RENDER RESULTS
      ========================= */

      const hotels =
        Array.isArray(data.hotels)
          ? data.hotels
          : [];

      resultsHeading.textContent =
        `Hotels in ${data.city}, ${data.country}`;

      if (hotels.length === 0) {
        hotelCardsEl.innerHTML = `
          <div class="recommendation">
            No reliable hotels were found
            for this location.
            Try another city or adjust your
            preferences.
          </div>
        `;
      } else {
        hotelCardsEl.innerHTML =
          hotels
            .map(renderHotelCard)
            .join("");
      }

      comparisonTableEl.innerHTML =
        renderComparisonTable(hotels);

      recommendationEl.textContent =
        data.recommendation ||
        "No recommendation was generated.";

      resultsSection.hidden = false;

      resultsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });

    } catch (error) {
      stopLoadingAnimation();

      console.error(
        "Hotel research error:",
        error
      );

      errorBox.hidden = false;

      errorBox.textContent =
        error.message ||
        "Couldn't reach the server. Check your connection and try again.";

    } finally {
      submitBtn.disabled = false;

      submitBtn.textContent =
        "Research Hotels";
    }
  }
);