import { ref } from "vue"

const onlineUsers = ref<string[]>([])

export function usePresenceStore() {
  function setOnlineUsers(users: string[]): void {
    onlineUsers.value = users
  }

  return { onlineUsers, setOnlineUsers }
}