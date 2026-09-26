<script setup lang="ts">
import { computed } from "vue"
import type { Block } from "../types"
import BlockComponent from "./Block.vue"

const props = defineProps<{ blocks: Block[] }>()

const isDocumentEmpty = computed(
  () => props.blocks.length === 1 && props.blocks[0].content === ""
)

function isFirstEmptyBlock(index: number): boolean {
  return index === 0 && isDocumentEmpty.value
}

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: [newBlockId: string, suffix: string, currentBlockId: string]
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
  cursorChange: [blockId: string, offset: number]
}>()
</script>

<template>
  <div class="editor-content">
    <BlockComponent
      v-for="(block, index) in blocks"
      :key="block.id"
      :block="block"
      :is-document-empty="isFirstEmptyBlock(index)"
      @insert="(id: string, pos: number, text: string) => emit('insert', id, pos, text)"
      @delete="(id: string, pos: number, len: number) => emit('delete', id, pos, len)"
      @create-block="(newBlockId: string, suffix: string, currentBlockId: string) => emit('createBlock', newBlockId, suffix, currentBlockId)"
      @delete-block="(id: string) => emit('deleteBlock', id)"
      @merge-up="(id: string) => emit('mergeUp', id)"
      @cursor-change="(id: string, offset: number) => emit('cursorChange', id, offset)"
    />
  </div>
</template>

<style scoped>
.editor-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-4) 0;
}
</style>