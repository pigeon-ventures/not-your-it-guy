"""SMS service — mock for Twilio integration.

Currently logs the SMS content to console.
Replace `_send_via_twilio` body when TWILIO_* env vars are available.
"""

import os

from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()


async def send_temp_password_sms(phone: str, temp_password: str, corporate_email: str) -> None:
    """Send temporary password to the employee's phone via SMS.

    Logs to console if TWILIO_ACCOUNT_SID is not set.
    """
    message = (
        f"Welcome to B2! Your corporate account has been created.\n"
        f"Login: {corporate_email}\n"
        f"Temporary password: {temp_password}\n"
        f"Please change your password after first login."
    )

    if os.getenv("TWILIO_ACCOUNT_SID"):
        await _send_via_twilio(to=phone, body=message)
    else:
        logger.info(
            "[sms_service] TWILIO not configured — temporary password for B2 account sent to {}: {}",
            phone,
            temp_password,
        )


async def _send_via_twilio(to: str, body: str) -> None:
    """TODO: implement Twilio SMS send.

    Example:
        from twilio.rest import Client
        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN"),
        )
        client.messages.create(
            body=body,
            from_=os.getenv("TWILIO_FROM_NUMBER"),
            to=to,
        )
    """
    logger.info("[sms_service] Twilio integration not yet implemented — skipping SMS to {}", to)
