import type { Block, Document, Operation } from "../types"

const MAX_INSERT_LENGTH = 10_000

export function applyOperation(doc: Document, op: Operation): Document {
  const blocks = structuredClone(doc.blocks)

  if (op.type === "insert") {
    const idx = findBlockIndex(blocks, op.block_id)
    blocks[idx] = { ...blocks[idx], content: doInsert(blocks[idx].content, op.position, op.content) }
  } else if (op.type === "delete") {
    const idx = findBlockIndex(blocks, op.block_id)
    blocks[idx] = { ...blocks[idx], content: doDelete(blocks[idx].content, op.position, op.length) }
  } else if (op.type === "create_block") {
    const newBlock: Block = {
      id: op.block_id ?? op.id,
      type: (op.content as Block["type"]) ?? "paragraph",
      content: "",
    }
    blocks.push(newBlock)
  } else if (op.type === "delete_block") {
    return { ...doc, blocks: blocks.filter((b) => b.id !== op.block_id) }
  } else if (op.type === "update_block") {
    const idx = findBlockIndex(blocks, op.block_id)
    blocks[idx] = { ...blocks[idx], content: op.content ?? "" }
  }

  return { ...doc, blocks }
}

function findBlockIndex(blocks: Block[], blockId: string | null): number {
  const idx = blocks.findIndex((b) => b.id === blockId)
  if (idx === -1) throw new Error(`Block '${blockId}' not found`)
  return idx
}

function doInsert(content: string, pos: number | null, text: string | null): string {
  if (text == null) throw new Error("Insert requires content")
  if (text.length > MAX_INSERT_LENGTH) {
    throw new Error(
      `❌ 内容超出 ${MAX_INSERT_LENGTH.toLocaleString()} 字符限制（当前 ${text.length.toLocaleString()} 字符），请拆分为多个段落`
    )
  }
  const p = pos ?? content.length
  if (p < 0 || p > content.length) {
    throw new Error(`Insert position ${p} out of range (length ${content.length})`)
  }
  return content.slice(0, p) + text + content.slice(p)
}

function doDelete(content: string, pos: number | null, length: number | null): string {
  const p = pos ?? content.length
  const len = length ?? 0
  if (p < 0 || p > content.length) {
    throw new Error(`Delete position ${p} out of range (length ${content.length})`)
  }
  const end = Math.min(p + len, content.length)
  return content.slice(0, p) + content.slice(end)
}