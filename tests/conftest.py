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


TEST_ADMIN_TOKEN = "test-admin-token"


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient

    from admission_agent.api import app, get_admin_token
    from admission_agent.db import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_admin_token] = lambda: TEST_ADMIN_TOKEN
    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"})
        yield test_client
    app.dependency_overrides.clear()
