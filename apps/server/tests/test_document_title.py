import pytest
import asyncio
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database.database import init_db, close_db
from app.types.models import Document


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def fresh_db():
    _run_async(init_db())
    yield
    _run_async(close_db())


@pytest.fixture
def client():
    return TestClient(app)


def _new_doc_id() -> str:
    return f"doc-title-{uuid.uuid4().hex[:8]}"


async def _mock_join_with_document(client_id: str, doc_id: str, ws) -> Document:
    doc = Document(id=doc_id, version=0, blocks=[])
    data = doc.model_dump()
    await ws.send_json(data)
    return doc


class TestDocumentTitle:
    def test_create_document_with_title(self, client):
        doc_id = _new_doc_id()
        res = client.post(f"/api/documents/{doc_id}", json={"title": "AI Agent 项目笔记"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "created"

        # verify title is persisted
        get_res = client.get(f"/api/documents/{doc_id}")
        assert get_res.status_code == 200
        doc = get_res.json()
        assert doc["title"] == "AI Agent 项目笔记"

    def test_create_document_without_title_uses_default(self, client):
        doc_id = _new_doc_id()
        res = client.post(f"/api/documents/{doc_id}", json={})
        assert res.status_code == 200

        get_res = client.get(f"/api/documents/{doc_id}")
        assert get_res.status_code == 200
        doc = get_res.json()
        assert doc["title"] == "未命名文档"

    def test_create_document_with_empty_title_uses_default(self, client):
        doc_id = _new_doc_id()
        res = client.post(f"/api/documents/{doc_id}", json={"title": "   "})
        assert res.status_code == 200

        get_res = client.get(f"/api/documents/{doc_id}")
        assert get_res.status_code == 200
        doc = get_res.json()
        assert doc["title"] == "未命名文档"

    def test_update_title(self, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={"title": "原始标题"})

        patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": "新标题"})
        assert patch_res.status_code == 200
        data = patch_res.json()
        assert data["status"] == "updated"
        assert data["title"] == "新标题"

        # verify persistence
        get_res = client.get(f"/api/documents/{doc_id}")
        assert get_res.status_code == 200
        doc = get_res.json()
        assert doc["title"] == "新标题"

    def test_update_title_trims_and_limits(self, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={})

        long_title = "a" * 150
        patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": f"  {long_title}  "})
        assert patch_res.status_code == 200
        data = patch_res.json()
        assert data["title"] == "a" * 100

    def test_update_title_empty_uses_default(self, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={"title": "有标题"})

        patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": "   "})
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "未命名文档"

        get_res = client.get(f"/api/documents/{doc_id}")
        assert get_res.json()["title"] == "未命名文档"

    def test_update_title_not_found(self, client):
        patch_res = client.patch("/api/documents/not-exist-title/title", json={"title": "新标题"})
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "not_found"

    def test_get_document_not_found(self, client):
        res = client.get("/api/documents/not-exist-title-2")
        assert res.status_code == 200
        assert res.json()["status"] == "not_found"

    def _receive_skipping_presence(self, ws):
        while True:
            msg = ws.receive_json()
            if msg.get("type") != "presence":
                return msg

    def test_title_update_broadcasts_to_all_clients(self, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={"title": "原始标题"})

        with client.websocket_connect(f"/ws/{doc_id}") as ws_a:
            ws_a.send_json({"type": "join", "client_id": "c_a"})
            ws_a.receive_json()

            with client.websocket_connect(f"/ws/{doc_id}") as ws_b:
                ws_b.send_json({"type": "join", "client_id": "c_b"})
                ws_b.receive_json()

                patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": "新标题"})
                assert patch_res.status_code == 200

                msg_a = self._receive_skipping_presence(ws_a)
                assert msg_a["type"] == "document_title_updated"
                assert msg_a["document_id"] == doc_id
                assert msg_a["title"] == "新标题"

                msg_b = self._receive_skipping_presence(ws_b)
                assert msg_b["type"] == "document_title_updated"
                assert msg_b["document_id"] == doc_id
                assert msg_b["title"] == "新标题"

    def test_title_update_not_broadcasted_to_other_documents(self, client):
        doc_id_a = _new_doc_id()
        doc_id_b = _new_doc_id()
        client.post(f"/api/documents/{doc_id_a}", json={"title": "A"})
        client.post(f"/api/documents/{doc_id_b}", json={"title": "B"})

        with client.websocket_connect(f"/ws/{doc_id_a}") as ws_a:
            ws_a.send_json({"type": "join", "client_id": "c_a"})
            ws_a.receive_json()

            with client.websocket_connect(f"/ws/{doc_id_b}") as ws_b:
                ws_b.send_json({"type": "join", "client_id": "c_b"})
                ws_b.receive_json()

                client.patch(f"/api/documents/{doc_id_a}/title", json={"title": "A新标题"})

                msg_a = self._receive_skipping_presence(ws_a)
                assert msg_a["type"] == "document_title_updated"
                assert msg_a["title"] == "A新标题"

    @patch("app.websocket.connection.ConnectionManager.broadcast_title_update", new_callable=AsyncMock)
    def test_title_update_broadcast_called_after_persistence(self, mock_broadcast, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={"title": "原始标题"})

        patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": "广播测试"})
        assert patch_res.status_code == 200

        mock_broadcast.assert_called_once_with(doc_id, "广播测试")

    def test_title_update_persisted_before_broadcast(self, client):
        doc_id = _new_doc_id()
        client.post(f"/api/documents/{doc_id}", json={"title": "原始标题"})

        with client.websocket_connect(f"/ws/{doc_id}") as ws:
            ws.send_json({"type": "join", "client_id": "c1"})
            ws.receive_json()

            patch_res = client.patch(f"/api/documents/{doc_id}/title", json={"title": "持久化测试"})
            assert patch_res.status_code == 200

            msg = self._receive_skipping_presence(ws)
            assert msg["type"] == "document_title_updated"
            assert msg["title"] == "持久化测试"

            get_res = client.get(f"/api/documents/{doc_id}")
            assert get_res.status_code == 200
            assert get_res.json()["title"] == "持久化测试"