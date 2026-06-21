<script setup lang="ts">
/**
 * 通用 4 KPI 统计卡
 * @props stats: [{ key, label, value, unit?, delta?, deltaType?, icon?, tone?, extra? }]
 * @props loading
 */
defineProps<{
  stats: Array<{
    key: string
    label: string
    value: number | string
    unit?: string
    delta?: number
    deltaType?: 'up' | 'down' | 'flat'
    extra?: string
    icon?: string
    tone?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  }>
  loading?: boolean
  cols?: number
}>()

function fmt(v: number | string, unit?: string): string {
  if (typeof v === 'string') return v
  if (unit === '元') {
    if (v >= 100000000) return (v / 100000000).toFixed(1) + ' 亿'
    if (v >= 10000) return (v / 10000).toFixed(1) + ' 万'
    return v.toLocaleString()
  }
  if (unit === '%') return v + '%'
  return v.toLocaleString() + (unit ? ' ' + unit : '')
}

function deltaColor(t?: string) {
  if (t === 'up') return 'var(--color-success)'
  if (t === 'down') return 'var(--color-danger)'
  return 'var(--color-text-tertiary)'
}
</script>

<template>
  <div :class="['kpi-grid', `cols-${cols || 4}`]" v-loading="loading || false">
    <div
      v-for="s in stats"
      :key="s.key"
      :class="['kpi-card', `tone-${s.tone || 'primary'}`]"
    >
      <div class="ic" v-if="s.icon">{{ s.icon }}</div>
      <div class="meta">
        <div class="l">
          {{ s.label }}
          <span v-if="s.unit" class="unit-hint">{{ s.unit }}</span>
        </div>
        <div class="v">{{ fmt(s.value, s.unit) }}</div>
        <div class="d" v-if="s.delta != null || s.extra">
          <template v-if="s.delta != null">
            较上期
            <span :style="{ color: deltaColor(s.deltaType), fontWeight: 600 }">
              {{ s.deltaType === 'up' ? '↑' : s.deltaType === 'down' ? '↓' : '→' }}
              {{ Math.abs(s.delta) }}{{ s.unit === '%' || s.unit === '元' ? '' : '%' }}
            </span>
          </template>
          <template v-else>{{ s.extra }}</template>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.kpi-grid {
  display: grid;
  gap: 14px;
  margin-bottom: 16px;
  grid-template-columns: repeat(4, 1fr);
  &.cols-2 { grid-template-columns: repeat(2, 1fr); }
  &.cols-3 { grid-template-columns: repeat(3, 1fr); }
  &.cols-4 { grid-template-columns: repeat(4, 1fr); }
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr) !important; }
}
.kpi-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  position: relative;
  overflow: hidden;
  &::after {
    content: '';
    position: absolute;
    right: -30px; top: -30px;
    width: 100px; height: 100px;
    border-radius: 50%;
    opacity: 0.12;
  }
  .ic {
    width: 44px; height: 44px;
    border-radius: var(--radius-md);
    display: grid; place-items: center;
    font-size: 22px;
    flex-shrink: 0;
  }
  .meta { flex: 1; min-width: 0; }
  .l {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 4px;
    .unit-hint { font-size: 10px; color: var(--color-text-tertiary); opacity: 0.6; }
  }
  .v {
    font-size: 24px; font-weight: 700;
    color: var(--color-text-primary);
    font-family: var(--font-family-mono);
    line-height: 1.1;
  }
  .d { font-size: 12px; color: var(--color-text-tertiary); margin-top: 4px; }

  &.tone-primary .ic { background: var(--color-primary-bg); color: var(--color-primary); }
  &.tone-primary::after { background: var(--color-primary); }
  &.tone-success .ic { background: var(--color-success-bg); color: var(--color-success); }
  &.tone-success::after { background: var(--color-success); }
  &.tone-warning .ic { background: var(--color-warning-bg); color: var(--color-warning); }
  &.tone-warning::after { background: var(--color-warning); }
  &.tone-danger .ic { background: var(--color-danger-bg); color: var(--color-danger); }
  &.tone-danger::after { background: var(--color-danger); }
  &.tone-info .ic { background: rgba(124, 58, 237, 0.12); color: #7C3AED; }
  &.tone-info::after { background: #7C3AED; }
}
</style>
