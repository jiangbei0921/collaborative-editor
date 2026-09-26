<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import type { Block, Document, Operation } from "../types"
import { useConnectionStore } from "../state/useConnectionStore"
import { usePresenceStore } from "../state/usePresenceStore"
import { useCursorStore } from "../state/useCursorStore"
import { WebSocketClient } from "../websocket/WebSocketClient"
import { buildOperation } from "../websocket/protocol"
import EditorHeader from "./EditorHeader.vue"
import EditorContent from "./EditorContent.vue"

const route = useRoute()
const router = useRouter()
const docId = route.params.docId as string
const clientId = crypto.randomUUID()

const { status, error, setStatus, setError } = useConnectionStore()
const { setOnlineUsers } = usePresenceStore()
const { setCursor, removeCursor, clearCursors } = useCursorStore()

const ws = ref<WebSocketClient | null>(null)
const docTitle = ref("")
const blocks = ref<Block[]>([])
const version = ref(0)
const pendingOps = ref<Operation[]>([])
const conflictOps = ref<Set<string>>(new Set())

function goHome(): void {
  router.push("/")
}

function createNewDoc(): void {
  router.push("/new")
}

async function updateTitle(newTitle: string): Promise<void> {
  const trimmed = newTitle.trim()
  if (!trimmed || trimmed === docTitle.value) return

  try {
    const res = await fetch(`/api/documents/${docId}/title`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: trimmed }),
    })
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const data = await res.json()
    if (data.status === "updated") {
      docTitle.value = data.title || trimmed
    } else if (data.status === "not_found") {
      throw new Error("Document not found")
    }
  } catch (err) {
    setError(`标题更新失败: ${err instanceof Error ? err.message : String(err)}`)
  }
}

function handleInsert(blockId: string, position: number, text: string): void {
  const op = buildOperation(docId, clientId, "insert", blockId, position, text, 0)
  pendingOps.value.push(op)
  trySendNext()
}

function handleDelete(blockId: string, position: number, length: number): void {
  const op = buildOperation(docId, clientId, "delete", blockId, position, null, 0, length)
  pendingOps.value.push(op)
  trySendNext()
}

function handleCreateBlock(newBlockId: string, suffix: string, currentBlockId: string): void {
  // 1. 找到当前 Block 的索引，在其后插入新 Block
  const currentIndex = blocks.value.findIndex((b) => b.id === currentBlockId)
  const insertIndex = currentIndex >= 0 ? currentIndex + 1 : blocks.value.length

  // 2. 先在本地添加新 Block（乐观更新），避免等待 ACK 时无法输入
  if (!blocks.value.some((b) => b.id === newBlockId)) {
    blocks.value.splice(insertIndex, 0, { id: newBlockId, type: "paragraph", content: "" })
  }

  // 3. 创建 create_block Operation，使用客户端生成的 Block ID，并指定 after_block_id
  const op = buildOperation(docId, clientId, "create_block", newBlockId, null, "paragraph", 0, null, currentBlockId)
  pendingOps.value.push(op)
  trySendNext()

  // 4. 如果有 suffix，创建 insert Operation 到新 Block
  if (suffix) {
    const insertOp = buildOperation(docId, clientId, "insert", newBlockId, 0, suffix, 0)
    pendingOps.value.push(insertOp)
    trySendNext()
  }

  // 5. 自动聚焦新 Block
  nextTick(() => {
    const newBlockEl = document.querySelector(`[data-block-id="${newBlockId}"] .block-content`) as HTMLElement | null
    if (newBlockEl) {
      newBlockEl.focus()
      const range = document.createRange()
      const sel = window.getSelection()
      if (sel) {
        range.setStart(newBlockEl.firstChild || newBlockEl, 0)
        range.collapse(true)
        sel.removeAllRanges()
        sel.addRange(range)
      }
    }
  })
}

function handleDeleteBlock(blockId: string): void {
  const op = buildOperation(docId, clientId, "delete_block", blockId, null, null, 0)
  pendingOps.value.push(op)
  trySendNext()
}

let hasPendingAck = false

function trySendNext(): void {
  if (hasPendingAck || pendingOps.value.length === 0 || !ws.value) return
  const op = pendingOps.value[0]
  op.version = version.value + 1
  hasPendingAck = true
  ws.value.send(op)
}

function handleMergeUp(blockId: string): void {
  const index = blocks.value.findIndex((b) => b.id === blockId)
  if (index <= 0) return
  const prev = blocks.value[index - 1]
  const current = blocks.value[index]
  const text = current.content
  const position = prev.content.length
  handleDelete(blockId, 0, text.length)
  handleInsert(prev.id, position, text)
  handleDeleteBlock(blockId)
}

function handleCursorChange(blockId: string, offset: number): void {
  ws.value?.sendCursor(blockId, offset)
}

