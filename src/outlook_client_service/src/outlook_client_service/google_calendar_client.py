"""Google Calendar implementation of the shared calendar client API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from calendar_client_api.client import Client as CalendarClient
from calendar_client_api.event import Event, EventPatch
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarEvent(Event):
    """Concrete event returned by Google Calendar."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        event_id: str,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize a concrete Google Calendar event."""
        self._id = event_id
        self._title = title
        self._starts_at = starts_at
        self._ends_at = ends_at
        self._location = location
        self._description = description

    @property
    def id(self) -> str:
        """Return the provider event ID."""
        return self._id

    @property
    def title(self) -> str:
        """Return the event title."""
        return self._title

    @property
    def starts_at(self) -> datetime:
        """Return the event start datetime."""
        return self._starts_at

    @property
    def ends_at(self) -> datetime:
        """Return the event end datetime."""
        return self._ends_at

    @property
    def location(self) -> str | None:
        """Return the event location, if provided."""
        return self._location

    @property
    def description(self) -> str | None:
        """Return the event description, if provided."""
        return self._description


class GoogleCalendarClient(CalendarClient):
    """Minimal Google Calendar provider implementation for provider-swapping demos."""

    def __init__(
        self,
        *,
        credentials_file: str,
        token_file: str,
        calendar_id: str = "primary",
        interactive: bool = False,
    ) -> None:
        """Initialize the Google Calendar client."""
        self._credentials_file = Path(credentials_file)
        self._token_file = Path(token_file)
        self._calendar_id = calendar_id
        self._interactive = interactive
        self._service = build("calendar", "v3", credentials=self._load_credentials())

    def get_event(self, event_id: str) -> Event:
        """Return an event by its ID."""
        try:
            item = (
                self._service.events()
                .get(calendarId=self._calendar_id, eventId=event_id)
                .execute()
            )
        except HttpError as exc:
            message = f"Failed to get Google Calendar event {event_id}: {exc}"
            raise RuntimeError(message) from exc

        return self._to_event(cast("dict[str, Any]", item))

    def list_events(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        types: list[str] | None = None,
    ) -> list[Event]:
        """Return a list of Google Calendar events with optional filters."""
        if start is not None:
            self._validate_datetime(start)
        if end is not None:
            self._validate_datetime(end)

        request_kwargs: dict[str, object] = {
            "calendarId": self._calendar_id,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if start is not None:
            request_kwargs["timeMin"] = start.isoformat()
        if end is not None:
            request_kwargs["timeMax"] = end.isoformat()

        try:
            response = self._service.events().list(**request_kwargs).execute()
        except HttpError as exc:
            message = f"Failed to list Google Calendar events: {exc}"
            raise RuntimeError(message) from exc

        items = cast("list[dict[str, Any]]", response.get("items", []))
        events = [self._to_event(item) for item in items]
        if types is not None:
            return []
        return events

    def create_event(
        self,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> Event:
        """Create an event from explicit creation fields and return it."""
        self._validate_datetime(starts_at)
        self._validate_datetime(ends_at)

        body = self._build_event_body(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            location=location,
            description=description,
        )

        try:
            item = (
                self._service.events()
                .insert(calendarId=self._calendar_id, body=body)
                .execute()
            )
        except HttpError as exc:
            message = f"Failed to create Google Calendar event: {exc}"
            raise RuntimeError(message) from exc

        return self._to_event(cast("dict[str, Any]", item))

    def delete_event(self, event_id: str) -> None:
        """Delete an event by its ID."""
        message = "Google provider demo only supports create and list."
        raise NotImplementedError(message)

    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        """Update an event by its ID with a payload."""
        message = "Google provider demo only supports create and list."
        raise NotImplementedError(message)

    def _load_credentials(self) -> Credentials:
        """Load Google credentials from disk or run local OAuth if enabled."""
        credentials: Credentials | None = None

        if self._token_file.exists():
            loaded_credentials = Credentials.from_authorized_user_file(  # type: ignore[no-untyped-call]
                str(self._token_file),
                GOOGLE_CALENDAR_SCOPES,
            )
            credentials = cast("Credentials", loaded_credentials)

        if credentials is not None and credentials.valid:
            return credentials

        if credentials is not None and credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleAuthRequest())
            self._save_credentials(credentials)
            return credentials

        if not self._interactive:
            message = (
                "Google Calendar token is missing or invalid. "
                "Set GOOGLE_INTERACTIVE_AUTH=true once to create token.json."
            )
            raise RuntimeError(message)

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_file),
            GOOGLE_CALENDAR_SCOPES,
        )
        generated_credentials = flow.run_local_server(port=0)
        credentials = cast("Credentials", generated_credentials)
        self._save_credentials(credentials)
        return credentials

    def _save_credentials(self, credentials: Credentials) -> None:
        """Persist Google credentials for later non-interactive runs."""
        credentials_json = cast("str", credentials.to_json())  # type: ignore[no-untyped-call]
        self._token_file.write_text(credentials_json, encoding="utf-8")

    @staticmethod
    def _validate_datetime(value: datetime) -> None:
        """Require timezone-aware datetimes for provider calls."""
        if value.tzinfo is None or value.utcoffset() is None:
            message = "Datetime values must be timezone-aware."
            raise ValueError(message)

    @staticmethod
    def _google_datetime(value: datetime) -> dict[str, str]:
        """Convert a Python datetime into Google Calendar datetime format."""
        return {"dateTime": value.isoformat()}

    @classmethod
    def _build_event_body(
        cls,
        *,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> dict[str, object]:
        """Build a Google Calendar event request body."""
        body: dict[str, object] = {
            "summary": title,
            "start": cls._google_datetime(starts_at),
            "end": cls._google_datetime(ends_at),
        }
        if location:
            body["location"] = location
        if description:
            body["description"] = description
        return body

    @staticmethod
    def _to_event(item: dict[str, Any]) -> Event:
        """Convert a Google Calendar event payload into the shared Event model."""
        start = cast("dict[str, str]", item.get("start", {}))
        end = cast("dict[str, str]", item.get("end", {}))
        start_value = start.get("dateTime") or start.get("date")
        end_value = end.get("dateTime") or end.get("date")

        if not start_value or not end_value:
            message = f"Google event is missing start or end time: {item.get('id', '')}"
            raise RuntimeError(message)

        return GoogleCalendarEvent(
            event_id=str(item["id"]),
            title=str(item.get("summary", "Untitled event")),
            starts_at=datetime.fromisoformat(start_value),
            ends_at=datetime.fromisoformat(end_value),
            location=cast("str | None", item.get("location")),
            description=cast("str | None", item.get("description")),
        )
