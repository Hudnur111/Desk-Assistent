import asyncio
import email.utils
import imaplib
import time
from email.message import EmailMessage
from typing import Protocol

from .base import Tool


class EmailBackend(Protocol):
    async def create_draft(self, to: str, subject: str, body: str) -> str: ...


class ImapEmailBackend:
    """Legt E-Mail-Entwuerfe per IMAP APPEND im Drafts-Ordner ab.

    Sendet nie selbststaendig - das Versenden bleibt bewusst ein manueller
    Schritt des Nutzers im E-Mail-Client (der geforderte Sicherheits-
    Bestaetigungsschritt). Nutzt ein App-Passwort statt eines vollen
    OAuth-Flows, um auf dem Pi 4 ohne zusaetzliche Google-API-Abhaengigkeiten
    auszukommen.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        drafts_folder: str = "[Gmail]/Drafts",
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._drafts_folder = drafts_folder

    async def create_draft(self, to: str, subject: str, body: str) -> str:
        def _run() -> str:
            message = EmailMessage()
            message["From"] = self._username
            message["To"] = to
            message["Subject"] = subject
            message["Date"] = email.utils.formatdate(localtime=True)
            message.set_content(body)

            with imaplib.IMAP4_SSL(self._host) as imap:
                imap.login(self._username, self._password)
                imap.append(
                    self._drafts_folder,
                    "\\Draft",
                    imaplib.Time2Internaldate(time.time()),
                    message.as_bytes(),
                )
            return f"E-Mail-Entwurf an {to} gespeichert (Betreff: {subject})"

        return await asyncio.to_thread(_run)


def build_email_draft_tool(backend: EmailBackend) -> Tool:
    async def _handler(to: str, subject: str, body: str) -> str:
        return await backend.create_draft(to=to, subject=subject, body=body)

    return Tool(
        name="create_email_draft",
        description=(
            "Erstellt einen E-Mail-Entwurf im Drafts-Ordner des Postfachs. "
            "Sendet die Mail NICHT - der Nutzer muss sie manuell im "
            "E-Mail-Client pruefen und abschicken."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Empfaenger-E-Mail-Adresse"},
                "subject": {"type": "string", "description": "Betreff"},
                "body": {"type": "string", "description": "Text der E-Mail"},
            },
            "required": ["to", "subject", "body"],
        },
        handler=_handler,
    )
