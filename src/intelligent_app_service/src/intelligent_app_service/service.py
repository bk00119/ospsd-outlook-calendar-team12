"""Core orchestration service for intelligent app."""

from datetime import datetime

from calendar_client_api.event import EventPatch

from ai_client_api import AIClient, TextGenerationRequest
from calendar_client_api import Client as CalendarClient
from intelligent_app_service.prompts import get_system_context


class IntelligentAppService:
    """Main orchestration controller tying Calendar and AI logic together."""

    def __init__(self, calendar_client: CalendarClient, ai_client: AIClient) -> None:
        """Initialize the orchestration service via Dependency Injection."""
        self._calendar = calendar_client
        self._ai = ai_client

    def process_chat(self, message: str, user_timezone: str = "UTC") -> str:  # noqa: C901, PLR0915
        """Process a natural language message and trigger calendar actions via AI."""
        last_tool_result: str | None = None

        def _record_tool_result(message: str) -> str:
            """Store the latest tool result for fallback replies."""
            nonlocal last_tool_result
            last_tool_result = message
            return message

        def create_outlook_event(
            title: str,
            start_iso_string: str,
            end_iso_string: str,
            location: str | None = None,
            description: str | None = None,
        ) -> str:
            """Create a new calendar event.

            Args:
                title: The title of the event.
                start_iso_string: Start time in exact ISO 8601 format (e.g., 2026-04-21T15:00:00+00:00).
                end_iso_string: End time in exact ISO 8601 format.
                location: Optional location or meeting room for the event.
                description: Optional description or notes for the event.

            """
            starts_at = datetime.fromisoformat(start_iso_string)
            ends_at = datetime.fromisoformat(end_iso_string)
            event = self._calendar.create_event(
                title=title,
                starts_at=starts_at,
                ends_at=ends_at,
                location=location,
                description=description,
            )
            summary = (
                f"Created event '{event.title}' (ID: {event.id}) "
                f"from {event.starts_at} to {event.ends_at}."
            )
            if event.location:
                summary += f" Location: {event.location}."
            if event.description:
                summary += f" Description: {event.description}"
            return _record_tool_result(summary)

        def list_my_events(start_iso_string: str, end_iso_string: str) -> str:
            """Retrieve the user's calendar events within a specific time range.

            Args:
                start_iso_string: Start boundaries in ISO 8601 format.
                end_iso_string: End boundaries in ISO 8601 format.

            """
            starts_at = datetime.fromisoformat(start_iso_string)
            ends_at = datetime.fromisoformat(end_iso_string)
            events = self._calendar.list_events(start=starts_at, end=ends_at)

            if not events:
                return _record_tool_result("The calendar is completely free during this time block!")

            lines = []
            for e in events:
                parts = [
                    f"Event '{e.title}' (ID: {e.id}) from {e.starts_at} to {e.ends_at}.",
                ]
                if e.location:
                    parts.append(f"Location: {e.location}.")
                if e.description:
                    parts.append(f"Description: {e.description}")
                lines.append(" ".join(parts))
            return _record_tool_result("\n".join(lines))

        def delete_outlook_event(event_id: str) -> str:
            """Delete a calendar event by its ID.

            Args:
                event_id: The unique ID string of the event to delete.

            """
            self._calendar.delete_event(event_id)
            return _record_tool_result(f"Deleted event {event_id}.")

        def get_outlook_event(event_id: str) -> str:
            """Retrieve details of a specific calendar event.

            Args:
                event_id: The unique ID string of the event to inspect.

            """
            try:
                event = self._calendar.get_event(event_id)
            except (LookupError, RuntimeError) as e:
                return _record_tool_result(f"Error finding event: {e}")

            details = (
                f"Event '{event.title}' (ID: {event.id}) starts at {event.starts_at} "
                f"and ends at {event.ends_at}."
            )
            if event.location:
                details += f" Location: {event.location}."
            if event.description:
                details += f" Description: {event.description}"
            return _record_tool_result(details)

        def update_outlook_event(  # noqa: PLR0913
            event_id: str,
            new_title: str | None = None,
            new_start_iso_string: str | None = None,
            new_end_iso_string: str | None = None,
            new_location: str | None = None,
            new_description: str | None = None,
        ) -> str:
            """Update an existing calendar event.

            Args:
                event_id: The ID of the event to update.
                new_title: Optional new title.
                new_start_iso_string: Optional new start time in ISO 8601.
                new_end_iso_string: Optional new end time in ISO 8601.
                new_location: Optional new location.
                new_description: Optional new description or notes.

            """
            patch = EventPatch(
                title=new_title,
                starts_at=datetime.fromisoformat(new_start_iso_string) if new_start_iso_string else None,
                ends_at=datetime.fromisoformat(new_end_iso_string) if new_end_iso_string else None,
                location=new_location,
                description=new_description,
            )
            event = self._calendar.update_event(event_id, patch)
            summary = (
                f"Updated event '{event.title}' (ID: {event.id}) "
                f"to run from {event.starts_at} to {event.ends_at}."
            )
            if event.location:
                summary += f" Location: {event.location}."
            if event.description:
                summary += f" Description: {event.description}"
            return _record_tool_result(summary)

        # Combine context with the user's message
        system_prompt = get_system_context(user_timezone)

        request = TextGenerationRequest(
            prompt=message,
            context={"system_instructions": system_prompt},
            tools=[
                create_outlook_event,
                list_my_events,
                delete_outlook_event,
                get_outlook_event,
                update_outlook_event,
            ],
        )

        try:
            response = self._ai.generate_text(request)
        except Exception as exc:
            if last_tool_result is not None:
                return (
                    f"The calendar action appears to have succeeded, but the AI failed while "
                    f"generating the final reply. Latest tool result: {last_tool_result}"
                )
            err_msg = f"AI generation failed before any tool completed: {exc}"
            raise RuntimeError(err_msg) from exc

        if response.text:
            return response.text

        if last_tool_result is not None:
            return last_tool_result

        err_msg = "AI returned an empty response and no tool result was recorded."
        raise RuntimeError(err_msg)
