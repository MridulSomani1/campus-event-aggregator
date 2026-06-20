# 🎓 Campus Event Aggregator

A full-stack web app that scrapes campus events from multiple sources, automatically
categorizes them, removes duplicates, and shows them on a dashboard with a calendar,
charts, search, dark mode, and CSV export.

**Stack:** Python · Flask · SQLite + SQLAlchemy · BeautifulSoup · APScheduler ·
vanilla HTML/CSS/JS · Chart.js · deployed on Render.com

---

## ✨ Features

- Scrapes 2 sources (university events + Eventbrite) with an automatic **mock-data
  fallback** (30 realistic events over the next 30 days) if the sites block scraping.
- **De-duplicates** events by title + date.
- **Auto-categorizes** every event: Academic / Sports / Social / Career / Other.
- Dashboard: today's events highlighted, full feed, category tabs, **calendar with
  event dots**, and a **donut chart** of counts by category.
- **Real-time search** by title or location.
- **Countdown** on each card ("today", "tomorrow", "in 3 days").
- **CSV export** of upcoming events.
- **Dark mode** saved to `localStorage`.
- **Last-updated** timestamp from the scrape log.
- **APScheduler** re-scrapes every 6 hours and on first startup.

---

## 🗂 Project structure

```
campu_event/
├── app.py            # Flask server + all API routes
├── models.py         # database tables (Event, ScrapeLog)
├── database.py       # SQLAlchemy engine + session setup
├── scraper.py        # scraping + mock data + dedup + save
├── scheduler.py      # APScheduler (every 6h, seeds DB on boot)
├── categorizer.py    # keyword-based category assignment
├── requirements.txt
├── render.yaml       # Render.com deploy config
├── .gitignore
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    └── index.html
```

---

## 💻 Run it locally

```powershell
# 1. (Optional but recommended) create a virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the app
python app.py
```

Then open **http://localhost:5000** in your browser. On first run the scraper fills
the database automatically, so you'll see 30 events right away.

---

## 🔌 API routes

| Method | Route               | What it does                                        |
|--------|---------------------|-----------------------------------------------------|
| GET    | `/events`           | All events. Supports `?category=` and `?search=`    |
| GET    | `/events/today`     | Only today's events                                 |
| GET    | `/events/calendar`  | Events grouped by date (for the calendar)           |
| GET    | `/stats`            | Counts per category + last scrape time              |
| POST   | `/scrape`           | Manually trigger the scraper                        |
| GET    | `/export`           | Download upcoming events as CSV                     |

---

## 🌐 Deploy to the internet (GitHub → Render)

### Step 0 — Install Git (one time)
Download from **https://git-scm.com/download/win**, install with default options,
then **close and reopen** your terminal. Check it works:
```powershell
git --version
```
*(Prefer clicking? Install **GitHub Desktop** from https://desktop.github.com instead
and use its "Add Local Repository" → "Publish" buttons — it does steps 1–3 for you.)*

### Step 1 — Put the code in a Git repo
From inside the `campu_event` folder:
```powershell
git init
git add .
git commit -m "Campus Event Aggregator"
git branch -M main
```

### Step 2 — Create a GitHub repo and push
1. Go to **https://github.com/new**.
2. Name it `campus-event-aggregator`, leave it **Public**, **don't** add a README
   (you already have one), click **Create repository**.
3. GitHub shows you a URL. Run these (replace `YOUR_USERNAME`):
```powershell
git remote add origin https://github.com/YOUR_USERNAME/campus-event-aggregator.git
git push -u origin main
```
Refresh the GitHub page — your files should appear.

### Step 3 — Connect to Render and go live
1. Sign up / log in at **https://render.com** (use "Sign in with GitHub").
2. Click **New +** → **Blueprint**.
3. Select your `campus-event-aggregator` repo. Render reads `render.yaml`
   automatically and fills in the build/start commands.
4. Click **Apply** / **Create Resources**.
5. Wait ~2–4 minutes for the build. When it says **Live**, click the URL at the
   top (looks like `https://campus-event-aggregator.onrender.com`).

**That's your live link — share it!** 🎉

> **Free-tier note:** Render free services "sleep" after ~15 minutes of no traffic,
> so the first visit after a while may take ~30–50 seconds to wake up. Also, the
> SQLite file resets when the service restarts — but that's fine here because the
> scheduler re-scrapes and refills the database automatically on every startup.

---

## 🔧 Swapping in real scraping later

Open `scraper.py` and read the big comment block at the top. In short:
1. Put the real page URL in `UNIVERSITY_URL` / `EVENTBRITE_URL`.
2. Open the site, press **F12**, inspect an event card, and copy its HTML
   classes.
3. Update the `soup.select(...)` selectors to match those classes.
4. Run `python scraper.py` to test. If real events come back, the mock fallback is
   skipped automatically — nothing else in the app needs to change.
