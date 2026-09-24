from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.types.models import Operation, OperationType
from app.websocket.connection import ConnectionManager

router = APIRouter()

_VALID_OPERATION_TYPES: frozenset[str] = frozenset(OperationType.__args__)


@router.websocket("/ws/{doc_id}")
async def websocket_endpoint(ws: WebSocket, doc_id: str):
    await ws.accept()
    client_id = ""

    try:
        join_msg = await ws.receive_json()
        client_id = join_msg.get("client_id", "")
        if not client_id:
            await ws.send_json({"type": "error", "reason": "Missing client_id"})
            await ws.close()
            return

        try:
            await ConnectionManager.join(client_id, doc_id, ws)
            await ConnectionManager.broadcast_presence(doc_id)
        except ValueError:
            return

        while True:
            raw = await ws.receive_json()
            msg_type = raw.get("type")

            if msg_type == "operation":
                op = Operation.model_validate(raw.get("operation", raw))
            elif msg_type in _VALID_OPERATION_TYPES:
                op = Operation.model_validate(raw)
            else:
                await ws.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })
                continue

            result = await ConnectionManager.handle_operation(
                client_id, doc_id, op
            )
            await ws.send_json(result.model_dump())

            if result.type == "ack" and result.status == "applied":
                op_data = op.model_dump()
                op_data["version"] = result.version
                await ConnectionManager.broadcast_raw(doc_id, client_id, op_data)

    except WebSocketDisconnect:
        pass
    finally:
        if client_id:
            await ConnectionManager.leave(client_id, doc_id)
            await ConnectionManager.broadcast_presence(doc_id)