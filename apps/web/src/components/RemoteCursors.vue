<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue"
import { useCursorStore } from "../state/useCursorStore"
import { usePresenceStore } from "../state/usePresenceStore"

const props = defineProps<{
  blockId: string
}>()

const { getCursorsForBlock } = useCursorStore()
const { onlineUsers } = usePresenceStore()

const cursorPositions = ref<Map<string, { left: number; top: number }>>(new Map())

const blockCursors = computed(() => {
  const cursors = getCursorsForBlock(props.blockId)
  return cursors.filter((c) => onlineUsers.value.includes(c.clientId))
})

function userColor(clientId: string): string {
  const colors = [
    "#2563eb", "#dc2626", "#16a34a", "#d97706",
    "#7c3aed", "#db2777", "#0891b2", "#65a30d",
  ]
  let hash = 0
  for (let i = 0; i < clientId.length; i++) {
    hash = clientId.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

function userName(clientId: string): string {
  return `用户 ${clientId.slice(0, 6)}`
}

function measureCursorPosition(clientId: string, offset: number): { left: number; top: number } {
  const blockEl = document.querySelector(`[data-block-id="${props.blockId}"]`)
  if (!blockEl) return { left: 0, top: 0 }

  const contentEl = blockEl.querySelector(".block-content") as HTMLElement
  if (!contentEl) return { left: 0, top: 0 }

  const text = contentEl.textContent ?? ""
  const clampedOffset = Math.min(offset, text.length)

  // Create a temporary range to measure position
  const range = document.createRange()
  const sel = window.getSelection()
  if (!sel) return { left: 0, top: 0 }

  // Find the text node and offset
  let pos = 0
  const walker = document.createTreeWalker(contentEl, NodeFilter.SHOW_TEXT)
  let textNode = walker.nextNode()
  while (textNode && pos + (textNode.textContent?.length ?? 0) < clampedOffset) {
    pos += textNode.textContent?.length ?? 0
    textNode = walker.nextNode()
  }

  if (textNode) {
    range.setStart(textNode, Math.min(clampedOffset - pos, textNode.textContent?.length ?? 0))
  } else {
    // If offset is beyond text length, place at end
    const lastChild = contentEl.lastChild
    if (lastChild) {
      range.setStartAfter(lastChild)
    } else {
      range.setStart(contentEl, 0)
    }
  }
  range.collapse(true)

  const rect = range.getBoundingClientRect()
  const contentRect = contentEl.getBoundingClientRect()

  return {
    left: rect.left - contentRect.left,
    top: rect.top - contentRect.top,
  }
}

watch(
  blockCursors,
  (cursors) => {
    nextTick(() => {
      const next = new Map<string, { left: number; top: number }>()
      for (const cursor of cursors) {
        next.set(cursor.clientId, measureCursorPosition(cursor.clientId, cursor.offset))
      }
      cursorPositions.value = next
    })
  },
  { immediate: true, deep: true }
)
</script>

<template>
  <div class="remote-cursors">
    <div
      v-for="cursor in blockCursors"
      :key="cursor.clientId"
      class="remote-cursor"
      :style="{
        '--cursor-color': userColor(cursor.clientId),
        left: `${cursorPositions.get(cursor.clientId)?.left ?? 0}px`,
        top: `${cursorPositions.get(cursor.clientId)?.top ?? 0}px`,
      }"
    >
      <span class="cursor-line" />
      <span class="cursor-label">{{ userName(cursor.clientId) }}</span>
    </div>
  </div>
</template>

<style scoped>
.remote-cursors {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 10;
}

.remote-cursor {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  animation: cursorFadeIn 0.15s ease;
}

@keyframes cursorFadeIn {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.cursor-line {
  width: 2px;
  height: 1.4em;
  background: var(--cursor-color);
  border-radius: 1px;
}

.cursor-label {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--cursor-color);
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
  margin-top: -2px;
  line-height: 1.4;
}
</style>