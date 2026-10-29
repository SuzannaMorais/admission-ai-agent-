from datetime import date

from admission_agent.models import Parent, Student


def test_create_parent_and_student_round_trip(db_session):
    parent = Parent(name="Dr. Ram", phone="9990001111")
    db_session.add(parent)
    db_session.commit()

    student = Student(parent_id=parent.id, name="Suzanna", dob=date(2015, 4, 1), grade_applied="3")
    db_session.add(student)
    db_session.commit()

    fetched = db_session.query(Student).filter_by(name="Suzanna").one()
    assert fetched.state == "waiting_for_student_details"
    assert fetched.parent_id == parent.id
