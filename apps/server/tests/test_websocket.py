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


class TestWebSocket:
    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    def test_connection_established(self, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            data = ws.receive_json()
            assert data.get("id") == "doc_1"

    @patch("app.websocket.connection.ConnectionManager.join", new_callable=AsyncMock)
    def test_missing_client_id_rejected(self, mock_join, client):
        mock_join.return_value = Document(id="doc_1", version=0, blocks=[])

        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join"})
            data = ws.receive_json()
            assert data.get("type") == "error"

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.handle_operation", new_callable=AsyncMock)
    @patch("app.websocket.connection.ConnectionManager.broadcast_raw", new_callable=AsyncMock)
    def test_operation_sent_and_ack_received(self, mock_broadcast, mock_handle, _mock_join, client):
        mock_handle.return_value = _make_ack_result("op1", 1)

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
            assert data.get("type") == "ack"

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.broadcast_raw", new_callable=AsyncMock)
    @patch("app.websocket.connection.ConnectionManager.handle_operation", new_callable=AsyncMock)
    def test_broadcast_excludes_sender(self, mock_handle, mock_broadcast, _mock_join, client):
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
            ws_a.receive_json()

            mock_broadcast.assert_called_once()
            _, sender_id, _ = mock_broadcast.call_args[0]
            assert sender_id == "c_a"

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.leave", new_callable=AsyncMock)
    def test_disconnect_calls_leave(self, mock_leave, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

        mock_leave.assert_called_once_with("c1", "doc_1")

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.broadcast_presence", new_callable=AsyncMock)
    def test_join_broadcasts_presence(self, mock_presence, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

        # join triggers broadcast_presence, and disconnect in finally also triggers it
        assert mock_presence.call_count == 2
        mock_presence.assert_called_with("doc_1")

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.leave", new_callable=AsyncMock)
    @patch("app.websocket.connection.ConnectionManager.broadcast_presence", new_callable=AsyncMock)
    def test_disconnect_broadcasts_presence(self, mock_presence, mock_leave, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

        mock_leave.assert_called_once_with("c1", "doc_1")
        mock_presence.assert_called_with("doc_1")

    @patch("app.websocket.connection.ConnectionManager.join", side_effect=mock_join_with_document)
    @patch("app.websocket.connection.ConnectionManager.broadcast_presence", new_callable=AsyncMock)
    def test_presence_includes_all_users(self, mock_presence, _mock_join, client):
        with client.websocket_connect("/ws/doc_1") as ws_a:
            ws_a.send_json({"type": "join", "client_id": "c_a"})
            ws_a.receive_json()

            with client.websocket_connect("/ws/doc_1") as ws_b:
                ws_b.send_json({"type": "join", "client_id": "c_b"})
                ws_b.receive_json()

        assert mock_presence.call_count >= 2

    def test_join_nonexistent_document(self, client):
        with client.websocket_connect("/ws/not-exist") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            data = ws.receive_json()
            assert data.get("type") == "error"
            assert "not found" in data.get("reason", "")