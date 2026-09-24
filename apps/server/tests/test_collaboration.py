import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.types.models import Document


async def mock_join_with_document(client_id: str, doc_id: str, ws) -> Document:
    doc = Document(id=doc_id, version=0, blocks=[])
    data = doc.model_dump()
    await ws.send_json(data)
    return doc


def _make_ack_result(op_id: str, version: int, status: str = "applied") -> MagicMock:
    m = MagicMock()
    m.type = "ack"
    m.operation_id = op_id
    m.version = version
    m.status = status
    m.document_id = "doc_1"
    m.model_dump.return_value = {
        "type": "ack",
        "operation_id": op_id,
        "version": version,
        "status": status,
        "document_id": "doc_1",
    }
    return m


def _make_conflict_result(op_id: str, version: int) -> MagicMock:
    m = MagicMock()
    m.type = "conflict"
    m.operation_id = op_id
    m.document_id = "doc_1"
    m.current_version = version
    m.reason = "Version mismatch"
    m.model_dump.return_value = {
        "type": "conflict",
        "operation_id": op_id,
        "current_version": version,
        "reason": "Version mismatch",
        "document_id": "doc_1",
    }
    return m


@pytest.fixture
def client():
    return TestClient(app)


class TestCollaboration:
    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.broadcast_raw", new_callable=AsyncMock)
    @patch("app.websocket.connection.ConnectionManager.handle_operation", new_callable=AsyncMock)
    def test_client_a_edits_client_b_receives(self, mock_handle, mock_broadcast, _mock_join, client):
        mock_handle.return_value = _make_ack_result("op1", 1)

        with client.websocket_connect("/ws/doc_1") as ws_a:
            ws_a.send_json({"type": "join", "client_id": "c_a"})
            ws_a.receive_json()

            ws_a.send_json({
                "type": "operation",
                "id": "op1",
                "client_id": "c_a",
                "document_id": "doc_1",
                "block_id": "b1",
                "type": "insert",
                "position": 0,
                "content": "hello",
                "version": 1,
            })
            ack = ws_a.receive_json()
            assert ack.get("type") == "ack"

            mock_broadcast.assert_called_once()
            _, sender_id, op_data = mock_broadcast.call_args[0]
            assert sender_id == "c_a"
            assert op_data.get("version") == 1

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.handle_operation", new_callable=AsyncMock)
    def test_conflict_scenario(self, mock_handle, _mock_join, client):
        mock_handle.return_value = _make_conflict_result("op1", 5)

        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

            ws.send_json({
                "type": "operation",
                "id": "op1",
                "client_id": "c1",
                "document_id": "doc_1",
                "block_id": "b1",
                "type": "insert",
                "position": 0,
                "content": "hello",
                "version": 1,
            })
            data = ws.receive_json()
            assert data.get("type") == "conflict"
            assert data.get("current_version") == 5

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.leave", new_callable=AsyncMock)
    def test_reconnect_cleanup(self, mock_leave, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

        mock_leave.assert_called_once_with("c1", "doc_1")

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.broadcast_raw", new_callable=AsyncMock)
    @patch("app.websocket.connection.ConnectionManager.handle_operation", new_callable=AsyncMock)
    def test_duplicate_operation_not_broadcast(self, mock_handle, mock_broadcast, _mock_join, client):
        mock_handle.return_value = _make_ack_result("op1", 1, status="duplicate")

        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

            ws.send_json({
                "type": "operation",
                "id": "op1",
                "client_id": "c1",
                "document_id": "doc_1",
                "block_id": "b1",
                "type": "insert",
                "position": 0,
                "content": "hello",
                "version": 1,
            })
            ack = ws.receive_json()
            assert ack.get("status") == "duplicate"
            mock_broadcast.assert_not_called()