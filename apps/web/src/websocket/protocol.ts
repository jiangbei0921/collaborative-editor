import { DEFAULT_DOCUMENT_TITLE, type JoinMessage, type Operation, type PresenceMessage, type ServerMessage } from "../types"

export function buildJoinMessage(clientId: string): JoinMessage {
  return { type: "join", client_id: clientId }
}

export function buildOperation(
  documentId: string,
  clientId: string,
  type: Operation["type"],
  blockId: string | null,
  position: number | null,
  content: string | null,
  version: number,
  length?: number | null,
  afterBlockId?: string | null
): Operation {
  return {
    id: crypto.randomUUID(),
    client_id: clientId,
    document_id: documentId,
    block_id: blockId,
    type,
    position,
    content,
    length: length ?? null,
    version,
    after_block_id: afterBlockId ?? null,
  }
}

export function parseServerMessage(data: unknown): ServerMessage {
  const msg = data as Record<string, unknown>
  if (msg.type === "ack") {
    return {
      type: "ack",
      operation_id: msg.operation_id as string,
      document_id: msg.document_id as string,
      version: msg.version as number,
      status: msg.status as "applied" | "duplicate",
    }
  }
  return {
    type: "conflict",
    operation_id: msg.operation_id as string,
    document_id: msg.document_id as string,
    current_version: msg.current_version as number,
    reason: msg.reason as string,
  }
}

export function parseDocument(data: unknown): {
  id: string
  title: string
  version: number
  blocks: unknown[]
  updated_at: number
} {
  const doc = data as Record<string, unknown>
  return {
    id: doc.id as string,
    title: (doc.title as string) || DEFAULT_DOCUMENT_TITLE,
    version: doc.version as number,
    blocks: doc.blocks as unknown[],
    updated_at: doc.updated_at as number,
  }
}

export function parsePresenceMessage(data: unknown): PresenceMessage {
  const msg = data as Record<string, unknown>
  return {
    type: "presence",
    document_id: msg.document_id as string,
    users: (msg.users as string[]) ?? [],
  }
}