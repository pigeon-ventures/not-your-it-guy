"""OpenAI Responses API compatible request/response models."""

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Router contract — passed from router_service to every subgraph
# ---------------------------------------------------------------------------


class EmployeeOnboardingParams(BaseModel):
    name: str = ""
    surname: str = ""
    email: str = ""          # private email (from the request metadata)
    phone: str = ""
    department: str = ""
    line_manager: str = ""


class RouterResult(BaseModel):
    """Structured output of the semantic router.

    `intent`     — matched subgraph name (e.g. "employee_onboarding") or "unknown"
    `params`     — intent-specific structured data extracted from the request
    `raw_input`  — original user message, always forwarded so subgraphs can use it
    `metadata`   — raw metadata dict from the API request (e.g. pre-filled form fields)
    """

    intent: str
    params: EmployeeOnboardingParams = Field(default_factory=EmployeeOnboardingParams)
    raw_input: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class ResponseInputText(BaseModel):
    type: Literal["input_text"] = "input_text"
    text: str


class ResponseInputMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str | list[ResponseInputText]


class ResponseRequest(BaseModel):
    model: str
    input: str | list[ResponseInputMessage]
    instructions: str | None = None
    max_output_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stream: bool | None = False
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class OutputTextContent(BaseModel):
    type: Literal["output_text"] = "output_text"
    text: str
    annotations: list = Field(default_factory=list)


class ResponseOutputMessage(BaseModel):
    id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:24]}")
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    status: Literal["completed"] = "completed"
    content: list[OutputTextContent]


class ResponseUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ResponseObject(BaseModel):
    id: str = Field(default_factory=lambda: f"resp_{uuid.uuid4().hex[:24]}")
    object: Literal["response"] = "response"
    created_at: int = Field(default_factory=lambda: int(time.time()))
    status: Literal["completed"] = "completed"
    model: str
    output: list[ResponseOutputMessage]
    usage: ResponseUsage = Field(default_factory=ResponseUsage)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Streaming events (Server-Sent Events)
# Mirrors the OpenAI Responses API streaming event shapes.
# ---------------------------------------------------------------------------


class StreamEventResponseCreated(BaseModel):
    type: Literal["response.created"] = "response.created"
    response: "ResponseObject"


class StreamEventTextDelta(BaseModel):
    type: Literal["response.output_text.delta"] = "response.output_text.delta"
    item_id: str
    output_index: int = 0
    content_index: int = 0
    delta: str


class StreamEventTextDone(BaseModel):
    type: Literal["response.output_text.done"] = "response.output_text.done"
    item_id: str
    output_index: int = 0
    content_index: int = 0
    text: str


class StreamEventResponseCompleted(BaseModel):
    type: Literal["response.completed"] = "response.completed"
    response: "ResponseObject"
