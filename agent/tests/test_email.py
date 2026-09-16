import pytest

from jarvis.tools.email import build_email_draft_tool


class FakeEmailBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def create_draft(self, to: str, subject: str, body: str) -> str:
        self.calls.append((to, subject, body))
        return f"Entwurf an {to} gespeichert (Betreff: {subject})"


@pytest.mark.asyncio
async def test_email_draft_tool_delegates_to_backend() -> None:
    backend = FakeEmailBackend()
    tool = build_email_draft_tool(backend)

    result = await tool.handler(
        to="kunde@example.com", subject="Angebot", body="Sehr geehrte Damen und Herren,"
    )

    assert backend.calls == [
        ("kunde@example.com", "Angebot", "Sehr geehrte Damen und Herren,")
    ]
    assert "kunde@example.com" in result


def test_email_draft_tool_schema() -> None:
    tool = build_email_draft_tool(FakeEmailBackend())
    schema = tool.to_anthropic_schema()

    assert schema["name"] == "create_email_draft"
    assert set(schema["input_schema"]["required"]) == {"to", "subject", "body"}
