# models.py
# ---------------------------------------------------------------------------
# This file defines the "shape" of our database tables as Python classes.
# Each class is a table; each attribute is a column. SQLAlchemy turns these
# into real SQL tables for us.
# ---------------------------------------------------------------------------

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from database import Base


class Event(Base):
    """One row in this table = one campus event."""

    __tablename__ = "events"

    # Primary key: a unique auto-incrementing number for each event.
    id = Column(Integer, primary_key=True, index=True)

    # Core event details.
    title = Column(String, nullable=False)         # e.g. "Spring Career Fair"
    date = Column(String, nullable=False)          # stored as "YYYY-MM-DD"
    time = Column(String, nullable=True)           # e.g. "10:00 AM"
    location = Column(String, nullable=True)       # e.g. "Student Union, Room 200"
    category = Column(String, nullable=False)      # Academic/Sports/Social/Career/Other
    source = Column(String, nullable=True)         # which site it came from
    link = Column(String, nullable=True)           # URL to the original listing

    # When this row was added to our database.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Deduplication rule: the database itself refuses to store two events that
    # share the SAME title AND the SAME date. This is a safety net on top of
    # the de-duplication we also do in the scraper.
    __table_args__ = (
        UniqueConstraint("title", "date", name="uq_title_date"),
    )

    def to_dict(self):
        """Convert this row into a plain dictionary so Flask can send it as
        JSON to the frontend."""
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "category": self.category,
            "source": self.source,
            "link": self.link,
        }


class ScrapeLog(Base):
    """One row per time the scraper runs. Lets us show a 'last updated'
    timestamp and keep a history of scrape runs."""

    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_at = Column(DateTime, default=datetime.utcnow)   # when the scrape ran
    events_added = Column(Integer, default=0)            # how many NEW events
    total_events = Column(Integer, default=0)            # total in DB afterward

    def to_dict(self):
        return {
            "id": self.id,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "events_added": self.events_added,
            "total_events": self.total_events,
        }
