<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { normalizeTitle } from "../types"

const router = useRouter()
const docIdInput = ref("")
const isCreating = ref(false)
const isJoining = ref(false)
const errorMsg = ref<string | null>(null)
const showTitleDialog = ref(false)
const titleInput = ref("")

function extractDocId(raw: string): string | null {
  const trimmed = raw.trim()
  if (!trimmed) return null

  try {
    const url = new URL(trimmed)
    const match = url.pathname.match(/\/doc\/([^/]+)/)
    if (match) return match[1]
  } catch {
    // not a URL, treat as plain docId
  }

  return trimmed
}

function openCreateDialog(): void {
  errorMsg.value = null
  titleInput.value = ""
  showTitleDialog.value = true
}

function closeCreateDialog(): void {
  showTitleDialog.value = false
}

async function confirmCreateDoc(): Promise<void> {
  const title = normalizeTitle(titleInput.value)
  showTitleDialog.value = false
  isCreating.value = true
  errorMsg.value = null
  const docId = crypto.randomUUID()

  try {
    const res = await fetch(`/api/documents/${docId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    })
    if (res.ok) {
      router.push(`/doc/${docId}`)
    } else {
      errorMsg.value = "创建文档失败，请稍后重试"
      isCreating.value = false
    }
  } catch {
    errorMsg.value = "网络错误，请检查后端服务是否运行"
    isCreating.value = false
  }
}

function joinDoc(): void {
  errorMsg.value = null
  const docId = extractDocId(docIdInput.value)
  if (!docId) {
    errorMsg.value = "请输入文档 ID 或链接"
    return
  }
  isJoining.value = true
  router.push(`/doc/${docId}`)
}
</script>

<template>
  <div class="home">
    <h1 class="title">Collaborative Editor</h1>
    <p class="subtitle">实时协同 Block 编辑器</p>

    <button class="btn-primary" :disabled="isCreating" @click="openCreateDialog">
      {{ isCreating ? "创建中..." : "新建文档" }}
    </button>

    <div class="divider">
      <span>或</span>
    </div>

    <div class="join-section">
      <label class="join-label">加入已有文档</label>
      <input
        v-model="docIdInput"
        placeholder="输入文档 ID 或粘贴文档链接"
        @keyup.enter="joinDoc"
      />
      <button class="btn-secondary" :disabled="isJoining" @click="joinDoc">
        {{ isJoining ? "加入中..." : "加入文档" }}
      </button>
      <p class="join-hint">💡 也可以直接打开别人分享的文档链接</p>
    </div>

    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

    <div v-if="showTitleDialog" class="dialog-overlay" @click="closeCreateDialog">
      <div class="dialog" @click.stop>
        <h3>新建文档</h3>
        <input
          v-model="titleInput"
          placeholder="输入文档名称（留空使用“未命名文档”）"
          maxlength="100"
          @keyup.enter="confirmCreateDoc"
        />
        <div class="dialog-actions">
          <button class="btn-secondary" @click="closeCreateDialog">取消</button>
          <button class="btn-primary" @click="confirmCreateDoc">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 16px;
  padding: 24px;
  background: #fafafa;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.subtitle {
  font-size: 14px;
  color: #666;
  margin: 0 0 16px;
}

.btn-primary {
  padding: 10px 32px;
  font-size: 16px;
  border: none;
  background: #1976d2;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #1565c0;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #999;
  font-size: 13px;
  width: 280px;
}

.divider::before,
.divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #e0e0e0;
}

.join-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 280px;
}

.join-label {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 2px;
}

.join-section input {
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
}

.join-section input:focus {
  border-color: #1976d2;
}

.join-hint {
  font-size: 12px;
  color: #888;
  margin: 2px 0 0;
}

.btn-secondary {
  padding: 10px 24px;
  font-size: 14px;
  border: 1px solid #ccc;
  background: #fff;
  color: #333;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background: #f5f5f5;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #d32f2f;
  font-size: 13px;
  margin: 4px 0 0;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  width: 360px;
  max-width: 90vw;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.dialog h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.dialog input {
  padding: 10px 12px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
}

.dialog input:focus {
  border-color: #1976d2;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>