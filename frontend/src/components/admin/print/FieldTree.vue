<!--
  FieldTree · 字段树组件 (M3 阶段 5 数据绑定 UI)
  - 显示字段树结构
  - 支持搜索过滤
  - 点击字段 emit select 事件
-->
<template>
  <div class="field-tree">
    <el-input
      v-model="searchText"
      placeholder="搜索字段..."
      clearable
      size="small"
      class="search-input"
    />
    <div class="tree-container">
      <el-tree
        :data="filteredTree"
        :props="{ label: 'label', children: 'children' }"
        node-key="path"
        highlight-current
        default-expand-all
        :filter-node-method="filterNode"
        @node-click="onNodeClick"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <span class="node-icon">{{ getNodeIcon(data) }}</span>
            <span class="node-label">{{ data.label }}</span>
            <span class="node-type">{{ data.type }}</span>
          </div>
        </template>
      </el-tree>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldNode } from './fieldData'

const props = defineProps<{
  fields: FieldNode[]
}>()

const emit = defineEmits<{
  (e: 'select', path: string, type: string): void
}>()

const searchText = ref('')

const filteredTree = computed(() => {
  return props.fields
})

watch(searchText, (val) => {
  // el-tree 的 filter 会自动触发
})

function filterNode(value: string, data: FieldNode): boolean {
  if (!value) return true
  const search = value.toLowerCase()
  return (
    data.label.toLowerCase().includes(search) ||
    data.key.toLowerCase().includes(search) ||
    data.path.toLowerCase().includes(search)
  )
}

function getNodeIcon(data: FieldNode): string {
  if (data.children && data.children.length > 0) {
    return '📁'
  }
  switch (data.type) {
    case 'string':
      return '📝'
    case 'number':
      return '🔢'
    case 'date':
    case 'datetime':
      return '📅'
    case 'boolean':
      return '✅'
    default:
      return '📄'
  }
}

function onNodeClick(data: FieldNode) {
  if (data.children && data.children.length > 0) {
    // 点击父节点不触发选择
    return
  }
  emit('select', data.path, data.type)
}
</script>

<style scoped>
.field-tree {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.search-input {
  margin-bottom: 4px;
}

.tree-container {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 4px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  font-size: 13px;
}

.node-icon {
  font-size: 14px;
}

.node-label {
  flex: 1;
  color: #1F2937;
}

.node-type {
  font-size: 11px;
  color: #9CA3AF;
  font-family: 'SF Mono', monospace;
}

:deep(.el-tree-node__content) {
  height: 28px;
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background-color: #EEF2FF;
  color: #4F6BFF;
}
</style>
