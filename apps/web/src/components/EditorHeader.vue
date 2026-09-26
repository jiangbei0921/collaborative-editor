<script setup lang="ts">
import { ref, nextTick } from "vue"
import { useRouter } from "vue-router"
import ConnectionIndicator from "./ConnectionIndicator.vue"
import OnlineUsers from "./OnlineUsers.vue"
import HelpModal from "./HelpModal.vue"
import { DEFAULT_DOCUMENT_TITLE } from "../types"

const props = defineProps<{
  docId: string
  title: string
}>()

const emit = defineEmits<{
  "update:title": [title: string]
}>()

const router = useRouter()
const isEditing = ref(false)
const editValue = ref("")
const inputRef = ref<HTMLInputElement | null>(null)
const showSharePanel = ref(false)
const showHelp = ref(false)
const copyFeedback = ref("")
const shareUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/doc/${props.docId}`

function goHome(): void {
  router.push("/")
}

function startEdit(): void {
  isEditing.value = true
  editValue.value = props.title || DEFAULT_DOCUMENT_TITLE
  nextTick(() => inputRef.value?.focus())
}

function saveTitle(): void {
  isEditing.value = false
  const trimmed = editValue.value.trim()
  if (trimmed && trimmed !== props.title) {
    emit("update:title", trimmed)
  }
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter") {
    e.preventDefault()
    saveTitle()
  }
  if (e.key === "Escape") {
    isEditing.value = false
  }
}

function copyDocId(): void {
  navigator.clipboard.writeText(props.docId).then(() => {
    showFeedback("文档 ID 已复制")
  })
}

function copyLink(): void {
  navigator.clipboard.writeText(shareUrl).then(() => {
    showFeedback("链接已复制")
  })
}

function showFeedback(text: string): void {
  copyFeedback.value = text
  setTimeout(() => {
    copyFeedback.value = ""
  }, 2000)
}
</script>

<template>
  <header class="editor-header">
    <div class="header-left">
      <button class="home-btn" title="返回首页" @click="goHome">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      </button>
      <div class="title-wrap">
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
        <div class="title-meta">
          <ConnectionIndicator />
        </div>
      </div>
    </div>

    <div class="header-right">
      <button class="help-btn" title="使用说明" @click="showHelp = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        帮助
      </button>

      <OnlineUsers />

      <div class="share-wrap">
        <button
          class="share-btn"
          :class="{ active: showSharePanel }"
          @click="showSharePanel = !showSharePanel"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
          分享
        </button>

        <div v-if="showSharePanel" class="share-panel" @click.stop>
          <div class="share-row">
            <span class="share-label">文档 ID</span>
            <div class="share-value-row">
              <code class="share-code">{{ docId }}</code>
              <button class="share-copy-btn" @click="copyDocId">复制</button>
            </div>
          </div>
          <div class="share-row">
            <span class="share-label">分享链接</span>
            <div class="share-value-row">
              <span class="share-link">{{ shareUrl }}</span>
              <button class="share-copy-btn" @click="copyLink">复制</button>
            </div>
          </div>
          <div v-if="copyFeedback" class="share-feedback">{{ copyFeedback }}</div>
        </div>
      </div>
    </div>

    <HelpModal v-if="showHelp" @close="showHelp = false" />
  </header>
</template>

<style scoped>
.editor-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--space-4);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  gap: var(--space-4);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}

.home-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}
.home-btn:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.doc-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 2px 6px;
  margin: -2px -6px;
  border-radius: var(--radius-sm);
  transition: background 0.12s ease;
  line-height: 1.4;
}
.doc-title:hover {
  background: var(--surface-hover);
}

.title-input {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  border: 1px solid var(--border-focus);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
  outline: none;
  background: var(--surface);
  width: 100%;
  max-width: 400px;
  line-height: 1.4;
}

.title-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.help-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.help-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-focus);
  color: var(--text);
}

.share-wrap {
  position: relative;
}

.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.share-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-focus);
}
.share-btn.active {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
}

.share-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-4);
  min-width: 320px;
  z-index: 200;
}

.share-row {
  margin-bottom: var(--space-3);
}
.share-row:last-child {
  margin-bottom: 0;
}

.share-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.share-value-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.share-code {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--bg);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  color: var(--text);
  word-break: break-all;
}

.share-link {
  flex: 1;
  font-size: 12px;
  background: var(--bg);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  color: var(--text);
  word-break: break-all;
}

.share-copy-btn {
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  flex-shrink: 0;
}
.share-copy-btn:hover {
  background: var(--surface-hover);
  color: var(--text);
  border-color: var(--border-focus);
}

.share-feedback {
  font-size: 12px;
  color: var(--success);
  margin-top: var(--space-2);
  text-align: center;
}

@media (max-width: 640px) {
  .editor-header {
    padding: 0 var(--space-3);
  }

  .share-panel {
    right: -40px;
    min-width: 280px;
  }
}
</style>