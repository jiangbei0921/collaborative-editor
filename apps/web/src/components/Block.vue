<script setup lang="ts">
import type { Block } from "../types"
import BlockContent from "./BlockContent.vue"

defineProps<{ block: Block }>()

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: []
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
}>()

function tagFor(type: string): string {
  const map: Record<string, string> = {
    heading: "h2",
    bullet: "li",
    quote: "blockquote",
    code: "pre",
  }
  return map[type] ?? "div"
}
</script>

<template>
  <component :is="tagFor(block.type)" class="block" :class="block.type">
    <span v-if="block.type === 'bullet'" class="bullet-marker">•</span>
    <BlockContent
      :content="block.content"
      :block-id="block.id"
      @insert="(id: string, pos: number, text: string) => emit('insert', id, pos, text)"
      @delete="(id: string, pos: number, len: number) => emit('delete', id, pos, len)"
      @create-block="emit('createBlock')"
      @delete-block="(id: string) => emit('deleteBlock', id)"
      @merge-up="(id: string) => emit('mergeUp', id)"
    />
  </component>
</template>

<style scoped>
.block {
  display: flex;
  gap: 4px;
  padding: 2px 0;
}
.bullet-marker {
  user-select: none;
  flex-shrink: 0;
}
.bullet {
  padding-left: 1em;
}
.quote {
  border-left: 3px solid #ccc;
  padding-left: 1em;
}
.code {
  background: #f5f5f5;
  font-family: monospace;
  padding: 8px;
  border-radius: 4px;
}
</style>