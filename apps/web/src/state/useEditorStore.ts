import { ref, shallowRef } from "vue"
import type { Block, Document } from "../types"
import { EditorState } from "../editor/EditorState"

const editorRef = shallowRef<EditorState | null>(null)
const blocks = ref<Block[]>([])

export function useEditorStore() {
  function init(editor: EditorState): void {
    editorRef.value = editor
    syncBlocks(editor.document)
  }

  function syncBlocks(doc: Document): void {
    blocks.value = [...doc.blocks]
  }

  function getEditor(): EditorState | null {
    return editorRef.value
  }

  return { editor: editorRef, blocks, init, syncBlocks, getEditor }
}