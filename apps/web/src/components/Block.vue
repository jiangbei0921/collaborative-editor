<script setup lang="ts">
import type { Block } from "../types"
import BlockContent from "./BlockContent.vue"
import RemoteCursors from "./RemoteCursors.vue"

defineProps<{ block: Block; isDocumentEmpty: boolean }>()

const emit = defineEmits<{
  insert: [blockId: string, position: number, text: string]
  delete: [blockId: string, position: number, length: number]
  createBlock: [newBlockId: string, suffix: string, currentBlockId: string]
  deleteBlock: [blockId: string]
  mergeUp: [blockId: string]
  cursorChange: [blockId: string, offset: number]
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
  <component :is="tagFor(block.type)" class="block" :class="block.type" :data-block-id="block.id">
    <span v-if="block.type === 'bullet'" class="bullet-marker" />
    <BlockContent
      :content="block.content"
      :block-id="block.id"
      :is-document-empty="isDocumentEmpty"
      @insert="(id: string, pos: number, text: string) => emit('insert', id, pos, text)"
      @delete="(id: string, pos: number, len: number) => emit('delete', id, pos, len)"
      @create-block="(newBlockId: string, suffix: string, currentBlockId: string) => emit('createBlock', newBlockId, suffix, currentBlockId)"
      @delete-block="(id: string) => emit('deleteBlock', id)"
      @merge-up="(id: string) => emit('mergeUp', id)"
      @cursor-change="(id: string, offset: number) => emit('cursorChange', id, offset)"
    />
    <RemoteCursors :block-id="block.id" />
  </component>
</template>

<style scoped>
.block {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: 3px var(--space-2);
  border-radius: var(--radius-sm);
  transition: background 0.12s ease;
  min-height: 1.6em;
}

.block:hover {
  background: var(--surface-hover);
}

.block:focus-within {
  background: var(--surface-active);
}

/* Paragraph */
.block.paragraph {
  font-size: 16px;
  line-height: 1.7;
  color: var(--text);
  padding-top: 3px;
  padding-bottom: 3px;
}

/* Heading */
.block.heading {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text);
  margin-top: var(--space-4);
  margin-bottom: var(--space-1);
  padding-top: var(--space-1);
  padding-bottom: var(--space-1);
}

.block.heading:hover,
.block.heading:focus-within {
  background: transparent;
}

/* Bullet */
.block.bullet {
  font-size: 16px;
  line-height: 1.7;
  color: var(--text);
  padding-top: 2px;
  padding-bottom: 2px;
}

.bullet-marker {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
  margin-top: 11px;
  flex-shrink: 0;
}

/* Quote */
.block.quote {
  font-size: 16px;
  line-height: 1.7;
  color: var(--text-secondary);
  border-left: 3px solid var(--border);
  padding-left: var(--space-4);
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
  font-style: italic;
}

.block.quote:hover,
.block.quote:focus-within {
  background: transparent;
  border-left-color: var(--text-tertiary);
}

/* Code */
.block.code {
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  background: #f8f9fa;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
}

.block.code:hover,
.block.code:focus-within {
  background: #f8f9fa;
  border-color: var(--border);
}
</style>