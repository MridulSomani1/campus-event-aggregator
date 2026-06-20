# scraper.py
# ---------------------------------------------------------------------------
# This file is responsible for GETTING the event data. It tries to scrape two
# real sources with BeautifulSoup + Requests. If those sites block us (which
# is very common on free tiers, and Eventbrite actively blocks bots), it
# automatically falls back to a built-in MOCK dataset of 30 realistic events.
#
# After collecting raw events it:
#   1. categorizes each one (categorizer.py)
#   2. de-duplicates by (title + date)
#   3. saves new events to the database
#   4. writes a ScrapeLog row so we know when it last ran
#
# ===========================================================================
# HOW TO SWAP IN REAL URLS LATER  (read me!)
# ===========================================================================
# Two functions below do real scraping: scrape_university() and
# scrape_eventbrite(). They currently point at example URLs and CSS selectors.
# To make them work against a REAL site:
#   1. Open the target site in your browser and press F12 (Developer Tools).
#   2. Use the "inspect" arrow to click on an event card on the page.
#   3. Note the HTML tags/classes wrapping the title, date, location, link.
#      e.g. <div class="event-card"> ... <h3 class="event-title"> ... </h3>
#   4. Put the real page URL in UNIVERSITY_URL / EVENTBRITE_URL below.
#   5. Update the soup.select(...) / .find(...) selectors to match those
#      classes you found in step 3.
#   6. Run `python scraper.py` directly to test. If real events come back,
#      the mock fallback is skipped automatically.
# Nothing else in the app needs to change — the database, API, and frontend
# all work the same whether the data is real or mock.
# ===========================================================================

from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from database import SessionLocal
from models import Event, ScrapeLog
from categorizer import categorize

# ---- Real source configuration (edit these to point at live pages) --------
UNIVERSITY_URL = "https://events.university.edu/calendar"   # <-- replace
EVENTBRITE_URL = "https://www.eventbrite.com/d/online/campus/"  # <-- replace

