<script setup lang="ts">
import { useConnectionStore } from "../state/useConnectionStore"

const { status, error } = useConnectionStore()

const label: Record<string, string> = {
  connected: "已连接",
  connecting: "连接中...",
  disconnected: "已断开",
  document_not_found: "文档不存在",
}

const color: Record<string, string> = {
  connected: "#4caf50",
  connecting: "#ff9800",
  disconnected: "#f44336",
  document_not_found: "#f44336",
}
</script>

<template>
  <div class="connection-indicator" :title="error ?? ''">
    <span class="dot" :style="{ background: color[status] }" />
    <span class="label">{{ label[status] }}</span>
  </div>
</template>

<style scoped>
.connection-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #888;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
</style>