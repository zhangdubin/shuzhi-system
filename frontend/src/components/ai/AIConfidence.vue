<script setup lang="ts">
/**
 * AIConfidence · AI 置信度 chip（自动判断 high/mid/low）
 * 用法：<AIConfidence :value="row.confidence" />
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** 0-100 整数或 0-1 小数 */
  value: number
  /** 后缀，默认 % */
  suffix?: string
  /** 显示文本（默认根据 value 自动） */
  label?: string
}>(), { suffix: '%' })

const level = computed<'high' | 'mid' | 'low'>(() => {
  // 兼容 0-100 整数 / 0-1 小数
  const pct = props.value > 1 ? props.value : props.value * 100
  if (pct >= 90) return 'high'
  if (pct >= 70) return 'mid'
  return 'low'
})

const display = computed(() => {
  if (props.label !== undefined) return props.label
  const pct = props.value > 1 ? props.value : props.value * 100
  return `${Math.round(pct)}${props.suffix}`
})
</script>

<template>
  <span :class="['ai-confidence', level]">{{ display }}</span>
</template>
