<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from "vue"

const props = defineProps<{
  content: string
  blockId: string
  isDocumentEmpty: boolean
}>()

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: [newBlockId: string, suffix: string, currentBlockId: string]
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
  cursorChange: [blockId: string, offset: number]
}>()

const editable = ref<HTMLElement | null>(null)
const composing = ref(false)
let lastLocalSnapshot = ""

onMounted(() => {
  if (editable.value) {
    editable.value.textContent = props.content
  }
  lastLocalSnapshot = props.content
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
    if (current === newVal) {
      lastLocalSnapshot = newVal
      return
    }
    // Only force update DOM if remote content is significantly different from local.
    // If local text starts with remote text (local is ahead), preserve local to avoid
    // losing characters during rapid input.
    if (current.startsWith(newVal) && current.length > newVal.length) {
      // Local is ahead of remote, preserve local DOM and just update snapshot
      lastLocalSnapshot = current
      return
    }
    const pos = getCursorPosition()
    editable.value.textContent = newVal
    lastLocalSnapshot = newVal
    nextTick(() => restoreCursor(pos))
  }
)

let lastCursorEmit = 0
const CURSOR_THROTTLE_MS = 150

function reportCursor(): void {
  const now = Date.now()
  if (now - lastCursorEmit < CURSOR_THROTTLE_MS) return
  lastCursorEmit = now
  const offset = getCursorPosition()
  emit("cursorChange", props.blockId, offset)
}

function getTextContent(el: HTMLElement): string {
  // Clone to avoid modifying DOM
  const clone = el.cloneNode(true) as HTMLElement
  // Replace <br>, <br/> with newline
  clone.querySelectorAll("br").forEach((br) => br.replaceWith("\n"))
  // Replace block-level elements with newline + text
  clone.querySelectorAll("div, p").forEach((block) => {
    const text = block.textContent || ""
    block.replaceWith("\n" + text)
  })
  return clone.textContent ?? ""
}

function onInput(): void {
  if (composing.value) return
  if (!editable.value) return
  const text = getTextContent(editable.value)
  const oldText = lastLocalSnapshot
  const pos = getCursorPosition()

  if (text.length > oldText.length) {
    const inserted = text.slice(pos - (text.length - oldText.length), pos)
    emit("insert", props.blockId, pos - inserted.length, inserted)
  } else if (text.length < oldText.length) {
    const deletedLen = oldText.length - text.length
    emit("delete", props.blockId, pos, deletedLen)
  }
  lastLocalSnapshot = text
  reportCursor()
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    const pos = getCursorPosition()
    const afterCursor = lastLocalSnapshot.slice(pos)
    const newBlockId = crypto.randomUUID()
    if (afterCursor) {
      emit("delete", props.blockId, pos, afterCursor.length)
    }
    emit("createBlock", newBlockId, afterCursor, props.blockId)
    lastLocalSnapshot = lastLocalSnapshot.slice(0, pos)
    return
  }

  // Shift+Enter: insert line break within current block
  if (e.key === "Enter" && e.shiftKey) {
    e.preventDefault()
    const pos = getCursorPosition()
    // Insert <br> at cursor position in DOM
    const sel = window.getSelection()
    if (sel && sel.rangeCount && editable.value) {
      const range = sel.getRangeAt(0)
      const br = document.createElement("br")
      range.deleteContents()
      range.insertNode(br)
      // Move cursor after <br>
      range.setStartAfter(br)
      range.collapse(true)
      sel.removeAllRanges()
      sel.addRange(range)
    }
    // Emit insert operation with newline
    emit("insert", props.blockId, pos, "\n")
    lastLocalSnapshot = lastLocalSnapshot.slice(0, pos) + "\n" + lastLocalSnapshot.slice(pos)
    return
  }

  if (e.key === "Backspace") {
    if (getCursorPosition() === 0 && lastLocalSnapshot.length === 0) {
      e.preventDefault()
      emit("deleteBlock", props.blockId)
    }
    if (getCursorPosition() === 0 && lastLocalSnapshot.length > 0) {
      e.preventDefault()
      emit("mergeUp", props.blockId)
    }
  }

  // Report cursor on navigation keys
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(e.key)) {
    requestAnimationFrame(reportCursor)
  }
}

function onSelectionChange(): void {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount) return
  const container = sel.getRangeAt(0).commonAncestorContainer
  if (editable.value && (container === editable.value || editable.value.contains(container))) {
    reportCursor()
  }
}

function onCompositionStart(): void {
  composing.value = true
}

function onCompositionEnd(): void {
  composing.value = false
  onInput()
}

onMounted(() => {
  document.addEventListener("selectionchange", onSelectionChange)
})

onUnmounted(() => {
  document.removeEventListener("selectionchange", onSelectionChange)
})
</script>

<template>
  <div
    ref="editable"
    contenteditable="true"
    class="block-content"
    :class="{ 'show-placeholder': props.isDocumentEmpty }"
    data-placeholder="开始输入内容…"
    @input="onInput"
    @keydown="onKeydown"
    @compositionstart="onCompositionStart"
    @compositionend="onCompositionEnd"
    @click="reportCursor"
    @focus="reportCursor"
  />
</template>

<style scoped>
.block-content {
  outline: none;
  min-height: 1.6em;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  cursor: text;
  padding: 2px 0;
  caret-color: var(--primary);
}

.block-content.show-placeholder:empty::before {
  content: attr(data-placeholder);
  color: var(--text-tertiary);
  pointer-events: none;
}
</style>