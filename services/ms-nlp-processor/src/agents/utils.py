"""Utility helpers for working with agents."""
from __future__ import annotations

import inspect
import logging

from .base_agent import BaseAgent
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

FunctionDescription = Dict[str, str]


def collect_agent_descriptions(agents: Iterable[BaseAgent]) -> List[FunctionDescription]:
    """Collect descriptions for provided agent instances."""
    descriptions: List[FunctionDescription] = []

    for agent in agents:
        name = getattr(agent, "name", agent.__class__.__name__)
        summary_line = _first_summary_line(getattr(agent, "description", None))
        if not summary_line:
            summary_line = _extract_docstring_summary(agent.__class__)
        if not summary_line:
            logger.debug("Skipping agent %s due to missing description", name)
            continue

        descriptions.append(
            {
                "name": name,
                "description": summary_line,
            }
        )

    descriptions.sort(key=lambda entry: entry["name"].lower())
    return descriptions


def _resolve_tool_name(tool: Any) -> str:
    """Return a readable name for a tool callable."""
    owner = getattr(tool, "__self__", None)
    method_name = getattr(tool, "__name__", None)
    owner_name = getattr(owner, "name", None) if owner else None

    if method_name and owner_name and method_name != owner_name:
        return f"{method_name} ({owner_name})"

    named_attr = getattr(tool, "name", None)
    if isinstance(named_attr, str):
        return named_attr

    if method_name:
        return method_name

    if hasattr(tool, "__class__"):
        return tool.__class__.__name__
    return str(tool)


def _first_summary_line(text: Optional[str]) -> Optional[str]:
    """Return the first non-empty line from the provided text."""
    if not text:
        return None

    for line in text.strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _extract_docstring_summary(obj: Any) -> Optional[str]:
    """Return the summary line derived from an object's docstring."""
    docstring = inspect.getdoc(obj)
    summary_line = _first_summary_line(docstring)
    if summary_line:
        return summary_line

    # Bound methods sometimes store docstring on __func__
    func = getattr(obj, "__func__", None)
    if func:
        return _first_summary_line(inspect.getdoc(func))
    return None


def collect_tool_descriptions(tools: Iterable[Any]) -> List[FunctionDescription]:
    """Collect descriptions for tool callables, using docstrings when available."""
    descriptions: List[FunctionDescription] = []
    
    for tool in tools:
        name = _resolve_tool_name(tool)
        summary_line = _first_summary_line(getattr(tool, "description", None))
        if not summary_line:
            summary_line = _extract_docstring_summary(tool)
        if not summary_line:
            logger.debug("Skipping tool %s due to missing description", name)
            continue

        descriptions.append(
            {
                "name": name,
                "description": summary_line,
            }
        )
    descriptions.sort(key=lambda entry: entry["name"].lower())
    return descriptions


__all__ = ["collect_agent_descriptions", "collect_tool_descriptions"]
