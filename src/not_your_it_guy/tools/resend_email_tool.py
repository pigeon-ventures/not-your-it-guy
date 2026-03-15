"""Resend email tool.

Uses the Resend Python SDK to send transactional emails.
Falls back to console logging if RESEND_API_KEY is not set.

Requirements:
- RESEND_API_KEY: from https://resend.com/api-keys
- RESEND_FROM_EMAIL: verified sender address, e.g. "B2 IT <onboarding@yourdomain.com>"
  On free tier without a verified domain use "onboarding@resend.dev" (sends only to your own email)
"""

import os

import resend

from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()


def _credentials_available() -> bool:
    return bool(os.getenv("RESEND_API_KEY"))


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Returns True on success, False on failure.

    Falls back to console log if RESEND_API_KEY is not set.
    """
    if not _credentials_available():
        return False

    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    resend.api_key = os.getenv("RESEND_API_KEY")

    try:
        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        email = resend.Emails.send(params)
        logger.info("[resend] email sent to {} | id={}", to, email.get("id"))
        return True
    except Exception as exc:
        logger.warning("[resend] email to {} not delivered ({}), continuing flow", to, exc)
        return False
