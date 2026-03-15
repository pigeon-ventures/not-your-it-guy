"""Employee onboarding subgraph.

Flow:
  handle → create_ad_user → END

- handle: logs and validates the incoming RouterResult contract
- create_ad_user: calls the mock Entra ID service to insert an employee row,
  generates a temporary password, triggers welcome email stub
"""

from typing import TYPE_CHECKING, AsyncIterator

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from not_your_it_guy.logger.logger_provider import get_logger
from not_your_it_guy.services.entra_id_mock_service import (
    DuplicateEmployeeError,
    create_ad_user,
)
from not_your_it_guy.services.sms_service import send_temp_password_sms
from not_your_it_guy.services.welcome_email_service import send_welcome_email

if TYPE_CHECKING:
    from not_your_it_guy.models import RouterResult

logger = get_logger()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class OnboardingState(TypedDict):
    name: str
    surname: str
    private_email: str     # from request metadata (personal inbox)
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
        "[employee_onboarding] invoked | name={} surname={} private_email={} "
        "phone={} department={} line_manager={} | raw_input={}",
        state["name"],
        state["surname"],
        state["private_email"],
        state["phone"],
        state["department"],
        state["line_manager"],
        state["raw_input"],
    )
    return state


async def create_ad_user_node(state: OnboardingState) -> OnboardingState:
    name = state["name"]
    surname = state["surname"]
    dept = state["department"] or "your department"
    phone = state["phone"] or "the registered phone number"

    try:
        record = await create_ad_user(
            name=name,
            surname=surname,
            private_email=state["private_email"] or None,
            phone=state["phone"] or None,
            department=state["department"] or None,
            line_manager=state["line_manager"] or None,
        )
        full_name = f"{record.name} {record.surname}".strip() or "the new employee"

        # Send temporary password via SMS (stub — logs if TWILIO not configured)
        await send_temp_password_sms(
            phone=phone,
            temp_password=record.temp_password,
            corporate_email=record.corporate_email,
        )

        # Send welcome email (stub — logs if RESEND_API_KEY not set)
        await send_welcome_email(
            name=record.name,
            corporate_email=record.corporate_email,
            private_email=record.private_email,
            phone=record.phone,
        )

        output = (
            f"Employee onboarding started for {full_name} in {dept} department. "
            f"Microsoft account was created for {record.corporate_email}. "
            f"A temporary password has been sent via SMS to {phone}. "
            f"A welcome email with onboarding instructions and useful links has been sent to {record.private_email or record.corporate_email} (private inbox)."
        )
        logger.info("[employee_onboarding] AD user created | id={}", record.id)

    except DuplicateEmployeeError as exc:
        logger.warning("[employee_onboarding] duplicate employee: {}", exc)
        full_name = f"{name} {surname}".strip() or "the employee"
        output = (
            f"Onboarding skipped — an account for {full_name} already exists in the system. "
            f"Please contact IT if you believe this is an error."
        )
    except Exception as exc:
        logger.exception("[employee_onboarding] unexpected error during AD user creation")
        output = "Onboarding could not be completed due to an unexpected error. Please contact AI Automation team."

    return {**state, "output": output}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def build() -> StateGraph:
    graph = StateGraph(OnboardingState)
    graph.add_node("handle", handle)
    graph.add_node("create_ad_user", create_ad_user_node)
    graph.set_entry_point("handle")
    graph.add_edge("handle", "create_ad_user")
    graph.add_edge("create_ad_user", END)
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
        private_email=p.email,   # metadata `email` field = private/personal email
        phone=p.phone,
        department=p.department,
        line_manager=p.line_manager,
        raw_input=router_result.raw_input,
        output="",
    )
    result = await graph.ainvoke(state)
    for word in result["output"].split():
        yield word + " "
