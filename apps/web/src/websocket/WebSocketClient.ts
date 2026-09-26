import type { DocumentTitleUpdatedMessage, Operation, PresenceMessage, ServerMessage } from "../types"
import { buildJoinMessage, parseDocument, parsePresenceMessage, parseServerMessage } from "./protocol"

type MessageHandler = (msg: ServerMessage | Operation | PresenceMessage | DocumentTitleUpdatedMessage | { type: "document"; data: unknown } | { type: "cursor"; client_id: string; block_id: string; offset: number }) => void
type DisconnectHandler = () => void

const MAX_RECONNECT_DELAY_MS = 10_000
const ACK_TIMEOUT_MS = 5_000
const MAX_RETRIES = 3

interface PendingOp {
  op: Operation
  retryCount: number
  timer: ReturnType<typeof setTimeout>
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private clientId: string
  private docId: string
  private handler: MessageHandler
  private onError?: (msg: string) => void
  private onDisconnect?: DisconnectHandler
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private pending: Operation[] = []
  private sentPending = new Map<string, PendingOp>()
  private _stopped = false

  constructor(
    baseUrl: string,
    clientId: string,
    docId: string,
    handler: MessageHandler,
    onError?: (msg: string) => void,
    onDisconnect?: DisconnectHandler
  ) {
    this.url = `${baseUrl}/ws/${docId}`
    this.clientId = clientId
    this.docId = docId
    this.handler = handler
    this.onError = onError
    this.onDisconnect = onDisconnect
    this.connect()
  }

  private getReconnectDelay(): number {
    const delay = 1000 * Math.pow(2, this.reconnectAttempts)
    return Math.min(delay, MAX_RECONNECT_DELAY_MS)
  }

  private connect(): void {
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.ws?.send(JSON.stringify(buildJoinMessage(this.clientId)))
      this.flush()
    }

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === "error") {
        this._handleServerError(data.reason as string)
        return
      }

      if (data.type === "ack" || data.type === "conflict") {
        const opId = data.operation_id
        if (opId && this.sentPending.has(opId)) {
          const pending = this.sentPending.get(opId)!
          clearTimeout(pending.timer)
          this.sentPending.delete(opId)
        }
      }

      if (data.type === "presence") {
        this.handler(parsePresenceMessage(data))
      } else if (data.type === "document_title_updated") {
        this.handler({
          type: "document_title_updated",
          document_id: data.document_id as string,
          title: data.title as string,
        } as DocumentTitleUpdatedMessage)
      } else if (data.type === "cursor") {
        this.handler({
          type: "cursor",
          client_id: data.client_id as string,
          block_id: data.block_id as string,
          offset: data.offset as number,
        })
      } else if (data.blocks !== undefined) {
        this.handler({ type: "document", data: parseDocument(data) })
      } else if (data.type === "ack" || data.type === "conflict") {
        this.handler(parseServerMessage(data))
      } else {
        this.handler(data as Operation)
      }
    }

    this.ws.onclose = () => {
      for (const pending of this.sentPending.values()) {
        clearTimeout(pending.timer)
        this.pending.push(pending.op)
      }
      this.sentPending.clear()

      // Notify Editor.vue to reset hasPendingAck so queued ops can be resent after reconnect
      this.onDisconnect?.()

      if (this._stopped) return

      const delay = this.getReconnectDelay()
      this.reconnectAttempts += 1
      this.reconnectTimer = setTimeout(() => this.connect(), delay)
    }
  }

  private _handleServerError(reason: string): void {
    if (reason.includes("not found") || reason.includes("Document")) {
      this._stopped = true
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }
      this.ws?.close()
      this.ws = null
      this.onError?.(`document_not_found:${reason}`)
      return
    }
    this.onError?.(reason)
  }

  private getRetryDelay(retryCount: number): number {
    return ACK_TIMEOUT_MS * Math.pow(2, retryCount)
  }

  private startAckTimer(op: Operation, retryCount: number = 0): void {
    const delay = this.getRetryDelay(retryCount)
    const timer = setTimeout(() => {
      this.onAckTimeout(op, retryCount)
    }, delay)
    this.sentPending.set(op.id, { op, retryCount, timer })
  }

  private onAckTimeout(op: Operation, retryCount: number): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      this.sentPending.delete(op.id)
      this.pending.push(op)
      return
    }

    if (retryCount >= MAX_RETRIES) {
      this.sentPending.delete(op.id)
      this.pending.push(op)
      this.onError?.("网络异常，部分修改可能尚未同步，请检查网络连接。")
      this.ws.close()
      return
    }

    const nextRetry = retryCount + 1
    this.ws.send(JSON.stringify(op))
    this.startAckTimer(op, nextRetry)
  }

  send(op: Operation): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(op))
      this.startAckTimer(op)
    } else {
      this.pending.push(op)
    }
  }

  sendCursor(blockId: string, offset: number): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({
      type: "cursor",
      document_id: this.docId,
      client_id: this.clientId,
      block_id: blockId,
      offset,
    }))
  }

  flush(): void {
    while (this.pending.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const op = this.pending.shift()!
      this.ws.send(JSON.stringify(op))
      this.startAckTimer(op)
    }
  }

  disconnect(): void {
    this._stopped = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    for (const pending of this.sentPending.values()) {
      clearTimeout(pending.timer)
    }
    this.sentPending.clear()
    this.reconnectAttempts = 0
    this.ws?.close()
    this.ws = null
  }
}