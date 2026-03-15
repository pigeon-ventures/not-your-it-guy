"""Welcome email service — sends onboarding email via SendGrid.

Falls back to console logging if SENDGRID_API_KEY is not configured.
"""

from not_your_it_guy.logger.logger_provider import get_logger
from not_your_it_guy.tools.sendgrid_email_tool import _credentials_available, send_email

logger = get_logger()

_USEFUL_LINKS_HTML = """
<ul>
  <li><a href="https://outlook.cloud.microsoft/">Microsoft Mailbox</a></li>
  <li><a href="https://www.notion.so/">Notion</a> (invite sent to corporate email)</li>
  <li><a href="https://teams.microsoft.com/">Microsoft Teams</a></li>
</ul>
"""


def _build_html(name: str, corporate_email: str, phone: str | None) -> str:
    phone_display = phone or "the phone number provided during onboarding"
    return f"""
<pre style="font-family:monospace;font-size:13px;color:#00ff99;background:#0d0d0d;padding:16px;border-radius:6px;">
  >> JESSICA
  >> YOUR AI IT ADMIN
  >> B2 CORP
</pre>

<p>Hey {name},</p>

<p>Account provisioned. You're in. Here's what you need:</p>

<table style="font-family:monospace;border-collapse:collapse;">
  <tr><td style="padding:4px 12px 4px 0;color:#888;">CORP EMAIL</td><td><strong>{corporate_email}</strong></td></tr>
  <tr><td style="padding:4px 12px 4px 0;color:#888;">TEMP PASSWORD</td><td>sent via SMS to <strong>{phone_display}</strong></td></tr>
</table>

<p style="color:#cc0000;"><strong>⚠ Change your password on first login.</strong></p>

<h3>Access your tools:</h3>
{_USEFUL_LINKS_HTML}

<p>I'll be around if you need anything. Just ask.<br>
— <strong>Jessica</strong>, your AI IT Admin</p>

<p style="font-size:11px;color:#888;font-family:monospace;">
  This message was generated automatically by Jessica, B2's AI IT Admin.
</p>
"""


def _build_text(name: str, corporate_email: str, phone: str | None) -> str:
    phone_display = phone or "the phone number provided during onboarding"
    return f"""
  >> JESSICA
  >> YOUR AI IT ADMIN
  >> B2 CORP

Hey {name},

Account provisioned. You're in.

  CORP EMAIL    : {corporate_email}
  TEMP PASSWORD : sent via SMS to {phone_display}

[!] Change your password on first login.

Access your tools:
  - Microsoft Mailbox : https://outlook.cloud.microsoft/
  - Notion            : https://www.notion.so/ (invite sent to corporate email)
  - Microsoft Teams   : https://teams.microsoft.com/

I'll be around if you need anything. Just ask.
— Jessica, your AI IT Admin

---
This message was generated automatically by Jessica, B2's AI IT Admin.
"""


async def send_welcome_email(
    name: str,
    corporate_email: str,
    private_email: str | None,
    phone: str | None,
) -> None:
    """Send welcome email to private inbox. Logs to console if Resend not configured."""
    # Welcome email goes to private inbox — contains instructions to access corporate email
    recipient = private_email or corporate_email
    if not private_email:
        logger.warning(
            "[welcome_email] no private email provided, falling back to corporate: {}",
            corporate_email,
        )

    subject = "Welcome to B2 — your account is ready"
    html = _build_html(name, corporate_email, phone)
    text = _build_text(name, corporate_email, phone)

    if _credentials_available():
        await send_email(to=recipient, subject=subject, html=html, text=text)
    else:
        logger.info(
            "[welcome_email] SENDGRID_API_KEY not set — logging email instead\nTo: {}\nSubject: {}\n\n{}",
            recipient, subject, text,
        )
