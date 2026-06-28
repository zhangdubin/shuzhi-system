<!--
  PropertyPanel · 右侧属性面板 (M3 阶段 3 设计器 V1)
  - 接收 component: 当前选中的组件 (或 null)
  - emit: update  (修改后向上传, 由画布/JSON 同步)
  - 按 type 分支: title/text/spacer/line/grid/table/pagebreak
-->
<template>
  <div class="prop-panel">
    <div class="prop-header">
      <span class="prop-title">⚙ 属性</span>
      <span v-if="component" class="prop-type">{{ typeLabel }}</span>
    </div>
    <div v-if="!component" class="prop-empty">
      <div class="empty-icon">👈</div>
      <div class="empty-hint">点选画布上的组件<br />在这里修改属性</div>
    </div>
    <div v-else class="prop-form">
      <!-- 通用: 文本 -->
      <el-form v-if="hasText" label-width="80px" size="default">
        <el-form-item label="文本内容">
          <el-input
            :model-value="component.text"
            type="textarea"
            :rows="3"
            @update:model-value="(v: string) => update('text', v)"
          />
        </el-form-item>
      </el-form>

      <!-- 数据绑定 (M3 阶段 5) -->
      <el-form v-if="hasText" label-width="80px" size="default">
        <el-form-item label="数据绑定">
          <div class="bind-section">
            <!-- 字段树下拉 -->
            <el-popover trigger="click" width="300">
              <template #reference>
                <el-input
                  :model-value="currentBindPath"
                  placeholder="点击选择字段..."
                  readonly
                  size="small"
                />
              </template>
              <FieldTree
                :fields="fieldTree"
                @select="onFieldSelect"
              />
            </el-popover>
            
            <!-- Filter 选择 -->
            <el-select v-model="selectedFilter" placeholder="Filter" clearable size="small" style="width: 100px;">
              <el-option label="(无)" value="" />
              <el-option label="money" value="money" />
              <el-option label="chinese_money" value="chinese_money" />
              <el-option label="date" value="date" />
              <el-option label="datetime" value="datetime" />
            </el-select>
            
            <!-- 操作按钮 -->
            <el-button size="small" type="primary" @click="insertBinding">插入绑定</el-button>
            <el-button size="small" @click="insertStatic">插入静态</el-button>
          </div>
        </el-form-item>
      </el-form>

      <!-- title / text: 字号/对齐/颜色/加粗 -->
      <el-form v-if="isTextLike" label-width="80px" size="default">
        <el-form-item label="字号">
          <el-input-number
            :model-value="component.fontSize || 12"
            :min="8" :max="48"
            @update:model-value="(v: number) => update('fontSize', v)"
          />
        </el-form-item>
        <el-form-item label="对齐">
          <el-radio-group
            :model-value="component.align || 'left'"
            @update:model-value="(v: any) => update('align', v)"
          >
            <el-radio-button value="left">左</el-radio-button>
            <el-radio-button value="center">中</el-radio-button>
            <el-radio-button value="right">右</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="文字色">
          <el-color-picker
            :model-value="component.color || '#1F2937'"
            @update:model-value="(v: string) => update('color', v)"
          />
        </el-form-item>
        <el-form-item v-if="component.type === 'text'" label="加粗">
          <el-switch
            :model-value="!!component.bold"
            @update:model-value="(v: boolean) => update('bold', v)"
          />
        </el-form-item>
      </el-form>

      <!-- spacer: 高度 -->
      <el-form v-if="component.type === 'spacer'" label-width="80px" size="default">
        <el-form-item label="高度 (mm)">
          <el-input-number
            :model-value="component.height || 6"
            :min="1" :max="100"
            @update:model-value="(v: number) => update('height', v)"
          />
        </el-form-item>
      </el-form>

      <!-- line: 颜色 -->
      <el-form v-if="component.type === 'line'" label-width="80px" size="default">
        <el-form-item label="线条颜色">
          <el-color-picker
            :model-value="component.color || '#E5E7EB'"
            @update:model-value="(v: string) => update('color', v)"
          />
        </el-form-item>
      </el-form>

      <!-- grid: 列数/边框/边框色 -->
      <el-form v-if="component.type === 'grid'" label-width="80px" size="default">
        <el-form-item label="列数">
          <el-input-number
            :model-value="component.colCount || 4"
            :min="1" :max="12"
            @update:model-value="(v: number) => updateColCount(v)"
          />
        </el-form-item>
        <el-form-item label="行数">
          <span class="readonly-val">{{ (component.rows || []).length }}</span>
          <el-button size="small" link @click="addGridRow">+ 行</el-button>
          <el-button size="small" link :disabled="!component.rows || component.rows.length <= 1" @click="removeGridRow">- 行</el-button>
        </el-form-item>
        <el-form-item label="显示边框">
          <el-switch
            :model-value="component.border !== false"
            @update:model-value="(v: boolean) => update('border', v)"
          />
        </el-form-item>
        <el-form-item v-if="component.border !== false" label="边框色">
          <el-color-picker
            :model-value="component.borderColor || '#000000'"
            @update:model-value="(v: string) => update('borderColor', v)"
          />
        </el-form-item>
        <!-- 单元格网格 (可点击编辑) -->
        <el-form-item label="单元格">
          <div class="cell-grid">
            <div v-for="(row, ri) in (component.rows || [])" :key="ri" class="cell-row">
              <div
                v-for="(cell, ci) in (row.cells || [])"
                :key="ci"
                class="cell-chip"
                :class="{ 'has-children': cell.children && cell.children.length > 0 }"
                :style="{ flex: cell.span || 1 }"
                @click="emit('editCell', ri, ci)"
              >
                <span v-if="cell.children && cell.children.length > 0" class="chip-badge">{{ cell.children.length }}</span>
                <span class="chip-text">{{ cell.text || '空' }}</span>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <!-- table: bind / columns -->
      <el-form v-if="component.type === 'table'" label-width="80px" size="default">
        <el-form-item label="数据路径">
          <el-input
            :model-value="component.bind"
            placeholder="form.details"
            @update:model-value="(v: string) => update('bind', v)"
          />
        </el-form-item>
        <el-form-item label="列数">
          <span class="readonly-val">{{ (component.columns || []).length }}</span>
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon>
          提示: V1 列定义请用 JSON 模式编辑.
        </el-alert>
      </el-form>

      <!-- pagebreak: 无属性 -->
      <div v-if="component.type === 'pagebreak'" class="pagebreak-tip">
        ⤓ 强制分页符, 无需配置属性.
      </div>

      <!-- qrcode: data / size / label -->
      <el-form v-if="component.type === 'qrcode'" label-width="80px" size="default">
        <el-form-item label="数据">
          <el-input
            :model-value="component.data"
            placeholder="{{ form.code }}"
            @update:model-value="(v: string) => update('data', v)"
          />
        </el-form-item>
        <el-form-item label="尺寸">
          <el-input-number
            :model-value="component.size || 120"
            :min="60" :max="300"
            @update:model-value="(v: number) => update('size', v)"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input
            :model-value="component.label || ''"
            placeholder="扫码说明（可选）"
            @update:model-value="(v: string) => update('label', v)"
          />
        </el-form-item>
      </el-form>

      <!-- barcode: data / height / label -->
      <el-form v-if="component.type === 'barcode'" label-width="80px" size="default">
        <el-form-item label="数据">
          <el-input
            :model-value="component.data"
            placeholder="{{ form.formNo }}"
            @update:model-value="(v: string) => update('data', v)"
          />
        </el-form-item>
        <el-form-item label="条码高度">
          <el-input-number
            :model-value="component.height || 50"
            :min="30" :max="120"
            @update:model-value="(v: number) => update('height', v)"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input
            :model-value="component.label || ''"
            placeholder="条码说明（可选）"
            @update:model-value="(v: string) => update('label', v)"
          />
        </el-form-item>
      </el-form>

      <!-- 通用: id (临时) -->
      <el-form label-width="80px" size="default" class="id-form">
        <el-form-item label="临时 ID">
          <span class="readonly-val id-val">{{ component.id || '(无)' }}</span>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { findMeta } from './compTemplates'
