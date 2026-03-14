"""Employee onboarding subgraph.

Stub implementation — logs the full RouterResult contract and streams a
placeholder response. Replace the node body with real logic as the flow
is developed.
"""

import logging
from typing import TYPE_CHECKING, AsyncIterator

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from not_your_it_guy.models import RouterResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class OnboardingState(TypedDict):
    name: str
    surname: str
    email: str
    phone: str
    department: str
    line_manager: str
    raw_input: str
    output: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


async def handle(state: OnboardingState) -> OnboardingState:
    logger.info(
        "[employee_onboarding] invoked | name=%r surname=%r email=%r "
        "phone=%r department=%r line_manager=%r | raw_input=%r",
        state["name"],
        state["surname"],
        state["email"],
        state["phone"],
        state["department"],
        state["line_manager"],
        state["raw_input"],
    )
    # TODO: replace with real onboarding logic
    name = f"{state['name']} {state['surname']}".strip() or "the new employee"
    dept = state["department"] or "your department"
    return {**state, "output": f"Employee onboarding started for {name} in {dept}."}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def build() -> StateGraph:
    graph = StateGraph(OnboardingState)
    graph.add_node("handle", handle)
    graph.set_entry_point("handle")
    graph.add_edge("handle", END)
    return graph.compile()


graph = build()


# ---------------------------------------------------------------------------
# Streaming helper — accepts RouterResult (the subgraph contract)
# ---------------------------------------------------------------------------


async def stream(router_result: "RouterResult") -> AsyncIterator[str]:
    """Invoke the subgraph and yield output chunks."""
    p = router_result.params
    state = OnboardingState(
        name=p.name,
        surname=p.surname,
        email=p.email,
        phone=p.phone,
        department=p.department,
        line_manager=p.line_manager,
        raw_input=router_result.raw_input,
        output="",
    )
    result = await graph.ainvoke(state)
    for word in result["output"].split():
        yield word + " "
