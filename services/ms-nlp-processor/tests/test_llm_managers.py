"""Unit tests for LangGraphManager helper methods."""

import pytest

from llm_managers import LangGraphManager


@pytest.fixture
def manager():
    """Create a LangGraphManager instance without running heavy __init__ logic."""
    return object.__new__(LangGraphManager)


@pytest.fixture
def base_state():
    """Provide a minimal AgentState-like dictionary."""
    return {
        "text": "Olá!",
        "messages": [],
        "user_email": "user@example.com",
        "is_authenticated": True,
        "notes_path": "https://github.com/example/repo",
        "metadata": {},
        "entities": {},
        "response": None,
        "confidence": 0.0,
    }


def test_configuration_router_requires_authentication(manager, base_state):
    """When the user is not authenticated, the router should trigger the auth flow."""
    state = base_state.copy()
    state["is_authenticated"] = False

    result = manager._configuration_router(state)

    assert result == "auth_flow"


def test_configuration_router_requests_notes_path(manager, base_state):
    """If notes_path is missing and text is not a URL, wait for more input."""
    state = base_state.copy()
    state["notes_path"] = None
    state["text"] = "Ainda não configurei"

    result = manager._configuration_router(state)

    assert result == "wait_for_input"


def test_configuration_router_accepts_notes_path_update(manager, base_state):
    """If notes_path is missing but text contains a GitHub URL, update it."""
    state = base_state.copy()
    state["notes_path"] = ""
    state["text"] = "https://github.com/example/new-repo"

    result = manager._configuration_router(state)

    assert result == "update_notes_path"


def test_configuration_router_allows_flow_when_configured(manager, base_state):
    """When authenticated with a valid notes_path, the flow should continue."""
    state = base_state.copy()

    result = manager._configuration_router(state)

    assert result == "continue"
