<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from "vue"

const props = defineProps<{
  content: string
  blockId: string
}>()

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: []
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
}>()

const editable = ref<HTMLElement | null>(null)
const composing = ref(false)

onMounted(() => {
  if (editable.value) {
    editable.value.textContent = props.content
  }
})

function getCursorPosition(): number {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount || !editable.value) return 0

  const range = sel.getRangeAt(0)
  const preRange = range.cloneRange()
  preRange.selectNodeContents(editable.value)
  preRange.setEnd(range.startContainer, range.startOffset)
  return preRange.toString().length
}

function restoreCursor(position: number): void {
  if (!editable.value) return
  const node = editable.value.firstChild
  if (!node) return

  const range = document.createRange()
  const sel = window.getSelection()
  if (!sel) return

  let pos = 0
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT)
  let textNode = walker.nextNode()
  while (textNode && pos + (textNode.textContent?.length ?? 0) < position) {
    pos += textNode.textContent?.length ?? 0
    textNode = walker.nextNode()
  }
  if (textNode) {
    range.setStart(textNode, Math.min(position - pos, textNode.textContent?.length ?? 0))
  } else {
    range.setStartAfter(node)
  }
  range.collapse(true)
  sel.removeAllRanges()
  sel.addRange(range)
}

watch(
  () => props.content,
  (newVal) => {
    if (!editable.value || composing.value) return
    const current = editable.value.textContent ?? ""
    if (current === newVal) return
    const pos = getCursorPosition()
    editable.value.textContent = newVal
    nextTick(() => restoreCursor(pos))
  }
)

function onInput(): void {
  if (composing.value) return
  if (!editable.value) return
  const text = editable.value.textContent ?? ""
  const oldText = props.content
  const pos = getCursorPosition()

  if (text.length > oldText.length) {
    const inserted = text.slice(pos - (text.length - oldText.length), pos)
    emit("insert", props.blockId, pos - inserted.length, inserted)
  } else {
    const deletedLen = oldText.length - text.length
    emit("delete", props.blockId, pos, deletedLen)
  }
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    const pos = getCursorPosition()
    const afterCursor = props.content.slice(pos)
    if (afterCursor) {
      emit("delete", props.blockId, pos, afterCursor.length)
      emit("insert", props.blockId, pos, afterCursor)
    }
    emit("createBlock")
  }

  if (e.key === "Backspace") {
    if (getCursorPosition() === 0 && props.content.length === 0) {
      e.preventDefault()
      emit("deleteBlock", props.blockId)
    }
    if (getCursorPosition() === 0 && props.content.length > 0) {
      e.preventDefault()
      emit("mergeUp", props.blockId)
    }
  }
}

function onCompositionStart(): void {
  composing.value = true
}

function onCompositionEnd(): void {
  composing.value = false
  onInput()
}
</script>

<template>
  <div
    ref="editable"
    contenteditable="true"
    class="block-content"
    data-placeholder="输入内容..."
    @input="onInput"
    @keydown="onKeydown"
    @compositionstart="onCompositionStart"
    @compositionend="onCompositionEnd"
  />
</template>

<style scoped>
.block-content {
  outline: none;
  min-height: 1.5em;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  cursor: text;
  padding: 2px 0;
}

.block-content:empty::before {
  content: attr(data-placeholder);
  color: #999;
  pointer-events: none;
}
</style>