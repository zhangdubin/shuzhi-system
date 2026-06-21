<script setup lang="ts">
/**
 * AIAlertBar · Dashboard 顶部 AI 提醒条
 * 用法：<AIAlertBar :alerts="alerts" :unread="3" @view-all="goToAlerts" />
 */
import { computed } from 'vue'

interface AlertItem {
  id: string
  level: 'high' | 'medium' | 'low'
  title: string
  objectType?: string
  objectId?: number
}

const props = withDefaults(defineProps<{
  /** 提醒列表（最多展示 2 条 + 提示更多） */
  alerts: AlertItem[]
  /** 未读数（顶部数字徽章） */
  unread?: number
  /** 自定义标题 */
  title?: string
  /** 自定义 "查看全部" 文案 */
  viewAllText?: string
}>(), {
  unread: 0,
  title: '今日 AI 提醒',
  viewAllText: '查看全部',
})

const hasAlerts = computed(() => props.alerts.length > 0)
const previewAlerts = computed(() => props.alerts.slice(0, 2))
const moreCount = computed(() => Math.max(0, props.alerts.length - 2))

defineEmits<{
  (e: 'view-all'): void
  (e: 'click-alert', alert: AlertItem): void
}>()
</script>

<template>
  <div v-if="hasAlerts" class="ai-alert-bar fade-up">
    <div class="ai-icon">✦</div>
    <div class="ai-body">
      <div class="ai-title-row">
        <span class="ai-badge">{{ title }}</span>
        <span class="text-tertiary">今日 <strong>{{ unread }}</strong> 条需要关注</span>
      </div>
      <div class="ai-summary">
        <div
          v-for="a in previewAlerts"
          :key="a.id"
          class="ai-summary-item"
          @click="$emit('click-alert', a)"
        >
          <AIRiskChip :level="a.level" />
          <span class="ai-summary-title">{{ a.title }}</span>
        </div>
        <span v-if="moreCount > 0" class="ai-summary-more">+{{ moreCount }} 更多</span>
      </div>
    </div>
    <div class="ai-actions">
      <button class="ai-btn-link" @click="$emit('view-all')">{{ viewAllText }} →</button>
    </div>
  </div>
</template>

<script lang="ts">
import AIRiskChip from './AIRiskChip.vue'
export default { components: { AIRiskChip } }
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

// AI 主题色（design 1:1）
$color-ai: #7C3AED;
$color-ai-2: #4F6BFF;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-bg: rgba(124, 58, 237, 0.05);
$color-ai-border: rgba(124, 58, 237, 0.2);

.ai-alert-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(79, 107, 255, 0.05) 100%);
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: $radius-lg;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: $gradient-ai;
  }
}
.ai-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: $gradient-ai;
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
}
.ai-body { flex: 1; min-width: 0; }
.ai-title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; font-size: 13px; color: $color-text-secondary; .text-tertiary { color: $color-text-tertiary; } strong { color: $color-text-primary; font-weight: 700; } }
.ai-badge { display: inline-block; padding: 2px 8px; background: $gradient-ai; color: #fff; border-radius: 9999px; font-size: 10.5px; font-weight: 600; }
.ai-summary { display: flex; flex-wrap: wrap; gap: 14px; font-size: 12.5px; }
.ai-summary-item { display: flex; align-items: center; gap: 6px; cursor: pointer; transition: opacity 0.15s; &:hover { opacity: 0.75; } }
.ai-summary-title { color: $color-text-primary; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-summary-more { color: $color-text-tertiary; font-size: 11.5px; padding: 1px 8px; background: $color-bg; border-radius: 9999px; }
.ai-actions { flex-shrink: 0; }
.ai-btn-link { background: transparent; border: 1px solid $color-ai-border; color: $color-ai; padding: 6px 14px; border-radius: $radius-md; font-size: 12.5px; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { background: $color-ai; color: #fff; } }
</style>
