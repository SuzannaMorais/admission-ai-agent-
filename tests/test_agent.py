from admission_agent.agent import run_agent_turn
from admission_agent.models import ConversationMessage
from tests.support.fake_anthropic import FakeAnthropicClient, text_response, tool_use_response


def test_run_agent_turn_returns_final_text_with_no_tool_use(db_session, sample_student):
    client = FakeAnthropicClient([text_response("Our office hours are 9-5.")])
    reply = run_agent_turn(db_session, sample_student.id, "What are your office hours?", client=client)
    assert reply == "Our office hours are 9-5."


def test_run_agent_turn_executes_tool_then_returns_text(db_session, sample_student):
    client = FakeAnthropicClient([
        tool_use_response("search_knowledge_base", {"query": "admission fee"}),
        text_response("The admission fee is 25,000."),
    ])
    reply = run_agent_turn(db_session, sample_student.id, "What's the admission fee?", client=client)
    assert reply == "The admission fee is 25,000."


def test_run_agent_turn_stops_after_max_iterations(db_session, sample_student):
    client = FakeAnthropicClient([tool_use_response("search_knowledge_base", {"query": "x"})] * 10)
    reply = run_agent_turn(db_session, sample_student.id, "confusing question", client=client, max_tool_iterations=2)
    assert "admission staff" in reply.lower()


def test_run_agent_turn_persists_conversation_messages(db_session, sample_student):
    client = FakeAnthropicClient([text_response("ok")])
    run_agent_turn(db_session, sample_student.id, "hello", client=client)
    messages = db_session.query(ConversationMessage).filter_by(student_id=sample_student.id).all()
    assert [m.role for m in messages] == ["parent", "agent"]
