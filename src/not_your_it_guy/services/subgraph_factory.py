"""Subgraph factory — registry of all available subgraphs.

Each entry maps an intent name to a stream function that accepts a RouterResult
and yields str chunks.

Add a new subgraph by importing it and adding an entry to SUBGRAPHS.
"""

from not_your_it_guy.logger.logger_provider import get_logger
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Callable

from not_your_it_guy.subgraphs import employee_onboarding

if TYPE_CHECKING:
    from not_your_it_guy.models import RouterResult

logger = get_logger()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

type StreamFn = Callable[["RouterResult"], AsyncIterator[str]]

SUBGRAPHS: dict[str, StreamFn] = {
    "employee_onboarding": employee_onboarding.stream,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get(intent: str) -> StreamFn | None:
    """Return the stream function for the given intent, or None if unknown."""
    fn = SUBGRAPHS.get(intent)
    if fn is None:
        logger.warning("subgraph_factory: no subgraph registered for intent={}", intent)
    return fn


def known_intents() -> list[str]:
    return list(SUBGRAPHS.keys())
