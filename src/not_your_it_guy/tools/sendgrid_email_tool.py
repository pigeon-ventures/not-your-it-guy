"""SendGrid email tool.

Uses the SendGrid Python SDK to send transactional emails.
Falls back to console logging if SENDGRID_API_KEY is not set.

Requirements:
- SENDGRID_API_KEY: from https://app.sendgrid.com/settings/api_keys
- SENDGRID_FROM_EMAIL: verified single sender, e.g. "B2 IT <onboarding@yourdomain.com>"
"""

import os

from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()


def _credentials_available() -> bool:
    return bool(os.getenv("SENDGRID_API_KEY"))


async def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send an email via SendGrid. Returns True on success, False on failure.

    Falls back to console log if SENDGRID_API_KEY is not set.
    """
    if not _credentials_available():
        return False

    import sendgrid
    from sendgrid.helpers.mail import Content, Email, Mail, To

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email_raw = os.getenv("SENDGRID_FROM_EMAIL", "onboarding@resend.dev")

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)

        contents = []
        if text:
            contents.append(Content("text/plain", text))
        contents.append(Content("text/html", html))

        mail = Mail(
            from_email=Email(from_email_raw),
            to_emails=To(to),
            subject=subject,
        )
        for content in contents:
            mail.add_content(content)

        response = sg.client.mail.send.post(request_body=mail.get())
        logger.info("[sendgrid] email sent to {} | status={}", to, response.status_code)
        return True
    except Exception as exc:
        logger.warning("[sendgrid] email to {} not delivered ({}), continuing flow", to, exc)
        return False
