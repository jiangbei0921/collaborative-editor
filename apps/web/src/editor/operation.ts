import type { Operation, OperationType } from "../types"
import { generateId } from "../utils/id"

export function createOperation(
  clientId: string,
  docId: string,
  type: OperationType,
  version: number,
  opts: {
    blockId?: string | null
    position?: number | null
    content?: string | null
    length?: number | null
  } = {}
): Operation {
  return {
    id: generateId(),
    client_id: clientId,
    document_id: docId,
    block_id: opts.blockId ?? null,
    type,
    position: opts.position ?? null,
    content: opts.content ?? null,
    length: opts.length ?? null,
    version,
  }
}