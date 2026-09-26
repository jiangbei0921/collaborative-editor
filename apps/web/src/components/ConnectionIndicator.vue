<script setup lang="ts">
import { useConnectionStore } from "../state/useConnectionStore"

const { status, error } = useConnectionStore()

const label: Record<string, string> = {
  connected: "已连接",
  connecting: "连接中",
  disconnected: "已断开",
  document_not_found: "文档不存在",
}

const colorClass: Record<string, string> = {
  connected: "status-success",
  connecting: "status-warning",
  disconnected: "status-danger",
  document_not_found: "status-danger",
}
</script>

<template>
  <div class="connection-indicator" :title="error ?? ''">
    <span class="status-pill" :class="colorClass[status]">
      <span class="status-dot" />
      <span class="status-label">{{ label[status] }}</span>
    </span>
  </div>
</template>

<style scoped>
.connection-indicator {
  display: flex;
  align-items: center;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-success {
  background: var(--success-bg);
  color: var(--success);
}
.status-success .status-dot {
  background: var(--success);
}

.status-warning {
  background: var(--warning-bg);
  color: var(--warning);
}
.status-warning .status-dot {
  background: var(--warning);
}

.status-danger {
  background: var(--danger-bg);
  color: var(--danger);
}
.status-danger .status-dot {
  background: var(--danger);
}

.status-label {
  white-space: nowrap;
}
</style>