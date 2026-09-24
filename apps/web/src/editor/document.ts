import type { Document } from "../types"
import { generateId } from "../utils/id"
import { DEFAULT_DOCUMENT_TITLE } from "../types"

export function createDocument(id?: string, title?: string): Document {
  return {
    id: id ?? generateId(),
    title: title ?? DEFAULT_DOCUMENT_TITLE,
    version: 0,
    blocks: [],
    updated_at: Date.now(),
  }
}