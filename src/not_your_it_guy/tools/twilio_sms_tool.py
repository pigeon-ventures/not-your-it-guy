"""Twilio SMS tool via LangChain community integration.

Uses TwilioAPIWrapper from langchain-community which wraps the Twilio
Python SDK. Falls back to console logging if credentials are not set.
"""

import os
from functools import lru_cache

from not_your_it_guy.logger.logger_provider import get_logger

logger = get_logger()


def _credentials_available() -> bool:
    return all(
        os.getenv(k)
        for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER")
    )


@lru_cache(maxsize=1)
def _get_twilio():
    from langchain_community.utilities.twilio import TwilioAPIWrapper

    return TwilioAPIWrapper(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        from_number=os.getenv("TWILIO_FROM_NUMBER"),
    )


async def send_sms(to: str, body: str) -> bool:
    """Send an SMS via Twilio. Returns True on success, False on failure.

    Falls back to console log if TWILIO_* env vars are not set.
    """
    if not _credentials_available():
        return False

    try:
        twilio = _get_twilio()
        twilio.run(body, to)
        logger.info("[twilio_sms] SMS sent to {}", to)
        return True
    except Exception as exc:
        logger.warning("[twilio_sms] SMS to {} not delivered ({}), continuing flow", to, exc)
        return False
