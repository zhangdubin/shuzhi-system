<script setup lang="ts">
/**
 * TagPill · 状态/类型 标签（design: .tag / .s-pill / .v-pill）
 *
 * 用法：
 *   <TagPill type="success">已识别</TagPill>
 *   <TagPill type="warning">待核验</TagPill>
 *   <TagPill type="danger">已失效</TagPill>
 *   <TagPill type="info">已入账</TagPill>
 *   <TagPill type="primary">电子普通</TagPill>
 *   <TagPill type="purple">数电发票</TagPill>
 *   <TagPill type="gray">已归档</TagPill>
 */
defineProps<{
  type?: 'success' | 'warning' | 'danger' | 'info' | 'primary' | 'purple' | 'gray'
}>()
</script>

<template>
  <span :class="['tag-pill', type || 'gray']">
    <slot />
  </span>
</template>

<style lang="scss" scoped>
.tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 9999px;
  line-height: 1.6;
  white-space: nowrap;
  &.success { background: #D1FAE5; color: #047857; }
  &.warning { background: #FEF3C7; color: #B45309; }
  &.danger  { background: #FEE2E2; color: #B91C1C; }
  &.info    { background: #CFFAFE; color: #0E7490; }
  &.primary { background: #E0E6FF; color: #4F6BFF; }
  &.purple  { background: #FAE8FF; color: #86198F; }
  &.gray    { background: #F1F5F9; color: #475569; }
}
</style>
