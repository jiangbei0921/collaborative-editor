from typing import Literal, Optional
from pydantic import BaseModel, Field

BlockType = Literal["paragraph", "heading", "bullet", "quote", "code"]
OperationType = Literal[
    "insert", "delete",
    "create_block", "delete_block", "update_block",
]


class Block(BaseModel):
    id: str
    type: BlockType
    content: str
    props: Optional[dict] = None


DEFAULT_DOCUMENT_TITLE = "未命名文档"
MAX_DOCUMENT_TITLE_LENGTH = 100


def normalize_title(title: str | None) -> str:
    if title is None:
        return DEFAULT_DOCUMENT_TITLE
    trimmed = title.strip()
    if not trimmed:
        return DEFAULT_DOCUMENT_TITLE
    return trimmed[:MAX_DOCUMENT_TITLE_LENGTH]


class Document(BaseModel):
    id: str
    title: str = DEFAULT_DOCUMENT_TITLE
    version: int = 0
    blocks: list[Block] = Field(default_factory=list)
    updated_at: int = 0


class Operation(BaseModel):
    id: str
    client_id: str
    document_id: str
    block_id: Optional[str] = None
    type: OperationType
    position: Optional[int] = None
    content: Optional[str] = None
    length: Optional[int] = None
    version: int
    # For create_block: block_id of the block after which to insert the new block
    # If None, append at the end
    after_block_id: Optional[str] = None


class JoinMessage(BaseModel):
    type: Literal["join"] = "join"
    document_id: str
    client_id: str


class DocumentMessage(BaseModel):
    type: Literal["document"] = "document"
    document: Document


class OperationMessage(BaseModel):
    type: Literal["operation"] = "operation"
    operation: Operation


class AckMessage(BaseModel):
    type: Literal["ack"] = "ack"
    operation_id: str
    document_id: str
    version: int
    status: str = "applied"


class ConflictMessage(BaseModel):
    type: Literal["conflict"] = "conflict"
    operation_id: str
    document_id: str
    current_version: int
    reason: str


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str


class PresenceMessage(BaseModel):
    type: Literal["presence"] = "presence"
    document_id: str
    client_id: str
    online: bool = True


class DocumentTitleUpdatedMessage(BaseModel):
    type: Literal["document_title_updated"] = "document_title_updated"
    document_id: str
    title: str


class CursorMessage(BaseModel):
    type: Literal["cursor"] = "cursor"
    document_id: str
    client_id: str
    block_id: str
    offset: int


WebSocketMessage = (
    JoinMessage
    | DocumentMessage
    | OperationMessage
    | AckMessage
    | ConflictMessage
    | ErrorMessage
    | PresenceMessage
    | DocumentTitleUpdatedMessage
    | CursorMessage
)