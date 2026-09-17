"""Live-Steuerung installierter Microsoft-Office-Apps via COM (Windows only).

Nutzt pywin32, um direkt mit laufenden/neu gestarteten Instanzen von Word,
Excel, PowerPoint und Outlook zu sprechen - im Gegensatz zu tools/documents.py
(reine Dateiformat-Manipulation, plattformunabhaengig) wirkt dies auf echte
App-Instanzen und kann z. B. Words eingebaute Rechtschreibpruefung nutzen.
Auf Nicht-Windows-Systemen liefert office_com_tools() eine leere Liste, damit
der Agent auf Linux/macOS/Raspberry Pi unveraendert weiterlaeuft.
"""

import asyncio
import sys
from pathlib import Path

from .base import Tool

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import win32com.client
    from win32com.client import constants as win32c


def _dispatch(app: str):
    return win32com.client.gencache.EnsureDispatch(app)


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------


async def _word_write(path: str, text: str) -> str:
    def _run() -> str:
        word = _dispatch("Word.Application")
        word.Visible = True
        file_path = str(Path(path).resolve())
        existing = Path(file_path).is_file()
        doc = word.Documents.Open(file_path) if existing else word.Documents.Add()
        doc.Content.InsertAfter("\n" + text if existing else text)
        doc.SaveAs(file_path) if not existing else doc.Save()
        return file_path

    result = await asyncio.to_thread(_run)
    return f"Word-Dokument geschrieben: {result}"


async def _word_check_spelling(path: str) -> str:
    def _run() -> str:
        word = _dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(Path(path).resolve()))
        errors = []
        for error_range in doc.SpellingErrors:
            suggestions = word.GetSpellingSuggestions(error_range.Text)
            best = suggestions.Item(1).Name if suggestions.Count > 0 else "?"
            errors.append(f"'{error_range.Text}' -> Vorschlag: '{best}'")
        grammar = [g.Description for g in doc.GrammaticalErrors]
        doc.Close(SaveChanges=False)
        if not errors and not grammar:
            return "Keine Rechtschreib-/Grammatikfehler gefunden."
        report = ["Rechtschreibfehler:"] + errors + ["Grammatikfehler:"] + grammar
        return "\n".join(report)

    return await asyncio.to_thread(_run)


async def _word_autocorrect(path: str) -> str:
    def _run() -> str:
        word = _dispatch("Word.Application")
        word.Visible = False
        file_path = str(Path(path).resolve())
        doc = word.Documents.Open(file_path)
        fixed = 0
        while doc.SpellingErrors.Count > 0:
            error_range = doc.SpellingErrors.Item(1)
            suggestions = word.GetSpellingSuggestions(error_range.Text)
            if suggestions.Count > 0:
                error_range.Text = suggestions.Item(1).Name
                fixed += 1
            else:
                break
        doc.Save()
        doc.Close()
        return f"{fixed} Rechtschreibfehler korrigiert in {file_path}"

    return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


async def _excel_write_cell(path: str, sheet: str, cell: str, value: str) -> str:
    def _run() -> str:
        excel = _dispatch("Excel.Application")
        excel.Visible = True
        file_path = str(Path(path).resolve())
        existing = Path(file_path).is_file()
        wb = excel.Workbooks.Open(file_path) if existing else excel.Workbooks.Add()
        try:
            ws = wb.Sheets(sheet)
        except Exception:
            ws = wb.Sheets.Add()
            ws.Name = sheet
        ws.Range(cell).Value = value
        wb.SaveAs(file_path) if not existing else wb.Save()
        return file_path

    result = await asyncio.to_thread(_run)
    return f"Excel-Zelle {cell} in '{sheet}' geschrieben: {result}"


async def _excel_read_range(path: str, sheet: str, cell_range: str) -> str:
    def _run() -> str:
        excel = _dispatch("Excel.Application")
        excel.Visible = False
        wb = excel.Workbooks.Open(str(Path(path).resolve()))
        ws = wb.Sheets(sheet)
        values = ws.Range(cell_range).Value
        wb.Close(SaveChanges=False)
        return str(values)

    return await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------


async def _powerpoint_add_slide(path: str, title: str, content: str) -> str:
    def _run() -> str:
        ppt = _dispatch("PowerPoint.Application")
        ppt.Visible = True
        file_path = str(Path(path).resolve())
        existing = Path(file_path).is_file()
        pres = ppt.Presentations.Open(file_path) if existing else ppt.Presentations.Add()
        layout = 1  # ppLayoutText
        slide = pres.Slides.Add(pres.Slides.Count + 1, layout)
        slide.Shapes.Title.TextFrame.TextRange.Text = title
        slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = content
        pres.SaveAs(file_path) if not existing else pres.Save()
        return file_path

    result = await asyncio.to_thread(_run)
    return f"PowerPoint-Folie hinzugefuegt: {result}"


