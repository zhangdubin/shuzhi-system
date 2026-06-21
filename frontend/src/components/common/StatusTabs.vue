<script setup lang="ts">
/**
 * StatusTabs · 状态切换（design: .status-tabs）
 *
 * 用法：
 *   <StatusTabs v-model:active="active" :tabs="[
 *     { key: 'all', label: '全部', count: 328 },
 *     { key: 'pending', label: '待核验', count: 12 },
 *   ]" />
 */
defineProps<{
  tabs: Array<{ key: string; label: string; count?: number }>
  active: string
}>()
const emit = defineEmits<{ (e: 'update:active', v: string): void }>()
</script>

<template>
  <div class="status-tabs">
    <a
      v-for="t in tabs"
      :key="t.key"
      href="javascript:void(0)"
      :class="['status-tab', { active: active === t.key }]"
      @click.prevent="emit('update:active', t.key)"
    >
      {{ t.label }} <span v-if="typeof t.count === 'number'" class="num">{{ t.count }}</span>
    </a>
  </div>
</template>

<style lang="scss" scoped>
.status-tabs {
  display: flex;
  gap: 4px;
  background: #fff;
  padding: 4px;
  border-radius: 10px;
  box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  margin-bottom: 16px;
  width: fit-content;
  flex-wrap: wrap;
}
.status-tab {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #475569;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  user-select: none;
  &:hover { background: #F1F5F9; color: #4F6BFF; }
  &.active {
    background: #4F6BFF;
    color: #fff;
    font-weight: 600;
    .num { background: rgba(255, 255, 255, 0.2); color: #fff; }
  }
  .num {
    margin-left: 4px;
    padding: 1px 6px;
    border-radius: 8px;
    background: #F1F5F9;
    color: #94A3B8;
    font-size: 11px;
    font-weight: 500;
  }
}
</style>
