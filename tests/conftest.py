import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from admission_agent.db import Base
from admission_agent.models import Parent, Student


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_student(db_session):
    parent = Parent(name="Dr. Ram", phone="9990001111")
    db_session.add(parent)
    db_session.commit()

    student = Student(parent_id=parent.id, name="Suzanna", dob=date(2015, 4, 1), grade_applied="3")
    db_session.add(student)
    db_session.commit()
    return student


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient

    from admission_agent.api import app
    from admission_agent.db import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
