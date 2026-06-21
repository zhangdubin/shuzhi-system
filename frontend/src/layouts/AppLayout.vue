<script setup lang="ts">
import { computed, type Component, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { menuGroups, type MenuItem } from '@/config/menu'
import GlobalAskDialog from '@/components/ai/GlobalAskDialog.vue'
import PWAInstallPrompt from '@/components/PWAInstallPrompt.vue'
import {
  Odometer, Folder, Document, Money, Wallet, Tickets, MagicStick, Setting,
  List, Files, Camera, CircleCheck, Warning, User, UserFilled, Lock, OfficeBuilding, Collection,
  Search, Bell, QuestionFilled, Sunny, Moon, Fold, Expand,
} from '@element-plus/icons-vue'

// 移动端侧栏状态
const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false) // 桌面端收起态（仅图标）
const isMobile = ref(window.innerWidth < 768)

function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value }
function closeSidebar() { sidebarOpen.value = false }
function toggleCollapse() { sidebarCollapsed.value = !sidebarCollapsed.value }

// 监听窗口大小变化
if (typeof window !== 'undefined') {
  window.addEventListener('resize', () => {
    isMobile.value = window.innerWidth < 768
    if (!isMobile.value) sidebarOpen.value = false
  })
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 触点 #14：全局命令面板 ⌘K
const cmdkVisible = ref(false)

// 体验增强：暗色模式
const isDark = ref(localStorage.getItem('shuzhi-dark') === '1')
function toggleDark() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('theme-dark', isDark.value)
  localStorage.setItem('shuzhi-dark', isDark.value ? '1' : '0')
  ElMessage.success(isDark.value ? '🌙 已切换为暗色模式' : '☀️ 已切换为亮色模式')
}
// 初始化主题
if (isDark.value) document.documentElement.classList.add('theme-dark')

const iconMap: Record<string, Component> = {
  Odometer, Folder, Document, Money, Wallet, Tickets, MagicStick, Setting,
  List, Files, Camera, CircleCheck, Warning, User, UserFilled, Lock, OfficeBuilding, Collection,
  Search, Bell, QuestionFilled,
}

const activeMenu = computed(() => route.path)
const breadcrumbs = computed(() => {
  const matched = route.matched || []
  return matched.filter((r: any) => r.meta?.title).map((m: any) => ({ title: m.meta.title, path: m.path }))
})

/** 暂时禁用权限过滤，全量展示菜单（多用户端自适应后续重做） */
const filteredGroups = computed(() => menuGroups)