import FieldTree from './FieldTree.vue'
import { getFieldTree, type FieldNode } from './fieldData'

const props = defineProps<{
  component: Record<string, any> | null
  docType?: string
}>()

const emit = defineEmits<{
  (e: 'update', key: string, value: any): void
  (e: 'editCell', rowIndex: number, cellIndex: number): void
}>()

// 数据绑定相关状态
const selectedFilter = ref('')
const currentBindPath = ref('')

// 获取字段树
const fieldTree = computed<FieldNode[]>(() => {
  return getFieldTree(props.docType || 'general')
})

// 字段选择回调
function onFieldSelect(path: string, type: string) {
  currentBindPath.value = path
}

// 插入绑定
function insertBinding() {
  if (!props.component || !currentBindPath.value) return
  let binding = `{{ ${currentBindPath.value} }}`
  if (selectedFilter.value) {
    binding = `{{ ${currentBindPath.value} | ${selectedFilter.value} }}`
  }
  // 在当前文本末尾插入
  const currentText = props.component.text || ''
  emit('update', 'text', currentText + binding)
}

// 插入静态文本
function insertStatic() {
  if (!props.component) return
  const currentText = props.component.text || ''
  emit('update', 'text', currentText + '文本')
}

const meta = computed(() => props.component ? findMeta(props.component.type) : null)
const typeLabel = computed(() => meta.value?.label || props.component?.type || '')

