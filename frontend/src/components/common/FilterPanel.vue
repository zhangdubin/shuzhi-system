<script setup lang="ts">
/**
 * FilterPanel · 高级筛选（design: .filter-panel）
 * - 头部 h3 + 右侧 slot（折叠/展开）
 * - 字段网格（默认 3 列，响应式）
 * - 底部 actions 按钮（应用/重置）
 *
 * 用法：
 *   <FilterPanel title="🔍 高级筛选" :collapsible="true">
 *     <div class="field"><label>关键词</label><input /></div>
 *     <div class="field"><label>类型</label><select /></div>
 *     <template #actions>
 *       <button class="btn btn-primary btn-sm">应用筛选</button>
 *       <button class="btn btn-ghost btn-sm">重置</button>
 *     </template>
 *   </FilterPanel>
 */
import { ref } from 'vue'
defineProps<{ title?: string; collapsible?: boolean }>()
const collapsed = ref(false)
</script>

<template>
  <div class="filter-panel fade-up">
    <div class="filter-head">
      <h3>
        <slot name="title">{{ title || '🔍 高级筛选' }}</slot>
      </h3>
      <a v-if="collapsible" class="filter-toggle" @click="collapsed = !collapsed">
        {{ collapsed ? '展开 ∨' : '收起 ∧' }}
      </a>
    </div>
    <div v-show="!collapsed" class="filter-body">
      <div class="filter-grid">
        <slot />
      </div>
      <div v-if="$slots.actions" class="filter-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/mixins.scss" as *;

.filter-panel {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #E2E8F0;
  box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  padding: 16px 20px;
  margin-bottom: 16px;
  .filter-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid #E2E8F0;
    h3 {
      font-size: 14px;
      font-weight: 600;
      margin: 0;
      color: #0F172A;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .filter-toggle {
      font-size: 12px;
      color: #4F6BFF;
      cursor: pointer;
    }
  }
  .filter-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px 16px;
    margin-bottom: 16px;
    @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
    @media (max-width: 640px) { grid-template-columns: 1fr; }
  }
  .filter-actions {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid #E2E8F0;
  }
}
</style>
