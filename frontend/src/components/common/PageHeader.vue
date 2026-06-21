<script setup lang="ts">
/**
 * PageHeader · 统一页面顶部
 * 设计：h1 + breadcrumb + 可选 sub-tabs + 可选 actions
 * 与 design/assets/common.css 1:1 对齐
 */
defineProps<{
  /** h1 标题 */
  title: string
  /** 副标题/描述 */
  desc?: string
  /** 面包屑 [{ label, to? }] */
  breadcrumbs?: Array<{ label: string; to?: string }>
  /** 是否显示 sub-tabs slot */
}>()
</script>

<template>
  <header class="page-header">
    <div class="page-header-main">
      <nav v-if="breadcrumbs && breadcrumbs.length" class="breadcrumb">
        <template v-for="(b, i) in breadcrumbs" :key="i">
          <router-link v-if="b.to && i < breadcrumbs.length - 1" :to="b.to">{{ b.label }}</router-link>
          <span v-else-if="i < breadcrumbs.length - 1">{{ b.label }}</span>
          <span v-else class="current">{{ b.label }}</span>
          <span v-if="i < breadcrumbs.length - 1" class="sep">/</span>
        </template>
      </nav>
      <h1>{{ title }}</h1>
      <p v-if="desc" class="page-desc">{{ desc }}</p>
      <slot name="tabs" />
    </div>
    <div v-if="$slots.actions" class="page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
  .page-header-main {
    flex: 1;
    min-width: 0;
  }
  h1 {
    font-size: 17px;
    font-weight: 600;
    color: #0F172A;
    margin: 0;
  }
  .page-desc {
    color: #475569;
    font-size: 13px;
    margin: 4px 0 0;
  }
  .breadcrumb {
    font-size: 12px;
    color: #94A3B8;
    margin-bottom: 4px;
    a { color: #94A3B8; }
    a:hover { color: #4F6BFF; }
    .sep { margin: 0 6px; opacity: 0.5; }
    .current { color: #475569; }
  }
  .page-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}
</style>
