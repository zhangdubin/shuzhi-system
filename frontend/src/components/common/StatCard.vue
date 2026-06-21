<script setup lang="ts">
/**
 * StatCard · 数据卡（design: .stat-card）
 * - label + icon + value + unit + delta
 * - 渐变光晕 hover 效果
 *
 * 用法：
 *   <StatCard label="本月查验" :value="186" unit="张" delta="↑ 24%" delta-type="up" icon="✓" icon-bg="rgba(...)" icon-color="#..." />
 */
defineProps<{
  label: string
  value: number | string
  unit?: string
  prefix?: string
  delta?: string
  deltaType?: 'up' | 'down' | 'plain'
  icon?: string
  iconBg?: string
  iconColor?: string
}>()
</script>

<template>
  <div class="stat-card">
    <div class="stat-label">
      <span>{{ label }}</span>
      <span v-if="icon" class="stat-icon" :style="{ background: iconBg || 'rgba(79,107,255,0.12)', color: iconColor || '#4F6BFF' }">
        {{ icon }}
      </span>
    </div>
    <div class="stat-value">
      <span v-if="prefix" class="prefix">{{ prefix }}</span>
      {{ value }}<span v-if="unit" class="unit">{{ unit }}</span>
    </div>
    <div v-if="delta || $slots.extra" class="stat-delta">
      <slot name="extra">{{ delta || '' }}</slot>
      <span v-if="delta" :class="['delta', deltaType || 'plain']">{{ delta }}</span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.stat-card {
  position: relative;
  background: #fff;
  border-radius: 14px;
  padding: 22px;
  border: 1px solid #E2E8F0;
  overflow: hidden;
  transition: all 0.2s;
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px -8px rgba(15, 23, 42, 0.12);
    border-color: transparent;
  }
  &::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 120px; height: 120px;
    background: linear-gradient(135deg, rgba(79,107,255,0.12) 0%, rgba(124,58,237,0.12) 100%);
    border-radius: 50%;
    filter: blur(20px);
    opacity: 0.6;
    pointer-events: none;
  }
  .stat-label {
    font-size: 12.5px;
    color: #475569;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: grid; place-items: center;
    font-size: 16px;
    font-weight: 600;
  }
  .stat-value {
    font-size: 26px;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 1;
    font-family: "SF Mono", Monaco, Consolas, monospace;
    .prefix { color: #94A3B8; font-size: 16px; margin-right: 2px; }
    .unit { font-size: 13px; color: #94A3B8; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta {
    margin-top: 10px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 4px;
    color: #94A3B8;
    position: relative;
    z-index: 1;
    .delta.up { color: #10B981; font-weight: 600; }
    .delta.down { color: #EF4444; font-weight: 600; }
    .delta.plain { color: #94A3B8; }
  }
}
</style>
