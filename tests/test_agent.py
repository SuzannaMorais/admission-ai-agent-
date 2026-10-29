import pytest
from sqlalchemy.exc import NoResultFound

from admission_agent.agent import run_agent_turn
from admission_agent.models import ConversationMessage
from tests.support.fake_anthropic import FakeAnthropicClient, text_response, tool_use_response


def test_run_agent_turn_returns_final_text_with_no_tool_use(db_session, sample_student):
    client = FakeAnthropicClient([text_response("Our office hours are 9-5.")])
    reply = run_agent_turn(db_session, sample_student.id, "What are your office hours?", sample_student.parent.phone, client=client)
    assert reply == "Our office hours are 9-5."


def test_run_agent_turn_executes_tool_then_returns_text(db_session, sample_student):
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "admission fee"}),
        text_response("The admission fee is 25,000."),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "What's the admission fee?", sample_student.parent.phone, client=client)
    assert reply == "The admission fee is 25,000."


def test_run_agent_turn_stops_after_max_iterations(db_session, sample_student):
    client = FakeAnthropicClient([tool_use_response("search_knowledge_base", {"query": "x"})] * 10)
    reply = run_agent_turn(db_session, sample_student.id, "confusing question", sample_student.parent.phone, client=client, max_tool_iterations=2)
    assert "admission staff" in reply.lower()


def test_run_agent_turn_persists_conversation_messages(db_session, sample_student):
    client = FakeAnthropicClient([text_response("ok")])
    run_agent_turn(db_session, sample_student.id, "hello", sample_student.parent.phone, client=client)
    messages = db_session.query(ConversationMessage).filter_by(student_id=sample_student.id).all()
    assert [m.role for m in messages] == ["parent", "agent"]


def test_run_agent_turn_empty_text_reply_falls_back_to_staff_message(db_session, sample_student):
    empty_reply = text_response("")
    client = FakeAnthropicClient([empty_reply])
    reply = run_agent_turn(db_session, sample_student.id, "???", sample_student.parent.phone, client=client)
    assert reply == "I need to check with our admission staff and will get back to you."


def test_run_agent_turn_unknown_student_id_raises_and_persists_nothing(db_session):
    client = FakeAnthropicClient([text_response("ok")])
    with pytest.raises(NoResultFound):
        run_agent_turn(db_session, 999999, "hello", "0000000000", client=client)
    assert db_session.query(ConversationMessage).count() == 0


def test_run_agent_turn_recovers_from_unknown_tool_name(db_session, sample_student):
    client = FakeAnthropicClient([
        tool_use_response("not_a_real_tool", {}),
        text_response("Let me get back to you on that."),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "weird request", sample_student.parent.phone, client=client)
    assert reply == "Let me get back to you on that."


def test_run_agent_turn_withholds_case_data_when_caller_phone_unverified(db_session, sample_student):
    client = FakeAnthropicClient([text_response("I can't confirm that without verifying your identity first.")])
    run_agent_turn(db_session, sample_student.id, "What's my child's application status?", "0000000000", client=client)

    context_message = client.calls[0]["messages"][0]["content"]
    assert sample_student.parent.phone not in context_message
    assert sample_student.state not in context_message
    assert sample_student.name not in context_message


def test_run_agent_turn_includes_case_data_when_caller_phone_verified(db_session, sample_student):
    client = FakeAnthropicClient([text_response("Here you go.")])
    run_agent_turn(db_session, sample_student.id, "What's my child's application status?", sample_student.parent.phone, client=client)

    context_message = client.calls[0]["messages"][0]["content"]
    assert sample_student.name in context_message
    assert sample_student.state in context_message
