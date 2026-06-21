<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  invoiceTemplateApi,
  type InvoiceTemplate,
  type InvoiceTemplateField,
  type InvoiceFieldType,
  type InvoiceTemplateCategory,
} from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const isEdit = computed(() => route.name === 'InvoiceTemplateEdit' || !!route.params.id)

// 表单数据
const form = reactive({
  code: '',
  name: '',
  category: '差旅' as InvoiceTemplateCategory | string,
  description: '',
  fields: [] as InvoiceTemplateField[],
})

// 类型 / 类别选项
const FIELD_TYPE_OPTIONS: { value: InvoiceFieldType; label: string }[] = [
  { value: 'text', label: '文本' },
  { value: 'number', label: '数字' },
  { value: 'date', label: '日期' },
  { value: 'select', label: '选择' },
  { value: 'textarea', label: '多行文本' },
]

const CATEGORY_OPTIONS: { value: InvoiceTemplateCategory; label: string }[] = [
  { value: '差旅', label: '差旅' },
  { value: '办公', label: '办公' },
  { value: '招待', label: '招待' },
  { value: '其他', label: '其他' },
]

// 编辑器表单 ref（用于校验）
const formRef = ref()

// 简易规则
const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
}

// 唯一 id 计数器（用于动态行的 stable key）
let keySeed = 0
function uid() {
  keySeed += 1
  return `tmp_${Date.now()}_${keySeed}`
}

