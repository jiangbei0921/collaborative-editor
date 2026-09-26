<script setup lang="ts">
import { onMounted, onUnmounted } from "vue"

const emit = defineEmits<{
  close: []
}>()

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "Escape") {
    emit("close")
  }
}

onMounted(() => {
  document.addEventListener("keydown", onKeydown)
})

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown)
})
</script>

<template>
  <div class="help-overlay" @click.self="emit('close')">
    <div class="help-modal">
      <div class="help-header">
        <h2 class="help-title">协同编辑器使用说明</h2>
        <button class="help-close" @click="emit('close')" aria-label="关闭">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div class="help-body">
        <section class="help-section">
          <h3>一、开始使用</h3>
          <p><strong>新建文档：</strong>在首页点击「新建文档」按钮即可创建。</p>
          <p><strong>加入文档：</strong>输入其他人提供的文档 ID 或文档链接，即可进入同一个文档共同编辑。</p>
        </section>

        <section class="help-section">
          <h3>二、编辑文档</h3>
          <p>直接点击文字区域即可开始输入。</p>
          <p><strong>普通输入：</strong>直接输入文字即可。</p>
          <p><strong>Enter：</strong>创建一个新的段落（Block）。</p>
          <div class="help-example">
            第一段<br>
            ↓ Enter<br>
            第二段
          </div>
          <p><strong>Shift + Enter：</strong>在当前段落内换行，不创建新段落。</p>
          <div class="help-example">
            第一行<br>
            第二行
          </div>
          <p class="help-note">这两行仍然属于同一个段落。</p>
        </section>

        <section class="help-section">
          <h3>三、协同编辑</h3>
          <p>把文档链接发送给其他用户，对方打开后即可共同编辑。</p>
          <p>一方修改内容，其他用户可以看到实时更新。</p>
          <p>右上角可以看到当前在线用户数量。</p>
        </section>

        <section class="help-section">
          <h3>四、分享文档</h3>
          <p>点击右上角「分享」按钮，可以复制文档链接或文档 ID。</p>
          <p>把链接发送给其他用户即可共同编辑。</p>
        </section>

        <section class="help-section">
          <h3>五、连接状态</h3>
          <p><span class="status-dot connected" /> <strong>已连接：</strong>当前可以正常同步。</p>
          <p><span class="status-dot connecting" /> <strong>连接中：</strong>正在建立连接。</p>
          <p><span class="status-dot disconnected" /> <strong>已断开：</strong>网络连接已断开，系统会尝试自动重新连接。</p>
        </section>

        <section class="help-section">
          <h3>六、编辑提示</h3>
          <p>当前文档为空时会显示「开始输入内容…」提示，开始输入后提示自动消失。</p>
        </section>

        <section class="help-section">
          <h3>七、注意事项</h3>
          <p>在网络异常期间继续编辑时，本地内容会在重新连接后自动同步。</p>
          <p>如果页面长时间显示断开，请检查网络并刷新页面。</p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.help-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.help-modal {
  background: var(--surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  width: 100%;
  max-width: 560px;
  max-height: calc(100vh - var(--space-8));
  display: flex;
  flex-direction: column;
  animation: slideUp 0.2s ease;
}

@keyframes slideUp {
  from { transform: translateY(12px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.help-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.help-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.help-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}
.help-close:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.help-body {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
  flex: 1;
}

.help-section {
  margin-bottom: var(--space-5);
}
.help-section:last-child {
  margin-bottom: 0;
}

.help-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 var(--space-2) 0;
}

.help-section p {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 var(--space-1) 0;
}

.help-example {
  background: var(--bg);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  margin: var(--space-2) 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.help-note {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.status-dot.connected {
  background: var(--success);
}
.status-dot.connecting {
  background: var(--warning);
}
.status-dot.disconnected {
  background: var(--danger);
}

@media (max-width: 640px) {
  .help-modal {
    max-height: calc(100vh - var(--space-4));
  }
  .help-header,
  .help-body {
    padding: var(--space-3) var(--space-4);
  }
}
</style>