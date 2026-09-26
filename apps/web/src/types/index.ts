export type BlockType = "paragraph" | "heading" | "bullet" | "quote" | "code"

export type OperationType =
  | "insert"
  | "delete"
  | "create_block"
  | "delete_block"
  | "update_block"

export interface Block {
  id: string
  type: BlockType
  content: string
  props?: Record<string, unknown>
}

export const DEFAULT_DOCUMENT_TITLE = "未命名文档"
export const MAX_DOCUMENT_TITLE_LENGTH = 100

export function normalizeTitle(title: string | null | undefined): string {
  if (title == null) return DEFAULT_DOCUMENT_TITLE
  const trimmed = title.trim()
  if (!trimmed) return DEFAULT_DOCUMENT_TITLE
  return trimmed.slice(0, MAX_DOCUMENT_TITLE_LENGTH)
}

export interface Document {
  id: string
  title: string
  version: number
  blocks: Block[]
  updated_at: number
}

export interface Operation {
  id: string
  client_id: string
  document_id: string
  block_id: string | null
  type: OperationType
  position: number | null
  content: string | null
  length: number | null
  version: number
  after_block_id?: string | null
}

export interface AckMessage {
  type: "ack"
  operation_id: string
  document_id: string
  version: number
  status: "applied" | "duplicate"
}

export interface ConflictMessage {
  type: "conflict"
  operation_id: string
  document_id: string
  current_version: number
  reason: string
}

export type ServerMessage = AckMessage | ConflictMessage

export interface JoinMessage {
  type: "join"
  client_id: string
}

export interface PresenceMessage {
  type: "presence"
  document_id: string
  users: string[]
}

export interface DocumentTitleUpdatedMessage {
  type: "document_title_updated"
  document_id: string
  title: string
}

export interface CursorMessage {
  type: "cursor"
  document_id: string
  client_id: string
  block_id: string
  offset: number
}

export type RemoteCursor = {
  clientId: string
  blockId: string
  offset: number
}