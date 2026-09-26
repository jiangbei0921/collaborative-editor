from app.types.models import Block, Document, Operation

MAX_INSERT_LENGTH = 10_000


def apply_operation(doc: Document, op: Operation) -> Document:
    if op.type in ("insert", "delete", "update_block"):
        if op.block_id is None:
            raise ValueError(f"Operation type '{op.type}' requires block_id")
        target_index = next(
            (i for i, b in enumerate(doc.blocks) if b.id == op.block_id), None
        )
        if target_index is None:
            raise ValueError(f"Block '{op.block_id}' not found in document")

    if op.type == "insert":
        if op.content is None:
            raise ValueError("Insert operation requires content")
        if len(op.content) > MAX_INSERT_LENGTH:
            raise ValueError(
                f"❗️内容超出 {MAX_INSERT_LENGTH:,} 字符限制（当前 {len(op.content):,} 字符），请拆分为多个段落"
            )
        block = doc.blocks[target_index]
        pos = op.position if op.position is not None else len(block.content)
        if pos < 0 or pos > len(block.content):
            raise ValueError(
                f"Insert position {pos} out of range for block '{op.block_id}' (length {len(block.content)})"
            )
        new_content = block.content[:pos] + op.content + block.content[pos:]
        doc.blocks[target_index] = block.model_copy(update={"content": new_content})

    elif op.type == "delete":
        if op.length is None or op.length < 0:
            raise ValueError("Delete operation requires non-negative length")
        block = doc.blocks[target_index]
        pos = op.position if op.position is not None else len(block.content)
        if pos < 0 or pos > len(block.content):
            raise ValueError(
                f"Delete position {pos} out of range for block '{op.block_id}' (length {len(block.content)})"
            )
        end = min(pos + op.length, len(block.content))
        new_content = block.content[:pos] + block.content[end:]
        doc.blocks[target_index] = block.model_copy(update={"content": new_content})

    elif op.type == "create_block":
        block_type = op.content or "paragraph"
        new_block_id = op.block_id or op.id
        new_block = Block(id=new_block_id, type=block_type, content="")
        if op.after_block_id:
            after_index = next(
                (i for i, b in enumerate(doc.blocks) if b.id == op.after_block_id), None
            )
            if after_index is not None:
                doc.blocks.insert(after_index + 1, new_block)
            else:
                doc.blocks.append(new_block)
        else:
            doc.blocks.append(new_block)

    elif op.type == "delete_block":
        if op.block_id is None:
            raise ValueError("Delete_block operation requires block_id")
        doc.blocks = [b for b in doc.blocks if b.id != op.block_id]

    elif op.type == "update_block":
        if op.content is None:
            raise ValueError("Update_block operation requires content")
        if len(op.content) > MAX_INSERT_LENGTH:
            raise ValueError(
                f"❌ 内容超出 {MAX_INSERT_LENGTH:,} 字符限制（当前 {len(op.content):,} 字符），请拆分为多个段落"
            )
        block = doc.blocks[target_index]
        doc.blocks[target_index] = block.model_copy(update={"content": op.content})

    else:
        raise ValueError(f"Unknown operation type: {op.type}")

    return doc