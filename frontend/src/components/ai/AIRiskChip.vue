<script setup lang="ts">
/**
 * AIRiskChip · AI 风险评级 chip
 * 用法：<AIRiskChip :level="row.aiRiskLevel" />
 *       <AIRiskChip level="high" label="高风险" />
 */
import { computed } from 'vue'

type RiskLevel = 'high' | 'medium' | 'low' | 'unknown'

const props = withDefaults(defineProps<{
  level: RiskLevel
  /** 自定义 label（默认按 level 显示） */
  label?: string
  /** 是否显示圆点（默认 true） */
  showDot?: boolean
}>(), { showDot: true })

const displayLabel = computed(() => {
  if (props.label !== undefined) return props.label
  return { high: '高', medium: '中', low: '低', unknown: '未评' }[props.level] || '未评'
})

// 兼容 medium -> medium (中) / medium class
const cssLevel = computed(() => props.level === 'medium' ? 'medium' : props.level)
</script>

<template>
  <span :class="['ai-risk-chip', cssLevel]">
    <span v-if="showDot" class="dot"></span>
    {{ displayLabel }}
  </span>
</template>