function goto(path: string) {
  if (route.path !== path) router.push(path)
  if (isMobile.value) sidebarOpen.value = false
}

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<template>
  <el-container :class="['app-layout', { 'sidebar-collapsed': sidebarCollapsed && !isMobile }]">
    <!-- 移动端遮罩层 -->
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="closeSidebar" />

    <!-- 侧栏（desktop: 固定 | mobile: 抽屉式） -->
    <el-aside :class="['app-sidebar', { 'mobile-open': sidebarOpen }]">
      <!-- 品牌区 -->
      <div class="brand">
        <div class="brand-logo">数</div>
        <div v-if="!isMobile && !sidebarCollapsed" class="brand-text">
          <div class="brand-name">数智化管理系统</div>
          <div class="brand-sub">Shuzhi v1.0</div>
        </div>
        <!-- 桌面端折叠按钮 -->
        <button v-if="!isMobile" class="collapse-btn" @click="toggleCollapse" :title="sidebarCollapsed ? '展开菜单' : '收起菜单'">
          <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>

      <!-- 菜单导航 -->
      <nav class="sidebar-nav">
        <template v-for="group in filteredGroups" :key="group.title">
          <div v-if="!sidebarCollapsed || isMobile" class="nav-group-title">{{ group.title }}</div>
          <template v-for="item in group.items" :key="item.index">
            <div v-if="item.children && item.children.length" class="nav-parent">
              <a
                :class="['nav-link', 'has-children', { active: isActive(item.index) }]"
                @click="goto(item.index)"
              >
                <el-icon class="nav-icon"><component :is="iconMap[item.icon || 'Document']" /></el-icon>
                <span v-if="!sidebarCollapsed && !isMobile" class="nav-label">{{ item.title }}</span>
                <el-icon v-if="!sidebarCollapsed && !isMobile" class="nav-arrow"><ArrowRight /></el-icon>
              </a>
              <div v-if="!sidebarCollapsed && !isMobile" class="nav-children" v-show="isActive(item.index) || item.children.some(c => isActive(c.index))">
                <a
                  v-for="child in item.children"
                  :key="child.index"
                  :class="['nav-child', { active: isActive(child.index) }]"
                  @click="goto(child.index)"
                >
                  <span class="child-dot"></span>
                  <span>{{ child.title }}</span>
                </a>
              </div>
            </div>
            <a
              v-else
              :class="['nav-link', { active: isActive(item.index) }]"
              @click="goto(item.index)"
            >
              <el-icon class="nav-icon"><component :is="iconMap[item.icon || 'Document']" /></el-icon>
              <span v-if="!sidebarCollapsed && !isMobile" class="nav-label">{{ item.title }}</span>
            </a>
          </template>
        </template>
      </nav>

    </el-aside>

    <el-container>
      <!-- 顶栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <!-- 移动端汉堡菜单按钮 -->
          <el-tooltip content="菜单" placement="bottom">
            <div class="icon-btn hamburger" @click="toggleSidebar">
              <el-icon :size="20"><component :is="sidebarOpen ? Fold : List" /></el-icon>
            </div>
          </el-tooltip>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-for="b in breadcrumbs.slice(1)" :key="b.path">
              {{ b.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-center">
          <div class="search-input" @click="cmdkVisible = true">
            <el-icon><Search /></el-icon>
            <span>问 AI / 搜索 / 跳转（⌘K）</span>
            <kbd>⌘K</kbd>
          </div>
        </div>
        <div class="header-right">
          <el-tooltip content="搜索" placement="bottom">
            <div class="icon-btn"><el-icon><Search /></el-icon></div>
          </el-tooltip>
          <el-tooltip content="通知" placement="bottom">
            <div class="icon-btn" @click="$router.push('/ai/alerts')">
              <el-icon><Bell /></el-icon>
              <span class="badge"></span>
            </div>
          </el-tooltip>
          <el-tooltip content="帮助" placement="bottom">
            <div class="icon-btn"><el-icon><QuestionFilled /></el-icon></div>
          </el-tooltip>
          <el-tooltip :content="isDark ? '切换为亮色' : '切换为暗色'" placement="bottom">
            <div class="icon-btn" @click="toggleDark">
              <el-icon><component :is="isDark ? 'Sunny' : 'Moon'" /></el-icon>
            </div>
          </el-tooltip>
          <!-- 触点 #50：系统设置快捷入口（仅管理员可见） -->
          <el-tooltip v-if="userStore.isAdmin" content="系统设置" placement="bottom">
            <div class="icon-btn icon-btn-accent" @click="$router.push('/admin/settings')">
              <el-icon><Setting /></el-icon>
            </div>
          </el-tooltip>
          <el-tag v-if="userStore.userInfo" type="info" effect="plain" size="small" class="role-tag">
            {{ userStore.userInfo.role }}
          </el-tag>
          <el-dropdown @command="(c: string) => c === 'logout' && handleLogout()">
            <div class="user-trigger">
              <el-avatar :size="32" class="user-avatar">
                {{ userStore.userInfo?.name?.charAt(0) || 'U' }}
              </el-avatar>
              <div class="user-info">
                <div class="user-name">{{ userStore.userInfo?.name || '未登录' }}</div>
                <small v-if="userStore.userInfo?.department">{{ userStore.userInfo.department }}</small>
              </div>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ userStore.userInfo?.department }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component, route }">
          <component :is="Component" :key="route.fullPath" />
        </router-view>
      </el-main>
    </el-container>
  </el-container>

  <!-- 触点 #14：⌘K 全局命令面板 -->
  <GlobalAskDialog v-model:visible="cmdkVisible" />
  <PWAInstallPrompt />
</template>

<style lang="scss" scoped>
.app-layout { height: 100vh; }