function handleMessage(msg: unknown): void {
  const m = msg as Record<string, unknown>

  if (m.type === "document") {
    const doc = (m.document ?? m.data) as Document
    docTitle.value = doc.title
    blocks.value = doc.blocks
    version.value = doc.version
    pendingOps.value = []
    hasPendingAck = false
    setStatus("connected")
    return
  }

  if (m.type === "cursor") {
    setCursor(m.client_id as string, m.block_id as string, m.offset as number)
    return
  }

  if (m.type === "presence") {
    const prevUsers = usePresenceStore().onlineUsers.value
    const nextUsers = (m.users as string[]) ?? []
    setOnlineUsers(nextUsers)
    for (const userId of prevUsers) {
      if (!nextUsers.includes(userId)) {
        removeCursor(userId)
      }
    }
    return
  }

  if (m.type === "document_title_updated") {
    docTitle.value = m.title as string
    return
  }

  if (m.type === "ack" || m.type === "conflict") {
    if (m.type === "ack") {
      version.value = m.version as number
      if (pendingOps.value.length > 0 && pendingOps.value[0].id === (m.operation_id as string)) {
        pendingOps.value.shift()
      }
      hasPendingAck = false
      trySendNext()
    } else {
      conflictOps.value.add(m.operation_id as string)
      setError(`Conflict: ${m.reason as string}`)
      pendingOps.value = []
      hasPendingAck = false
    }
    return
  }

  const op = m as unknown as Operation
  if (op.type === "insert" && op.block_id && op.content !== null && op.position !== null) {
    const block = blocks.value.find((b) => b.id === op.block_id)
    if (block) {
      block.content =
        block.content.slice(0, op.position) + op.content + block.content.slice(op.position)
    }
  }
  if (op.type === "delete" && op.block_id && op.length !== null && op.position !== null) {
    const block = blocks.value.find((b) => b.id === op.block_id)
    if (block) {
      block.content =
        block.content.slice(0, op.position) + block.content.slice(op.position + op.length)
    }
  }
  if (op.type === "create_block") {
    const remoteBlockId = op.block_id || op.id
    const blockType = (op.content as Block["type"]) || "paragraph"
    if (!blocks.value.some((b) => b.id === remoteBlockId)) {
      // Insert at correct position based on after_block_id
      if (op.after_block_id) {
        const afterIndex = blocks.value.findIndex((b) => b.id === op.after_block_id)
        if (afterIndex >= 0) {
          blocks.value.splice(afterIndex + 1, 0, { id: remoteBlockId, type: blockType, content: "" })
        } else {
          blocks.value.push({ id: remoteBlockId, type: blockType, content: "" })
        }
      } else {
        blocks.value.push({ id: remoteBlockId, type: blockType, content: "" })
      }
    }
  }
  if (op.type === "delete_block" && op.block_id) {
    blocks.value = blocks.value.filter((b) => b.id !== op.block_id)
  }
  if (op.type === "update_block" && op.block_id && op.content !== null) {
    const block = blocks.value.find((b) => b.id === op.block_id)
    if (block) block.content = op.content
  }
  if (op.version !== undefined) {
    version.value = op.version
  }
}

function handleError(msg: string): void {
  if (msg.startsWith("document_not_found:")) {
    setStatus("document_not_found")
    setError(msg.replace("document_not_found:", ""))
    return
  }
  setStatus("disconnected")
  setError(msg)
}

function handleDisconnect(): void {
  hasPendingAck = false
}

onMounted(() => {
  setStatus("connecting")
  ws.value = new WebSocketClient(
    import.meta.env.VITE_WS_URL || "ws://localhost:8000",
    clientId,
    docId,
    handleMessage,
    handleError,
    handleDisconnect
  )
})

onUnmounted(() => {
  ws.value?.disconnect()
  clearCursors()
})

watch(
  () => route.params.docId,
  (newId) => {
    if (newId !== docId) {
      ws.value?.disconnect()
      clearCursors()
      setStatus("connecting")
      ws.value = new WebSocketClient(
        import.meta.env.VITE_WS_URL || "ws://localhost:8000",
        clientId,
        newId as string,
        handleMessage,
        handleError,
        handleDisconnect
      )
    }
  }
)
</script>

<template>
  <div v-if="status === 'document_not_found'" class="error-screen">
    <div class="error-card">
      <div class="error-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h2>文档不存在</h2>
      <p>请检查文档链接是否正确，或创建一个新文档。</p>
      <div class="error-actions">
        <button class="btn-primary" @click="goHome">返回首页</button>
        <button class="btn-secondary" @click="createNewDoc">新建文档</button>
      </div>
    </div>
  </div>

  <div v-else class="editor-layout">
    <EditorHeader
      :doc-id="docId"
      :title="docTitle"
      @update:title="updateTitle"
    />

    <main class="editor-main">
      <div class="editor-canvas">
        <div v-if="status === 'connecting'" class="loading-state">
          <div class="loading-spinner" />
          <p>正在连接文档…</p>
        </div>

        <template v-else>
          <EditorContent
            :blocks="blocks"
            @insert="handleInsert"
            @delete="handleDelete"
            @create-block="(newBlockId: string, suffix: string, currentBlockId: string) => handleCreateBlock(newBlockId, suffix, currentBlockId)"
            @delete-block="handleDeleteBlock"
            @merge-up="handleMergeUp"
            @cursor-change="handleCursorChange"
          />
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.editor-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

.editor-main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
}

.editor-canvas {
  width: 100%;
  max-width: var(--editor-max-width);
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-8) var(--space-10);
  min-height: 60vh;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-16) 0;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--bg);
  padding: var(--space-4);
}

.error-card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-10) var(--space-12);
  text-align: center;
  max-width: 440px;
  width: 100%;
}

.error-icon {
  color: var(--text-tertiary);
  margin-bottom: var(--space-4);
}

.error-card h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: var(--space-2);
}

.error-card p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: var(--space-6);
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}

.btn-primary,
.btn-secondary {
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--primary);
  color: var(--text-inverse);
  border: none;
}
.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--surface-hover);
  color: var(--text);
  border: 1px solid var(--border);
}
.btn-secondary:hover {
  background: var(--surface-active);
}

@media (max-width: 768px) {
  .editor-main {
    padding: var(--space-4) var(--space-3);
  }

  .editor-canvas {
    padding: var(--space-6) var(--space-5);
  }
}
</style>