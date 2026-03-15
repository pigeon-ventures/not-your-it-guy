"""SMS service — sends temporary password via Twilio.

Uses the LangChain TwilioAPIWrapper tool under the hood.
Falls back to console logging if TWILIO_* env vars are not configured.
"""

from not_your_it_guy.logger.logger_provider import get_logger
from not_your_it_guy.tools.twilio_sms_tool import _credentials_available, send_sms

logger = get_logger()


async def send_temp_password_sms(phone: str, temp_password: str, corporate_email: str) -> None:
    """Send the temporary password to the employee's phone via SMS."""
    body = (
        f"Welcome to B2! Your corporate account has been created.\n"
        f"Login: {corporate_email}\n"
        f"Temporary password: {temp_password}\n"
        f"Please change your password after first login."
    )

    if _credentials_available():
        await send_sms(to=phone, body=body)
    else:
        logger.info(
            "[sms_service] Twilio not configured — temporary password for B2 account"
            " sent to {}: {}",
            phone,
            temp_password,
        )