// 自动从 label 生成 snake_case 标识
function suggestKey(label: string): string {
  if (!label) return ''
  // 移除空格/标点，转拼音的简化版：直接用英文映射太重，这里给一个"标签简化"版本
  // 用户可在界面手动改
  const cleaned = label
    .replace(/[·・、，。；：""''《》【】\[\]()（）{}「」『』!?！？.,;:\'"<>?!/\-_]/g, '')
    .trim()
  if (!cleaned) return ''
  // 简易 pinyin 映射（不完整，仅给建议用）
  const map: Record<string, string> = {
    发: 'fa', 票: 'piao', 类: 'lei', 型: 'xing', 代: 'dai', 码: 'ma',
    号: 'hao', 开: 'kai', 具: 'ju', 日: 'ri', 期: 'qi', 销: 'xiao',
    售: 'shou', 方: 'fang', 名: 'ming', 称: 'cheng', 购: 'gou', 买: 'mai',
    价: 'jia', 税: 'shui', 合: 'he', 计: 'ji', 率: 'lv', 额: 'e',
    不: 'bu', 含: 'han', 金: 'jin', 报: 'bao', 人: 'ren',
    部: 'bu', 门: 'men', 备: 'bei', 注: 'zhu', 公: 'gong', 司: 'si',
    客: 'ke', 户: 'hu', 项: 'xiang', 目: 'mu', 单: 'dan',
  }
  let r = ''
  for (const ch of cleaned) r += map[ch] || ch
  return (r || cleaned).toLowerCase().replace(/\s+/g, '_').slice(0, 32)
}

// 初始化新行
function makeField(partial: Partial<InvoiceTemplateField> = {}): InvoiceTemplateField {
  const order = form.fields.length + 1
  return {
    key: partial.key || uid(),
    label: partial.label || '',
    type: partial.type || 'text',
    required: partial.required ?? false,
    defaultValue: partial.defaultValue || '',
    options: partial.options || [],
    order,
  }
}

// 监听 label 自动补 key（仅当 key 为空或与上次 suggest 一致时）
const lastSuggestMap = reactive<Record<string, string>>({})
watch(
  () => form.fields.map(f => ({ key: f.key, label: f.label })),
  (curr, prev) => {
    if (!prev) return
    for (let i = 0; i < curr.length; i++) {
      const cur = curr[i]
      const prevRow = prev[i]
      if (!cur) continue
      // label 变了，且 key 是空 或 key 与之前根据旧 label 建议的值一致 → 自动改
      if (cur.label !== prevRow?.label) {
        const last = lastSuggestMap[cur.key]
        if (!cur.key || cur.key === last) {
          const sug = suggestKey(cur.label)
          if (sug) {
            cur.key = sug
            lastSuggestMap[sug] = sug
          }
        }
        lastSuggestMap[cur.key] = suggestKey(cur.label)
      }
    }
  },
  { deep: true }
)

// 行操作
function addField() {
  form.fields.push(makeField())
}

function removeField(idx: number) {
  form.fields.splice(idx, 1)
  // 重新编号
  form.fields.forEach((f, i) => (f.order = i + 1))
}

function moveUp(idx: number) {
  if (idx <= 0) return
  const tmp = form.fields[idx - 1]
  form.fields[idx - 1] = form.fields[idx]
  form.fields[idx] = tmp
  form.fields.forEach((f, i) => (f.order = i + 1))
}

function moveDown(idx: number) {
  if (idx >= form.fields.length - 1) return
  const tmp = form.fields[idx + 1]
  form.fields[idx + 1] = form.fields[idx]
  form.fields[idx] = tmp
  form.fields.forEach((f, i) => (f.order = i + 1))
}

// options 文本与数组互转
function optionsText(f: InvoiceTemplateField): string {
  return (f.options || []).join('\n')
}
function setOptionsText(f: InvoiceTemplateField, text: string) {
  f.options = text
    .split(/[\n,，]/)
    .map(s => s.trim())
    .filter(Boolean)
}

// 类别切换时给字段顺序重新编号（保持）
// （不做特殊处理）

// 加载
async function load() {
  if (!isEdit.value) {
    // 新建：填默认值
    Object.assign(form, {
      code: '',
      name: '',
      category: '差旅',
      description: '',
      fields: [
        makeField({ label: '发票类型', type: 'select', required: true, options: ['增值税电子普通发票', '增值税专用发票'] }),
        makeField({ label: '发票代码', type: 'text', required: true }),
        makeField({ label: '发票号码', type: 'text', required: true }),
        makeField({ label: '开票日期', type: 'date', required: true }),
        makeField({ label: '价税合计', type: 'number', required: true }),
      ],
    })
    return
  }
  loading.value = true
  try {
    const id = Number(route.params.id)
    const r = await invoiceTemplateApi.detail(id).catch(() => null)
    if (r) {
      Object.assign(form, {
        code: r.code,
        name: r.name,
        category: r.category,
        description: r.description || '',
        fields: (r.fields || []).map((f, i) => ({ ...f, order: f.order || i + 1 })),
      })
    } else {
      // 拉不到时用 mock（演示态）
      Object.assign(form, {
        code: 'TPL-TR-2026-001',
        name: '差旅报销模板',
        category: '差旅',
        description: '含机票/酒店/打车/餐补，自动汇总差旅报销明细',
        fields: [
          makeField({ key: 'invoice_type', label: '发票类型', type: 'select', required: true, options: ['增值税电子普通发票', '增值税专用发票'] }),
          makeField({ key: 'invoice_code', label: '发票代码', type: 'text', required: true }),
          makeField({ key: 'invoice_no', label: '发票号码', type: 'text', required: true }),
          makeField({ key: 'issue_date', label: '开票日期', type: 'date', required: true }),
          makeField({ key: 'total_amount', label: '价税合计', type: 'number', required: true }),
        ],
      })
    }
  } finally {
    loading.value = false
  }
}

function gotoBack() {
  if (isEdit.value) {
    router.push(`/invoice/template/${route.params.id}`)
  } else {
    router.push('/invoice/template')
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('放弃本次编辑？已修改的内容将不会保存。', '提示', {
      type: 'warning',
      confirmButtonText: '放弃',
      cancelButtonText: '继续编辑',
    })
    gotoBack()
  } catch {
    /* 用户取消 */
  }
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    ElMessage.error('请补全必填项')
    return
  }
  if (form.fields.length === 0) {
    ElMessage.error('至少添加 1 个字段')
    return
  }
  // 校验：所有字段 label 必填
  for (const f of form.fields) {
    if (!f.label?.trim()) {
      ElMessage.error('每个字段都需要填写「字段名」')
      return
    }
    if (!f.key?.trim()) {
      ElMessage.error(`字段「${f.label}」需要填写「字段标识」`)
      return
    }
  }

  saving.value = true
  try {
    const payload: Partial<InvoiceTemplate> = {
      code: form.code,
      name: form.name,
      category: form.category,
      description: form.description,
      fields: form.fields,
    }
    if (isEdit.value) {
      await invoiceTemplateApi.update(Number(route.params.id), payload).catch(() => null)
      ElMessage.success('已保存（演示）')
      router.push(`/invoice/template/${route.params.id}`)
    } else {
      await invoiceTemplateApi.create(payload).catch(() => null)
      ElMessage.success('已创建（演示），返回列表')
      router.push('/invoice/template')
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/invoice/template" style="color: var(--color-text-tertiary)">发票模板</router-link>
          <template v-if="isEdit"> / <router-link :to="`/invoice/template/${route.params.id}`" style="color: var(--color-text-tertiary)">{{ form.code || '详情' }}</router-link> / 编辑</template>
          <template v-else> / 新建</template>
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          {{ isEdit ? '编辑模板' : '新建模板' }}
          <span class="tag tag-info">编辑器</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">✓ 保存模板</el-button>
      </div>
    </div>

    <!-- 基础信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📋 模板基本信息</h3>
        <span class="req">带 <span style="color: var(--color-danger)">*</span> 为必填</span>
      </div>
      <div class="fs-body">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <div class="form-row-3">
            <div class="field">
              <label>模板名称 <span class="req">*</span></label>
              <el-input v-model="form.name" placeholder="如：差旅报销模板" maxlength="50" show-word-limit />
            </div>
            <div class="field">
              <label>模板编号</label>
              <el-input v-model="form.code" placeholder="新建时自动生成" :disabled="isEdit" />
            </div>
            <div class="field">
              <label>类别 <span class="req">*</span></label>
              <el-select v-model="form.category" placeholder="请选择类别" style="width: 100%">
                <el-option v-for="c in CATEGORY_OPTIONS" :key="c.value" :label="c.label" :value="c.value" />
              </el-select>
            </div>
            <div class="field" style="grid-column: 1 / 3">
              <label>描述</label>
              <el-input v-model="form.description" placeholder="简要说明本模板的使用场景" maxlength="200" show-word-limit />
            </div>
            <div class="field">
              <label>状态</label>
              <el-tag type="success" effect="plain">保存后默认为「启用中」</el-tag>
            </div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 字段配置 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🧩 字段配置（{{ form.fields.length }} 个字段，必填 {{ form.fields.filter(f => f.required).length }}）</h3>
        <el-button type="primary" size="small" @click="addField">+ 添加字段</el-button>
      </div>
      <div class="fs-body" style="padding: 0">
        <el-table :data="form.fields" row-class-name="edit-field-row" :row-style="() => ({} as any)">
          <el-table-column label="顺序" width="64" align="center">
            <template #default="{ $index }">
              <div class="order-controls">
                <button :disabled="$index === 0" @click="moveUp($index)" title="上移">▲</button>
                <span class="order-num">{{ $index + 1 }}</span>
                <button :disabled="$index === form.fields.length - 1" @click="moveDown($index)" title="下移">▼</button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="字段名" min-width="140">
            <template #default="{ row }">
              <el-input v-model="row.label" placeholder="如：发票类型" size="small" maxlength="20" />
            </template>
          </el-table-column>
          <el-table-column label="字段标识" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.key" placeholder="如：invoice_type" size="small" maxlength="32" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="130">
            <template #default="{ row }">
              <el-select v-model="row.type" size="small" style="width: 100%">
                <el-option v-for="t in FIELD_TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="必填" width="80" align="center">
            <template #default="{ row }">
              <el-switch v-model="row.required" />
            </template>
          </el-table-column>
          <el-table-column :label="form.fields.some(f => f.type === 'select') ? '默认值 / 选项' : '默认值'" min-width="220">
            <template #default="{ row }">
              <template v-if="(row as InvoiceTemplateField).type === 'select'">
                <el-input
                  :model-value="optionsText(row as InvoiceTemplateField)"
                  @update:model-value="(v: string) => setOptionsText(row as InvoiceTemplateField, v)"
                  type="textarea"
                  :rows="2"
                  size="small"
                  placeholder="每行一个选项"
                />
              </template>
              <template v-else>
                <el-input v-model="row.defaultValue" placeholder="可选" size="small" />
              </template>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center" fixed="right">
            <template #default="{ $index }">
              <el-button type="danger" link @click="removeField($index)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无字段，点击右上角「+ 添加字段」开始配置">
              <el-button type="primary" @click="addField">+ 添加字段</el-button>
            </el-empty>
          </template>
        </el-table>
      </div>
    </div>

    <!-- 实时预览 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>👁 实时预览</h3>
        <span class="req">保存后用户录入页面将依据此配置生成</span>
      </div>
      <div class="fs-body">
        <div v-if="form.fields.length === 0" class="empty-preview">
          <el-empty description="请先在「字段配置」添加字段" />
        </div>
        <el-form v-else label-position="top" :model="{}" class="preview-form">
          <div v-for="(f, idx) in form.fields" :key="f.key + idx" class="preview-row" :class="{ 'full-row': f.type === 'textarea' }">
            <el-form-item :label="`${f.label || '未命名字段'}${f.required ? ' *' : ''}`">
              <el-input
                v-if="f.type === 'text'"
                :placeholder="f.defaultValue || `请输入${f.label || ''}`"
              />
              <el-input-number
                v-else-if="f.type === 'number'"
                :placeholder="f.defaultValue || `请输入${f.label || ''}`"
                :controls="false"
                style="width: 100%"
              />
              <el-date-picker
                v-else-if="f.type === 'date'"
                type="date"
                placeholder="选择日期"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
              <el-select
                v-else-if="f.type === 'select'"
                :placeholder="f.defaultValue || `请选择${f.label || ''}`"
                style="width: 100%"
              >
                <el-option
                  v-for="opt in f.options || []"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
              <el-input
                v-else-if="f.type === 'textarea'"
                type="textarea"
                :rows="2"
                :placeholder="f.defaultValue || `请输入${f.label || ''}`"
              />
            </el-form-item>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot" style="border-radius: 14px; margin-top: 20px">
      <div style="font-size: 12.5px; color: var(--color-text-tertiary)">
        修改后请及时保存；未保存的更改会在离开页面时丢失。
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">✓ 保存模板</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

// 顺序控制
.order-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  button {
    width: 20px;
    height: 18px;
    border: 1px solid var(--color-border);
    border-radius: 4px;
    background: #fff;
    color: var(--color-text-secondary);
    font-size: 9px;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    transition: all 0.15s;
    &:hover:not(:disabled) {
      background: var(--color-primary-bg);
      color: var(--color-primary);
      border-color: var(--color-primary);
    }
    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }
  .order-num {
    font-size: 11px;
    color: var(--color-text-tertiary);
    font-family: $font-family-mono;
  }
}

:deep(.edit-field-row:hover) {
  background: var(--color-primary-bg);
}

// 预览表单
.preview-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;

  .preview-row {
    :deep(.el-form-item) {
      margin-bottom: 14px;
    }
    &.full-row {
      grid-column: 1 / -1;
    }
  }
}

.empty-preview {
  padding: 20px;
  text-align: center;
}
</style>
