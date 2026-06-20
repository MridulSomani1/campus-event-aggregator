# scheduler.py
# ---------------------------------------------------------------------------
# This file sets up APScheduler, a background scheduler that automatically
# runs our scraper on a timer (every 6 hours) without blocking the web server.
#
# It also exposes start_scheduler() which the app calls on startup. On the
# very first startup we run the scraper immediately so the database is never
# empty when a user opens the page.
# ---------------------------------------------------------------------------

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from models import Event
from scraper import run_scraper

# How often the scraper runs automatically, in hours.
SCRAPE_INTERVAL_HOURS = 6

# A single shared scheduler instance for the whole app.
scheduler = BackgroundScheduler(daemon=True)


def start_scheduler():
    """Start the background scheduler and ensure the database has data.

    Called once when the Flask app boots.
    """
    # 1) On first startup, if the database is empty, run the scraper now so the
    #    user never sees an empty dashboard.
    db = SessionLocal()
    try:
        count = db.query(Event).count()
    finally:
        db.close()

    if count == 0:
        print("[scheduler] Database empty — running scraper immediately.")
        run_scraper()

    # 2) Schedule the scraper to run automatically every 6 hours.
    #    "interval" means "repeat on this fixed interval".
    if not scheduler.get_jobs():
        scheduler.add_job(
            func=run_scraper,
            trigger="interval",
            hours=SCRAPE_INTERVAL_HOURS,
            id="scrape_job",
            replace_existing=True,
        )

    # 3) Start the scheduler if it is not already running.
    if not scheduler.running:
        scheduler.start()
        print(f"[scheduler] Started. Scraper will run every {SCRAPE_INTERVAL_HOURS} hours.")
