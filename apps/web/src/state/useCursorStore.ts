import { ref } from "vue"
import type { RemoteCursor } from "../types"

const cursors = ref<Map<string, RemoteCursor>>(new Map())

export function useCursorStore() {
  function setCursor(clientId: string, blockId: string, offset: number): void {
    const next = new Map(cursors.value)
    next.set(clientId, { clientId, blockId, offset })
    cursors.value = next
  }

  function removeCursor(clientId: string): void {
    const next = new Map(cursors.value)
    next.delete(clientId)
    cursors.value = next
  }

  function clearCursors(): void {
    cursors.value = new Map()
  }

  function getCursorsForBlock(blockId: string): RemoteCursor[] {
    return Array.from(cursors.value.values()).filter((c) => c.blockId === blockId)
  }

  return { cursors, setCursor, removeCursor, clearCursors, getCursorsForBlock }
}