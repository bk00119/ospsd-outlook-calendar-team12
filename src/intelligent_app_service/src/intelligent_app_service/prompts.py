"""Prompt templates used by the intelligent app service."""

import datetime


def get_system_context(user_timezone: str = "UTC") -> str:
    """Return the system context block to inject into the AI prompt."""
    now_utc = datetime.datetime.now(datetime.UTC).isoformat()
    return (
        f"You are a scheduling assistant. Today's current date and time is {now_utc} (UTC).\n"
        f"The user is operating in the timezone: {user_timezone}.\n"
        f"When scheduling or interacting with events, always ensure times align with the user's local timezone. "
        f"Do not ask for timezone details unless completely ambiguous.\n\n"
        # TIME-CONFLICT RULE
        f"CRITICAL CONFLICT RULE: Before you create an event, you must check the user's calendar. "
        f"If there is a conflict, DO NOT create the event. Warn the user and ask them to confirm exactly. "
        f"Only schedule a conflicting event if the user explicitly replies 'yes' or override.\n\n"
    )
