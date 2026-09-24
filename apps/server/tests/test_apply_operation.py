import pytest
from app.operation.apply import apply_operation
from app.types.models import Block, Document, Operation


def make_doc(*blocks: Block) -> Document:
    return Document(id="doc_1", version=0, blocks=list(blocks))


def make_block(block_id: str, content: str, type_: str = "paragraph") -> Block:
    return Block(id=block_id, type=type_, content=content)


def make_op(
    op_id: str,
    type_: str,
    block_id: str | None = None,
    position: int | None = None,
    content: str | None = None,
    length: int | None = None,
    version: int = 1,
) -> Operation:
    return Operation(
        id=op_id,
        client_id="c1",
        document_id="doc_1",
        block_id=block_id,
        type=type_,
        position=position,
        content=content,
        length=length,
        version=version,
    )


class TestInsert:
    def test_insert_at_beginning(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "insert", block_id="b1", position=0, content="XX")
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "XXhello"

    def test_insert_at_end(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "insert", block_id="b1", position=5, content="!!")
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "hello!!"

    def test_insert_in_middle(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "insert", block_id="b1", position=2, content="__")
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "he__llo"

    def test_insert_position_default_appends(self):
        doc = make_doc(make_block("b1", "abc"))
        op = make_op("op1", "insert", block_id="b1", content="xyz")
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "abcxyz"

    def test_insert_block_not_found_raises(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "insert", block_id="missing", position=0, content="x")
        with pytest.raises(ValueError, match="Block 'missing' not found"):
            apply_operation(doc, op)

    def test_insert_position_out_of_range_raises(self):
        doc = make_doc(make_block("b1", "hi"))
        op = make_op("op1", "insert", block_id="b1", position=10, content="x")
        with pytest.raises(ValueError, match="out of range"):
            apply_operation(doc, op)

    def test_insert_requires_content(self):
        doc = make_doc(make_block("b1", "hi"))
        op = make_op("op1", "insert", block_id="b1", position=0, content=None)
        with pytest.raises(ValueError, match="requires content"):
            apply_operation(doc, op)


class TestDelete:
    def test_delete_from_beginning(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="b1", position=0, length=2)
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "llo"

    def test_delete_from_middle(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="b1", position=1, length=3)
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "ho"

    def test_delete_at_end(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="b1", position=3, length=10)
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "hel"

    def test_delete_zero_length_noop(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="b1", position=2, length=0)
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "hello"

    def test_delete_position_default_deletes_from_end(self):
        doc = make_doc(make_block("b1", "abc"))
        op = make_op("op1", "delete", block_id="b1", position=0, length=1)
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "bc"

    def test_delete_block_not_found_raises(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="missing", position=0, length=1)
        with pytest.raises(ValueError, match="not found"):
            apply_operation(doc, op)

    def test_delete_negative_length_raises(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "delete", block_id="b1", position=0, length=-1)
        with pytest.raises(ValueError, match="non-negative length"):
            apply_operation(doc, op)


class TestCreateBlock:
    def test_create_block_appends(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "create_block", content="heading")
        result = apply_operation(doc, op)
        assert len(result.blocks) == 2
        assert result.blocks[1].type == "heading"
        assert result.blocks[1].content == ""
        assert result.blocks[1].id == "op1"

    def test_create_block_with_explicit_block_id(self):
        doc = make_doc()
        op = make_op("op1", "create_block", block_id="b2", content="bullet")
        result = apply_operation(doc, op)
        assert result.blocks[0].id == "b2"
        assert result.blocks[0].type == "bullet"

    def test_create_block_requires_content(self):
        doc = make_doc()
        op = make_op("op1", "create_block", content=None)
        with pytest.raises(ValueError, match="requires content"):
            apply_operation(doc, op)


class TestDeleteBlock:
    def test_delete_block_removes_it(self):
        doc = make_doc(make_block("b1", "a"), make_block("b2", "b"))
        op = make_op("op1", "delete_block", block_id="b1")
        result = apply_operation(doc, op)
        assert len(result.blocks) == 1
        assert result.blocks[0].id == "b2"

    def test_delete_block_requires_block_id(self):
        doc = make_doc(make_block("b1", "a"))
        op = make_op("op1", "delete_block", block_id=None)
        with pytest.raises(ValueError, match="requires block_id"):
            apply_operation(doc, op)


class TestUpdateBlock:
    def test_update_block_content(self):
        doc = make_doc(make_block("b1", "old"))
        op = make_op("op1", "update_block", block_id="b1", content="new")
        result = apply_operation(doc, op)
        assert result.blocks[0].content == "new"

    def test_update_block_not_found_raises(self):
        doc = make_doc(make_block("b1", "old"))
        op = make_op("op1", "update_block", block_id="missing", content="new")
        with pytest.raises(ValueError, match="not found"):
            apply_operation(doc, op)

    def test_update_block_requires_content(self):
        doc = make_doc(make_block("b1", "old"))
        op = make_op("op1", "update_block", block_id="b1", content=None)
        with pytest.raises(ValueError, match="requires content"):
            apply_operation(doc, op)


class TestIdempotency:
    def test_same_operation_twice_yields_same_result(self):
        doc = make_doc(make_block("b1", "hello"))
        op = make_op("op1", "insert", block_id="b1", position=0, content="X")
        first = apply_operation(doc, op)
        second = apply_operation(first, op)
        assert first.blocks[0].content == second.blocks[0].content