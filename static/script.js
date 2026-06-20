// script.js
// ---------------------------------------------------------------------------
// All the frontend logic. It talks to the Flask API using fetch(), then
// builds the HTML for cards, the calendar, and the donut chart. Everything
// updates automatically after a scrape (the Refresh button re-fetches data).
// ---------------------------------------------------------------------------

// ---- Global state we keep track of ----
let currentCategory = "All";   // which filter tab is active
let currentSearch = "";        // current search text
let categoryChart = null;      // the Chart.js instance (so we can update it)
let calendarDate = new Date(); // which month the calendar is showing
let eventsByDate = {};         // calendar data: { "2026-06-18": [...] }

// ---- Grab references to elements we use repeatedly ----
const todayEl = document.getElementById("todayEvents");
const feedEl = document.getElementById("eventFeed");
const searchInput = document.getElementById("searchInput");
const lastUpdatedEl = document.getElementById("lastUpdated");
const calendarGrid = document.getElementById("calendarGrid");
const calendarTitle = document.getElementById("calendarTitle");


// ===========================================================================
// HELPER: figure out the countdown text ("today", "tomorrow", "in 3 days").
// ===========================================================================
function getCountdown(dateStr) {
    // Parse "YYYY-MM-DD" into a Date at local midnight.
    const eventDate = new Date(dateStr + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0); // strip the time so we compare whole days

    // Difference in whole days.
    const msPerDay = 1000 * 60 * 60 * 24;
    const diff = Math.round((eventDate - today) / msPerDay);

    if (diff < 0) return "past";
    if (diff === 0) return "today";
    if (diff === 1) return "tomorrow";
    return `in ${diff} days`;
}


// ===========================================================================
// HELPER: format "2026-06-18" into "Thu, Jun 18".
// ===========================================================================
function formatDate(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
    });
}


// ===========================================================================
// HELPER: build the HTML for a single event card.
// ===========================================================================
function cardHTML(ev) {
    const countdown = getCountdown(ev.date);
    // Use a safe category class (falls back to "Other" if unexpected).
    const cat = ev.category || "Other";

    return `
        <div class="card cat-${cat}">
            <div class="card-top">
                <span class="badge cat-${cat}">${cat}</span>
                <span class="countdown">${countdown}</span>
            </div>
            <div class="card-title">${ev.title}</div>
            <div class="card-row">📅 ${formatDate(ev.date)}${ev.time ? " · " + ev.time : ""}</div>
            <div class="card-row">📍 ${ev.location || "TBA"}</div>
            <div class="card-row">🔗 ${ev.source || "Unknown source"}</div>
            ${ev.link ? `<a class="card-link" href="${ev.link}" target="_blank" rel="noopener">View event →</a>` : ""}
        </div>
    `;
}


// ===========================================================================
// LOAD: today's events (the highlighted section at the top).
// ===========================================================================
async function loadTodayEvents() {
    const res = await fetch("/events/today");
    const events = await res.json();

    if (events.length === 0) {
        todayEl.innerHTML = `<p class="empty">No events scheduled for today.</p>`;
        return;
    }
    todayEl.innerHTML = events.map(cardHTML).join("");
}


// ===========================================================================
// LOAD: the full event feed, honoring the active category + search filters.
// We pass the filters to the API as query parameters.
// ===========================================================================
async function loadEvents() {
    // Build the query string, e.g. /events?category=Sports&search=soccer
    const params = new URLSearchParams();
    if (currentCategory !== "All") params.append("category", currentCategory);
    if (currentSearch) params.append("search", currentSearch);

    const res = await fetch("/events?" + params.toString());
    const events = await res.json();

    if (events.length === 0) {
        feedEl.innerHTML = `<p class="empty">No events match your filters.</p>`;
        return;
    }
    feedEl.innerHTML = events.map(cardHTML).join("");
}


// ===========================================================================
// LOAD: stats — updates the donut chart and the "last updated" label.
// ===========================================================================
async function loadStats() {
    const res = await fetch("/stats");
    const data = await res.json();

    // Update the "last updated" text.
    if (data.last_scrape) {
        const when = new Date(data.last_scrape + "Z"); // stored as UTC
        lastUpdatedEl.textContent =
            "Last updated: " + when.toLocaleString();
    } else {
        lastUpdatedEl.textContent = "Last updated: never";
    }

    // Update (or create) the donut chart.
    renderChart(data.counts);
}


// ===========================================================================
// CHART: draw/update the donut chart of events per category.
// ===========================================================================
function renderChart(counts) {
    const labels = Object.keys(counts);     // ["Academic", "Sports", ...]
    const values = Object.values(counts);   // [5, 3, 8, ...]

    // Colors matching our CSS category colors.
    const colors = {
        Academic: "#3b82f6",
        Sports: "#10b981",
        Social: "#f59e0b",
        Career: "#8b5cf6",
        Other: "#64748b",
    };
    const bg = labels.map((l) => colors[l] || "#64748b");

    // If the chart already exists, just update its data (no flicker).
    if (categoryChart) {
        categoryChart.data.labels = labels;
        categoryChart.data.datasets[0].data = values;
        categoryChart.update();
        return;
    }

    // Otherwise create it for the first time.
    const ctx = document.getElementById("categoryChart").getContext("2d");
    categoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{ data: values, backgroundColor: bg, borderWidth: 0 }],
        },
        options: {
            plugins: {
                legend: { position: "bottom", labels: { boxWidth: 14 } },
            },
        },
    });
}


