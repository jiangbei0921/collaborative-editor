<script setup lang="ts">
import type { Block as BlockType } from "../types"
import Block from "./Block.vue"

defineProps<{ blocks: BlockType[] }>()

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: []
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
}>()
</script>

<template>
  <div class="editor-content">
    <Block
      v-for="block in blocks"
      :key="block.id"
      :block="block"
      @insert="(blockId: string, position: number, text: string) => emit('insert', blockId, position, text)"
      @delete="(blockId: string, position: number, length: number) => emit('delete', blockId, position, length)"
      @create-block="emit('createBlock')"
      @delete-block="(blockId: string) => emit('deleteBlock', blockId)"
      @merge-up="(blockId: string) => emit('mergeUp', blockId)"
    />
  </div>
</template>

<style scoped>
.editor-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px 32px;
}
</style>