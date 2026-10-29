from admission_agent.models import ConversationMessage, Parent, Student
from admission_agent.tools import TOOL_DISPATCH, TOOL_SCHEMAS

MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096

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


UNVERIFIED_CONTEXT_BLOCK = (
    "Case context — caller identity NOT verified. Do not disclose this student's application "
    "status, grade, fees paid, or any other case-specific detail. If the caller needs their "
    "status, use the query_applicant_status tool (it independently re-checks identity) or ask "
    "them to confirm the phone number on file."
)


def _build_context_block(student: Student, parent: Parent, caller_verified: bool) -> str:
    if not caller_verified:
        return UNVERIFIED_CONTEXT_BLOCK
    return (
        f"Case context — caller identity verified. Student: {student.name}, grade applied: "
        f"{student.grade_applied}, state: {student.state}, parent contact: {parent.phone} "
        f"(preferred channel: {parent.preferred_channel})."
    )


def _extract_text(content) -> str:
    return "".join(block.text for block in content if block.type == "text")


def _run_tool(db, block) -> dict:
    tool_fn = TOOL_DISPATCH.get(block.name)
    if tool_fn is None:
        return {"type": "tool_result", "tool_use_id": block.id, "content": f"Unknown tool: {block.name}", "is_error": True}
    try:
        result = tool_fn(db=db, **block.input)
    except Exception as exc:  # noqa: BLE001 - deliberately broad: any tool failure must become a recoverable tool_result, never an unhandled 500
        return {"type": "tool_result", "tool_use_id": block.id, "content": f"Tool error: {exc}", "is_error": True}
    return {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}


def run_agent_turn(
    db,
    student_id: int,
    parent_message: str,
    parent_phone: str,
    client=None,
    max_tool_iterations: int = 6,
) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    student = db.query(Student).filter_by(id=student_id).one()
    parent = db.query(Parent).filter_by(id=student.parent_id).one()
    caller_verified = parent_phone == parent.phone

    parent_msg = ConversationMessage(student_id=student_id, role="parent", content=parent_message)
    db.add(parent_msg)
    db.commit()

    history = (
        db.query(ConversationMessage)
        .filter_by(student_id=student_id)
        .order_by(ConversationMessage.id)
        .all()
    )

    messages = [{"role": "user", "content": _build_context_block(student, parent, caller_verified)}]
    for entry in history:
        role = "user" if entry.role == "parent" else "assistant"
        messages.append({"role": role, "content": entry.content})

    iterations = 0
    final_text = FALLBACK_REPLY

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_SCHEMAS,
        )

        if response.stop_reason != "tool_use":
            extracted = _extract_text(response.content)
            final_text = extracted if extracted else FALLBACK_REPLY
            break

        if iterations >= max_tool_iterations:
            final_text = FALLBACK_REPLY
            break

        iterations += 1
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_results.append(_run_tool(db, block))
        messages.append({"role": "user", "content": tool_results})

    agent_msg = ConversationMessage(student_id=student_id, role="agent", content=final_text)
    db.add(agent_msg)
    db.commit()
    return final_text