// ========== 侧栏 ==========
.app-sidebar {
  background: linear-gradient(180deg, $color-sidebar-bg 0%, $color-sidebar-bg-2 100%);
  color: $color-sidebar-text;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

// ========== 品牌区 ==========
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 22px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  .brand-logo {
    width: 36px; height: 36px;
    border-radius: 10px;
    background: $gradient-brand;
    display: grid; place-items: center;
    color: #fff;
    font-size: 18px; font-weight: 700;
    box-shadow: $shadow-glow;
    flex-shrink: 0;
  }
  .brand-text { line-height: 1.2; }
  .brand-name {
    color: #fff; font-size: 15px; font-weight: 600; letter-spacing: 0.3px;
  }
  .brand-sub {
    color: rgba(148, 163, 184, 0.7); font-size: 11px; margin-top: 4px; letter-spacing: 0.5px;
  }
}

// ========== 导航菜单 ==========
.sidebar-nav {
  flex: 1;
  padding: 8px 12px 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.nav-group-title {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.55);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  padding: 18px 12px 6px;
  font-weight: 600;
  &:first-child { padding-top: 12px; }
}

// 父级菜单（含子级）
.nav-parent { display: flex; flex-direction: column; }

// 一级菜单链接
.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: $radius-md;
  color: $color-sidebar-text;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.18s;
  font-size: 14px;
  margin: 2px 0;
  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #E2E8F0;
  }
  &.active {
    background: $color-sidebar-active-bg;
    color: #fff;
    font-weight: 500;
    box-shadow: 0 2px 8px rgba(79, 107, 255, 0.15);
    &::before {
      content: '';
      position: absolute;
      left: -12px; top: 50%;
      transform: translateY(-50%);
      width: 4px; height: 18px;
      background: $gradient-brand;
      border-radius: 0 2px 2px 0;
    }
  }
  .nav-icon { font-size: 16px; flex-shrink: 0; }
  .nav-label { flex: 1; }
  .nav-arrow { font-size: 12px; opacity: 0.6; }
}

// 二级菜单（缩进 + 小圆点，不带图标）
.nav-children {
  display: flex;
  flex-direction: column;
  margin: 2px 0 8px 0;
  padding-left: 24px;
  position: relative;
  &::before {
    content: '';
    position: absolute;
    left: 19px; top: 4px; bottom: 4px;
    width: 1px;
    background: rgba(148, 163, 184, 0.15);
  }
}
.nav-child {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border-radius: $radius-md;
  color: $color-sidebar-text;
  text-decoration: none;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.18s;
  margin: 1px 0;
  &:hover {
    background: rgba(255, 255, 255, 0.04);
    color: #E2E8F0;
  }
  &.active {
    background: rgba(79, 107, 255, 0.12);
    color: #fff;
    font-weight: 500;
    .child-dot {
      background: $gradient-brand;
      box-shadow: 0 0 6px rgba(79, 107, 255, 0.6);
    }
  }
  .child-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: rgba(148, 163, 184, 0.4);
    flex-shrink: 0;
    transition: all 0.2s;
  }
}

// ========== 顶栏 ==========
.app-header {
  background: $color-bg-card;
  border-bottom: 1px solid $color-border;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $layout-header-height;
  padding: 0 $space-lg;
  box-shadow: $shadow-sm;
  .header-center { flex: 1; max-width: 480px; margin: 0 32px;
    .search-input {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 14px; background: $color-bg; border-radius: $radius-md;
      color: $color-text-tertiary; font-size: 13px; cursor: pointer;
      transition: all 0.2s;
      &:hover { background: $color-primary-bg; color: $color-primary; }
      kbd {
        margin-left: auto; padding: 2px 6px; font-size: 10px;
        background: #fff; border: 1px solid $color-border; border-radius: 3px;
        color: $color-text-tertiary; font-family: $font-family-mono;
      }
    }
  }
  .header-right { display: flex; align-items: center; gap: $space-md; }
  .icon-btn {
    position: relative; width: 36px; height: 36px;
    display: grid; place-items: center; border-radius: $radius-md;
    color: $color-text-tertiary; cursor: pointer; transition: all 0.2s;
    &:hover { background: $color-bg; color: $color-primary; }
    .el-icon { font-size: 18px; }
    .badge {
      position: absolute; top: 8px; right: 8px;
      width: 8px; height: 8px; border-radius: 50%;
      background: $color-danger;
      box-shadow: 0 0 0 2px $color-bg-card;
    }
  }
  .role-tag { margin-right: 4px; }
  .user-trigger {
    display: flex; align-items: center; gap: $space-sm;
    cursor: pointer; padding: 4px 12px; border-radius: $radius-md;
    transition: background 0.2s;
    &:hover { background: rgba(0, 0, 0, 0.04); }
  }
  .user-avatar {
    background: $gradient-brand; color: #fff; font-weight: 600;
  }
  .user-info { line-height: 1.2; }
  .user-name { font-size: 13px; color: $color-text-primary; font-weight: 500; }
  .user-info small { font-size: 11px; color: $color-text-tertiary; }
}

