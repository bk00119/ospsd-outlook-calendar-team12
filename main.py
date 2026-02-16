"""Main module for demonstrating the calendar client.

TODO: import these
import contextlib
import outlook_client_impl
"""
import logging

import calendar_client_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """Initialize the client and demonstrate all calendar client methods."""
    # Now, get_client() returns a OutlookClient instance...
    client = calendar_client_api.get_client(interactive=False)

    # TODO: update test_event_id for get_event() after implementing get_messages()
    test_event_id = 1
    event = client.get_event(test_event_id)
    if not event:
      return

    # TODO: add methods to demonstrate here

    print("Demo complete.")

if __name__ == "__main__":
    main()
