import { ref } from "vue"

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "document_not_found"

const status = ref<ConnectionStatus>("disconnected")
const error = ref<string | null>(null)

export function useConnectionStore() {
  function setStatus(s: ConnectionStatus): void {
    status.value = s
    if (s === "connected") {
      error.value = null
    }
  }

  function setError(msg: string): void {
    error.value = msg
    status.value = "disconnected"
  }

  function setDocumentNotFound(msg: string): void {
    error.value = msg
    status.value = "document_not_found"
  }

  return { status, error, setStatus, setError, setDocumentNotFound }
}