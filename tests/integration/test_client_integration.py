"""Integration tests for dependency injection between API and implementation."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, cast

import pytest
from outlook_client_impl.outlook_impl import OutlookClient

import calendar_client_api
import outlook_client_impl

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

pytestmark = pytest.mark.integration

@pytest.mark.circleci
def test_importing_implementation_registers_client_factory() -> None:
    """Import side effects wire the API factory to the Outlook implementation."""
    importlib.reload(calendar_client_api)
    importlib.reload(outlook_client_impl)

    assert calendar_client_api.get_client.__module__ == "outlook_client_impl.outlook_impl"
    assert calendar_client_api.get_client.__name__ == "get_client_impl"


@pytest.mark.circleci
def test_get_client_returns_outlook_client_after_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns OutlookClient when implementation package is imported."""
    importlib.reload(calendar_client_api)
    importlib.reload(outlook_client_impl)

    fake_service = cast("GraphServiceClient", object())

    monkeypatch.setattr(OutlookClient, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(
        OutlookClient,
        "AUTHORITY",
        "https://login.microsoftonline.com/consumers",
    )

    def _fake_get_graph_client(self: object) -> GraphServiceClient:
        _ = self
        return fake_service

    monkeypatch.setattr(
        "outlook_client_impl.outlook_impl.AuthManager.get_graph_client",
        _fake_get_graph_client,
    )

    client = calendar_client_api.get_client(interactive=False)

    assert isinstance(client, OutlookClient)
    assert client.service is fake_service


@pytest.mark.circleci
def test_importing_implementation_registers_event_factory() -> None:
    """Import side effects wire the API event factory to Outlook event implementation."""
    importlib.reload(calendar_client_api)
    importlib.reload(outlook_client_impl)

    event = calendar_client_api.get_event(
        event_id="evt-123",
        raw_data='{"subject":"DI Event","start":{"dateTime":"2026-03-01T10:00:00+00:00"},'
        '"end":{"dateTime":"2026-03-01T11:00:00+00:00"}}',
    )

    assert event.id == "evt-123"
    assert event.title == "DI Event"


@pytest.mark.circleci
def test_di_client_exposes_expected_interface_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DI-created client exposes the expected interface methods."""
    importlib.reload(calendar_client_api)
    importlib.reload(outlook_client_impl)

    fake_service = cast("GraphServiceClient", object())

    monkeypatch.setattr(OutlookClient, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(
        OutlookClient,
        "AUTHORITY",
        "https://login.microsoftonline.com/consumers",
    )

    def _fake_get_graph_client(self: object) -> GraphServiceClient:
        _ = self
        return fake_service

    monkeypatch.setattr(
        "outlook_client_impl.outlook_impl.AuthManager.get_graph_client",
        _fake_get_graph_client,
    )

    client = calendar_client_api.get_client(interactive=False)

    assert hasattr(client, "get_event")
    assert hasattr(client, "create_event")
    assert hasattr(client, "delete_event")
    assert hasattr(client, "update_event")
    assert hasattr(client, "list_events")
