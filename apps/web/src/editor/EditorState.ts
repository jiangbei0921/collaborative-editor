import { applyOperation } from "./applyOperation"
import { createBlock } from "./block"
import { createDocument } from "./document"
import { createOperation } from "./operation"
import {
  DEFAULT_DOCUMENT_TITLE,
  type AckMessage,
  type Block,
  type BlockType,
  type ConflictMessage,
  type Document,
  type Operation,
  type ServerMessage,
} from "../types"
import type { WebSocketClient } from "../websocket/WebSocketClient"

export interface EditorCallbacks {
  onDocumentChange: (doc: Document) => void
  onConflict: (reason: string) => void
}

export class EditorState {
  private doc: Document
  private clientId: string
  private wsClient: WebSocketClient | null = null
  private callbacks: EditorCallbacks

  private pendingOps: Set<string> = new Set()

  constructor(
    clientId: string,
    callbacks: EditorCallbacks
  ) {
    this.clientId = clientId
    this.callbacks = callbacks
    this.doc = createDocument()
  }

  attachWsClient(ws: WebSocketClient): void {
    this.wsClient = ws
  }

  private send(op: Operation): void {
    this.wsClient?.send(op)
  }

  get document(): Document {
    return this.doc
  }

  get version(): number {
    return this.doc.version
  }

  async handleServerMessage(msg: ServerMessage | Operation | { type: "document"; data: unknown }): Promise<void> {
    if ("type" in msg && msg.type === "document") {
      const data = msg.data as {
        id: string
        title?: string
        version: number
        blocks: Block[]
        updated_at: number
      }
      this.doc = {
        id: data.id,
        title: data.title || DEFAULT_DOCUMENT_TITLE,
        version: data.version,
        blocks: data.blocks,
        updated_at: data.updated_at,
      }
      this.callbacks.onDocumentChange(this.doc)
      return
    }

    const serverMsg = msg as ServerMessage
    if (serverMsg.type === "ack") {
      this.handleAck(serverMsg as AckMessage)
    } else if (serverMsg.type === "conflict") {
      await this.handleConflict(serverMsg as ConflictMessage)
    } else if ("block_id" in serverMsg) {
      const remoteOp = serverMsg as unknown as Operation
      this.applyRemoteOperation(remoteOp)
    }
  }

  private handleAck(ack: AckMessage): void {
    if (ack.status === "applied") {
      this.doc.version = ack.version
    }
    this.pendingOps.delete(ack.operation_id)
  }

  private async handleConflict(conflict: ConflictMessage): Promise<void> {
    this.pendingOps.delete(conflict.operation_id)
    this.callbacks.onConflict(conflict.reason)

    try {
      const res = await fetch(`/api/documents/${conflict.document_id}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const latest = await res.json() as Document
      this.doc = latest
      this.callbacks.onDocumentChange(this.doc)
    } catch (e) {
      this.callbacks.onConflict(`Failed to refresh document: ${e}`)
    }
  }

  private applyRemoteOperation(op: Operation): void {
    this.doc = applyOperation(this.doc, op)
    this.doc.version = op.version
    this.callbacks.onDocumentChange(this.doc)
  }

  insertText(blockId: string, position: number, text: string): void {
    const version = this.doc.version + 1
    const op = createOperation(this.clientId, this.doc.id, "insert", version, {
      blockId,
      position,
      content: text,
    })

    this.doc = applyOperation(this.doc, op)
    this.pendingOps.add(op.id)
    this.callbacks.onDocumentChange(this.doc)

    this.send(op)
  }

  deleteText(blockId: string, position: number, length: number): void {
    const version = this.doc.version + 1
    const op = createOperation(this.clientId, this.doc.id, "delete", version, {
      blockId,
      position,
      length,
    })

    this.doc = applyOperation(this.doc, op)
    this.pendingOps.add(op.id)
    this.callbacks.onDocumentChange(this.doc)

    this.send(op)
  }

  createBlock(type: BlockType = "paragraph"): void {
    const block = createBlock(type)
    const version = this.doc.version + 1
    const op = createOperation(
      this.clientId,
      this.doc.id,
      "create_block",
      version,
      { blockId: block.id, content: type }
    )

    this.doc = applyOperation(this.doc, op)
    this.pendingOps.add(op.id)
    this.callbacks.onDocumentChange(this.doc)

    this.send(op)
  }

  deleteBlock(blockId: string): void {
    const version = this.doc.version + 1
    const op = createOperation(
      this.clientId,
      this.doc.id,
      "delete_block",
      version,
      { blockId }
    )

    this.doc = applyOperation(this.doc, op)
    this.pendingOps.add(op.id)
    this.callbacks.onDocumentChange(this.doc)

    this.send(op)
  }

  updateBlock(blockId: string, content: string): void {
    const version = this.doc.version + 1
    const op = createOperation(
      this.clientId,
      this.doc.id,
      "update_block",
      version,
      { blockId, content }
    )

    this.doc = applyOperation(this.doc, op)
    this.pendingOps.add(op.id)
    this.callbacks.onDocumentChange(this.doc)

    this.send(op)
  }

  replaceDocument(doc: Document): void {
    this.doc = doc
    this.callbacks.onDocumentChange(this.doc)
  }
}