# app.py
# ---------------------------------------------------------------------------
# This is the heart of the application — the Flask web server. It:
#   * serves the frontend page (index.html)
#   * exposes a JSON API the frontend talks to via fetch()
#   * starts the background scheduler so events are scraped automatically
#
# API routes:
#   GET  /events           all events (?category= and ?search= filters)
#   GET  /events/today     only today's events
#   GET  /events/calendar  events grouped by date for the calendar view
#   GET  /stats            event counts by category + last scrape time
#   POST /scrape           manually trigger the scraper
#   GET  /export           download all upcoming events as a CSV file
# ---------------------------------------------------------------------------

import csv
import io
from datetime import datetime

from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS

from database import SessionLocal, init_db
from models import Event, ScrapeLog
from scraper import run_scraper
from scheduler import start_scheduler

# Create the Flask application. It will look for templates/ and static/ folders
# automatically.
app = Flask(__name__)

# Enable CORS so the API can be called from anywhere (handy for testing).
CORS(app)

# Make sure the database tables exist before we do anything else.
init_db()

# Start the background scheduler (also seeds the DB on first run).
start_scheduler()


# ---------------------------------------------------------------------------
# PAGE ROUTE — serve the single-page frontend.
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the main dashboard HTML page."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# GET /events — return all events, newest dates first.
# Supports optional ?category=Sports and ?search=soccer query parameters.
# ---------------------------------------------------------------------------
@app.route("/events")
def get_events():
    # Read optional query parameters from the URL.
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip().lower()

    db = SessionLocal()
    try:
        query = db.query(Event)

        # Filter by category if one was given (and it is not "All").
        if category and category.lower() != "all":
            query = query.filter(Event.category == category)

        # Order events by date so the soonest events come first.
        events = query.order_by(Event.date.asc()).all()

        # Convert to dictionaries.
        result = [e.to_dict() for e in events]

        # Apply the text search in Python (matches title OR location).
        if search:
            result = [
                e for e in result
                if search in (e["title"] or "").lower()
                or search in (e["location"] or "").lower()
            ]

        return jsonify(result)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /events/today — return only events happening today.
# ---------------------------------------------------------------------------
@app.route("/events/today")
def get_today_events():
    today = datetime.now().strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        events = (
            db.query(Event)
            .filter(Event.date == today)
            .order_by(Event.time.asc())
            .all()
        )
        return jsonify([e.to_dict() for e in events])
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /events/calendar — events grouped by date: { "2026-06-18": [ ... ] }.
# The frontend uses this to put dots on the calendar.
# ---------------------------------------------------------------------------
@app.route("/events/calendar")
def get_calendar():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.date.asc()).all()

        grouped = {}
        for e in events:
            grouped.setdefault(e.date, []).append(e.to_dict())

        return jsonify(grouped)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# GET /stats — counts of events per category + when the scraper last ran.
# The frontend uses this for the donut chart and "last updated" label.
# ---------------------------------------------------------------------------
@app.route("/stats")
def get_stats():
    db = SessionLocal()
    try:
        # Count events in each of the five categories.
        categories = ["Academic", "Sports", "Social", "Career", "Other"]
        counts = {}
        for cat in categories:
            counts[cat] = db.query(Event).filter(Event.category == cat).count()

        total = db.query(Event).count()

        # Find the most recent scrape log entry.
        last_log = db.query(ScrapeLog).order_by(ScrapeLog.run_at.desc()).first()
        last_scrape = last_log.run_at.isoformat() if last_log else None

        return jsonify({
            "counts": counts,
            "total": total,
            "last_scrape": last_scrape,
        })
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /scrape — manually trigger the scraper (used by the "Refresh" button).
# ---------------------------------------------------------------------------
@app.route("/scrape", methods=["POST"])
def trigger_scrape():
    summary = run_scraper()
    return jsonify({"status": "ok", "result": summary})


# ---------------------------------------------------------------------------
# GET /export — download all upcoming events as a CSV file.
# ---------------------------------------------------------------------------
@app.route("/export")
def export_csv():
    today = datetime.now().strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        # Only upcoming events (today or later).
        events = (
            db.query(Event)
            .filter(Event.date >= today)
            .order_by(Event.date.asc())
            .all()
        )

        # Build the CSV in memory using Python's csv module.
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Title", "Date", "Time", "Location", "Category", "Source", "Link"])
        for e in events:
            writer.writerow([
                e.title, e.date, e.time, e.location, e.category, e.source, e.link
            ])

        # Send it back as a downloadable file.
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=campus_events.csv"},
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Local development entry point. In production, gunicorn imports `app` instead
# of running this block (see render.yaml).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
