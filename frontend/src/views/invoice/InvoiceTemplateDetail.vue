<script setup lang="ts">
/**
 * InvoiceTemplateDetail · 发票模板详情（无 design，按 R9 统一详情 pattern 自造）
 * - 顶部 detail-hero 蓝紫渐变（编号 + 名称 + 分类 + 状态 + 元信息 + 操作）
 * - 4 detail-tabs：基本信息 / 字段配置 / 使用记录 / 操作日志
 * - 左 detail-section 3 个（模板信息/关键字段统计/已绑定单据）
 * - 右 meta-card 4 个（当前状态/操作日志/版本信息/相关推荐）
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { invoiceTemplateApi, type InvoiceTemplate, type InvoiceTemplateField, type InvoiceFieldType } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<InvoiceTemplate | null>(null)
const activeTab = ref<'basic' | 'fields' | 'usage' | 'logs'>('basic')

const FIELD_TYPE_LABEL: Record<InvoiceFieldType, string> = {
  text: '文本',
  number: '数字',
  date: '日期',
  select: '选择',
  textarea: '多行文本',
}

const STATUS_TAG: Record<string, { type: string; label: string } | undefined> = {
  '启用中':   { type: 'success', label: '启用中' },
  'enabled':  { type: 'success', label: '启用中' },
  '待启用':   { type: 'warning', label: '待启用' },
  '已停用':   { type: 'info',    label: '已停用' },
  'disabled': { type: 'info',    label: '已停用' },
  '已停用': { type: 'info', label: '已停用' },
}

const mockTemplate: InvoiceTemplate = {
  id: 1,
  code: 'TPL-TR-2026-001',
  name: '差旅报销模板 v2.1',
  category: '差旅',
  description: '含机票/酒店/打车/餐补，自动汇总差旅报销明细。覆盖销售/技术/市场等高频差旅场景。新版增加票据类型 + 增值税识别号必填。',
  status: '启用中',
  createdBy: '张明',
  createdAt: '2026-05-12 10:23',
  updatedBy: '陈思琪',
  updatedAt: '2026-06-10 14:08',
  fields: [
    { key: 'invoice_type',     label: '发票类型',   type: 'select',   required: true,  options: ['增值税电子普通发票', '增值税专用发票', '增值税电子专用发票'], order: 1 },
    { key: 'invoice_code',     label: '发票代码',   type: 'text',     required: true,  order: 2 },
    { key: 'invoice_no',       label: '发票号码',   type: 'text',     required: true,  order: 3 },
    { key: 'issue_date',       label: '开票日期',   type: 'date',     required: true,  order: 4 },
    { key: 'seller_name',      label: '销售方名称', type: 'text',     required: true,  order: 5 },
    { key: 'buyer_name',       label: '购买方名称', type: 'text',     required: true,  order: 6 },
    { key: 'total_amount',     label: '价税合计',   type: 'number',   required: true,  defaultValue: '0.00', order: 7 },
    { key: 'tax_rate',         label: '税率',       type: 'select',   required: false, options: ['6%', '9%', '13%', '3%'], defaultValue: '6%', order: 8 },
    { key: 'tax_amount',       label: '税额',       type: 'number',   required: false, defaultValue: '0.00', order: 9 },
    { key: 'amount_excl_tax',  label: '不含税金额', type: 'number',   required: false, defaultValue: '0.00', order: 10 },
    { key: 'reimburse_user',   label: '报销人',     type: 'text',     required: true,  order: 11 },
    { key: 'department',       label: '部门',       type: 'text',     required: false, order: 12 },
    { key: 'remark',           label: '备注',       type: 'textarea', required: false, order: 13 },
  ],
}

const usageRecords = ref([
  { code: 'FP-2026-Q2-031', amount: 18650.5, user: '陈思琪', at: '2026-06-11 16:23', status: '已入账' },
  { code: 'FP-2026-Q2-029', amount: 4220.0,  user: '刘洋',   at: '2026-06-10 09:45', status: '已入账' },
  { code: 'FP-2026-Q2-024', amount: 9870.0,  user: '王芳',   at: '2026-06-08 14:12', status: '已入账' },
  { code: 'FP-2026-Q2-018', amount: 5680.0,  user: '李明',   at: '2026-06-05 11:08', status: '已入账' },
  { code: 'FP-2026-Q2-012', amount: 12450.0, user: '张明',   at: '2026-06-02 15:30', status: '已入账' },
  { code: 'FP-2026-Q2-008', amount: 3250.0,  user: '周雨',   at: '2026-05-30 10:15', status: '已入账' },
])

const opLogs = ref([
  { action: '更新模板',     user: '陈思琪', at: '2026-06-10 14:08', desc: '新增字段：增值税识别号' },
  { action: '发布新版 v2.1', user: '陈思琪', at: '2026-06-10 14:08', desc: '从 v2.0 升级到 v2.1' },
  { action: '停用',         user: '张明',   at: '2026-05-25 09:20', desc: '临时停用进行字段调整' },
  { action: '重新启用',     user: '张明',   at: '2026-05-12 11:00', desc: '字段调整完成，恢复启用' },
  { action: '创建模板',     user: '张明',   at: '2026-05-12 10:23', desc: '基于销售发票模板 v1.0 派生' },
])

const sortedFields = computed<InvoiceTemplateField[]>(() => {
  if (!data.value?.fields) return []
  return [...data.value.fields].sort((a, b) => a.order - b.order)
})
const requiredCount = computed(() => data.value?.fields?.filter(f => f.required).length || 0)
const fieldCount = computed(() => data.value?.fields?.length || 0)
const usageCount = computed(() => usageRecords.value.length)
const usageTotal = computed(() => usageRecords.value.reduce((s, r) => s + r.amount, 0))

const statusInfo = computed<{ type: string; label: string } | null>(() => {
  const v = data.value
  if (!v) return null
  const s = v.status || ''
  return STATUS_TAG[s] || { type: 'info', label: s || '未知' }
})

function goEdit() { router.push(`/invoice/template/${route.params.id}/edit`) }
function goBack() { router.push('/invoice/template') }
async function toggleTemplate() {
  if (!data.value) return
  const isEnabled = data.value.status === 'enabled' || data.value.status === '启用中'
  const action = isEnabled ? '停用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确认${action}模板「${data.value.name}」？${isEnabled ? '停用后此模板将不可用于新建发票。' : '启用后此模板可正常使用。'}`,
      `${action}模板`,
      { type: isEnabled ? 'warning' : 'info' }
    )
  } catch { return }
  try {
    const r: any = await invoiceTemplateApi.toggleStatus(data.value.templateId || data.value.id)
    const newStatus = r?.status || r?.data?.status
    if (newStatus) data.value = { ...data.value, status: newStatus }
    ElMessage.success(isEnabled ? '已停用' : '已启用')
  } catch (e: any) {
    ElMessage.error((isEnabled ? '停用' : '启用') + '失败：' + (e?.message || '未知错误'))
  }
}
function copyTemplate() { ElMessage.success('模板已复制为草稿') }

onMounted(() => {
  loading.value = true
  const id = Number(route.params.id) || 1
  invoiceTemplateApi.detail(id)
    .then((res) => { data.value = res })
    .catch(() => { data.value = mockTemplate })
    .finally(() => { loading.value = false })
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/invoice/template')">财务</a>
          <span class="sep">/</span>
          <a @click="router.push('/invoice/template')">发票模板</a>
          <span class="sep">/</span>
          <span class="current">{{ data?.name || '模板详情' }}</span>
        </div>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="goBack">← 返回</button>
        <button class="btn btn-outline btn-sm" @click="copyTemplate">📋 复制</button>
        <button
          v-if="data && (data.status === 'enabled' || data.status === '启用中')"
          class="btn btn-outline btn-sm"
          @click="toggleTemplate"
        >⏸ 停用</button>
        <button
          v-else-if="data"
          class="btn btn-outline btn-sm"
          @click="toggleTemplate"
        >▶ 启用</button>
        <button class="btn btn-primary btn-sm" @click="goEdit">✎ 编辑</button>
      </div>
    </div>

    <!-- detail-hero 蓝紫渐变 -->
    <div v-if="data" class="detail-hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-meta">
          <span class="hero-code">{{ data.code }}</span>
          <span class="hero-tag" :class="statusInfo?.type">{{ statusInfo?.label }}</span>
          <span class="hero-tag soft">{{ data.category }}</span>
        </div>
        <h1 class="hero-title">{{ data.name }}</h1>
        <p class="hero-desc">{{ data.description }}</p>
        <div class="hero-stats">
          <div class="stat">
            <div class="stat-num">{{ fieldCount }}</div>
            <div class="stat-lbl">字段总数</div>
          </div>
          <div class="stat">
            <div class="stat-num">{{ requiredCount }}</div>
            <div class="stat-lbl">必填字段</div>
          </div>
          <div class="stat">
            <div class="stat-num">{{ usageCount }}</div>
            <div class="stat-lbl">使用次数</div>
          </div>
          <div class="stat">
            <div class="stat-num">¥ {{ (usageTotal / 10000).toFixed(1) }}万</div>
            <div class="stat-lbl">累计入账</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 4 detail-tabs -->
    <div class="detail-tabs">
      <div :class="['tab', { active: activeTab === 'basic' }]" @click="activeTab = 'basic'">📋 基本信息</div>
      <div :class="['tab', { active: activeTab === 'fields' }]" @click="activeTab = 'fields'">🧩 字段配置 ({{ fieldCount }})</div>
      <div :class="['tab', { active: activeTab === 'usage' }]" @click="activeTab = 'usage'">📊 使用记录 ({{ usageCount }})</div>
      <div :class="['tab', { active: activeTab === 'logs' }]" @click="activeTab = 'logs'">📜 操作日志</div>
    </div>

    <div v-if="data" class="detail-grid">
      <!-- 左：detail-section 3 个 -->
      <div class="detail-left">
        <div v-show="activeTab === 'basic'" class="tab-pane">
          <div class="detail-section">
            <div class="section-title">📋 模板信息</div>
            <div class="info-grid">
              <div class="info-row"><span class="lbl">模板编号</span><span class="val mono">{{ data.code }}</span></div>
              <div class="info-row"><span class="lbl">模板名称</span><span class="val">{{ data.name }}</span></div>
              <div class="info-row"><span class="lbl">分类</span><span class="val">{{ data.category }}</span></div>
              <div class="info-row"><span class="lbl">状态</span><span class="val"><span :class="['tag', statusInfo?.type]">{{ statusInfo?.label }}</span></span></div>
              <div class="info-row full"><span class="lbl">描述</span><span class="val">{{ data.description }}</span></div>
              <div class="info-row"><span class="lbl">创建人</span><span class="val">{{ data.createdBy }}</span></div>
              <div class="info-row"><span class="lbl">创建时间</span><span class="val mono">{{ data.createdAt }}</span></div>
              <div class="info-row"><span class="lbl">最后修改</span><span class="val">{{ data.updatedBy }}</span></div>
              <div class="info-row"><span class="lbl">修改时间</span><span class="val mono">{{ data.updatedAt }}</span></div>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-title">📊 字段统计</div>
            <div class="field-stats">
              <div class="fs-item">
                <div class="fs-num">{{ fieldCount }}</div>
                <div class="fs-lbl">字段总数</div>
              </div>
              <div class="fs-item highlight">
                <div class="fs-num">{{ requiredCount }}</div>
                <div class="fs-lbl">必填字段</div>
              </div>
              <div class="fs-item">
                <div class="fs-num">{{ data.fields.filter(f => f.type === 'select').length }}</div>
                <div class="fs-lbl">选择类</div>
              </div>
              <div class="fs-item">
                <div class="fs-num">{{ data.fields.filter(f => f.type === 'textarea').length }}</div>
                <div class="fs-lbl">多行文本</div>
              </div>
            </div>
            <div class="type-distribution">
              <div v-for="(count, type) in {
                文本: data.fields.filter(f => f.type === 'text').length,
                数字: data.fields.filter(f => f.type === 'number').length,
                日期: data.fields.filter(f => f.type === 'date').length,
                选择: data.fields.filter(f => f.type === 'select').length,
                多行: data.fields.filter(f => f.type === 'textarea').length,
              }" :key="type" class="type-bar">
                <div class="type-name">{{ type }}</div>
                <div class="type-bar-bg">
                  <div class="type-bar-fill" :style="{ width: fieldCount ? (count / fieldCount * 100) + '%' : '0%' }"></div>
                </div>
                <div class="type-count">{{ count }}</div>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-title">🔗 已绑定单据</div>
            <div class="bind-list">
              <div class="bind-item">
                <div class="bind-icon">📝</div>
                <div class="bind-info">
                  <div class="bind-name">销售费用录入单</div>
                  <div class="bind-meta">EX-2026-* · 共 12 个字段</div>
                </div>
                <div class="bind-status">已绑定</div>
              </div>
              <div class="bind-item">
                <div class="bind-icon">📋</div>
                <div class="bind-info">
                  <div class="bind-name">费用报销单</div>
                  <div class="bind-meta">EXP-2026-* · 共 10 个字段</div>
                </div>
                <div class="bind-status">已绑定</div>
              </div>
              <div class="bind-item">
                <div class="bind-icon">📊</div>
                <div class="bind-info">
                  <div class="bind-name">差旅申请单</div>
                  <div class="bind-meta">TR-2026-* · 共 6 个字段</div>
                </div>
                <div class="bind-status">已绑定</div>
              </div>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'fields'" class="tab-pane">
          <div class="detail-section">
            <div class="section-title">🧩 字段配置（{{ fieldCount }} 个）</div>
            <table class="tpl-table">
              <thead>
                <tr>
                  <th style="width:50px;">序</th>
                  <th>字段标识</th>
                  <th>字段名</th>
                  <th>类型</th>
                  <th>必填</th>
                  <th>默认值</th>
                  <th>选项</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="f in sortedFields" :key="f.key">
                  <td><span class="cell-mono">{{ f.order }}</span></td>
                  <td><span class="cell-mono">{{ f.key }}</span></td>
                  <td>{{ f.label }}</td>
                  <td><span class="tag-pill soft">{{ FIELD_TYPE_LABEL[f.type] }}</span></td>
                  <td>
                    <span :class="['tag-pill', f.required ? 'danger' : 'info']">{{ f.required ? '是' : '否' }}</span>
                  </td>
                  <td><span class="cell-mono">{{ f.defaultValue || '—' }}</span></td>
                  <td>
                    <div v-if="f.options" class="options-list">
                      <span v-for="(o, i) in f.options" :key="i" class="opt-chip">{{ o }}</span>
                    </div>
                    <span v-else class="cell-mono">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-show="activeTab === 'usage'" class="tab-pane">
          <div class="detail-section">
            <div class="section-title">📊 使用记录（最近 {{ usageCount }} 条）</div>
            <table class="tpl-table">
              <thead>
                <tr>
                  <th>单据号</th>
                  <th>金额</th>
                  <th>使用人</th>
                  <th>时间</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in usageRecords" :key="i">
                  <td><span class="cell-mono">{{ r.code }}</span></td>
                  <td><span class="cell-amount">¥ {{ r.amount.toLocaleString() }}</span></td>
                  <td>{{ r.user }}</td>
                  <td><span class="cell-mono">{{ r.at }}</span></td>
                  <td><span class="tag-pill success">{{ r.status }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-show="activeTab === 'logs'" class="tab-pane">
          <div class="detail-section">
            <div class="section-title">📜 操作日志</div>
            <div class="timeline">
              <div v-for="(l, i) in opLogs" :key="i" class="tl-item">
                <div class="tl-dot"></div>
                <div class="tl-content">
                  <div class="tl-head">
                    <span class="tl-action">{{ l.action }}</span>
                    <span class="tl-user">by {{ l.user }}</span>
                    <span class="tl-time">{{ l.at }}</span>
                  </div>
                  <div class="tl-desc">{{ l.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：meta-card 4 个 -->
      <div class="detail-right">
        <div class="meta-card">
          <div class="m-title">📊 当前状态</div>
          <div class="status-row">
            <span :class="['tag', statusInfo?.type]">{{ statusInfo?.label }}</span>
            <span class="muted">·</span>
            <span class="muted">已发布 v2.1</span>
          </div>
          <div class="meta-rows">
            <div class="row"><span>使用次数</span><b>{{ usageCount }} 次</b></div>
            <div class="row"><span>累计金额</span><b>¥ {{ (usageTotal / 10000).toFixed(2) }} 万</b></div>
            <div class="row"><span>最近使用</span><b class="mono">{{ usageRecords[0]?.at || '—' }}</b></div>
            <div class="row"><span>平均入账</span><b>¥ {{ usageCount ? (usageTotal / usageCount).toFixed(0) : 0 }}</b></div>
          </div>
        </div>

        <div class="meta-card">
          <div class="m-title">📋 版本信息</div>
          <div class="meta-rows">
            <div class="row"><span>当前版本</span><b>v2.1</b></div>
            <div class="row"><span>上一版本</span><b>v2.0</b></div>
            <div class="row"><span>发布时间</span><b class="mono">2026-06-10</b></div>
            <div class="row"><span>升级说明</span><b>+1 字段</b></div>
          </div>
        </div>

        <div class="meta-card">
          <div class="m-title">🔗 快速操作</div>
          <div class="quick-actions">
            <button class="qa-btn" @click="goEdit">✎ 编辑模板</button>
            <button class="qa-btn" @click="copyTemplate">📋 复制为新模板</button>
            <button class="qa-btn" @click="router.push('/invoice/ocr')">🧪 试录入发票</button>
            <button class="qa-btn" @click="router.push('/invoice/template')">📚 查看所有模板</button>
          </div>
        </div>

        <div class="meta-card">
          <div class="m-title">💡 相关推荐</div>
          <div class="related">
            <div class="rel-item" @click="router.push('/invoice/template')">
              <div class="rel-icon">📋</div>
              <div class="rel-info">
                <div class="rel-name">办公报销模板</div>
                <div class="rel-meta">TPL-OF-2026-003 · 启用中</div>
              </div>
            </div>
            <div class="rel-item" @click="router.push('/invoice/template')">
              <div class="rel-icon">🍽</div>
              <div class="rel-info">
                <div class="rel-name">业务招待模板</div>
                <div class="rel-meta">TPL-BZ-2026-002 · 启用中</div>
              </div>
            </div>
            <div class="rel-item" @click="router.push('/invoice/template')">
              <div class="rel-icon">🏢</div>
              <div class="rel-info">
                <div class="rel-name">项目支出模板</div>
                <div class="rel-meta">TPL-PRJ-2026-001 · 启用中</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-actions { display: flex; gap: 8px; }

// detail-hero（蓝紫渐变 + 高对比度，stat 分组清晰）
.detail-hero {
  position: relative;
  border-radius: $radius-lg;
  padding: 28px 32px;
  margin-bottom: 16px;
  overflow: hidden;
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  color: #fff;
  box-shadow: 0 8px 24px -8px rgba(79,107,255,0.4);
}
.hero-bg { display: none; }
.hero-content { position: relative; z-index: 1; }
.hero-meta { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.hero-code { font-family: $font-family-mono; font-size: 12px; color: #fff; background: rgba(255,255,255,0.18); padding: 3px 10px; border-radius: $radius-sm; backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,0.2); }
.hero-tag { font-size: 12px; padding: 3px 10px; border-radius: 9999px; font-weight: 500; background: rgba(255,255,255,0.22); color: #fff; border: 1px solid rgba(255,255,255,0.25); }
.hero-tag.soft { background: rgba(255,255,255,0.22); color: #fff; }
.hero-tag.success { background: rgba(16,185,129,0.5); color: #fff; }
.hero-tag.warning { background: rgba(245,158,11,0.5); color: #fff; }
.hero-tag.info { background: rgba(255,255,255,0.22); color: #fff; }
.hero-title { font-size: 24px; font-weight: 700; color: #fff; margin: 0 0 8px 0; letter-spacing: 0.5px; line-height: 1.3; }
.hero-desc { color: rgba(255,255,255,0.85); font-size: 13px; line-height: 1.6; margin: 0 0 20px 0; max-width: 800px; }
.hero-stats { display: flex; gap: 48px; padding: 16px 20px; background: rgba(255,255,255,0.12); border-radius: $radius-md; border: 1px solid rgba(255,255,255,0.18); backdrop-filter: blur(6px); }
.hero-stats .stat { .stat-num { font-size: 26px; font-weight: 700; color: #fff; line-height: 1.2; letter-spacing: 0.5px; } .stat-lbl { font-size: 12px; color: rgba(255,255,255,0.75); margin-top: 4px; font-weight: 500; } }

// detail-tabs
.detail-tabs {
  display: flex; gap: 4px;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 4px;
  margin-bottom: 16px;
  overflow-x: auto;
}
.detail-tabs .tab {
  padding: 8px 16px;
  border-radius: $radius-md;
  font-size: 13px;
  color: $color-text-secondary;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  &:hover { color: $color-text-primary; background: $color-bg; }
  &.active { background: $color-primary-bg; color: $color-primary; font-weight: 500; }
}

// detail-grid
.detail-grid { display: grid; grid-template-columns: 1fr 320px; gap: 16px; @media (max-width: 1100px) { grid-template-columns: 1fr; } }
.detail-left { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.detail-right { display: flex; flex-direction: column; gap: 12px; }

// detail-section
.detail-section { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 20px; }
.section-title { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-bottom: 12px; }

.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px 24px; }
.info-row { display: flex; gap: 12px; font-size: 13px; padding: 4px 0; &.full { grid-column: 1 / -1; } .lbl { color: $color-text-tertiary; min-width: 72px; flex-shrink: 0; } .val { color: $color-text-primary; } .val.mono { font-family: $font-family-mono; font-size: 12.5px; } }

// field stats
.field-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.fs-item { text-align: center; padding: 12px 8px; background: $color-bg; border-radius: $radius-md; .fs-num { font-size: 20px; font-weight: 700; color: $color-text-primary; } .fs-lbl { font-size: 11.5px; color: $color-text-tertiary; margin-top: 4px; } &.highlight .fs-num { color: $color-primary; } }
.type-distribution { display: flex; flex-direction: column; gap: 6px; }
.type-bar { display: grid; grid-template-columns: 40px 1fr 30px; gap: 8px; align-items: center; font-size: 12px; .type-name { color: $color-text-tertiary; } .type-count { color: $color-text-primary; font-weight: 600; text-align: right; } }
.type-bar-bg { height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; }
.type-bar-fill { height: 100%; background: $gradient-brand; border-radius: 3px; transition: width 0.3s; }

// bind list
.bind-list { display: flex; flex-direction: column; gap: 8px; }
.bind-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: $color-bg; border-radius: $radius-md; }
.bind-icon { font-size: 20px; flex-shrink: 0; }
.bind-info { flex: 1; min-width: 0; .bind-name { font-size: 13px; font-weight: 500; color: $color-text-primary; } .bind-meta { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; font-family: $font-family-mono; } }
.bind-status { font-size: 11px; color: #10B981; background: rgba(16,185,129,0.1); padding: 2px 8px; border-radius: 9999px; }

// tpl table
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: $color-bg; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; }
.tpl-table td { padding: 10px 12px; border-bottom: 1px solid $color-border; color: $color-text-primary; }
.tpl-table tbody tr:hover { background: $color-bg; }
.cell-mono { font-family: $font-family-mono; font-size: 11.5px; color: $color-text-secondary; }
.cell-amount { font-family: $font-family-mono; color: $color-text-primary; font-weight: 600; }
.options-list { display: flex; flex-wrap: wrap; gap: 4px; }
.opt-chip { font-size: 10.5px; padding: 1px 6px; background: $color-primary-bg; color: $color-primary; border-radius: $radius-sm; font-family: $font-family-mono; }

// tag pill
.tag-pill { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag-pill.soft { background: $color-primary-bg; color: $color-primary; }
.tag-pill.success { background: rgba(16,185,129,0.1); color: #10B981; }
.tag-pill.danger { background: rgba(239,68,68,0.1); color: #EF4444; }
.tag-pill.info { background: rgba(148,163,184,0.15); color: #64748B; }

// timeline
.timeline { display: flex; flex-direction: column; gap: 0; padding-left: 12px; border-left: 2px dashed $color-border; }
.tl-item { position: relative; padding: 10px 0 10px 20px; }
.tl-dot { position: absolute; left: -7px; top: 14px; width: 12px; height: 12px; border-radius: 50%; background: $gradient-brand; box-shadow: 0 0 0 3px #fff; }
.tl-content { .tl-head { display: flex; align-items: center; gap: 8px; font-size: 13px; margin-bottom: 4px; .tl-action { font-weight: 600; color: $color-text-primary; } .tl-user { color: $color-text-tertiary; font-size: 12px; } .tl-time { color: $color-text-tertiary; font-size: 11.5px; margin-left: auto; font-family: $font-family-mono; } } .tl-desc { color: $color-text-secondary; font-size: 12.5px; } }

// meta-card
.meta-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 14px 16px; }
.m-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 10px; }
.status-row { display: flex; gap: 6px; align-items: center; margin-bottom: 10px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.success { background: rgba(16,185,129,0.1); color: #10B981; }
.tag.warning { background: rgba(245,158,11,0.1); color: #F59E0B; }
.tag.info { background: rgba(148,163,184,0.15); color: #64748B; }
.muted { color: $color-text-tertiary; font-size: 12px; }
.meta-rows { display: flex; flex-direction: column; gap: 6px; }
.meta-rows .row { display: flex; justify-content: space-between; font-size: 12.5px; color: $color-text-secondary; b { color: $color-text-primary; font-weight: 500; } b.mono { font-family: $font-family-mono; font-size: 11.5px; } }

.quick-actions { display: flex; flex-direction: column; gap: 6px; }
.qa-btn { padding: 8px 12px; text-align: left; font-size: 12.5px; background: $color-bg; border: 1px solid $color-border; border-radius: $radius-md; color: $color-text-primary; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-primary; color: $color-primary; background: $color-primary-bg; } }

.related { display: flex; flex-direction: column; gap: 6px; }
.rel-item { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: $radius-md; cursor: pointer; transition: all 0.15s; &:hover { background: $color-bg; } }
.rel-icon { font-size: 18px; flex-shrink: 0; }
.rel-info { flex: 1; min-width: 0; .rel-name { font-size: 12.5px; color: $color-text-primary; font-weight: 500; } .rel-meta { font-size: 11px; color: $color-text-tertiary; font-family: $font-family-mono; } }

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
}
</style>
