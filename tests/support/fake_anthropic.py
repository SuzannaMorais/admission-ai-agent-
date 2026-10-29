class ContentBlock:
    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input
        self.id = id


class FakeMessage:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def text_response(text: str) -> FakeMessage:
    return FakeMessage(stop_reason="end_turn", content=[ContentBlock("text", text=text)])


def tool_use_response(name: str, input: dict) -> FakeMessage:
    return FakeMessage(
        stop_reason="tool_use",
        content=[ContentBlock("tool_use", name=name, input=input, id=f"toolu_{name}")],
    )


REQUIRED_CREATE_KWARGS = ("model", "max_tokens", "messages")


class _FakeMessagesResource:
    def __init__(self, client: "FakeAnthropicClient"):
        self._client = client

    def create(self, **kwargs):
        missing = [name for name in REQUIRED_CREATE_KWARGS if kwargs.get(name) is None]
        if missing:
            raise TypeError(f"messages.create() missing required argument(s): {', '.join(missing)}")
        self._client.calls.append(kwargs)
        return self._client._responses.pop(0)


class FakeAnthropicClient:
    def __init__(self, responses: list[FakeMessage]):
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.messages = _FakeMessagesResource(self)
