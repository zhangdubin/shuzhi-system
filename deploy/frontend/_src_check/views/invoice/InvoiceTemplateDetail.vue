<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  invoiceTemplateApi,
  type InvoiceTemplate,
  type InvoiceTemplateField,
  type InvoiceFieldType,
} from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<InvoiceTemplate | null>(null)
const activeTab = ref<'basic' | 'fields' | 'preview' | 'usage'>('basic')

// 类型映射（展示用）
const FIELD_TYPE_LABEL: Record<InvoiceFieldType, string> = {
  text: '文本',
  number: '数字',
  date: '日期',
  select: '选择',
  textarea: '多行文本',
}

// 状态映射
const STATUS_TAG: Record<string, { type: string; label: string }> = {
  '启用中': { type: 'success', label: '启用中' },
  '待启用': { type: 'warning', label: '待启用' },
  '已停用': { type: 'info', label: '已停用' },
}

// 模拟详情数据（design 1:1 演示态）
const mockTemplate: InvoiceTemplate = {
  id: 1,
  code: 'TPL-TR-2026-001',
  name: '差旅报销模板',
  category: '差旅',
  description: '含机票/酒店/打车/餐补，自动汇总差旅报销明细。覆盖销售/技术/市场等高频差旅场景。',
  status: '启用中',
  createdBy: '张明',
  createdAt: '2026-05-12 10:23',
  updatedBy: '张明',
  updatedAt: '2026-06-10 14:08',
  fields: [
    { key: 'invoice_type', label: '发票类型', type: 'select', required: true, options: ['增值税电子普通发票', '增值税专用发票', '增值税电子专用发票'], order: 1 },
    { key: 'invoice_code', label: '发票代码', type: 'text', required: true, order: 2 },
    { key: 'invoice_no', label: '发票号码', type: 'text', required: true, order: 3 },
    { key: 'issue_date', label: '开票日期', type: 'date', required: true, order: 4 },
    { key: 'seller_name', label: '销售方名称', type: 'text', required: true, order: 5 },
    { key: 'buyer_name', label: '购买方名称', type: 'text', required: true, order: 6 },
    { key: 'total_amount', label: '价税合计', type: 'number', required: true, defaultValue: '0.00', order: 7 },
    { key: 'tax_rate', label: '税率', type: 'select', required: false, options: ['6%', '9%', '13%', '3%'], defaultValue: '6%', order: 8 },
    { key: 'tax_amount', label: '税额', type: 'number', required: false, defaultValue: '0.00', order: 9 },
    { key: 'amount_excl_tax', label: '不含税金额', type: 'number', required: false, defaultValue: '0.00', order: 10 },
    { key: 'reimburse_user', label: '报销人', type: 'text', required: true, order: 11 },
    { key: 'department', label: '部门', type: 'text', required: false, order: 12 },
    { key: 'remark', label: '备注', type: 'textarea', required: false, order: 13 },
  ],
}

// 模拟使用记录
const usageRecords = ref([
  { code: 'FP-2026-Q2-031', amount: 18650.5, user: '陈思琪', at: '2026-06-11 16:23', status: '已入账' },
  { code: 'FP-2026-Q2-029', amount: 4220.0, user: '刘洋', at: '2026-06-10 09:45', status: '已入账' },
  { code: 'FP-2026-Q2-024', amount: 9870.0, user: '王芳', at: '2026-06-08 14:12', status: '已入账' },
  { code: 'FP-2026-Q2-018', amount: 5680.0, user: '李明', at: '2026-06-05 11:08', status: '已入账' },
  { code: 'FP-2026-Q2-012', amount: 12450.0, user: '张明', at: '2026-06-02 15:30', status: '已入账' },
])

// 按 order 排序后的字段
const sortedFields = computed<InvoiceTemplateField[]>(() => {
  if (!data.value?.fields) return []
  return [...data.value.fields].sort((a, b) => a.order - b.order)
})

// 必填字段数
const requiredCount = computed(() => sortedFields.value.filter(f => f.required).length)

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    // 优先拉真实接口；失败时用 mock 演示数据
    const r = await invoiceTemplateApi.detail(id).catch(() => null)
    data.value = r ?? mockTemplate
  } finally {
    loading.value = false
  }
}

