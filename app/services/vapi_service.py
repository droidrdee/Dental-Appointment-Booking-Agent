from typing import Any

from pydantic import BaseModel, Field


class VapiCall(BaseModel):
    id: str
    customer: dict[str, Any] = Field(default_factory=dict)


class VapiToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class VapiMessage(BaseModel):
    type: str
    call: VapiCall | None = None
    toolCallList: list[VapiToolCall] = Field(default_factory=list)
    transcript: str | None = None
    summary: str | None = None


class VapiWebhookPayload(BaseModel):
    message: VapiMessage


def extract_tool_text(tool_call: VapiToolCall) -> str:
    arguments = tool_call.arguments
    for key in ("value", "text", "name", "service", "datetime", "confirmation"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(arguments).strip()


def build_tool_result(tool_call_id: str, result: str) -> dict[str, list[dict[str, str]]]:
    return {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": result,
            }
        ]
    }


def build_tool_results(results: list[tuple[str, str]]) -> dict[str, list[dict[str, str]]]:
    return {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": result,
            }
            for tool_call_id, result in results
        ]
    }


def build_assistant_config() -> dict[str, Any]:
    return {
        "assistant": {
            "name": "SmileCare Dental Receptionist",
            "firstMessage": "Thanks for calling SmileCare Dental. I can help book an appointment.",
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a dental receptionist. Collect patient name, service, "
                            "date/time, and confirmation using the configured server tools."
                        ),
                    }
                ],
            },
            "serverMessages": ["tool-calls", "end-of-call-report", "status-update"],
        }
    }

