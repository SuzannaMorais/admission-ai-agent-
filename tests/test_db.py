from sqlalchemy import create_engine, inspect

from admission_agent.db import init_db


def test_init_db_creates_all_model_tables_on_a_fresh_engine():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "parents",
        "students",
        "conversation_messages",
        "documents",
        "reminders",
        "approval_requests",
        "calendar_bookings",
    }.issubset(tables)
