<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { menuGroups, type MenuItem } from '@/config/menu'
import {
  Odometer, Folder, Document, Money, Wallet, Tickets, MagicStick, Setting,
  List, Files, Camera, CircleCheck, Warning, User, UserFilled, Lock, OfficeBuilding, Collection,
  Search, Bell, QuestionFilled,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

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

/** 过滤掉无权限的菜单项 */
const filteredGroups = computed(() => {
  return menuGroups.map(g => ({
    title: g.title,
    items: g.items.filter((m) => !m.permission || userStore.hasPerm(m.permission)),
  })).filter(g => g.items.length > 0)
})

function goto(path: string) {
  if (route.path !== path) router.push(path)
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
  <el-container class="app-layout">
    <!-- 侧栏（design 1:1：深色 + 分组标题 + 圆角选中态） -->
    <el-aside width="240px" class="app-sidebar">
      <!-- 品牌区（design 风格） -->
      <div class="brand">
        <div class="brand-logo">数</div>
        <div class="brand-text">
          <div class="brand-name">数智化管理系统</div>
          <div class="brand-sub">Shuzhi v1.0</div>
        </div>
      </div>

      <!-- 菜单导航 -->
      <nav class="sidebar-nav">
        <template v-for="group in filteredGroups" :key="group.title">
          <div class="nav-group-title">{{ group.title }}</div>
          <template v-for="item in group.items" :key="item.index">
            <!-- 有子菜单：父级 + 子级（子级无图标，仅缩进） -->
            <div v-if="item.children && item.children.length" class="nav-parent">
              <a
                :class="['nav-link', 'has-children', { active: isActive(item.index) }]"
                @click="goto(item.index)"
              >
                <el-icon class="nav-icon"><component :is="iconMap[item.icon || 'Document']" /></el-icon>
                <span class="nav-label">{{ item.title }}</span>
                <el-icon class="nav-arrow"><ArrowRight /></el-icon>
              </a>
              <div class="nav-children" v-show="isActive(item.index) || item.children.some(c => isActive(c.index))">
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
            <!-- 普通菜单项 -->
            <a
              v-else
              :class="['nav-link', { active: isActive(item.index) }]"
              @click="goto(item.index)"
            >
              <el-icon class="nav-icon"><component :is="iconMap[item.icon || 'Document']" /></el-icon>
              <span class="nav-label">{{ item.title }}</span>
            </a>
          </template>
        </template>
      </nav>

      <!-- 底部 PRO 卡片（design 风格） -->
      <div class="sidebar-pro">
        <h4>数据驾驶舱 PRO</h4>
        <p>解锁 AI 智能分析、自定义看板与高级报表</p>
        <button @click="$message?.info('PRO 功能即将上线')">升级 PRO</button>
      </div>
    </el-aside>

    <el-container>
      <!-- 顶栏（与 design 一致：面包屑 / 搜索 / 通知 / 用户） -->
      <el-header class="app-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-for="b in breadcrumbs.slice(1)" :key="b.path">
              {{ b.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-center">
          <div class="search-input" @click="$message?.info('全局搜索开发中')">
            <el-icon><Search /></el-icon>
            <span>搜索合同 / 客户 / 发票...</span>
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
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
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

// ========== 底部 PRO 卡片 ==========
.sidebar-pro {
  margin: 12px 16px 16px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(79, 107, 255, 0.18) 0%, rgba(124, 58, 237, 0.18) 100%);
  border: 1px solid rgba(79, 107, 255, 0.25);
  border-radius: $radius-md;
  position: relative;
  overflow: hidden;
  &::after {
    content: '';
    position: absolute;
    right: -30px; top: -30px;
    width: 80px; height: 80px;
    background: radial-gradient(circle, rgba(124, 58, 237, 0.4) 0%, transparent 70%);
    border-radius: 50%;
  }
  h4 { color: #fff; font-size: 13px; font-weight: 600; margin: 0 0 4px; }
  p { color: rgba(226, 232, 240, 0.7); font-size: 11px; line-height: 1.5; margin: 0 0 10px; }
  button {
    width: 100%;
    padding: 6px;
    background: $gradient-brand;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
    &:hover { opacity: 0.9; }
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
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
