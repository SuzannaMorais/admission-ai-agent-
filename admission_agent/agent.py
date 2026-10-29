from admission_agent.models import ConversationMessage, Parent, Student
from admission_agent.tools import TOOL_DISPATCH, TOOL_SCHEMAS

MODEL = "claude-sonnet-5"

FALLBACK_REPLY = "I need to check with our admission staff and will get back to you."

SYSTEM_PROMPT = """You are an AI: Admission Assistant.
Your responsibility is to: Help parents with admission enquiries and provide accurate school information.
You can: Answer questions about fees, eligibility, deadlines and admission procedures.
You cannot: Approve or reject admissions or disclose confidential information.
When uncertain, you: Search for verified information or ask school staff for help.
You must ask a human when: A query requires an exception, final approval or a decision beyond your authority.

When uncertain, follow this order:
1. Search the knowledge base.
2. Try another tool or database.
3. Ask the parent for clarification.
4. Ask a human expert or school staff.
5. Stop if the answer cannot be verified.
"""


def _build_context_block(student: Student, parent: Parent) -> str:
    return (
        f"Case context — student: {student.name}, grade applied: {student.grade_applied}, "
        f"state: {student.state}, parent contact: {parent.phone} "
        f"(preferred channel: {parent.preferred_channel})."
    )


def _extract_text(content) -> str:
    return "".join(block.text for block in content if block.type == "text")


def run_agent_turn(db, student_id: int, parent_message: str, client=None, max_tool_iterations: int = 6) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    parent_msg = ConversationMessage(student_id=student_id, role="parent", content=parent_message)
    db.add(parent_msg)
    db.commit()

    student = db.query(Student).filter_by(id=student_id).one()
    parent = db.query(Parent).filter_by(id=student.parent_id).one()

    history = (
        db.query(ConversationMessage)
        .filter_by(student_id=student_id)
        .order_by(ConversationMessage.id)
        .all()
    )

    messages = [{"role": "user", "content": _build_context_block(student, parent)}]
    for entry in history:
        role = "user" if entry.role == "parent" else "assistant"
        messages.append({"role": role, "content": entry.content})

    iterations = 0
    final_text = FALLBACK_REPLY

    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )

        if response.stop_reason != "tool_use":
            final_text = _extract_text(response.content)
            break

        if iterations >= max_tool_iterations:
            final_text = FALLBACK_REPLY
            break

        iterations += 1
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_fn = TOOL_DISPATCH[block.name]
                result = tool_fn(db=db, **block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                )
        messages.append({"role": "user", "content": tool_results})

    agent_msg = ConversationMessage(student_id=student_id, role="agent", content=final_text)
    db.add(agent_msg)
    db.commit()
    return final_text
