<!--
  PWAInstallPrompt.vue
  R14C PWA 安装提示组件
  - 监听 beforeinstallprompt 事件，捕获 deferredPrompt
  - 监听 appinstalled 事件，标记已安装
  - 监听 online/offline 事件，提示离线状态
  - 智能提示：用户已关闭过 7 天内不再提示
  - 移动端优先（PWA 主要价值在手机）
-->
<template>
  <Teleport to="body">
    <!-- 离线提示（toast） -->
    <Transition name="offline-fade">
      <div v-if="!online" class="pwa-offline-bar">
        <span class="ico">📡</span>
        <span>网络已断开，部分功能不可用</span>
      </div>
    </Transition>

    <!-- 安装提示（卡片） -->
    <Transition name="install-fade">
      <div v-if="showInstallPrompt" class="pwa-install-card">
        <div class="pic">
          <img src="/pwa-192x192.png" alt="数智化管理系统" />
        </div>
        <div class="body">
          <div class="title">📱 添加到主屏幕</div>
          <div class="desc">像 App 一样使用数智化管理系统，免输入网址 + 离线可用</div>
          <div class="actions">
            <button class="btn-primary" @click="install">立即安装</button>
            <button class="btn-secondary" @click="dismiss">稍后</button>
          </div>
        </div>
        <button class="close" @click="dismiss">×</button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const online = ref(navigator.onLine)
const showInstallPrompt = ref(false)
let deferredPrompt: any = null
const STORAGE_KEY = 'shuzhi-pwa-install-dismissed'
const COOLDOWN_DAYS = 7

function shouldShowPrompt(): boolean {
  const ts = localStorage.getItem(STORAGE_KEY)
  if (!ts) return true
  const daysSince = (Date.now() - parseInt(ts, 10)) / (1000 * 60 * 60 * 24)
  return daysSince > COOLDOWN_DAYS
}

function onBeforeInstallPrompt(e: Event) {
  // 阻止默认的浏览器提示
  e.preventDefault()
  deferredPrompt = e
  // 7 天冷却：用户刚关过就不再打扰
  if (shouldShowPrompt()) {
    setTimeout(() => {
      showInstallPrompt.value = true
    }, 5000)  // 用户进来 5 秒后再说
  }
}

function onAppInstalled() {
  showInstallPrompt.value = false
  deferredPrompt = null
  // 标记为已安装
  try { localStorage.setItem('shuzhi-pwa-installed', '1') } catch {}
}

async function install() {
  if (!deferredPrompt) return
  showInstallPrompt.value = false
  deferredPrompt.prompt()
  const { outcome } = await deferredPrompt.userChoice
  if (outcome === 'accepted') {
    // 用户同意安装
  } else {
    // 用户拒绝：记录 dismiss，7 天内不再提示
    localStorage.setItem(STORAGE_KEY, String(Date.now()))
  }
  deferredPrompt = null
}

function dismiss() {
  showInstallPrompt.value = false
  localStorage.setItem(STORAGE_KEY, String(Date.now()))
}

function onOnline() { online.value = true }
function onOffline() { online.value = false }

onMounted(() => {
  window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.addEventListener('appinstalled', onAppInstalled)
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)

  // 注册 SW（VitePWA 已自动注册，但这里再保险一次）
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then((regs) => {
      if (regs.length > 0) {
        // SW 已注册
        console.log(`[PWA] ${regs.length} service worker(s) registered`)
      }
    })
  }
})

onUnmounted(() => {
  window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
  window.removeEventListener('appinstalled', onAppInstalled)
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
})
</script>

<style lang="scss" scoped>
.pwa-offline-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
  color: #fff;
  padding: 10px 20px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 2px 12px rgba(239, 68, 68, 0.4);
  .ico { font-size: 16px; }
}
.offline-fade-enter-active, .offline-fade-leave-active { transition: all 0.3s; }
.offline-fade-enter-from, .offline-fade-leave-to { transform: translateY(-100%); opacity: 0; }

.pwa-install-card {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9998;
  width: 360px;
  max-width: calc(100vw - 48px);
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18), 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 18px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  border: 1px solid #E2E8F0;
  .pic {
    flex-shrink: 0;
    img { width: 56px; height: 56px; border-radius: 14px; box-shadow: 0 4px 12px rgba(79, 107, 255, 0.3); }
  }
  .body { flex: 1; min-width: 0; }
  .title { font-size: 14px; font-weight: 600; color: #0F172A; margin-bottom: 4px; }
  .desc { font-size: 12.5px; color: #64748B; line-height: 1.5; margin-bottom: 12px; }
  .actions { display: flex; gap: 8px; }
  button {
    padding: 7px 16px;
    font-size: 12.5px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .btn-primary {
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
    color: #fff;
    box-shadow: 0 2px 8px rgba(79, 107, 255, 0.3);
  }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); }
  .btn-secondary { background: #F1F5F9; color: #475569; }
  .btn-secondary:hover { background: #E2E8F0; }
  .close {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    color: #94A3B8;
    font-size: 20px;
    line-height: 1;
    border-radius: 6px;
  }
  .close:hover { background: #F1F5F9; color: #475569; }
}
.install-fade-enter-active, .install-fade-leave-active { transition: all 0.3s; }
.install-fade-enter-from, .install-fade-leave-to { transform: translateY(20px); opacity: 0; }

@media (max-width: 640px) {
  .pwa-install-card {
    bottom: 16px;
    right: 16px;
    left: 16px;
    width: auto;
    max-width: none;
  }
}
</style>
