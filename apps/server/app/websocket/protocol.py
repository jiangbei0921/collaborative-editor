import json
from typing import Any

from app.types.models import Operation, WebSocketMessage


def parse_message(raw: str | bytes | dict[str, Any]) -> Any:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def parse_operation(data: dict[str, Any]) -> Operation:
    return Operation.model_validate(data)


def serialize_message(msg: WebSocketMessage) -> dict[str, Any]:
    return msg.model_dump()