# ---------------------------------------------------------------------------
# Outlook
# ---------------------------------------------------------------------------


async def _outlook_create_draft(to: str, subject: str, body: str) -> str:
    def _run() -> str:
        outlook = _dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # olMailItem
        mail.To = to
        mail.Subject = subject
        mail.Body = body
        mail.Save()  # landet im Entwuerfe-Ordner, wird NICHT gesendet
        return subject

    result = await asyncio.to_thread(_run)
    return f"Outlook-Entwurf gespeichert: '{result}' an {to}"


async def _outlook_read_inbox(count: int = 5) -> str:
    def _run() -> str:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # olFolderInbox
        messages = inbox.Items
        messages.Sort("[ReceivedTime]", True)
        lines = []
        for i, msg in enumerate(messages):
            if i >= count:
                break
            lines.append(f"- {msg.SenderName}: {msg.Subject} ({msg.ReceivedTime})")
        return "\n".join(lines) if lines else "Posteingang ist leer."

    return await asyncio.to_thread(_run)


def office_com_tools() -> list[Tool]:
    if not _IS_WINDOWS:
        return []
    return [
        Tool(
            name="word_write",
            description="Schreibt Text in ein Word-Dokument via echter Word-App (erstellt es, falls nicht vorhanden).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Pfad zur .docx-Datei"},
                    "text": {"type": "string", "description": "Zu schreibender Text"},
                },
                "required": ["path", "text"],
            },
            handler=_word_write,
        ),
        Tool(
            name="word_check_spelling",
            description="Prueft Rechtschreibung und Grammatik eines Word-Dokuments mit Words eigener Pruefung und listet Fehler mit Vorschlaegen.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Pfad zur .docx-Datei"}},
                "required": ["path"],
            },
            handler=_word_check_spelling,
        ),
        Tool(
            name="word_autocorrect",
            description="Korrigiert alle erkannten Rechtschreibfehler in einem Word-Dokument automatisch anhand des ersten Vorschlags.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Pfad zur .docx-Datei"}},
                "required": ["path"],
            },
            handler=_word_autocorrect,
        ),
        Tool(
            name="excel_write_cell",
            description="Schreibt einen Wert in eine Excel-Zelle via echter Excel-App (erstellt Datei/Blatt, falls noetig).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Pfad zur .xlsx-Datei"},
                    "sheet": {"type": "string", "description": "Name des Arbeitsblatts"},
                    "cell": {"type": "string", "description": "Zelle, z. B. 'A1'"},
                    "value": {"type": "string", "description": "Zu schreibender Wert"},
                },
                "required": ["path", "sheet", "cell", "value"],
            },
            handler=_excel_write_cell,
        ),
        Tool(
            name="excel_read_range",
            description="Liest einen Zellbereich aus einer Excel-Datei.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Pfad zur .xlsx-Datei"},
                    "sheet": {"type": "string", "description": "Name des Arbeitsblatts"},
                    "cell_range": {"type": "string", "description": "Bereich, z. B. 'A1:C10'"},
                },
                "required": ["path", "sheet", "cell_range"],
            },
            handler=_excel_read_range,
        ),
        Tool(
            name="powerpoint_add_slide",
            description="Fuegt einer PowerPoint-Praesentation eine neue Folie mit Titel und Textinhalt hinzu.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Pfad zur .pptx-Datei"},
                    "title": {"type": "string", "description": "Folientitel"},
                    "content": {"type": "string", "description": "Folieninhalt"},
                },
                "required": ["path", "title", "content"],
            },
            handler=_powerpoint_add_slide,
        ),
        Tool(
            name="outlook_create_draft",
            description="Erstellt einen E-Mail-Entwurf direkt in der lokalen Outlook-App (landet in Entwuerfe, wird nie automatisch gesendet).",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Empfaengeradresse"},
                    "subject": {"type": "string", "description": "Betreff"},
                    "body": {"type": "string", "description": "Nachrichtentext"},
                },
                "required": ["to", "subject", "body"],
            },
            handler=_outlook_create_draft,
        ),
        Tool(
            name="outlook_read_inbox",
            description="Liest die neuesten E-Mails aus dem lokalen Outlook-Posteingang.",
            input_schema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Anzahl der Mails (Standard 5)"}
                },
                "required": [],
            },
            handler=_outlook_read_inbox,
        ),
    ]