function gotoBack() {
  router.push('/invoice/template')
}

function gotoEdit() {
  const id = route.params.id
  router.push(`/invoice/template/${id}/edit`)
}

async function handleCopy() {
  try {
    await ElMessageBox.confirm(
      `确定基于「${data.value?.name}」复制生成一份新模板吗？`,
      '复制模板',
      { type: 'info', confirmButtonText: '复制', cancelButtonText: '取消' }
    )
    ElMessage.success('已复制：' + (data.value?.name ?? '') + '（演示）')
  } catch {
    /* 用户取消 */
  }
}

function handleExport() {
  ElMessage.success('模板 JSON 已导出（演示）')
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
          / {{ data?.code }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          模板详情
          <span v-if="data?.status" :class="['tag', `tag-${STATUS_TAG[data.status]?.type || 'info'}`]">
            {{ STATUS_TAG[data.status!]?.label || data.status }}
          </span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="handleExport">导出 JSON</el-button>
        <el-button @click="handleCopy">⎘ 复制模板</el-button>
        <el-button type="primary" @click="gotoEdit">✎ 编辑模板</el-button>
      </div>
    </div>

    <!-- Hero -->
    <div class="detail-hero">
      <div class="dh-left">
        <div class="dh-id">{{ data?.code }}</div>
        <h2>{{ data?.name }}</h2>
        <div class="dh-meta">
          类别：<strong style="color: #fff">{{ data?.category }}</strong>
          · {{ sortedFields.length }} 个字段（必填 {{ requiredCount }}）
          · 创建于 {{ data?.createdAt }}
        </div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">使用次数</div>
        <div class="dh-amount">{{ usageRecords.length }}+</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">📋 基本信息</a>
      <a :class="{ active: activeTab === 'fields' }" @click="activeTab = 'fields'">🧩 字段配置（{{ sortedFields.length }}）</a>
      <a :class="{ active: activeTab === 'preview' }" @click="activeTab = 'preview'">👁 预览</a>
      <a :class="{ active: activeTab === 'usage' }" @click="activeTab = 'usage'">📈 使用记录（{{ usageRecords.length }}）</a>
    </div>

    <!-- 基本信息 -->
    <div v-if="activeTab === 'basic'" class="detail-section">
      <div class="detail-section-head">
        <h4>📋 模板基本信息</h4>
      </div>
      <div class="detail-section-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">模板编号</span><span class="v mono">{{ data?.code }}</span></div>
          <div class="info-row"><span class="l">模板名称</span><span class="v">{{ data?.name }}</span></div>
          <div class="info-row"><span class="l">类别</span><span class="v">{{ data?.category }}</span></div>
          <div class="info-row"><span class="l">状态</span><span class="v">
            <span v-if="data?.status" :class="['tag', `tag-${STATUS_TAG[data.status]?.type || 'info'}`]">
              {{ STATUS_TAG[data.status!]?.label || data.status }}
            </span>
          </span></div>
          <div class="info-row"><span class="l">字段数</span><span class="v">{{ sortedFields.length }} 个（必填 {{ requiredCount }}）</span></div>
          <div class="info-row"><span class="l">使用次数</span><span class="v">{{ usageRecords.length }}+</span></div>
          <div class="info-row"><span class="l">创建人</span><span class="v">{{ data?.createdBy }}</span></div>
          <div class="info-row"><span class="l">创建时间</span><span class="v mono">{{ data?.createdAt }}</span></div>
          <div class="info-row"><span class="l">更新人</span><span class="v">{{ data?.updatedBy }}</span></div>
          <div class="info-row"><span class="l">更新时间</span><span class="v mono">{{ data?.updatedAt }}</span></div>
          <div class="info-row full">
            <span class="l">描述</span>
            <div class="term-block">
              <div class="d">{{ data?.description || '—' }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 字段配置 -->
    <div v-if="activeTab === 'fields'" class="detail-section">
      <div class="detail-section-head">
        <h4>🧩 字段配置（{{ sortedFields.length }} 个字段，必填 {{ requiredCount }}）</h4>
        <div style="font-size: 12px; color: var(--color-text-tertiary)">按展示顺序展示，不可拖拽排序（如需调整请使用编辑器）</div>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="sortedFields" stripe row-class-name="field-row">
          <el-table-column prop="order" label="顺序" width="80" align="center">
            <template #default="{ row }">
              <span class="order-badge">{{ row.order }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="label" label="字段名" min-width="160" />
          <el-table-column label="字段标识" min-width="160">
            <template #default="{ row }">
              <span class="mono" style="font-size: 12.5px">{{ row.key }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="row.type === 'number' ? 'success' : row.type === 'date' ? 'warning' : row.type === 'select' ? 'primary' : 'info'">
                {{ FIELD_TYPE_LABEL[row.type as InvoiceFieldType] || row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="必填" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.required" size="small" type="danger">必填</el-tag>
              <span v-else style="color: var(--color-text-tertiary)">—</span>
            </template>
          </el-table-column>
          <el-table-column label="默认值 / 选项" min-width="200">
            <template #default="{ row }">
              <span v-if="row.type === 'select' && row.options?.length" style="font-size: 12px; color: var(--color-text-secondary)">
                {{ row.options.join(' / ') }}
              </span>
              <span v-else-if="row.defaultValue" class="mono" style="font-size: 12.5px">{{ row.defaultValue }}</span>
              <span v-else style="color: var(--color-text-tertiary)">—</span>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="该模板暂无字段" />
          </template>
        </el-table>
      </div>
    </div>

    <!-- 预览 -->
    <div v-if="activeTab === 'preview'" class="detail-section">
      <div class="detail-section-head">
        <h4>👁 模板预览（按字段配置渲染）</h4>
        <div style="font-size: 12px; color: var(--color-text-tertiary)">只读预览，实际录入页面将依据此配置生成</div>
      </div>
      <div class="detail-section-body">
        <el-form label-position="top" :model="{}" class="preview-form" disabled>
          <div v-for="(f, idx) in sortedFields" :key="f.key" class="preview-row">
            <el-form-item :label="`${f.label}${f.required ? ' *' : ''}`">
              <el-input
                v-if="f.type === 'text'"
                :placeholder="f.defaultValue || `请输入${f.label}`"
              />
              <el-input-number
                v-else-if="f.type === 'number'"
                :placeholder="f.defaultValue || `请输入${f.label}`"
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
                :placeholder="f.defaultValue || `请选择${f.label}`"
                style="width: 100%"
              >
                <el-option
                  v-for="opt in f.options"
                  :key="opt"
                  :label="opt"
                  :value="opt"
                />
              </el-select>
              <el-input
                v-else-if="f.type === 'textarea'"
                type="textarea"
                :rows="2"
                :placeholder="f.defaultValue || `请输入${f.label}`"
              />
            </el-form-item>
            <div v-if="(idx + 1) % 2 === 0" class="preview-row-clear"></div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 使用记录 -->
    <div v-if="activeTab === 'usage'" class="detail-section">
      <div class="detail-section-head">
        <h4>📈 使用记录（最近 {{ usageRecords.length }} 条）</h4>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="usageRecords" stripe>
          <el-table-column prop="code" label="单据号" width="180" />
          <el-table-column label="金额" width="140" align="right">
            <template #default="{ row }">
              <span class="mono">¥ {{ row.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="user" label="使用人" width="120" />
          <el-table-column prop="at" label="时间" min-width="180" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" type="success">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default>
              <el-button type="primary" link>查看</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无使用记录" />
          </template>
        </el-table>
      </div>
    </div>

    <!-- 底部 -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0">
      <el-button @click="gotoBack">← 返回列表</el-button>
      <div style="display: flex; gap: 8px">
        <el-button @click="handleCopy">⎘ 复制模板</el-button>
        <el-button type="primary" @click="gotoEdit">✎ 编辑模板</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

.detail-section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-badge {
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 600;
  font-family: $font-family-mono;
}

:deep(.field-row:hover) {
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
  }
  .preview-row-clear {
    grid-column: 1 / -1;
  }
}

// textarea 类型独占一行
:deep(.preview-form .preview-row:nth-last-child(1)) {
  grid-column: 1 / -1;
}
</style>
