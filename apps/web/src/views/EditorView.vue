<script setup lang="ts">
import { computed } from "vue"
import { useRoute } from "vue-router"
import Editor from "../components/Editor.vue"

const route = useRoute()
const docId = computed(() => route.params.docId as string)
const clientId = crypto.randomUUID()
const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
const wsBaseUrl = `${protocol}//${window.location.host}`
</script>

<template>
  <Editor :doc-id="docId" :client-id="clientId" :ws-base-url="wsBaseUrl" />
</template>