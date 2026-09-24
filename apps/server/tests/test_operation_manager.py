import pytest
from unittest.mock import AsyncMock, patch

from app.operation.manager import OperationManager
from app.types.models import AckMessage, ConflictMessage, Document, Operation


def make_op(op_id: str, doc_id: str, version: int) -> Operation:
    return Operation(
        id=op_id,
        client_id="c1",
        document_id=doc_id,
        block_id="b1",
        type="insert",
        position=0,
        content="x",
        version=version,
    )


@pytest.mark.asyncio
class TestOperationManager:
    @patch("app.operation.manager.OperationRepository.exists", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.get_document", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.apply_operation", new_callable=AsyncMock)
    @patch("app.operation.manager.OperationRepository.create", new_callable=AsyncMock)
    async def test_normal_operation_applied(self, mock_create, mock_apply, mock_get_doc, mock_exists):
        mock_exists.return_value = False
        mock_get_doc.return_value = Document(id="doc_1", version=0, blocks=[])
        mock_apply.return_value = (Document(id="doc_1", version=1, blocks=[]), 1)

        op = make_op("op1", "doc_1", version=1)
        result = await OperationManager.process("c1", "doc_1", op)

        assert isinstance(result, AckMessage)
        assert result.status == "applied"
        assert result.version == 1
        assert result.operation_id == "op1"

    @patch("app.operation.manager.OperationRepository.exists", new_callable=AsyncMock)
    async def test_duplicate_operation_returns_duplicate(self, mock_exists):
        mock_exists.return_value = True

        op = make_op("op1", "doc_1", version=1)
        result = await OperationManager.process("c1", "doc_1", op)

        assert isinstance(result, AckMessage)
        assert result.status == "duplicate"
        assert result.version == 1

    @patch("app.operation.manager.OperationRepository.exists", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.get_document", new_callable=AsyncMock)
    async def test_document_not_found_returns_conflict(self, mock_get_doc, mock_exists):
        mock_exists.return_value = False
        mock_get_doc.return_value = None

        op = make_op("op1", "doc_1", version=1)
        result = await OperationManager.process("c1", "doc_1", op)

        assert isinstance(result, ConflictMessage)
        assert "not found" in result.reason.lower()

    @patch("app.operation.manager.OperationRepository.exists", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.get_document", new_callable=AsyncMock)
    async def test_version_mismatch_returns_conflict(self, mock_get_doc, mock_exists):
        mock_exists.return_value = False
        mock_get_doc.return_value = Document(id="doc_1", version=5, blocks=[])

        op = make_op("op1", "doc_1", version=1)
        result = await OperationManager.process("c1", "doc_1", op)

        assert isinstance(result, ConflictMessage)
        assert "version mismatch" in result.reason.lower()
        assert result.current_version == 5

    @patch("app.operation.manager.OperationRepository.exists", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.get_document", new_callable=AsyncMock)
    @patch("app.operation.manager.DocumentService.apply_operation", new_callable=AsyncMock)
    async def test_apply_raises_returns_conflict(self, mock_apply, mock_get_doc, mock_exists):
        mock_exists.return_value = False
        mock_get_doc.return_value = Document(id="doc_1", version=0, blocks=[])
        mock_apply.side_effect = ValueError("Invalid position")

        op = make_op("op1", "doc_1", version=1)
        result = await OperationManager.process("c1", "doc_1", op)

        assert isinstance(result, ConflictMessage)
        assert "invalid position" in result.reason.lower()