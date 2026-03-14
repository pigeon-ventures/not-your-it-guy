"""POST /v1/responses — OpenAI Responses API stub."""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from not_your_it_guy.models import (
    OutputTextContent,
    ResponseObject,
    ResponseOutputMessage,
    ResponseRequest,
    ResponseUsage,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["responses"])


@router.post("/responses")
async def create_response(request: ResponseRequest) -> ResponseObject:
    logger.debug("POST /v1/responses model=%s stream=%s", request.model, request.stream)
    logger.info(
        "Incoming request:\n%s",
        json.dumps(request.model_dump(), indent=2, default=str),
    )

    response = ResponseObject(
        model=request.model,
        output=[
            ResponseOutputMessage(
                content=[OutputTextContent(text="Prompt accepted.")]
            )
        ],
        usage=ResponseUsage(input_tokens=0, output_tokens=2, total_tokens=2),
        metadata=request.metadata or {},
    )

    logger.info(
        "Outgoing response:\n%s",
        json.dumps(response.model_dump(), indent=2, default=str),
    )

    return response
