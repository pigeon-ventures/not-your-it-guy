"""LangGraph/LangChain tool: create an AD user via the mock Entra ID service."""

from not_your_it_guy.logger.logger_provider import get_logger

from langchain_core.tools import tool

from not_your_it_guy.services.entra_id_mock_service import (
    DuplicateEmployeeError,
    create_ad_user,
)

logger = get_logger()


@tool
async def create_ad_user_tool(
    name: str,
    surname: str,
    email: str = "",
    phone: str = "",
    department: str = "",
    line_manager: str = "",
) -> str:
    """Create a new employee account in the mock Active Directory / Entra ID system.

    Args:
        name: Employee first name.
        surname: Employee last name.
        email: Corporate email — derived as name.surname@msmock.com if omitted.
        phone: Mobile phone number for temporary password delivery.
        department: Department the employee belongs to.
        line_manager: Full name of the employee's line manager.

    Returns:
        Confirmation message with the assigned employee ID and email.
    """
    try:
        record = await create_ad_user(
            name=name,
            surname=surname,
            email=email or None,
            phone=phone or None,
            department=department or None,
            line_manager=line_manager or None,
        )
        return (
            f"AD account created successfully. "
            f"Employee ID: {record.id}, email: {record.email}, "
            f"department: {record.department or 'N/A'}, "
            f"line manager: {record.line_manager or 'N/A'}."
        )
    except DuplicateEmployeeError as exc:
        logger.warning("[ad_user_tool] duplicate: {}", exc)
        return f"Account already exists: {exc}"
    except ValueError as exc:
        logger.error("[ad_user_tool] validation error: {}", exc)
        return f"Validation error: {exc}"
