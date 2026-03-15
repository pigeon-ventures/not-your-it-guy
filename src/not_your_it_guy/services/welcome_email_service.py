"""Welcome email service — stub for Resend integration.

Currently logs the email content. Replace `_send_via_resend` body
when RESEND_API_KEY is available.
"""

import os

from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()

_USEFUL_LINKS = """
- Microsoft mailbox: https://outlook.cloud.microsoft/
- Notion: https://www.notion.so/ (invite sent to corporate email)
- Microsoft Teams: https://teams.microsoft.com/
"""


def _build_body(
    name: str,
    corporate_email: str,
    phone: str | None,
) -> str:
    phone_display = phone or "the phone number provided during onboarding"
    return f"""Hi {name},

You have been successfully onboarded at B2 company!

Your corporate email address is: {corporate_email}
Your temporary password was sent to: {phone_display}

Useful links:{_USEFUL_LINKS}
We're happy you're with us and excited to connect once you log in to our corporate suite.

Welcome aboard!
The IT Team
"""


async def send_welcome_email(
    name: str,
    corporate_email: str,
    private_email: str | None,
    phone: str | None,
) -> None:
    """Send a welcome email to the new employee's private inbox.

    Currently a stub — logs the email. Wire up Resend when ready.
    """
    body = _build_body(name, corporate_email, phone)
    # Welcome email goes to private inbox — the user needs it to access corporate email
    recipient = private_email or corporate_email
    if not private_email:
        logger.warning("[welcome_email] no private email provided, falling back to corporate: {}", corporate_email)

    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key:
        await _send_via_resend(
            api_key=resend_api_key,
            to=recipient,
            subject="Welcome to B2 — your account is ready",
            body=body,
        )
    else:
        logger.info(
            "[welcome_email] RESEND_API_KEY not set — logging email instead\n"
            "To: {}\nSubject: Welcome to B2 — your account is ready\n\n{}",
            recipient, body,
        )


async def _send_via_resend(api_key: str, to: str, subject: str, body: str) -> None:
    """TODO: implement Resend API call.

    Example:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": "onboarding@b2.com",
            "to": to,
            "subject": subject,
            "text": body,
        })
    """
    logger.info("[welcome_email] Resend integration not yet implemented — skipping send to {}", to)
