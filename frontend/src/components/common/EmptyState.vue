<script setup lang="ts">
/**
 * EmptyState · 空状态（design: .empty-state）
 *
 * 用法：
 *   <EmptyState icon="📭" title="暂无数据" message="还没有任何记录">
 *     <button class="btn btn-primary btn-sm">立即创建</button>
 *   </EmptyState>
 */
defineProps<{
  icon?: string
  title?: string
  message?: string
}>()
</script>

<template>
  <div class="empty-state">
    <div class="ico">{{ icon || '📭' }}</div>
    <div v-if="title" class="t">{{ title }}</div>
    <div v-if="message" class="m">{{ message }}</div>
    <div v-if="$slots.actions" class="actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  .ico {
    width: 80px; height: 80px;
    border-radius: 50%;
    background: #F1F5F9;
    color: #94A3B8;
    display: grid; place-items: center;
    font-size: 36px;
    margin-bottom: 16px;
  }
  .t {
    font-size: 15px;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 6px;
  }
  .m {
    font-size: 12.5px;
    color: #94A3B8;
    line-height: 1.6;
    max-width: 320px;
    margin-bottom: 16px;
  }
  .actions { display: flex; gap: 8px; }
}
</style>
