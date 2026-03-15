"""POST /v1/responses — OpenAI Responses API with streaming support."""

import json
from not_your_it_guy.logger.logger_provider import get_logger
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from not_your_it_guy.auth import require_auth
from not_your_it_guy.models import (
    OutputTextContent,
    ResponseObject,
    ResponseOutputMessage,
    ResponseRequest,
    ResponseUsage,
    StreamEventResponseCompleted,
    StreamEventResponseCreated,
    StreamEventTextDelta,
    StreamEventTextDone,
)
from not_your_it_guy.services import router_service, subgraph_factory

logger = get_logger()
router = APIRouter(prefix="/v1", tags=["responses"], dependencies=[Depends(require_auth)])

_FALLBACK_TEXT = (
    "I'm not sure how to help with that yet. "
    "No matching workflow was found for your request."
)


def _sse(event: str, data: str) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {data}\n\n"


def _extract_text(request: ResponseRequest) -> str:
    """Pull plain text out of either a string or message-list input."""
    if isinstance(request.input, str):
        return request.input
    parts = []
    for msg in request.input:
        if isinstance(msg.content, str):
            parts.append(msg.content)
        else:
            parts.extend(item.text for item in msg.content)
    return " ".join(parts)


async def _stream_response(request: ResponseRequest) -> AsyncIterator[bytes]:
    """Core streaming generator.

    1. Classify intent + extract params via router_service (RouterResult).
    2. Look up the matching subgraph in subgraph_factory.
    3. Stream chunks back as OpenAI-compatible SSE events.
    """
    resp_id = f"resp_{uuid.uuid4().hex[:24]}"
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    user_text = _extract_text(request)

    logger.debug("POST /v1/responses stream=True model={} input={}", request.model, user_text)
    logger.info("Incoming streaming request | model={} | input={}", request.model, user_text)

    # ── response.created ────────────────────────────────────────────────────
    yield _sse(
        "response.created",
        StreamEventResponseCreated(
            response=ResponseObject(
                id=resp_id, model=request.model, output=[], metadata=request.metadata or {}
            )
        ).model_dump_json(),
    ).encode()

    # ── classify intent + extract params ────────────────────────────────────
    router_result = await router_service.detect_intent(user_text, request.metadata)
    stream_fn = subgraph_factory.get(router_result.intent)

    # ── stream text deltas ───────────────────────────────────────────────────
    full_text = ""
    chunks: AsyncIterator[str]

    if stream_fn is None:
        logger.info("No subgraph for intent={} — streaming fallback", router_result.intent)
        chunks = _fallback_stream()
    else:
        chunks = stream_fn(router_result)

    async for chunk in chunks:
        full_text += chunk
        yield _sse(
            "response.output_text.delta",
            StreamEventTextDelta(item_id=msg_id, delta=chunk).model_dump_json(),
        ).encode()

    # ── response.output_text.done ────────────────────────────────────────────
    yield _sse(
        "response.output_text.done",
        StreamEventTextDone(item_id=msg_id, text=full_text).model_dump_json(),
    ).encode()

    # ── response.completed ───────────────────────────────────────────────────
    yield _sse(
        "response.completed",
        StreamEventResponseCompleted(
            response=ResponseObject(
                id=resp_id,
                model=request.model,
                output=[
                    ResponseOutputMessage(
                        id=msg_id, content=[OutputTextContent(text=full_text)]
                    )
                ],
                usage=ResponseUsage(output_tokens=len(full_text.split())),
                metadata=request.metadata or {},
            )
        ).model_dump_json(),
    ).encode()

    logger.info(
        "Streaming complete | resp_id=%s | intent=%r | chars=%d",
        resp_id, router_result.intent, len(full_text),
    )


async def _fallback_stream() -> AsyncIterator[str]:
    for word in _FALLBACK_TEXT.split():
        yield word + " "


@router.post("/responses", response_model=None)
async def create_response(request: ResponseRequest) -> StreamingResponse | ResponseObject:
    logger.debug("POST /v1/responses model={} stream={}", request.model, request.stream)
    logger.info(
        "Incoming request:\n%s",
        json.dumps(request.model_dump(), indent=2, default=str),
    )

    if request.stream:
        return StreamingResponse(
            _stream_response(request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Non-streaming: collect full response then return JSON ────────────────
    user_text = _extract_text(request)
    router_result = await router_service.detect_intent(user_text, request.metadata)
    stream_fn = subgraph_factory.get(router_result.intent)

    full_text = ""
    if stream_fn is None:
        logger.info("No subgraph for intent={} — using fallback", router_result.intent)
        async for chunk in _fallback_stream():
            full_text += chunk
    else:
        async for chunk in stream_fn(router_result):
            full_text += chunk

    response = ResponseObject(
        model=request.model,
        output=[ResponseOutputMessage(content=[OutputTextContent(text=full_text.strip())])],
        usage=ResponseUsage(output_tokens=len(full_text.split())),
        metadata=request.metadata or {},
    )

    logger.info(
        "Outgoing response:\n%s",
        json.dumps(response.model_dump(), indent=2, default=str),
    )
    return response
