<!--
  ComponentPalette · 左侧组件库 (M3 阶段 3 设计器 V1)
  - 7 个组件可点击 / 拖拽 (拖拽 V1 只做点击插入)
  - 点击 → emit('add', meta)
-->
<template>
  <div class="palette">
    <div class="palette-title">📦 组件库</div>
    <div class="palette-hint">点击插入到画布</div>
    <div class="palette-grid">
      <div
        v-for="meta in COMP_PALETTE"
        :key="meta.type"
        class="palette-item"
        :title="meta.desc"
        @click="$emit('add', meta)"
        draggable="true"
        @dragstart="onDragStart($event, meta)"
      >
        <div class="palette-icon">{{ meta.icon }}</div>
        <div class="palette-label">{{ meta.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { COMP_PALETTE, type CompMeta } from './compTemplates'

defineEmits<{
  (e: 'add', meta: CompMeta): void
}>()

function onDragStart(e: DragEvent, meta: CompMeta) {
  e.dataTransfer?.setData('application/x-udpe-comp', meta.type)
  e.dataTransfer!.effectAllowed = 'copy'
}
</script>

<style scoped>
.palette {
  width: 140px;
  flex-shrink: 0;
  padding: 8px;
  border-right: 1px solid #F1F5F9;
  background: #FAFBFC;
  height: 100%;
  overflow-y: auto;
}
.palette-title {
  font-size: 13px; font-weight: 600; color: #0F172A;
  margin-bottom: 4px;
}
.palette-hint {
  font-size: 11px; color: #9CA3AF; margin-bottom: 12px;
}
.palette-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
}
.palette-item {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 10px 6px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.palette-item:hover {
  background: #EEF2FF;
  border-color: #4F6BFF;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(79,107,255,0.15);
}
.palette-icon { font-size: 18px; color: #4F6BFF; }
.palette-label { font-size: 12px; color: #334155; font-weight: 500; }
</style>
