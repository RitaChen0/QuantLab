"""
Pytest configuration for repository tests
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import all models to ensure relationships are properly configured
from app.db.session import ensure_models_imported
from app.db.base import Base

# Ensure all models are imported before creating tables
ensure_models_imported()


@pytest.fixture(scope="function")
def db_session():
    """
    Create a test database session using in-memory SQLite.

    Each test function gets a fresh database session with all tables created.
    After the test completes, the session is rolled back and closed.
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)
