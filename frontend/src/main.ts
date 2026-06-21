// ============================================================
// 应用入口
// ============================================================
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './assets/styles/global.scss'
// R16 设计系统级暗色主题：必须早于业务组件加载
import './assets/styles/dark-theme.scss'

// === R16 主题尽早初始化（避免 FOUC）===
// 在 Vue mount 前根据 localStorage 立即设 class
;(function initTheme() {
  try {
    const isDark = localStorage.getItem('shuzhi-dark') === '1'
    if (isDark) {
      document.documentElement.classList.add('theme-dark')
    }
  } catch (e) { /* localStorage 不可用，忽略 */ }
})()

const app = createApp(App)

// 注册所有 Element Plus 图标（全局可用）
for (const [name, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, comp as never)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 全局权限指令
import permission from '@/directives/permission'
app.directive('permission', permission)

app.mount('#app')

// === 启动时如有 token，异步拉一次最新用户信息覆盖 localStorage ===
// 解决旧版本没存 isAdmin 字段导致 router requireAdmin 误判
// 已经在 /login 页面时不主动拉（避免触发 401 弹窗）
import { useUserStore } from '@/stores/user'
const _userStore = useUserStore()
if (_userStore.token && window.location.pathname !== '/login') {
  _userStore.fetchMe().catch(() => {})
}
