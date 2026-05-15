from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fpl_data.db")

# check_same_thread=False is needed for SQLite in Streamlit/multi-thread environments
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Generator to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Creates the tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