# A browser-like User-Agent makes us look less like a bot. Some sites still
# block scraping; that is expected and handled by the mock fallback.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# REAL SCRAPER #1 — University events page
# ---------------------------------------------------------------------------
def scrape_university():
    """Try to scrape the university events calendar. Returns a list of event
    dictionaries, or an empty list if the site blocks us / structure differs."""
    events = []
    try:
        # Download the page HTML (timeout so we never hang forever).
        response = requests.get(UNIVERSITY_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()  # raise an error for 4xx/5xx responses

        # Parse the HTML into a searchable tree.
        soup = BeautifulSoup(response.text, "html.parser")

        # ---- EDIT THESE SELECTORS to match the real site (see header note) --
        for card in soup.select(".event-card"):
            title_el = card.select_one(".event-title")
            date_el = card.select_one(".event-date")
            location_el = card.select_one(".event-location")
            link_el = card.select_one("a")

            if not title_el or not date_el:
                continue  # skip cards missing the essentials

            events.append({
                "title": title_el.get_text(strip=True),
                "date": date_el.get_text(strip=True),     # expect "YYYY-MM-DD"
                "time": "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "source": "University Events",
                "link": link_el["href"] if link_el and link_el.has_attr("href") else "",
            })
    except Exception as e:
        # Any failure (blocked, offline, layout changed) -> return nothing and
        # let the mock fallback take over.
        print(f"[scraper] University scrape failed: {e}")

    return events


# ---------------------------------------------------------------------------
# REAL SCRAPER #2 — Eventbrite public listings for the campus city
# ---------------------------------------------------------------------------
def scrape_eventbrite():
    """Try to scrape Eventbrite public listings. Eventbrite aggressively blocks
    bots, so this usually returns empty and we fall back to mock data."""
    events = []
    try:
        response = requests.get(EVENTBRITE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # ---- EDIT THESE SELECTORS to match Eventbrite's current markup -----
        for card in soup.select("div.discover-search-desktop-card"):
            title_el = card.select_one("h2")
            date_el = card.select_one("p")
            link_el = card.select_one("a")

            if not title_el:
                continue

            events.append({
                "title": title_el.get_text(strip=True),
                "date": date_el.get_text(strip=True) if date_el else "",
                "time": "",
                "location": "Campus City",
                "source": "Eventbrite",
                "link": link_el["href"] if link_el and link_el.has_attr("href") else "",
            })
    except Exception as e:
        print(f"[scraper] Eventbrite scrape failed: {e}")

    return events


# ---------------------------------------------------------------------------
# MOCK DATA — 30 realistic events spread across the next 30 days
# ---------------------------------------------------------------------------
def get_mock_events():
    """Return 30 realistic campus events covering all 5 categories, with dates
    spread across the next 30 days starting from today."""
    today = datetime.now().date()

    # Each tuple: (days_from_today, title, time, location, source, link)
    raw = [
        (0,  "Intro to Machine Learning Seminar", "10:00 AM", "Maxwell Hall, Room 204", "University Events", "https://events.university.edu/ml-seminar"),
        (0,  "Pickup Basketball at the Rec",       "06:00 PM", "Thompson Recreation Center", "University Events", "https://events.university.edu/rec-basketball"),
        (1,  "Spring Career Fair",                 "11:00 AM", "Student Union Ballroom",     "University Events", "https://events.university.edu/career-fair"),
        (1,  "Open Mic Night",                     "08:00 PM", "The Grind Coffeehouse",      "Eventbrite",        "https://eventbrite.com/open-mic-night"),
        (2,  "Quantum Physics Guest Lecture",      "02:00 PM", "Feynman Auditorium",         "University Events", "https://events.university.edu/quantum-lecture"),
        (3,  "Intramural Soccer Championship",     "04:30 PM", "North Athletic Fields",      "University Events", "https://events.university.edu/soccer-final"),
        (4,  "Resume Workshop with Career Services","01:00 PM", "Career Center, Room 110",    "University Events", "https://events.university.edu/resume-workshop"),
        (5,  "Friday Night Movie: Inception",      "09:00 PM", "Memorial Lawn (outdoor)",    "Eventbrite",        "https://eventbrite.com/movie-night"),
        (6,  "Undergraduate Research Symposium",   "09:00 AM", "Science Complex Atrium",     "University Events", "https://events.university.edu/research-symposium"),
        (7,  "Tech Startup Networking Mixer",      "06:30 PM", "Innovation Hub",             "Eventbrite",        "https://eventbrite.com/startup-mixer"),
        (8,  "Yoga in the Park",                   "07:30 AM", "Central Quad",               "University Events", "https://events.university.edu/yoga"),
        (9,  "International Food Festival",         "12:00 PM", "Student Union Plaza",        "Eventbrite",        "https://eventbrite.com/food-festival"),
        (10, "Calculus II Review Session",         "05:00 PM", "Maxwell Hall, Room 118",     "University Events", "https://events.university.edu/calc-review"),
        (11, "Volleyball vs. State University",    "07:00 PM", "Thompson Arena",             "University Events", "https://events.university.edu/volleyball"),
        (12, "Alumni Mentorship Coffee Chat",      "10:00 AM", "Career Center Lounge",       "University Events", "https://events.university.edu/mentorship"),
        (13, "Spring Concert: The Local Band",     "08:00 PM", "Amphitheater",               "Eventbrite",        "https://eventbrite.com/spring-concert"),
        (14, "History of Art Colloquium",          "03:00 PM", "Humanities Building 302",    "University Events", "https://events.university.edu/art-colloquium"),
        (15, "5K Charity Fun Run",                 "08:00 AM", "Campus Loop Trail",          "Eventbrite",        "https://eventbrite.com/charity-run"),
        (16, "Engineering Career Panel",           "04:00 PM", "Engineering Hall Auditorium","University Events", "https://events.university.edu/eng-panel"),
        (17, "Board Game Night",                   "07:00 PM", "Student Union, Room 250",    "University Events", "https://events.university.edu/board-games"),
        (18, "Biology Research Workshop",          "01:30 PM", "Science Complex Lab 4",      "University Events", "https://events.university.edu/bio-workshop"),
        (19, "Tennis Doubles Tournament",          "09:00 AM", "West Tennis Courts",         "University Events", "https://events.university.edu/tennis"),
        (20, "LinkedIn Profile Building Session",  "02:00 PM", "Career Center, Room 110",    "University Events", "https://events.university.edu/linkedin"),
        (21, "Karaoke Night",                      "09:00 PM", "The Grind Coffeehouse",      "Eventbrite",        "https://eventbrite.com/karaoke"),
        (22, "Economics Guest Speaker Series",     "11:00 AM", "Business School Room 140",   "University Events", "https://events.university.edu/econ-speaker"),
        (23, "Homecoming Football Game",           "06:00 PM", "Memorial Stadium",           "University Events", "https://events.university.edu/homecoming"),
        (24, "Internship Info Session: Google",    "05:30 PM", "Innovation Hub Auditorium",  "Eventbrite",        "https://eventbrite.com/google-info"),
        (26, "Welcome Back BBQ",                   "12:00 PM", "Central Quad",               "University Events", "https://events.university.edu/welcome-bbq"),
        (28, "Astronomy Night & Telescope Viewing","08:30 PM", "Observatory Rooftop",        "University Events", "https://events.university.edu/astronomy"),
        (29, "Entrepreneurship Pitch Competition", "03:00 PM", "Innovation Hub",             "Eventbrite",        "https://eventbrite.com/pitch-competition"),
    ]

    events = []
    for days_ahead, title, time, location, source, link in raw:
        event_date = today + timedelta(days=days_ahead)
        events.append({
            "title": title,
            "date": event_date.strftime("%Y-%m-%d"),
            "time": time,
            "location": location,
            "source": source,
            "link": link,
        })
    return events


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT — collect, categorize, de-duplicate, and save.
# ---------------------------------------------------------------------------
def run_scraper():
    """Run the full scrape pipeline. Returns a dict summary of what happened."""
    print("[scraper] Starting scrape run...")

    # 1) Try the real sources first.
    collected = []
    collected.extend(scrape_university())
    collected.extend(scrape_eventbrite())

    # 2) If real scraping returned nothing (blocked/offline), use mock data.
    if not collected:
        print("[scraper] No real events found — using mock dataset.")
        collected = get_mock_events()

    # 3) Open a database session.
    db = SessionLocal()
    added = 0
    try:
        # Build a set of (title, date) pairs already in the DB so we can skip
        # duplicates quickly.
        existing = {
            (title, date)
            for (title, date) in db.query(Event.title, Event.date).all()
        }
        # Also track duplicates WITHIN this batch (e.g. same event on both sites).
        seen_this_run = set()

        for ev in collected:
            key = (ev["title"], ev["date"])

            # 4) De-duplicate by (title + date).
            if key in existing or key in seen_this_run:
                continue
            seen_this_run.add(key)

            # 5) Categorize the event automatically.
            category = categorize(ev["title"], ev.get("location", ""))

            # 6) Create and stage the new Event row.
            db.add(Event(
                title=ev["title"],
                date=ev["date"],
                time=ev.get("time", ""),
                location=ev.get("location", ""),
                category=category,
                source=ev.get("source", ""),
                link=ev.get("link", ""),
            ))
            added += 1

        # 7) Count total events after this run and write a scrape log entry.
        db.flush()  # send pending inserts so the count below is accurate
        total = db.query(Event).count()
        db.add(ScrapeLog(
            run_at=datetime.utcnow(),
            events_added=added,
            total_events=total,
        ))

        db.commit()  # save everything permanently
        print(f"[scraper] Done. Added {added} new events. Total now {total}.")
        return {"events_added": added, "total_events": total}
    except Exception as e:
        db.rollback()  # undo partial changes if something went wrong
        print(f"[scraper] ERROR during save: {e}")
        return {"events_added": 0, "total_events": 0, "error": str(e)}
    finally:
        db.close()


# Allow running this file directly to test scraping: `python scraper.py`
if __name__ == "__main__":
    from database import init_db
    init_db()
    run_scraper()
