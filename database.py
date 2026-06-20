# database.py
# ---------------------------------------------------------------------------
# This file sets up our connection to the SQLite database using SQLAlchemy.
# SQLAlchemy is an "ORM" (Object Relational Mapper). It lets us work with
# database rows as if they were normal Python objects, instead of writing
# raw SQL by hand.
# ---------------------------------------------------------------------------

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# The folder where this file lives. We store the .db file right next to the
# code so it is easy to find. os.path.abspath makes the path absolute so it
# works the same whether we run locally or on Render.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# The location of our SQLite database file.
DB_PATH = os.path.join(BASE_DIR, "events.db")

# The connection string SQLAlchemy uses. "sqlite:///" means "use SQLite and
# read/write to this file path".
DATABASE_URL = f"sqlite:///{DB_PATH}"

# The "engine" is the core object that knows how to talk to the database.
# check_same_thread=False is needed because Flask + APScheduler may touch the
# database from more than one thread.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# A "session" is a workspace for talking to the database (querying, adding,
# deleting). SessionLocal is a factory that creates a fresh session whenever
# we call it.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base is the parent class that all of our database models inherit from.
# It connects the Python classes in models.py to real database tables.
Base = declarative_base()


def init_db():
    """Create all database tables if they do not already exist.

    We import models here (not at the top) so that the model classes are
    registered with Base before we ask Base to build the tables.
    """
    import models  # noqa: F401  (imported for its side effect of registering models)
    Base.metadata.create_all(bind=engine)
