"""Mock Entra ID / Active Directory user provisioning service.

Validates and normalises employee input, then inserts a row into the
`employees` table to simulate account creation in a central AD system.

Flow:
- private_email  = email supplied in the request (personal inbox)
- corporate_email = derived as name.surname@b2.com
- temp_password   = generated, stored as bcrypt hash; raw value returned once
                    so it can be sent via SMS (Twilio) or email (Resend)
"""

import hashlib
import secrets
import string
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from not_your_it_guy.db.models import Employee
from not_your_it_guy.db.session import get_session
from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%"
_PASSWORD_LENGTH = 12


def _generate_temp_password() -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(_PASSWORD_LENGTH))


def _hash_password(password: str) -> str:
    """SHA-256 hash — swap for bcrypt when adding auth layer."""
    return hashlib.sha256(password.encode()).hexdigest()


def _derive_corporate_email(name: str, surname: str) -> str:
    return f"{name.lower()}.{surname.lower()}@b2.com"


@dataclass
class EmployeeRecord:
    id: int
    name: str
    surname: str
    corporate_email: str
    private_email: str | None
    phone: str | None
    department: str | None
    line_manager: str | None
    temp_password: str  # raw — send via SMS/email, never log or store


class DuplicateEmployeeError(Exception):
    """Raised when an employee with the same corporate email already exists."""


async def create_ad_user(
    name: str,
    surname: str,
    private_email: str | None,
    phone: str | None,
    department: str | None,
    line_manager: str | None,
) -> EmployeeRecord:
    """Validate input, derive corporate email, generate temp password, insert row."""
    name = name.strip()
    surname = surname.strip()

    if not name or not surname:
        raise ValueError("name and surname are required to create an AD user")

    corporate_email = _derive_corporate_email(name, surname)
    private_email_clean = private_email.strip().lower() if private_email else None

    temp_password = _generate_temp_password()
    password_hash = _hash_password(temp_password)

    logger.info(
        "[entra_id_mock] provisioning AD user | name={} surname={} corporate={} dept={}",
        name, surname, corporate_email, department,
    )

    async for session in get_session():
        existing = await session.scalar(
            select(Employee).where(Employee.corporate_email == corporate_email)
        )
        if existing:
            raise DuplicateEmployeeError(
                f"Employee with corporate email {corporate_email!r} already exists (id={existing.id})"
            )

        employee = Employee(
            name=name,
            surname=surname,
            email=corporate_email,          # kept for backwards compat (unique constraint)
            corporate_email=corporate_email,
            private_email=private_email_clean,
            temp_password_hash=password_hash,
            phone=phone or None,
            department=department or None,
            line_manager=line_manager or None,
        )
        session.add(employee)
        try:
            await session.commit()
            await session.refresh(employee)
        except IntegrityError:
            await session.rollback()
            raise DuplicateEmployeeError(
                f"Employee with corporate email {corporate_email!r} already exists (race condition)"
            )

        logger.info(
            "[entra_id_mock] AD user created | id={} corporate_email={}",
            employee.id, corporate_email,
        )
        return EmployeeRecord(
            id=employee.id,
            name=employee.name,
            surname=employee.surname,
            corporate_email=corporate_email,
            private_email=private_email_clean,
            phone=employee.phone,
            department=employee.department,
            line_manager=employee.line_manager,
            temp_password=temp_password,
        )

    raise RuntimeError("get_session() yielded nothing — database not initialised")
