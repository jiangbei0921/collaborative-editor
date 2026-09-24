<script setup lang="ts">
import { ref, watch, nextTick } from "vue"
import ConnectionIndicator from "./ConnectionIndicator.vue"
import OnlineUsers from "./OnlineUsers.vue"
import { normalizeTitle, DEFAULT_DOCUMENT_TITLE } from "../types"

const props = defineProps<{
  docId: string
  title: string
}>()

const emit = defineEmits<{
  (e: "update:title", title: string): void
}>()

const isEditing = ref(false)
const editValue = ref("")
const inputRef = ref<HTMLInputElement | null>(null)
const copyFeedback = ref<string | null>(null)

watch(
  () => props.title,
  (newTitle) => {
    if (!isEditing.value) {
      editValue.value = newTitle
    }
  },
  { immediate: true }
)

function startEdit(): void {
  isEditing.value = true
  editValue.value = props.title
  nextTick(() => {
    inputRef.value?.focus()
    inputRef.value?.select()
  })
}

function saveTitle(): void {
  const normalized = normalizeTitle(editValue.value)
  isEditing.value = false
  if (normalized !== props.title) {
    emit("update:title", normalized)
  }
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter") {
    saveTitle()
  } else if (e.key === "Escape") {
    isEditing.value = false
    editValue.value = props.title
  }
}

function showCopyFeedback(msg: string): void {
  copyFeedback.value = msg
  setTimeout(() => {
    copyFeedback.value = null
  }, 2000)
}

async function copyDocId(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.docId)
    showCopyFeedback("ID 已复制")
  } catch {
    const textarea = document.createElement("textarea")
    textarea.value = props.docId
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand("copy")
    document.body.removeChild(textarea)
    showCopyFeedback("ID 已复制")
  }
}

async function copyLink(): Promise<void> {
  const url = `${window.location.origin}/doc/${props.docId}`
  try {
    await navigator.clipboard.writeText(url)
    showCopyFeedback("链接已复制")
  } catch {
    const textarea = document.createElement("textarea")
    textarea.value = url
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand("copy")
    document.body.removeChild(textarea)
    showCopyFeedback("链接已复制")
  }
}
</script>

<template>
  <div class="editor-header">
    <div class="title-section">
      <input
        v-if="isEditing"
        ref="inputRef"
        v-model="editValue"
        class="title-input"
        maxlength="100"
        @blur="saveTitle"
        @keydown="handleKeydown"
      />
      <h1
        v-else
        class="doc-title"
        :title="docId"
        @click="startEdit"
      >
        {{ title || DEFAULT_DOCUMENT_TITLE }}
      </h1>
      <div class="doc-id-row">
        <span class="doc-id-label">文档 ID:</span>
        <span class="doc-id-value">{{ docId }}</span>
        <button class="copy-btn" @click="copyDocId">复制 ID</button>
        <button class="copy-btn" @click="copyLink">复制链接</button>
        <span v-if="copyFeedback" class="copy-feedback">{{ copyFeedback }}</span>
      </div>
    </div>
    <div class="header-right">
      <OnlineUsers />
      <ConnectionIndicator />
    </div>
  </div>
</template>

<style scoped>
.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.doc-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.15s;
}

.doc-title:hover {
  background: #e3f2fd;
}

.title-input {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  border: 1px solid #1976d2;
  border-radius: 4px;
  padding: 2px 4px;
  outline: none;
  width: 400px;
  max-width: 60vw;
}

.doc-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.doc-id-label {
  font-size: 11px;
  color: #666;
}

.doc-id-value {
  font-size: 11px;
  color: #999;
  font-family: monospace;
}

.copy-btn {
  font-size: 11px;
  padding: 1px 6px;
  border: 1px solid #ccc;
  border-radius: 3px;
  background: #fff;
  color: #555;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.copy-btn:hover {
  background: #f0f0f0;
  border-color: #999;
}

.copy-feedback {
  font-size: 11px;
  color: #2e7d32;
  margin-left: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
</style>