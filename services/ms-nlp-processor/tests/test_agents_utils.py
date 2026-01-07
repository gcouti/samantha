"""Unit tests for helper utilities defined in agents.utils."""

from __future__ import annotations

import sys
import types

import pytest

# agents.__init__ imports OrchestratorAgent, which is not present in the repo.
# Provide a lightweight stub so we can import agents.utils without failures.
if "agents.orchestrator_agent" not in sys.modules:  # pragma: no cover - setup
    stub_module = types.ModuleType("agents.orchestrator_agent")

    class _OrchestratorStub:  # pragma: no cover - setup
        """Stub used only to satisfy package-level imports."""

    stub_module.OrchestratorAgent = _OrchestratorStub
    sys.modules["agents.orchestrator_agent"] = stub_module

from typing import Any, Dict

import pytest

from agents.utils import (  # noqa: E402
    collect_agent_descriptions,
    collect_tool_descriptions,
    _extract_docstring_summary,
    _first_summary_line,
)


class _StubAgent(BaseAgent):  # pragma: no cover - helper
    """Stub agent used within tests."""

    def __init__(self, name: str = "stub_agent", description: str | None = None):
        super().__init__(name=name, description=description or "")

    def can_handle(self, intent: str, entities: Dict[str, Any]) -> bool:
        return False

    async def handle(self, text: str, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        return {}


def test_first_summary_line_returns_first_non_empty_line():
    """Should trim whitespace and return the first non-empty entry."""
    text = "\n  First line.\n\nSecond line."
    assert _first_summary_line(text) == "First line."


def test_first_summary_line_handles_missing_or_blank_text():
    """None or whitespace-only inputs should yield None."""
    assert _first_summary_line(None) is None
    assert _first_summary_line("   \n\t") is None


def test_extract_docstring_summary_prefers_direct_docstring():
    """Should pull the first meaningful line from an object's docstring."""

    class Sample:
        """Primary summary.

        Extra detail that should be ignored.
        """

    assert _extract_docstring_summary(Sample) == "Primary summary."


def test_extract_docstring_summary_falls_back_to_func_docstring():
    """Objects exposing __func__ should use that docstring when needed."""

    def source_fn():
        """Docstring provided on underlying function."""

    class DoclessCallable:
        __doc__ = None

        def __init__(self, func):
            self.__func__ = func

        def __call__(self):
            return self.__func__()

    proxy = DoclessCallable(source_fn)

    assert (
        _extract_docstring_summary(proxy) == "Docstring provided on underlying function."
    )


def test_collect_tool_descriptions_prefers_explicit_description():
    """Explicit description attribute should take precedence over docstrings."""

    def tool_with_description():
        """Fallback docstring that should be ignored."""

    tool_with_description.description = "Summary from attribute.\nMore details here."

    descriptions = collect_tool_descriptions([tool_with_description])

    assert descriptions == [
        {
            "name": "tool_with_description",
            "description": "Summary from attribute.",
        }
    ]


def test_collect_tool_descriptions_extracts_docstring_summary():
    """Docstrings should be parsed and trimmed to the first non-empty line."""

    def doc_only_tool():
        """
        Main capability line.

        Additional information should be ignored.
        """

    descriptions = collect_tool_descriptions([doc_only_tool])

    assert descriptions == [
        {
            "name": "doc_only_tool",
            "description": "Main capability line.",
        }
    ]


def test_collect_agent_descriptions_uses_instance_description():
    """Explicit description attribute (multi-line) should be trimmed."""

    agent = _StubAgent(description="Custom summary.\nMore detail.")
    agent.name = "custom_agent"

    assert collect_agent_descriptions([agent]) == [
        {"name": "custom_agent", "description": "Custom summary."}
    ]


def test_collect_agent_descriptions_falls_back_to_docstring():
    """When instance lacks description, use the class docstring."""

    class DocOnlyAgent(_StubAgent):
        """Doc-only summary."""

        def __init__(self):
            super().__init__(description="")

    agent = DocOnlyAgent()
    agent.name = "doc_agent"

    assert collect_agent_descriptions([agent]) == [
        {"name": "doc_agent", "description": "Doc-only summary."}
    ]


def test_collect_agent_descriptions_skips_when_missing_description(caplog):
    """Agents without description sources should be ignored."""

    class DoclessAgent(_StubAgent):
        __doc__ = None

        def __init__(self):
            super().__init__(description="")

    agent = DoclessAgent()
    agent.name = "docless"

    with caplog.at_level(logging.DEBUG):
        assert collect_agent_descriptions([agent]) == []
        assert any("docless" in message for message in caplog.messages)


def test_collect_tool_descriptions_supports_bound_methods():
    """Bound methods should produce readable names that include the owner name."""

    class ToolOwner:
        def __init__(self, name: str):
            self.name = name

        def perform(self):
            """Executes the primary operation."""

    owner = ToolOwner("owner-instance")

    descriptions = collect_tool_descriptions([owner.perform])

    assert descriptions == [
        {
            "name": "perform (owner-instance)",
            "description": "Executes the primary operation.",
        }
    ]


def test_collect_tool_descriptions_skips_items_without_description(caplog):
    """Callables without any description should be ignored and logged at debug."""

    def undocumented_tool():
        pass

    with caplog.at_level("DEBUG"):
        descriptions = collect_tool_descriptions([undocumented_tool])

    assert descriptions == []
    assert any("missing description" in message for message in caplog.messages)


def test_collect_tool_descriptions_sorts_results():
    """Returned descriptions should be sorted case-insensitively by name."""

    def tool_b():
        """Second tool."""

    def tool_a():
        """First tool."""

    descriptions = collect_tool_descriptions([tool_b, tool_a])

    assert [entry["name"] for entry in descriptions] == ["tool_a", "tool_b"]