.app-main {
  background: $color-bg;
  padding: $space-md;
  overflow-y: auto;
  @media (max-width: 639px) { padding: 12px; }
}

// ========== 响应式 ==========
$bp-tablet: 768px;
$bp-mobile: 639px;
$bp-collapse: 1024px;

// 桌面端折叠态（仅图标）
.sidebar-collapsed {
  .app-sidebar { width: 64px !important; }
  .app-main { margin-left: 0; }
}

// 移动端遮罩层
.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  backdrop-filter: blur(2px);
  @media (max-width: #{$bp-tablet - 1}) { display: block; }
}

// 移动端侧栏（抽屉式从左侧滑入）
.app-sidebar {
  width: 240px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  @media (max-width: #{$bp-tablet - 1}) {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 1000;
    width: 260px;
    transform: translateX(-110%);
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3);
    &.mobile-open { transform: translateX(0); }
  }
}

// 顶栏左侧布局
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  @media (max-width: #{$bp-mobile}) { gap: 6px; }
}
.hamburger {
  display: none;
  @media (max-width: #{$bp-tablet - 1}) { display: flex !important; }
}

// 顶栏搜索（移动端隐藏）
.header-center {
  @media (max-width: #{$bp-tablet - 1}) { display: none; }
}

// 用户信息（移动端隐藏名字）
.user-info {
  @media (max-width: #{$bp-mobile}) { display: none; }
}
.user-trigger {
  @media (max-width: #{$bp-mobile}) { padding: 4px 8px; }
}
.role-tag {
  @media (max-width: #{$bp-mobile}) { display: none; }
}

// 顶栏图标（移动端缩小）
.icon-btn {
  cursor: pointer;
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  color: #475569;
  transition: all 0.15s;
  position: relative;
  &:hover { background: rgba(79, 107, 255, 0.08); color: #4F6BFF; }
  &.icon-btn-accent {
    background: linear-gradient(135deg, rgba(79, 107, 255, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%);
    color: #4F6BFF;
    border: 1px solid rgba(79, 107, 255, 0.2);
    &:hover {
      background: linear-gradient(135deg, rgba(79, 107, 255, 0.18) 0%, rgba(124, 58, 237, 0.18) 100%);
      transform: translateY(-1px);
      box-shadow: 0 4px 10px rgba(79, 107, 255, 0.2);
    }
  }
  @media (max-width: #{$bp-mobile}) { width: 32px; height: 32px; }
}

// 品牌区折叠按钮
.collapse-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: rgba(148, 163, 184, 0.6);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
  &:hover { color: #fff; }
  @media (max-width: #{$bp-tablet - 1}) { display: none; }
}

// 移动端导航项图标居中
@media (max-width: #{$bp-tablet - 1}) {
  .nav-icon { margin: 0 auto; }
  .nav-link { justify-content: center; }
  .nav-group-title { text-align: center; }
  .brand { justify-content: center; padding: 16px; }
  .brand-logo { width: 40px; height: 40px; font-size: 20px; }
}

// ============================================================
// 路由切换 fade transition（mode="out-in" 必须有 CSS 才会触发 transitionend）
// 否则 Vue 兜底 200ms 后才挂载新组件，肉眼会感觉"点击后空白，刷新才显示"
// ============================================================
.fade-enter-active,
.fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
