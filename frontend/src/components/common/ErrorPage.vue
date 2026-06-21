<script setup lang="ts">
/**
 * ErrorPage · 错误页统一组件（design: .err-wrap / .err-code / .err-icon / .err-title / .err-sub / .err-tips）
 *
 * 4 个错误页（403 / 404 / 500 / network）共用此组件
 */
import { useRouter } from 'vue-router'

const router = useRouter()

withDefaults(defineProps<{
  /** 大字错误码（404 / 403 / 500），传空字符串隐藏 */
  code?: string
  /** 大图标 */
  icon: string
  /** 错误标题 */
  title: string
  /** 错误副标题（多行用 \n 或传 array） */
  sub: string
  /** 是否显示 4 个推荐链接（默认 true） */
  showTips?: boolean
  /** 自定义推荐链接 [{label, to}]，不传走默认 4 个 */
  tips?: Array<{ label: string; to: string }>
}>(), {
  code: '',
  showTips: true,
  tips: () => [
    { label: 'Dashboard 总览', to: '/dashboard' },
    { label: '发票识别', to: '/invoice/ocr' },
    { label: '合同管理', to: '/contract/list' },
    { label: '项目管理', to: '/project/list' },
  ],
})

function go(to: string) { router.push(to) }
</script>

<template>
  <div class="err-page">
    <div class="err-wrap">
      <div v-if="code" class="err-code">{{ code }}</div>
      <div v-else-if="icon" class="err-code err-code-icon">{{ icon }}</div>
      <h1 class="err-title">{{ title }}</h1>
      <p class="err-sub" v-html="sub" />
      <div class="err-actions">
        <a class="btn btn-primary btn-lg" @click.prevent="go('/dashboard')">🏠 返回首页</a>
        <a class="btn btn-outline btn-lg" @click.prevent="router.back()">← 返回上页</a>
        <a class="btn btn-ghost" @click.prevent="go('/index')">📑 页面总览</a>
      </div>
      <div v-if="showTips" class="err-tips">
        <div class="head">💡 你可能想访问</div>
        <ul>
          <li v-for="t in tips" :key="t.to">
            <a @click.prevent="go(t.to)">{{ t.label }}</a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.err-page {
  min-height: 100vh;
  background: var(--color-bg, #F1F5F9);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.err-wrap {
  max-width: 520px;
  text-align: center;
  padding: 48px 32px;
}
.err-code {
  font-size: 120px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 16px;
  letter-spacing: -4px;
}
.err-code-icon {
  font-size: 96px;
  -webkit-text-fill-color: initial;
  background: none;
  margin-bottom: 24px;
}
.err-icon {
  font-size: 64px;
  margin-bottom: 8px;
  display: inline-block;
}
.err-title {
  font-size: 22px;
  font-weight: 700;
  color: #0F172A;
  margin: 0 0 8px 0;
}
.err-sub {
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
  margin: 0 0 28px 0;
}
.err-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.err-tips {
  margin-top: 40px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  text-align: left;
  .head {
    font-size: 12.5px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }
  ul {
    list-style: none;
    padding: 0; margin: 0;
  }
  li {
    font-size: 13px;
    color: #475569;
    padding: 4px 0;
    padding-left: 16px;
    position: relative;
    &::before {
      content: '→';
      position: absolute;
      left: 0;
      color: #4F6BFF;
      font-weight: 600;
    }
    a {
      color: #4F6BFF;
      cursor: pointer;
      &:hover { text-decoration: underline; }
    }
  }
}

// 按钮（与 design 一致）
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 18px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 10px;
  transition: all 0.18s ease;
  white-space: nowrap;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  text-decoration: none;
  &.btn-primary {
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
    color: #fff;
    box-shadow: 0 8px 32px -4px rgba(79, 107, 255, 0.35);
    &:hover { transform: translateY(-1px); }
  }
  &.btn-outline {
    background: #fff;
    color: #0F172A;
    border-color: #E2E8F0;
    &:hover { border-color: #4F6BFF; color: #4F6BFF; }
  }
  &.btn-ghost {
    background: transparent;
    color: #475569;
    &:hover { background: rgba(79, 107, 255, 0.08); color: #4F6BFF; }
  }
  &.btn-lg { height: 48px; padding: 0 24px; font-size: 15px; }
}
</style>
