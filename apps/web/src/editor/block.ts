import type { Block, BlockType } from "../types"
import { generateId } from "../utils/id"

export function createBlock(type: BlockType = "paragraph", content = ""): Block {
  return {
    id: generateId(),
    type,
    content,
  }
}