// ===========================================================================
// CALENDAR: load grouped-by-date data, then draw the current month.
// ===========================================================================
async function loadCalendar() {
    const res = await fetch("/events/calendar");
    eventsByDate = await res.json();
    renderCalendar();
}

function renderCalendar() {
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth(); // 0 = January

    // Title like "June 2026".
    calendarTitle.textContent = calendarDate.toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
    });

    // Start fresh.
    calendarGrid.innerHTML = "";

    // Weekday header row.
    const dows = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
    for (const d of dows) {
        const cell = document.createElement("div");
        cell.className = "cal-dow";
        cell.textContent = d;
        calendarGrid.appendChild(cell);
    }

    // What day of the week does the 1st fall on? (0=Sunday)
    const firstDay = new Date(year, month, 1).getDay();
    // How many days are in this month?
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Add blank cells before the 1st so the dates line up under weekdays.
    for (let i = 0; i < firstDay; i++) {
        const blank = document.createElement("div");
        blank.className = "cal-day empty-cell";
        calendarGrid.appendChild(blank);
    }

    // Today's date string for highlighting.
    const todayStr = new Date().toISOString().slice(0, 10);

    // One cell per day of the month.
    for (let day = 1; day <= daysInMonth; day++) {
        // Build the "YYYY-MM-DD" key for this cell.
        const mm = String(month + 1).padStart(2, "0");
        const dd = String(day).padStart(2, "0");
        const dateStr = `${year}-${mm}-${dd}`;

        const cell = document.createElement("div");
        cell.className = "cal-day has-day";
        if (dateStr === todayStr) cell.classList.add("today");

        // The day number.
        const num = document.createElement("span");
        num.textContent = day;
        cell.appendChild(num);

        // If there are events on this day, add a dot.
        if (eventsByDate[dateStr] && eventsByDate[dateStr].length > 0) {
            const dot = document.createElement("span");
            dot.className = "cal-dot";
            cell.title = eventsByDate[dateStr].length + " event(s)";
            cell.appendChild(dot);
        }

        calendarGrid.appendChild(cell);
    }
}


// ===========================================================================
// REFRESH EVERYTHING: re-fetch all data. Called on page load and after a
// scrape so the cards, chart, and calendar all stay in sync.
// ===========================================================================
async function refreshAll() {
    await Promise.all([
        loadTodayEvents(),
        loadEvents(),
        loadStats(),
        loadCalendar(),
    ]);
}


// ===========================================================================
// EVENT LISTENERS — wire up the buttons, tabs, and search box.
// ===========================================================================

// Category filter tabs.
document.getElementById("categoryTabs").addEventListener("click", (e) => {
    if (!e.target.classList.contains("tab")) return;
    // Move the "active" highlight to the clicked tab.
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    e.target.classList.add("active");
    currentCategory = e.target.dataset.category;
    loadEvents();
});

// Search box — filters in real time as you type.
searchInput.addEventListener("input", () => {
    currentSearch = searchInput.value.trim();
    loadEvents();
});

// Refresh button — triggers the scraper, then reloads all data.
document.getElementById("refreshBtn").addEventListener("click", async (e) => {
    const btn = e.target;
    btn.disabled = true;
    btn.textContent = "Scraping…";
    await fetch("/scrape", { method: "POST" }); // run the scraper on the server
    await refreshAll();                          // pull fresh data
    btn.disabled = false;
    btn.textContent = "↻ Refresh";
});

// Export CSV button — just navigate to /export, which downloads the file.
document.getElementById("exportBtn").addEventListener("click", () => {
    window.location.href = "/export";
});

// Calendar month navigation.
document.getElementById("prevMonth").addEventListener("click", () => {
    calendarDate.setMonth(calendarDate.getMonth() - 1);
    renderCalendar();
});
document.getElementById("nextMonth").addEventListener("click", () => {
    calendarDate.setMonth(calendarDate.getMonth() + 1);
    renderCalendar();
});


// ===========================================================================
// DARK MODE — toggle and remember the choice in localStorage.
// ===========================================================================
const themeToggle = document.getElementById("themeToggle");

// On load, apply the saved theme (if any).
if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark");
    themeToggle.textContent = "☀️";
}

themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    const isDark = document.body.classList.contains("dark");
    themeToggle.textContent = isDark ? "☀️" : "🌙";
    // Save the preference so it persists across visits.
    localStorage.setItem("theme", isDark ? "dark" : "light");
});


// ===========================================================================
// GO! Load everything when the page first opens.
// ===========================================================================
refreshAll();
