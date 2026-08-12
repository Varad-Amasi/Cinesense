/* ═══════════════════════════════════════════════════════════════════════════
   CineSense — Frontend Logic
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  // ── Elements ─────────────────────────────────────────────────────────────
  const searchInput = document.getElementById("searchInput");
  const searchBtn = document.getElementById("searchBtn");
  const modelStatus = document.getElementById("modelStatus");
  const hero = document.getElementById("hero");
  
  const searchResultsSection = document.getElementById("searchResultsSection");
  const searchResultsGrid = document.getElementById("searchResultsGrid");
  const backToSearchBtn = document.getElementById("backToSearch");
  
  const loadingSection = document.getElementById("loadingSection");
  const loadingText = document.getElementById("loadingText");
  
  const resultSection = document.getElementById("resultSection");
  const newSearchBtn = document.getElementById("newSearch");
  
  // Card elements
  const resultPoster = document.getElementById("resultPoster");
  const resultTitle = document.getElementById("resultTitle");
  const resultYear = document.getElementById("resultYear");
  const verdictBadge = document.getElementById("verdictBadge");
  const verdictEmoji = document.getElementById("verdictEmoji");
  const verdictText = document.getElementById("verdictText");
  const confidenceRing = document.getElementById("confidenceRing");
  const confidenceValue = document.getElementById("confidenceValue");
  const posCount = document.getElementById("posCount");
  const negCount = document.getElementById("negCount");
  const totalCount = document.getElementById("totalCount");
  const sourcesBreakdown = document.getElementById("sourcesBreakdown");
  const ticker = document.getElementById("ticker");

  // ── State ────────────────────────────────────────────────────────────────
  let isReady = false;
  let backendLabel = "";

  // ── Initialization ───────────────────────────────────────────────────────
  checkServerStatus();

  function checkServerStatus() {
    fetch("/api/status")
      .then(res => res.json())
      .then(data => {
        backendLabel = data.backend ? ` (${data.backend})` : "";
        if (data.ready) {
          isReady = true;
          searchInput.disabled = false;
          searchBtn.disabled = false;
          modelStatus.innerHTML = `<span style=\"color:var(--emerald);\">●</span> ML Engine Online & Ready${backendLabel}`;
          searchInput.focus();
        } else {
          // Informative warm-up message while training/initializing
          modelStatus.innerHTML = `<span class=\"loading-dot\"></span> Warming up the projection room…${backendLabel}`;
          setTimeout(checkServerStatus, 1500);
        }
      })
      .catch((err) => {
        // Network or server error — show explicit offline message and retry
        console.warn('checkServerStatus failed:', err);
        modelStatus.innerHTML = `<span style=\"color:var(--amber-v);\">●</span> Backend offline — retrying...`;
        searchInput.disabled = true;
        searchBtn.disabled = true;
        setTimeout(checkServerStatus, 3000);
      });
  }

  // ── Event Listeners ──────────────────────────────────────────────────────
  searchBtn.addEventListener("click", performSearch);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !searchBtn.disabled) performSearch();
  });

  backToSearchBtn.addEventListener("click", showSearchMode);
  newSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    showSearchMode();
    searchInput.focus();
  });

  // ── Searching ────────────────────────────────────────────────────────────
  async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    searchBtn.disabled = true;
    searchInput.disabled = true;
    modelStatus.innerHTML = `<span class="loading-dot"></span> Searching archives...`;

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      
      if (data.results && data.results.length > 0) {
        renderSearchResults(data.results);
      } else {
        modelStatus.innerHTML = `<span style="color:var(--crimson);">●</span> No results found. Try another title.`;
      }
    } catch (e) {
      modelStatus.innerHTML = `<span style="color:var(--crimson);">●</span> Search failed. Server unreachable.`;
    } finally {
      searchBtn.disabled = false;
      searchInput.disabled = false;
    }
  }

  function renderSearchResults(results) {
    searchResultsGrid.innerHTML = "";
    
    results.forEach((movie) => {
      const card = document.createElement("div");
      card.className = "movie-card";
      
      const fallbackImg = "data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 300' fill='%23111'%3E%3Crect width='200' height='300'/%3E%3Ctext x='50%25' y='50%25' fill='%23333' text-anchor='middle' font-family='sans-serif' font-size='16'%3ENo Poster%3C/text%3E%3C/svg%3E";
      const imgSrc = movie.poster_url || fallbackImg;

      card.innerHTML = `
        <img class="movie-card__poster" src="${imgSrc}" alt="${movie.title}" onerror="this.src='${fallbackImg}'">
        <div class="movie-card__body">
          <h3 class="movie-card__title">${movie.title}</h3>
          <p class="movie-card__year">${movie.year}</p>
        </div>
      `;
      card.addEventListener("click", () => startClassification(movie));
      searchResultsGrid.appendChild(card);
    });

    document.getElementById("searchSection").style.display = "none";
    searchResultsSection.style.display = "block";
    hero.style.display = "none";
  }

  function showSearchMode() {
    searchResultsSection.style.display = "none";
    resultSection.style.display = "none";
    loadingSection.style.display = "none";
    document.getElementById("searchSection").style.display = "block";
    hero.style.display = "block";
    modelStatus.innerHTML = `<span style="color:var(--emerald);">●</span> ML Engine Online & Ready${backendLabel}`;
  }

  // ── Classification ───────────────────────────────────────────────────────
  async function startClassification(movie) {
    searchResultsSection.style.display = "none";
    loadingSection.style.display = "block";
    
    const messages = [
      "Connecting to IMDb, Rotten Tomatoes, and Letterboxd...",
      "Scraping thousands of audience reviews...",
      "Extracting TF-IDF text features...",
      "Running GPU-accelerated sentiment classifier...",
      "Aggregating massive sentiment scores...",
      "Finalizing verdict..."
    ];
    let msgIdx = 0;
    const msgInterval = setInterval(() => {
      msgIdx = (msgIdx + 1) % messages.length;
      loadingText.textContent = messages[msgIdx];
    }, 2000);

    try {
      const res = await fetch("/api/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(movie),
      });
      const data = await res.json();
      
      clearInterval(msgInterval);

      if (res.ok) {
        displayResults(data);
      } else {
        alert(data.error || "An error occurred during classification.");
        showSearchMode();
      }
    } catch (e) {
      clearInterval(msgInterval);
      alert("Network error: Could not connect to the server.");
      showSearchMode();
    }
  }

  function displayResults(data) {
    loadingSection.style.display = "none";
    resultSection.style.display = "block";

    // Populate card
    const fallbackImg = "data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 300' fill='%23111'%3E%3Crect width='200' height='300'/%3E%3C/svg%3E";
    resultPoster.src = data.poster_url || fallbackImg;
    resultTitle.textContent = data.movie_title;
    resultYear.textContent = data.year;
    
    verdictBadge.setAttribute("data-verdict", data.verdict);
    verdictEmoji.textContent = data.verdict_emoji;
    verdictText.textContent = data.verdict;

    // Animate stats counting
    animateValue(posCount, 0, data.positive_count, 1000);
    animateValue(negCount, 0, data.negative_count, 1000);
    animateValue(totalCount, 0, data.total_reviews, 1000);

    // Animate confidence ring
    const percentage = data.confidence;
    const circumference = 326.73; // 2 * pi * 52
    const offset = circumference - (percentage / 100) * circumference;
    
    // Set ring color based on verdict
    let ringColor = "var(--emerald)";
    if (data.verdict === "WORTH WATCHING") ringColor = "var(--teal)";
    else if (data.verdict === "MIXED") ringColor = "var(--amber-v)";
    else if (data.verdict === "SKIP") ringColor = "var(--orange)";
    else if (data.verdict === "HARD SKIP") ringColor = "var(--crimson)";
    
    confidenceRing.style.strokeDashoffset = circumference;
    confidenceRing.style.stroke = ringColor;
    
    setTimeout(() => {
      confidenceRing.style.strokeDashoffset = offset;
      animateValue(confidenceValue, 0, Math.round(percentage), 1500);
    }, 300);

    // Populate sources
    sourcesBreakdown.innerHTML = "";
    if (data.source_counts) {
      for (const [source, count] of Object.entries(data.source_counts)) {
        if (count > 0) {
          const badge = document.createElement("div");
          badge.className = "source-badge";
          badge.innerHTML = `${source} <span>${count}</span>`;
          sourcesBreakdown.appendChild(badge);
        }
      }
    }

    // Populate ticker
    ticker.innerHTML = "";
    // Duplicate samples to create an infinite loop effect
    const tickerItems = [...data.sample_reviews, ...data.sample_reviews, ...data.sample_reviews];
    
    tickerItems.forEach(rev => {
      const isPos = rev.label === "Positive";
      const item = document.createElement("div");
      item.className = "ticker-item";
      item.innerHTML = `
        <span class="ticker-item__tag ticker-item__tag--${isPos ? 'pos' : 'neg'}">
          ${isPos ? '✅ POSITIVE' : '❌ NEGATIVE'} · ${rev.confidence}%
        </span>
        <p class="ticker-item__text">"${rev.text}..."</p>
      `;
      ticker.appendChild(item);
    });
  }

  // ── Utils ────────────────────────────────────────────────────────────────
  function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      
      // Easing function: easeOutQuart
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      
      obj.innerHTML = Math.floor(easeProgress * (end - start) + start);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }
});
