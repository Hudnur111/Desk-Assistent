from pathlib import Path

import pytest

import jarvis.tools.documents as documents_module
from jarvis.tools.documents import document_tools


def _tools() -> dict[str, object]:
    return {tool.name: tool for tool in document_tools()}


@pytest.mark.asyncio
async def test_create_read_and_append_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documents_module, "DOCUMENTS_DIR", tmp_path)
    tools = _tools()

    create_result = await tools["create_document"].handler(
        title="Angebot", content="Erster Absatz.\n\nZweiter Absatz."
    )
    doc_path = tmp_path / "Angebot.docx"
    assert str(doc_path) in create_result
    assert doc_path.is_file()

    read_result = await tools["read_document"].handler(path=str(doc_path))
    assert "Angebot" in read_result
    assert "Erster Absatz." in read_result
    assert "Zweiter Absatz." in read_result

    append_result = await tools["append_to_document"].handler(
        path=str(doc_path), text="Dritter Absatz."
    )
    assert "angehaengt" in append_result

    read_after_append = await tools["read_document"].handler(path=str(doc_path))
    assert "Dritter Absatz." in read_after_append


@pytest.mark.asyncio
async def test_read_document_missing_file_returns_error_text() -> None:
    tools = _tools()
    result = await tools["read_document"].handler(path="/does/not/exist.docx")
    assert "nicht gefunden" in result


@pytest.mark.asyncio
async def test_append_to_document_missing_file_returns_error_text() -> None:
    tools = _tools()
    result = await tools["append_to_document"].handler(
        path="/does/not/exist.docx", text="egal"
    )
    assert "nicht gefunden" in result
