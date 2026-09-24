<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue"
import { useRouter } from "vue-router"
import { EditorState } from "../editor/EditorState"
import { WebSocketClient } from "../websocket/WebSocketClient"
import { useEditorStore } from "../state/useEditorStore"
import { useConnectionStore } from "../state/useConnectionStore"
import { usePresenceStore } from "../state/usePresenceStore"
import { DEFAULT_DOCUMENT_TITLE, normalizeTitle } from "../types"
import type { Block } from "../types"
import EditorHeader from "./EditorHeader.vue"
import EditorContent from "./EditorContent.vue"

const props = defineProps<{
  docId: string
  clientId: string
  wsBaseUrl: string
}>()

const router = useRouter()
const { blocks, init, syncBlocks, getEditor } = useEditorStore()
const { status, setStatus, setError, setDocumentNotFound } = useConnectionStore()
const { setOnlineUsers } = usePresenceStore()

const docTitle = ref(DEFAULT_DOCUMENT_TITLE)

let editor: EditorState
let wsClient: WebSocketClient

onMounted(() => {
  setStatus("connecting")

  editor = new EditorState(props.clientId, {
    onDocumentChange: (doc) => syncBlocks(doc),
    onConflict: (reason) => setError(reason),
  })

  wsClient = new WebSocketClient(
    props.wsBaseUrl,
    props.clientId,
    props.docId,
    async (msg) => {
      if ("type" in msg && msg.type === "presence") {
        setOnlineUsers(msg.users)
        return
      }
      if ("type" in msg && msg.type === "document_title_updated") {
        docTitle.value = normalizeTitle(msg.title)
        return
      }
      if ("type" in msg && msg.type === "document") {
        setStatus("connected")
        const data = msg.data as { id: string; title: string; version: number; blocks: Block[]; updated_at: number }
        docTitle.value = data.title || DEFAULT_DOCUMENT_TITLE
        editor.replaceDocument({
          id: data.id,
          title: data.title || DEFAULT_DOCUMENT_TITLE,
          version: data.version,
          blocks: data.blocks,
          updated_at: data.updated_at,
        })
        if (editor.document.blocks.length === 0) {
          editor.createBlock("paragraph")
        }
        syncBlocks(editor.document)
        return
      }
      await editor.handleServerMessage(msg)
      syncBlocks(editor.document)
    },
    (err) => {
      if (err.startsWith("document_not_found:")) {
        setDocumentNotFound(err)
      } else {
        setError(err)
      }
    }
  )

  editor.attachWsClient(wsClient)
  init(editor)
})

onUnmounted(() => {
  wsClient?.disconnect()
})

function goHome(): void {
  router.push("/")
}

function createNewDoc(): void {
  router.push("/")
}

async function updateTitle(title: string): Promise<void> {
  docTitle.value = title
  try {
    await fetch(`/api/documents/${props.docId}/title`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    })
  } catch {
    // silently fail, title will be updated on next page load
  }
}

function handleInsert(blockId: string, position: number, text: string): void {
  getEditor()?.insertText(blockId, position, text)
}

function handleDelete(blockId: string, position: number, length: number): void {
  getEditor()?.deleteText(blockId, position, length)
}

function handleCreateBlock(): void {
  getEditor()?.createBlock("paragraph")
}

function handleDeleteBlock(blockId: string): void {
  getEditor()?.deleteBlock(blockId)
}

function handleMergeUp(blockId: string): void {
  const ed = getEditor()
  if (!ed) return
  const idx = ed.document.blocks.findIndex((b) => b.id === blockId)
  if (idx <= 0) return
  const prev = ed.document.blocks[idx - 1]
  const cur = ed.document.blocks[idx]
  ed.deleteBlock(blockId)
  ed.insertText(prev.id, prev.content.length, cur.content)
}
</script>

<template>
  <div v-if="status === 'document_not_found'" class="error-screen">
    <div class="error-card">
      <h2>文档不存在</h2>
      <p>请检查文档链接是否正确。</p>
      <div class="error-actions">
        <button class="btn-primary" @click="goHome">返回首页</button>
        <button class="btn-secondary" @click="createNewDoc">新建文档</button>
      </div>
    </div>
  </div>
  <div v-else class="editor">
    <EditorHeader :doc-id="docId" :title="docTitle" @update:title="updateTitle" />
    <EditorContent
      :blocks="blocks"
      @insert="handleInsert"
      @delete="handleDelete"
      @create-block="handleCreateBlock"
      @delete-block="handleDeleteBlock"
      @merge-up="handleMergeUp"
    />
  </div>
</template>

<style scoped>
.error-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #fafafa;
}

.error-card {
  text-align: center;
  padding: 48px 32px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  max-width: 400px;
  width: 90%;
}

.error-card h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #1a1a1a;
}

.error-card p {
  margin: 0 0 24px;
  font-size: 14px;
  color: #666;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-primary {
  padding: 8px 20px;
  font-size: 14px;
  border: none;
  background: #1976d2;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1565c0;
}

.btn-secondary {
  padding: 8px 20px;
  font-size: 14px;
  border: 1px solid #ccc;
  background: #fff;
  color: #333;
  border-radius: 6px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #f5f5f5;
}

.editor {
  min-height: 100vh;
  background: #fff;
}
</style>