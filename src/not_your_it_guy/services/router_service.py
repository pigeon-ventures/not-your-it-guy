"""Router service — keyword pre-filter + LLM-based intent classification.

Two-stage routing:
  1. Fast keyword scan — if a clear signal is found, skip the LLM call entirely.
  2. LLM call (gpt-4o-mini) — for ambiguous inputs; returns structured JSON with
     both the intent and extracted parameters.

Returns a RouterResult which is the contract passed to every subgraph.
"""

import json
from not_your_it_guy.logger.logger_provider import get_logger
import os

from openai import AsyncOpenAI

from not_your_it_guy.models import EmployeeOnboardingParams, RouterResult
from not_your_it_guy.services.subgraph_factory import known_intents

logger = get_logger()

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY env variable is not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Keyword pre-filter
# Per-intent keyword lists — extend as new intents are added.
# ---------------------------------------------------------------------------

_KEYWORDS: dict[str, list[str]] = {
    "employee_onboarding": [
        "onboard",
        "onboarding",
        "new hire",
        "new employee",
        "new joiner",
        "first day",
        "start date",
        "joining",
        "welcome",
        "induction",
        "probation",
        "equipment setup",
        "laptop setup",
        "access setup",
        "badge",
        "orientation",
    ],
}


def _keyword_match(text: str) -> str | None:
    """Return the first intent whose keywords match the input, or None."""
    lower = text.lower()
    for intent, keywords in _KEYWORDS.items():
        if intent not in known_intents():
            continue
        if any(kw in lower for kw in keywords):
            logger.info("router_service: keyword match → intent={}", intent)
            return intent
    return None


# ---------------------------------------------------------------------------
# LLM prompt with few-shot examples
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an intent classifier and parameter extractor for an AI assistant backend.

Given a user message (and optionally pre-filled metadata), classify the request \
into one of the following intents and extract structured parameters.

Available intents:
{intents}

Rules:
- Return ONLY a valid JSON object, nothing else.
- JSON must have exactly two keys: "intent" and "params".
- If no intent matches, set "intent" to "unknown" and "params" to {{}}.
- Extract as much structured data as possible from BOTH the message and the metadata.

Intent schemas:

employee_onboarding:
  params: {{ name, surname, email, phone, department, line_manager }}

Examples:

Input: "I need to onboard John Doe starting Monday in the Engineering team"
Metadata: {{}}
Output:
{{
  "intent": "employee_onboarding",
  "params": {{
    "name": "John",
    "surname": "Doe",
    "email": "",
    "phone": "",
    "department": "Engineering",
    "line_manager": ""
  }}
}}

Input: "help me onboard a new employee"
Metadata: {{"name": "Anna", "surname": "Smith", "email": "anna@company.com", "phone": "+1 555 000 1111", "department": "Sales", "line_manager": "Bob Jones"}}
Output:
{{
  "intent": "employee_onboarding",
  "params": {{
    "name": "Anna",
    "surname": "Smith",
    "email": "anna@company.com",
    "phone": "+1 555 000 1111",
    "department": "Sales",
    "line_manager": "Bob Jones"
  }}
}}

Input: "what is the weather today"
Metadata: {{}}
Output:
{{
  "intent": "unknown",
  "params": {{}}
}}
"""


async def _llm_classify(user_input: str, metadata: dict) -> tuple[str, dict]:
    """Call gpt-4o-mini and return (intent, params dict).

    Falls back to ("unknown", {}) on any failure.
    """
    intents = known_intents()
    system = _SYSTEM_PROMPT.format(intents="\n".join(f"- {i}" for i in intents))
    user_msg = f'Input: "{user_input}"\nMetadata: {json.dumps(metadata)}'

    try:
        response = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
        # Strip accidental markdown code fences
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
        intent = parsed.get("intent", "unknown").strip().lower()
        params = parsed.get("params", {})
        if intent not in intents:
            logger.info("router_service: LLM returned unknown intent={}", intent)
            intent = "unknown"
        return intent, params
    except Exception:
        logger.exception("router_service: LLM classification failed")
        return "unknown", {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_intent(user_input: str, metadata: dict | None = None) -> RouterResult:
    """Classify user_input and extract structured parameters.

    Stage 1 — keyword pre-filter (no API call).
    Stage 2 — LLM classification with parameter extraction.

    Always returns a RouterResult; intent is "unknown" when nothing matches.
    """
    metadata = metadata or {}

    # Stage 1: keyword pre-filter
    keyword_intent = _keyword_match(user_input)
    if keyword_intent:
        # Still call LLM to extract params, but we already know the intent
        logger.debug("router_service: keyword hit, calling LLM for param extraction only")
        _, params = await _llm_classify(user_input, metadata)
        # Merge metadata into params as fallback for empty fields
        merged = {**metadata, **{k: v for k, v in params.items() if v}}
    else:
        # Stage 2: full LLM classification
        logger.debug("router_service: no keyword match, calling LLM for classification")
        keyword_intent, params = await _llm_classify(user_input, metadata)
        merged = {**metadata, **{k: v for k, v in params.items() if v}}

    intent = keyword_intent or "unknown"

    # Build typed params for the matched intent
    if intent == "employee_onboarding":
        typed_params = EmployeeOnboardingParams(**{
            k: merged.get(k, "") for k in EmployeeOnboardingParams.model_fields
        })
    else:
        typed_params = EmployeeOnboardingParams()

    result = RouterResult(
        intent=intent,
        params=typed_params,
        raw_input=user_input,
        metadata=metadata,
    )

    logger.info(
        "router_service: intent={} name={} dept={}",
        result.intent,
        result.params.name,
        result.params.department,
    )
    return result
