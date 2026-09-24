<script setup lang="ts">
import { computed, ref } from "vue"
import { usePresenceStore } from "../state/usePresenceStore"

const { onlineUsers } = usePresenceStore()
const showList = ref(false)

const count = computed(() => onlineUsers.value.length)

function formatUserId(clientId: string): string {
  return `用户-${clientId.slice(0, 8)}`
}
</script>

<template>
  <div class="online-users" @click="showList = !showList">
    <span class="indicator">🟢 {{ count }}人在线</span>
    <div v-if="showList" class="user-list">
      <div
        v-for="userId in onlineUsers"
        :key="userId"
        class="user-item"
      >
        {{ formatUserId(userId) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.online-users {
  position: relative;
  cursor: pointer;
  user-select: none;
}
.indicator {
  font-size: 12px;
  color: #666;
}
.user-list {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px 12px;
  min-width: 120px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  z-index: 100;
}
.user-item {
  font-size: 13px;
  color: #333;
  padding: 4px 0;
}
</style>