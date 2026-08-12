/* ═══════════════════════════════════════════════════════════════════════════
   CineSense — Frontend Logic with Firebase Auth & 1-Visit Guest Pass Limit
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

  // Auth Elements
  const authModal = document.getElementById("authModal");
  const openAuthModalBtn = document.getElementById("openAuthModalBtn");
  const closeAuthModal = document.getElementById("closeAuthModal");
  const googleAuthBtn = document.getElementById("googleAuthBtn");
  const guestAuthBtn = document.getElementById("guestAuthBtn");
  const guestAuthBtnText = document.getElementById("guestAuthBtnText");
  const guestExpiredBanner = document.getElementById("guestExpiredBanner");
  const authInfoBanner = document.getElementById("authInfoBanner");
  const authInfoText = document.getElementById("authInfoText");
  
  const authUserProfile = document.getElementById("authUserProfile");
  const userAvatar = document.getElementById("userAvatar");
  const userName = document.getElementById("userName");
  const userStatusBadge = document.getElementById("userStatusBadge");
  const signOutBtn = document.getElementById("signOutBtn");
  const authActions = document.getElementById("authActions");

  // ── State ────────────────────────────────────────────────────────────────
  let isReady = false;
  let backendLabel = "";
  let auth = null;
  let currentUser = null;
  const GUEST_PASS_KEY = "has_used_guest_pass";
  const GUEST_SESSION_KEY = "current_guest_session";

  // ── Initialization ───────────────────────────────────────────────────────
  checkServerStatus();
  initFirebaseAuth();

  function checkServerStatus() {
    fetch("/api/status")
      .then(res => res.json())
      .then(data => {
        backendLabel = data.backend ? ` (${data.backend})` : "";
        if (data.ready) {
          isReady = true;
          if (canUserSearch()) {
            searchInput.disabled = false;
            searchBtn.disabled = false;
          }
          modelStatus.innerHTML = `<span style="color:var(--emerald);">●</span> ML Engine Online & Ready${backendLabel}`;
        } else {
          modelStatus.innerHTML = `<span class="loading-dot"></span> Warming up the projection room…${backendLabel}`;
          setTimeout(checkServerStatus, 1500);
        }
      })
      .catch((err) => {
        console.warn('checkServerStatus failed:', err);
        modelStatus.innerHTML = `<span style="color:var(--amber-v);">●</span> Backend offline — retrying...`;
        searchInput.disabled = true;
        searchBtn.disabled = true;
        setTimeout(checkServerStatus, 3000);
      });
  }

  // ── Firebase Auth & 1-Visit Guest Pass Enforcement ───────────────────────
  function initFirebaseAuth() {
    fetch("/api/firebase-config")
      .then(res => res.json())
      .then(config => {
        if (config && config.apiKey && typeof firebase !== "undefined") {
          if (!firebase.apps.length) {
            firebase.initializeApp(config);
          }
          auth = firebase.auth();
          listenToAuthState();
        } else {
          console.warn("Firebase config not set or SDK uninitialized. Running local auth mode.");
          evaluateGuestPassStatus();
        }
      })
      .catch(err => {
        console.warn("Failed to fetch Firebase config:", err);
        evaluateGuestPassStatus();
      });
  }

  function evaluateGuestPassStatus() {
    const hasUsedGuestPass = localStorage.getItem(GUEST_PASS_KEY) === "true";
    const isGuestActive = sessionStorage.getItem(GUEST_SESSION_KEY) === "active";

    if (hasUsedGuestPass && !isGuestActive) {
      showGuestExpiredUI();
    } else if (isGuestActive) {
      showSignedInUI({ displayName: "Guest User", photoURL: "", isAnonymous: true }, true);
    } else {
      showSignedOutUI();
    }
  }

  function listenToAuthState() {
    if (!auth) return;

    auth.onAuthStateChanged(async (user) => {
      currentUser = user;
      const hasUsedGuestPass = localStorage.getItem(GUEST_PASS_KEY) === "true";
      const isGuestActive = sessionStorage.getItem(GUEST_SESSION_KEY) === "active";

      if (user) {
        if (user.isAnonymous) {
          // Anonymous Guest Session
          if (hasUsedGuestPass && !isGuestActive) {
            // Guest pass was already used on a previous visit -> Expire & Sign Out!
            await auth.signOut();
            currentUser = null;
            sessionStorage.removeItem(GUEST_SESSION_KEY);
            showGuestExpiredUI();
            openAuthModalHandler();
            return;
          }
          // Mark guest pass as consumed for future visits
          localStorage.setItem(GUEST_PASS_KEY, "true");
          sessionStorage.setItem(GUEST_SESSION_KEY, "active");
          showSignedInUI(user, true);
        } else {
          // Permanent User (Google Sign-In)
          sessionStorage.removeItem(GUEST_SESSION_KEY);
          showSignedInUI(user, false);
        }
      } else {
        // Not signed in
        if (hasUsedGuestPass) {
          showGuestExpiredUI();
        } else {
          showSignedOutUI();
        }
      }
    });
  }

  function canUserSearch() {
    const hasUsedGuestPass = localStorage.getItem(GUEST_PASS_KEY) === "true";
    const isGuestActive = sessionStorage.getItem(GUEST_SESSION_KEY) === "active";

    if (currentUser) {
      if (currentUser.isAnonymous && hasUsedGuestPass && !isGuestActive) return false;
      return true;
    }
    if (isGuestActive) return true;
    if (hasUsedGuestPass) return false;
    return true;
  }

  function showGuestExpiredUI() {
    guestAuthBtn.disabled = true;
    guestAuthBtnText.textContent = "🎟️ Guest Pass Used (Expired)";
    guestExpiredBanner.style.display = "flex";
    authInfoBanner.style.display = "none";
    
    authUserProfile.style.display = "none";
    authActions.style.display = "block";
    
    searchInput.disabled = true;
    searchBtn.disabled = true;
    searchInput.placeholder = "Guest access expired. Please sign in with Google...";
    modelStatus.innerHTML = `<span style="color:var(--crimson);">●</span> Guest access expired. Sign in with Google to continue.`;
  }

  function showSignedOutUI() {
    const hasUsedGuestPass = localStorage.getItem(GUEST_PASS_KEY) === "true";
    guestExpiredBanner.style.display = hasUsedGuestPass ? "flex" : "none";
    authInfoBanner.style.display = "none";

    guestAuthBtn.disabled = hasUsedGuestPass;
    guestAuthBtnText.textContent = hasUsedGuestPass 
      ? "🎟️ Guest Pass Used (Expired)" 
      : "🎟️ Continue as Guest (1-Visit Pass)";

    authUserProfile.style.display = "none";
    authActions.style.display = "block";

    if (hasUsedGuestPass) {
      searchInput.disabled = true;
      searchBtn.disabled = true;
      searchInput.placeholder = "Guest access expired. Please sign in...";
    } else if (isReady) {
      searchInput.disabled = false;
      searchBtn.disabled = false;
      searchInput.placeholder = "Enter a movie title...";
    }
  }

  function showSignedInUI(user, isGuest) {
    guestExpiredBanner.style.display = "none";
    authInfoBanner.style.display = "block";
    authInfoText.textContent = isGuest 
      ? "Active Guest Session (1-Visit Pass)" 
      : `Signed in as ${user.email || user.displayName}`;

    const defaultAvatar = "data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' fill='%23555'%3E%3Ccircle cx='50' cy='35' r='20'/%3E%3Cpath d='M15 85c0-20 15-30 35-30s35 10 35 30'/%3E%3C/svg%3E";
    userAvatar.src = user.photoURL || defaultAvatar;
    userName.textContent = user.displayName || (isGuest ? "Guest User" : "CineSense User");
    userStatusBadge.textContent = isGuest ? "1-Visit Pass" : "Permanent Account";

    authUserProfile.style.display = "flex";
    authActions.style.display = "none";

    if (isReady) {
      searchInput.disabled = false;
      searchBtn.disabled = false;
      searchInput.placeholder = "Enter a movie title...";
    }
  }

  // ── Auth Event Handlers ──────────────────────────────────────────────────
  function openAuthModalHandler() {
    authModal.style.display = "flex";
  }

  function closeAuthModalHandler() {
    authModal.style.display = "none";
  }

  openAuthModalBtn.addEventListener("click", openAuthModalHandler);
  closeAuthModal.addEventListener("click", closeAuthModalHandler);

  authModal.addEventListener("click", (e) => {
    if (e.target === authModal) closeAuthModalHandler();
  });

  googleAuthBtn.addEventListener("click", async () => {
    if (!auth) {
      alert("Firebase Auth is not initialized. Please configure FIREBASE_* environment variables.");
      return;
    }
    try {
      const provider = new firebase.auth.GoogleAuthProvider();
      await auth.signInWithPopup(provider);
      closeAuthModalHandler();
    } catch (err) {
      console.error("Google Sign-In error:", err);
      if (err.code !== "auth/popup-closed-by-user") {
        alert(err.message || "Google Sign-In failed.");
      }
    }
  });

  guestAuthBtn.addEventListener("click", async () => {
    const hasUsedGuestPass = localStorage.getItem(GUEST_PASS_KEY) === "true";
    if (hasUsedGuestPass) {
      showGuestExpiredUI();
      return;
    }

    if (!auth) {
      // Local fallback mode when Firebase config env vars aren't set
      localStorage.setItem(GUEST_PASS_KEY, "true");
      sessionStorage.setItem(GUEST_SESSION_KEY, "active");
      showSignedInUI({ displayName: "Guest User", photoURL: "", isAnonymous: true }, true);
      closeAuthModalHandler();
      return;
    }

    try {
      await auth.signInAnonymously();
      closeAuthModalHandler();
    } catch (err) {
      console.error("Guest Auth error:", err);
      // Fallback if Firebase anonymous auth is disabled in console
      localStorage.setItem(GUEST_PASS_KEY, "true");
      sessionStorage.setItem(GUEST_SESSION_KEY, "active");
      showSignedInUI({ displayName: "Guest User", photoURL: "", isAnonymous: true }, true);
      closeAuthModalHandler();
    }
  });

  signOutBtn.addEventListener("click", async () => {
    sessionStorage.removeItem(GUEST_SESSION_KEY);
    if (auth) {
      try {
        await auth.signOut();
      } catch (err) {
        console.error("Sign-out error:", err);
      }
    }
    currentUser = null;
    showSignedOutUI();
  });

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
    if (!canUserSearch()) {
      showGuestExpiredUI();
      openAuthModalHandler();
      return;
    }

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
      if (canUserSearch()) {
        searchBtn.disabled = false;
        searchInput.disabled = false;
      }
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
    if (!canUserSearch()) {
      showGuestExpiredUI();
      openAuthModalHandler();
      return;
    }

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
      
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      
      obj.innerHTML = Math.floor(easeProgress * (end - start) + start);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }
});
