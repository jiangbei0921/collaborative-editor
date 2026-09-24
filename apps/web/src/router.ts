import { createRouter, createWebHistory } from "vue-router"
import HomeView from "./views/HomeView.vue"
import EditorView from "./views/EditorView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView },
    { path: "/doc/:docId", component: EditorView, props: true },
  ],
})

export default router