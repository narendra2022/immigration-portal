// Frontend Logic - US Immigration News Portal

document.addEventListener("DOMContentLoaded", () => {
  // State variables
  let allArticles = [];
  let currentCategory = "all";
  let searchQuery = "";
  
  // Cache DOM elements
  const newsGrid = document.getElementById("news-grid");
  const loader = document.getElementById("news-loader");
  const emptyState = document.getElementById("empty-state");
  const searchInput = document.getElementById("search-input");
  const categoryFilters = document.getElementById("category-filters");
  const refreshBtn = document.getElementById("refresh-btn");
  const refreshIcon = document.getElementById("refresh-icon");
  const themeToggle = document.getElementById("theme-toggle");
  
  // Stats element
  const statTotal = document.getElementById("stat-total");
  const statOfficial = document.getElementById("stat-official");
  const statLastUpdate = document.getElementById("stat-last-update");
  
  // Modal elements
  const detailModal = document.getElementById("detail-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalBadge = document.getElementById("modal-badge");
  const modalTitle = document.getElementById("modal-title");
  const modalSource = document.getElementById("modal-source");
  const modalDate = document.getElementById("modal-date");
  const modalSummary = document.getElementById("modal-summary");
  const modalDesc = document.getElementById("modal-desc");
  const modalLinkBtn = document.getElementById("modal-link-btn");
  const modalCoverageSection = document.getElementById("modal-coverage-section");
  const modalCoverageLinks = document.getElementById("modal-coverage-links");

  // Initialize Lucide Icons
  lucide.createIcons();

  // 1. Theme Toggle Configuration
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  
  themeToggle.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
  });

  // 2. Live Clock Widget
  function updateClock() {
    const clock = document.getElementById("live-time");
    if (!clock) return;
    const now = new Date();
    clock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 3. Helper: Time Ago calculator
  function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const secondsDiff = Math.floor((now - date) / 1000);
    
    if (secondsDiff < 60) return "Just now";
    
    const minutes = Math.floor(secondsDiff / 60);
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days === 1) return "Yesterday";
    if (days < 7) return `${days} days ago`;
    
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  }

  // 4. Calculate Portal Statistics
  function calculateStats(articles) {
    statTotal.textContent = articles.length;
    
    const officialCount = articles.filter(a => a.source_type === "official").length;
    statOfficial.textContent = officialCount;
    
    if (articles.length > 0) {
      // Find the most recent date
      const dates = articles.map(a => new Date(a.pub_date));
      const newestDate = new Date(Math.max.apply(null, dates));
      statLastUpdate.textContent = timeAgo(newestDate);
    } else {
      statLastUpdate.textContent = "-";
    }
  }

  // 5. Generate Card HTML element
  function createCardElement(art, index) {
    const card = document.createElement("div");
    card.className = "news-card";
    card.setAttribute("data-cat", art.category || "General Policy");
    card.style.animationDelay = `${index * 0.05}s`;
    
    // Select category badge class
    let badgeClass = "badge-general";
    const category = art.category || "General Policy";
    if (category === "H-1B Visa") badgeClass = "badge-h1b";
    else if (category === "US Citizenship") badgeClass = "badge-citizen";
    else if (category === "Visa Bulletin") badgeClass = "badge-bulletin";
    else if (category === "USCIS Announcements") badgeClass = "badge-uscis";
    
    // Parse summary text (handling bullets if generated as Markdown list)
    let summaryHTML = "";
    const summaryText = art.summary || "";
    if (summaryText.includes("* ") || summaryText.includes("- ")) {
      const bullets = summaryText.split(/\n[*-]\s+/).map(b => b.replace(/^[*-]\s+/, "").trim()).filter(b => b);
      summaryHTML = `<ul class="summary-bullets">` + 
        bullets.map(b => `<li>${b}</li>`).join("") + 
        `</ul>`;
    } else {
      // Fallback: split by sentences and display as bullets
      const sentences = summaryText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 10);
      summaryHTML = `<ul class="summary-bullets">` + 
        sentences.map(s => `<li>${s.trim()}</li>`).join("") + 
        `</ul>`;
    }

    const title = art.title.replace(/"/g, '&quot;');
    const isOfficial = art.source_type === 'official';
    
    let relHTML = "";
    if (art.related_coverage && art.related_coverage.length > 0) {
      const links = art.related_coverage.slice(0, 3).map(rc => 
        `<a href="${rc.link}" class="related-link" target="_blank" onclick="event.stopPropagation();">${rc.source}</a>`
      ).join(", ");
      relHTML = `<div class="related-box"><span>Also covered:</span> ${links}</div>`;
    }

    card.innerHTML = `
      <div class="card-header">
        <span class="badge ${badgeClass}">${category}</span>
        <span class="time-label">${timeAgo(art.pub_date)}</span>
      </div>
      <h2>${title}</h2>
      ${summaryHTML}
      ${relHTML}
      <div class="card-footer">
        <span class="source-tag">
          <i data-lucide="${isOfficial ? 'shield' : 'globe'}"></i>
          <span>${art.source}</span>
        </span>
        <span class="read-more-trigger">
          <span>Details</span>
          <i data-lucide="chevron-right"></i>
        </span>
      </div>
    `;

    // Click handler to open detail modal
    card.addEventListener("click", () => openModal(art));
    
    return card;
  }

  // 6. Modal Interactivity
  function openModal(art) {
    let badgeClass = "";
    const category = art.category || "General Policy";
    if (category === "H-1B Visa") badgeClass = "badge-h1b";
    else if (category === "US Citizenship") badgeClass = "badge-citizen";
    else if (category === "Visa Bulletin") badgeClass = "badge-bulletin";
    else if (category === "USCIS Announcements") badgeClass = "badge-uscis";

    modalBadge.className = `badge ${badgeClass}`;
    modalBadge.textContent = category;
    modalTitle.textContent = art.title;
    modalSource.textContent = art.source;
    
    const pDate = new Date(art.pub_date);
    modalDate.textContent = pDate.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    
    // Parse summary list for modal
    let summaryHTML = "";
    const summaryText = art.summary || "";
    if (summaryText.includes("* ") || summaryText.includes("- ")) {
      const bullets = summaryText.split(/\n[*-]\s+/).map(b => b.replace(/^[*-]\s+/, "").trim()).filter(b => b);
      summaryHTML = `<ul>` + bullets.map(b => `<li>${b}</li>`).join("") + `</ul>`;
    } else {
      const sentences = summaryText.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 10);
      summaryHTML = `<ul>` + sentences.map(s => `<li>${s.trim()}</li>`).join("") + `</ul>`;
    }
    modalSummary.innerHTML = summaryHTML;
    modalDesc.textContent = art.description;
    
    modalLinkBtn.href = art.link;

    // Handle related coverages in modal
    if (art.related_coverage && art.related_coverage.length > 0) {
      modalCoverageSection.classList.remove("hidden");
      modalCoverageLinks.innerHTML = art.related_coverage.map(rc => `
        <a href="${rc.link}" class="coverage-pill" target="_blank">
          <i data-lucide="external-link"></i>
          <span>${rc.source}</span>
        </a>
      `).join("");
    } else {
      modalCoverageSection.classList.add("hidden");
    }

    // Refresh icons inside modal
    lucide.createIcons({
      nodeList: detailModal.querySelectorAll("[data-lucide]")
    });

    detailModal.classList.remove("hidden");
    document.body.style.overflow = "hidden"; // Disable background scrolling
  }

  function closeModal() {
    detailModal.classList.add("hidden");
    document.body.style.overflow = ""; // Restore background scrolling
  }

  modalCloseBtn.addEventListener("click", closeModal);
  detailModal.addEventListener("click", (e) => {
    if (e.target === detailModal) closeModal();
  });
  
  // Close modal on escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !detailModal.classList.contains("hidden")) {
      closeModal();
    }
  });

  // 7. Core Render Loop
  function renderNews() {
    newsGrid.innerHTML = "";
    
    // Filter logic
    const filtered = allArticles.filter(art => {
      // Category filter
      const matchesCategory = currentCategory === "all" || art.category === currentCategory;
      
      // Search filter
      const text = (art.title + " " + art.description + " " + (art.category || "")).lowerCase();
      const matchesSearch = text.includes(searchQuery.lowerCase());
      
      return matchesCategory && matchesSearch;
    });

    // Check empty state
    if (filtered.length === 0) {
      emptyState.classList.remove("hidden");
    } else {
      emptyState.classList.add("hidden");
      filtered.forEach((art, index) => {
        const card = createCardElement(art, index);
        newsGrid.appendChild(card);
      });
    }

    // Bind icons
    lucide.createIcons({
      nodeList: newsGrid.querySelectorAll("[data-lucide]")
    });
  }

  // Helper string extension for ease
  String.prototype.lowerCase = function() {
    return this.toLowerCase();
  };

  // 8. Search & Filtering Listeners
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value;
    renderNews();
  });

  categoryFilters.addEventListener("click", (e) => {
    const btn = e.target.closest(".pill");
    if (!btn) return;
    
    // Toggle active classes
    categoryFilters.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    
    currentCategory = btn.getAttribute("data-category");
    renderNews();
  });

  // 9. API Trigger: Refresh News Script
  async function triggerRefresh() {
    console.log("Triggering backend scraper API...");
    refreshBtn.disabled = true;
    refreshIcon.classList.add("rotating");
    refreshBtn.querySelector("span").textContent = "Scraping Feeds...";
    
    try {
      const response = await fetch("/api/refresh", {
        method: "POST"
      });
      const data = await response.json();
      
      if (data.status === "success") {
        console.log("News database refreshed successfully!");
        // Re-load news data file
        await loadNewsData();
      } else {
        alert("Scraper completed with error: " + data.message);
      }
    } catch (err) {
      console.error("Refresh request failed:", err);
      alert("Failed to contact the backend scraping server. Make sure run.py is active!");
    } finally {
      refreshBtn.disabled = false;
      refreshIcon.classList.remove("rotating");
      refreshBtn.querySelector("span").textContent = "Refresh News";
    }
  }

  refreshBtn.addEventListener("click", triggerRefresh);

  // 10. Load Data File on Startup
  async function loadNewsData() {
    loader.classList.remove("hidden");
    newsGrid.classList.add("hidden");
    
    try {
      const response = await fetch("news_data.json");
      allArticles = await response.json();
      
      console.log(`Loaded ${allArticles.length} articles.`);
      
      // Calculate Stats
      calculateStats(allArticles);
      
      // Render Card Grid
      renderNews();
      
      loader.classList.add("hidden");
      newsGrid.classList.remove("hidden");
    } catch (err) {
      console.warn("Failed to load news_data.json (may not exist yet).", err);
      allArticles = [];
      loader.classList.add("hidden");
      newsGrid.classList.remove("hidden");
      emptyState.classList.remove("hidden");
    }
  }

  // Execute startup load
  loadNewsData();
});