const hasText = computed(() => props.component && ['title', 'text', 'qrcode', 'barcode'].includes(props.component.type))
const isTextLike = computed(() => props.component && ['title', 'text'].includes(props.component.type))

function update(key: string, value: any) {
  emit('update', key, value)
}

function updateColCount(newCount: number) {
  emit('update', 'colCount', newCount)
}

function addGridRow() {
  if (!props.component) return
  const rows = [...(props.component.rows || [])]
  const colCount = props.component.colCount || 4
  rows.push({
    height: 12,
    cells: Array.from({ length: colCount }, (_, i) => ({ text: '', span: 1, align: 'left' as any })),
  })
  emit('update', 'rows', rows)
}

function removeGridRow() {
  if (!props.component) return
  const rows = [...(props.component.rows || [])]
  if (rows.length <= 1) return
  rows.pop()
  emit('update', 'rows', rows)
}
</script>

<style scoped>
.prop-panel {
  display: flex; flex-direction: column;
  height: 220px;
  min-height: 0;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  width: 100%;
  flex-shrink: 0;
  overflow: hidden;
}
.prop-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  background: #FAFBFC;
  border-bottom: 1px solid #F1F5F9;
}
.prop-title { font-size: 13px; font-weight: 600; color: #0F172A; }
.prop-type {
  font-size: 11px; padding: 2px 8px;
  background: #EEF2FF; color: #4F6BFF;
  border-radius: 10px;
  font-weight: 500;
}
.prop-empty {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #9CA3AF; gap: 8px;
  text-align: center; padding: 24px;
}
.empty-icon { font-size: 32px; opacity: 0.6; }
.empty-hint { font-size: 12px; line-height: 1.6; }
.prop-form {
  flex: 1; overflow-y: auto;
  padding: 16px;
}
.prop-form :deep(.el-form-item) { margin-bottom: 12px; }
.readonly-val { color: #475569; font-size: 12px; margin-right: 8px; }
.id-val { font-family: 'SF Mono', monospace; font-size: 11px; }
.id-form { margin-top: 16px; padding-top: 12px; border-top: 1px dashed #E5E7EB; }
.pagebreak-tip {
  padding: 16px;
  text-align: center;
  color: #DC2626;
  font-size: 12px;
  background: #FEF2F2;
  border-radius: 6px;
}

.bind-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.bind-section .el-select {
  width: 100px;
}

.bind-section .el-button {
  margin-left: 0;
}
.cell-grid {
  width: 100%;
  border: 1px solid #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
}
.cell-row {
  display: flex;
  border-bottom: 1px solid #E5E7EB;
}
.cell-row:last-child { border-bottom: none; }
.cell-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 8px;
  border-right: 1px solid #E5E7EB;
  cursor: pointer;
  font-size: 11px;
  color: #6B7280;
  transition: all 0.15s;
  position: relative;
  min-height: 28px;
}
.cell-chip:last-child { border-right: none; }
.cell-chip:hover { background: #EEF2FF; color: #4F6BFF; }
.cell-chip.has-children { background: #F0FDF4; color: #16A34A; }
.chip-badge {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 9px;
  background: #16A34A;
  color: white;
  border-radius: 50%;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chip-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60px;
}
</style>
