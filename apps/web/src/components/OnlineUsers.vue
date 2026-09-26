<script setup lang="ts">
import { ref, computed } from "vue"
import { usePresenceStore } from "../state/usePresenceStore"

const { onlineUsers } = usePresenceStore()
const showList = ref(false)

const count = computed(() => onlineUsers.value.length)

function userColor(userId: string): string {
  const colors = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706",
    "#7c3aed", "#db2777", "#0891b2", "#65a30d",
  ]
  let hash = 0
  for (let i = 0; i < userId.length; i++) {
    hash = userId.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function formatUserId(userId: string): string {
  return `用户 ${userId.slice(0, 6)}`
}
</script>

<template>
  <div class="online-users" @click="showList = !showList">
    <div class="users-trigger">
      <span class="users-dot" />
      <span class="users-count">{{ count }} 人在线</span>
      <svg
        class="users-chevron"
        :class="{ open: showList }"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>
    <div v-if="showList" class="user-list">
      <div
        v-for="userId in onlineUsers"
        :key="userId"
        class="user-item"
      >
        <span class="user-avatar" :style="{ background: userColor(userId) }">
          {{ userId.slice(0, 1).toUpperCase() }}
        </span>
        <span class="user-name">{{ formatUserId(userId) }}</span>
      </div>
      <div v-if="onlineUsers.length === 0" class="user-empty">
        暂无在线用户
      </div>
    </div>
  </div>
</template>

<style scoped>
.online-users {
  position: relative;
  cursor: pointer;
}

.users-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--surface);
  transition: all 0.15s ease;
}
.users-trigger:hover {
  background: var(--surface-hover);
}

.users-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--success);
  flex-shrink: 0;
}

.users-count {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
}

.users-chevron {
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
}
.users-chevron.open {
  transform: rotate(180deg);
}

.user-list {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-2);
  min-width: 180px;
  z-index: 200;
}

.user-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  transition: background 0.12s ease;
}
.user-item:hover {
  background: var(--surface-hover);
}

.user-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  color: var(--text);
}

.user-empty {
  font-size: 13px;
  color: var(--text-tertiary);
  padding: 8px;
  text-align: center;
}
</style>