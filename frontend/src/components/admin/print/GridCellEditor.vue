<!--
  GridCellEditor · grid 单元格内容编辑器 (M3 阶段 6 嵌套 grid)
  - 弹窗内显示一个简化画布, 编辑单个 cell 的 children
  - 支持: title / text / spacer / line 组件
  - emit: update(children) → 更新 cell 的 children 数组
-->
<template>
  <el-dialog
    :model-value="modelValue"
    title="📝 编辑单元格内容"
    width="700px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="cell-editor">
      <div class="cell-toolbar">
        <span class="cell-info">
          行 {{ rowIndex + 1 }} · 列 {{ cellIndex + 1 }}
          <el-tag v-if="cell.span > 1" size="small" type="info">跨 {{ cell.span }} 列</el-tag>
        </span>
        <div class="cell-actions">
          <el-button size="small" @click="addComponent('text')">+ 文本</el-button>
          <el-button size="small" @click="addComponent('title')">+ 标题</el-button>
          <el-button size="small" @click="addComponent('spacer')">+ 间距</el-button>
          <el-button size="small" @click="addComponent('line')">+ 分割线</el-button>
        </div>
      </div>

      <div class="cell-canvas">
        <div v-if="localChildren.length === 0" class="cell-empty">
          <p>空单元格</p>
          <p class="muted">添加组件，或保持使用简单文本模式</p>
          <el-input
            v-model="simpleText"
            type="textarea"
            :rows="2"
            placeholder="输入简单文本（不使用嵌套组件时）"
            style="margin-top: 12px;"
          />
        </div>
        <div v-else>
          <div
            v-for="(comp, i) in localChildren"
            :key="comp.id || i"
            class="cell-item"
            :class="{ 'is-selected': selectedIndex === i }"
            @click="selectedIndex = i"
          >
            <span class="item-type">{{ findMeta(comp.type)?.icon || '?' }}</span>
            <span class="item-preview">
              {{ comp.text || comp.type }}
            </span>
            <div v-if="selectedIndex === i" class="item-tools">
              <el-button link size="small" :disabled="i === 0" @click.stop="moveItem(i, -1)">↑</el-button>
              <el-button link size="small" :disabled="i === localChildren.length - 1" @click.stop="moveItem(i, 1)">↓</el-button>
              <el-button link size="small" type="danger" @click.stop="removeItem(i)">✕</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 选中组件的属性编辑 -->
      <div v-if="selectedComp" class="cell-props">
        <el-form label-width="70px" size="small">
          <el-form-item v-if="selectedComp.type === 'text' || selectedComp.type === 'title'" label="文本">
            <el-input v-model="selectedComp.text" @input="onPropChange" />
          </el-form-item>
          <el-form-item v-if="selectedComp.type === 'text' || selectedComp.type === 'title'" label="字号">
            <el-input-number v-model="selectedComp.fontSize" :min="8" :max="36" @change="onPropChange" />
          </el-form-item>
          <el-form-item v-if="selectedComp.type === 'text' || selectedComp.type === 'title'" label="对齐">
            <el-radio-group v-model="selectedComp.align" @change="onPropChange">
              <el-radio-button value="left">左</el-radio-button>
              <el-radio-button value="center">中</el-radio-button>
              <el-radio-button value="right">右</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="selectedComp.type === 'spacer'" label="高度mm">
            <el-input-number v-model="selectedComp.height" :min="1" :max="50" @change="onPropChange" />
          </el-form-item>
          <el-form-item v-if="selectedComp.type === 'line'" label="颜色">
            <el-color-picker v-model="selectedComp.color" @change="onPropChange" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="confirmSave">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { findMeta, newCompId } from './compTemplates'

const props = defineProps<{
  modelValue: boolean
  cell: Record<string, any>
  rowIndex: number
  cellIndex: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'save', children: Record<string, any>[], simpleText: string): void
}>()

const localChildren = ref<Record<string, any>[]>([])
const selectedIndex = ref(-1)
const simpleText = ref('')

const selectedComp = computed(() => {
  if (selectedIndex.value < 0 || selectedIndex.value >= localChildren.value.length) return null
  return localChildren.value[selectedIndex.value]
})

watch(() => props.modelValue, (v) => {
  if (v) {
    // 初始化: 如果 cell 有 children 用 children, 否则用空
    localChildren.value = (props.cell.children || []).map((c: any) =>
      c.id ? c : { id: newCompId(), ...c }
    )
    simpleText.value = props.cell.text || ''
    selectedIndex.value = localChildren.value.length > 0 ? 0 : -1
  }
})

function addComponent(type: string) {
  const meta = findMeta(type)
  if (!meta) return
  const comp = { id: newCompId(), ...meta.default() }
  localChildren.value = [...localChildren.value, comp]
  selectedIndex.value = localChildren.value.length - 1
}

function removeItem(i: number) {
  const arr = [...localChildren.value]
  arr.splice(i, 1)
  localChildren.value = arr
  if (selectedIndex.value >= arr.length) selectedIndex.value = arr.length - 1
}

function moveItem(i: number, dir: number) {
  const newIdx = i + dir
  if (newIdx < 0 || newIdx >= localChildren.value.length) return
  const arr = [...localChildren.value]
  const [item] = arr.splice(i, 1)
  arr.splice(newIdx, 0, item)
  localChildren.value = arr
  selectedIndex.value = newIdx
}

function onPropChange() {
  // 触发响应式更新
  localChildren.value = [...localChildren.value]
}

function confirmSave() {
  // 剔除临时 id
  const children = localChildren.value.map(({ id, ...rest }) => rest)
  emit('save', children, simpleText.value)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.cell-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cell-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #F8FAFC;
  border-radius: 6px;
}
.cell-info {
  font-size: 13px;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 8px;
}
.cell-actions {
  display: flex;
  gap: 4px;
}
.cell-canvas {
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  padding: 12px;
  min-height: 120px;
  max-height: 300px;
  overflow-y: auto;
  background: #FAFBFC;
}
.cell-empty {
  text-align: center;
  color: #9CA3AF;
  padding: 16px;
}
.cell-empty p { margin: 0; font-size: 13px; }
.cell-empty .muted { font-size: 12px; margin-top: 4px; }
.cell-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #E5E7EB;
  border-radius: 4px;
  background: #FFFFFF;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.cell-item:hover { border-color: #4F6BFF; }
.cell-item.is-selected {
  border-color: #4F6BFF;
  background: #EEF2FF;
}
.item-type { font-size: 14px; width: 24px; text-align: center; }
.item-preview { flex: 1; font-size: 12px; color: #1F2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-tools { display: flex; gap: 2px; }
.cell-props {
  padding: 12px;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  background: #FFFFFF;
}
</style>
