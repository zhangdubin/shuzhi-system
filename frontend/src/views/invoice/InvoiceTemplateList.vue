<script setup lang="ts">
/**
 * InvoiceTemplateList · 发票模板（1:1 复刻 design/invoice-template.html）
 * - 4 KPI（design 同款：12 / 186 / 9 / 42）
 * - 4 类 filter-chip（全部/差旅/办公/通用/自定义）
 * - tpl-card 卡片网格（3 列）：含 6 张模板示例
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { invoiceTemplateApi } from '@/api/modules'

onMounted(loadData)

const router = useRouter()

const activeCat = ref<string>('all')
const previewVisible = ref(false)
const previewTemplate = ref<any>(null)

// 4 KPI
const stats = ref([
  { label: '模板总数',     value: 12,  unit: '个', icon: '▣', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', delta: '本月新增 2 个' },
  { label: '本月使用次数', value: 186, unit: '次', icon: '⚡', iconBg: 'rgba(124,58,237,0.12)',  iconColor: '#7C3AED', delta: '较上月 ↑ 24%' },
  { label: '启用中',       value: 9,   unit: '个', icon: '✓', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', delta: '停用 3 个' },
  { label: '节省人工',     value: 42,  unit: '小时', icon: '⏱', iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B', delta: '本年累计' },
])

// 4 类 filter-chip
const cats = ref([
  { key: 'all',     label: '全部',   count: 12 },
  { key: 'travel',  label: '差旅',   count: 4 },
  { key: 'office',  label: '办公',   count: 3 },
  { key: 'general', label: '通用',   count: 3 },
  { key: 'custom',  label: '自定义', count: 2 },
])

// 6 张模板卡（design 真实数据）
const templates = ref([
  { id: 1, name: '差旅报销模板',   cat: 'travel',  catLabel: '差旅', icon: '✈', status: 'active',   creator: '管理员',  useCount: 86, fields: 12, color: 'info' },
  { id: 2, name: '办公用品模板',   cat: 'office',  catLabel: '办公', icon: '📎', status: 'active',   creator: '管理员',  useCount: 42, fields: 8,  color: 'primary' },
  { id: 3, name: '通用电子发票',   cat: 'general', catLabel: '通用', icon: '▤', status: 'active',   creator: '系统',    useCount: 28, fields: 10, color: 'success' },
  { id: 4, name: '餐饮服务模板',   cat: 'general', catLabel: '通用', icon: '🍴', status: 'active',   creator: '管理员',  useCount: 18, fields: 6,  color: 'warning' },
  { id: 5, name: '软件订阅模板',   cat: 'office',  catLabel: '办公', icon: '💻', status: 'inactive', creator: '管理员',  useCount: 0,  fields: 9,  color: 'info' },
  { id: 6, name: '客户接待模板',   cat: 'custom',  catLabel: '自定义', icon: '🤝', status: 'active', creator: '王芳',    useCount: 12, fields: 11, color: 'purple' },
])

const filtered = computed(() => {
  if (activeCat.value === 'all') return templates.value
  return templates.value.filter(t => t.cat === activeCat.value)
})

function gotoEdit(t: any) { router.push(`/invoice/template/${t.id}`) }
function gotoPreview(t: any) {
  previewTemplate.value = t
  previewVisible.value = true
}
function gotoCreate() { router.push('/invoice/template/create') }

// 真实加载我的模板列表（后端 + 本地 mock 合并）
async function loadData() {
  try {
    const r: any = await invoiceTemplateApi.list({ page: 1, pageSize: 50, filters: {} })
    const list: any[] = r?.list || r?.data?.list || []
    if (list.length === 0) return
    // 按后端返回填充
    templates.value = list.map((t: any) => {
      const catMap: Record<string, { label: string; color: string }> = {
        travel:   { label: '差旅',   color: 'info' },
        office:   { label: '办公',   color: 'primary' },
        general:  { label: '通用',   color: 'success' },
        custom:   { label: '自定义', color: 'purple' },
        catering: { label: '通用',   color: 'warning' },
        taxi:     { label: '交通',   color: 'info' },
        hotel:    { label: '住宿',   color: 'info' },
        training: { label: '培训',   color: 'info' },
        medical:  { label: '医疗',   color: 'info' },
      }
      const cat = t.category || 'custom'
      const cm = catMap[cat] || catMap.custom
      return {
        id: t.templateId || t.id,
        name: t.name,
        cat,
        catLabel: cm.label,
        icon: t.icon || '📄',
        status: t.status === 'enabled' ? 'active' : 'inactive',
        creator: t.creator?.name || '系统',
        useCount: t.usageCount || 0,
        fields: t.fieldCount || 0,
        color: cm.color,
      }
    })
    // 顶部 KPI 用列表派生（更真实）
    stats.value[0].value = list.length
    stats.value[2].value = list.filter((x: any) => x.status === 'enabled').length
    // cats 计数
    cats.value = [
      { key: 'all',     label: '全部',   count: list.length },
      { key: 'travel',  label: '差旅',   count: list.filter((x: any) => x.category === 'travel').length },
      { key: 'office',  label: '办公',   count: list.filter((x: any) => x.category === 'office').length },
      { key: 'general', label: '通用',   count: list.filter((x: any) => ['general','catering','taxi','hotel','training','medical'].includes(x.category)).length },
      { key: 'custom',  label: '自定义', count: list.filter((x: any) => !['travel','office','general','catering','taxi','hotel','training','medical'].includes(x.category)).length },
    ]
  } catch (e) {
    console.warn('loadData failed, keep mock:', e)
  }
}

async function duplicateTemplate(t: any) {
  try {
    await ElMessageBox.confirm(`确定复制模板「${t.name}」？复制后可在「我的模板」中找到。`, '复制模板', { type: 'info' })
  } catch { return }
  try {
    const r: any = await invoiceTemplateApi.duplicate(t.id)
    const newId = r?.templateId || r?.id || r?.data?.id
    ElMessage.success(`已复制「${t.name}」 → 跳转到编辑页`)
    if (newId) router.push(`/invoice/template/${newId}`)
    else loadData()
  } catch (e: any) {
    ElMessage.error('复制失败：' + (e?.message || '未知错误'))
  }
}

// 模板市场（公共模板库，一键导入到我的模板）
const marketVisible = ref(false)
const marketCategory = ref('all')
const marketTemplates = ref<any[]>([])

const marketCats = [
  { key: 'all',      label: '全部' },
  { key: 'travel',   label: '✈️ 差旅' },
  { key: 'office',   label: '🖇 办公' },
  { key: 'catering', label: '🍴 餐饮' },
  { key: 'taxi',     label: '🚕 交通' },
  { key: 'hotel',    label: '🏨 住宿' },
  { key: 'training', label: '📚 培训' },
  { key: 'medical',  label: '💊 医疗' },
]

function openMarket() {
  marketVisible.value = true
  // 公共模板 mock（系统预设，导入即用）
  marketTemplates.value = [
    { id: 'm1', name: '✈️ 国内差旅报销模板', cat: 'travel',   desc: '覆盖机票/火车票/住宿/餐补/市内交通，6 字段', fields: 6,  downloads: 234 },
    { id: 'm2', name: '🖇 办公用品采购模板', cat: 'office',   desc: '含发票号/品名/数量/单价/金额/供应商',         fields: 6,  downloads: 189 },
    { id: 'm3', name: '🍴 业务招待模板',     cat: 'catering', desc: '含客户/陪同人数/餐厅/金额/日期',             fields: 5,  downloads: 156 },
    { id: 'm4', name: '🚕 出租车票模板',     cat: 'taxi',     desc: '含上下车时间/起止地点/金额',                  fields: 5,  downloads: 142 },
    { id: 'm5', name: '🏨 酒店住宿模板',     cat: 'hotel',    desc: '含入住/离店日期/酒店/房型/金额',              fields: 5,  downloads: 128 },
    { id: 'm6', name: '📚 员工培训模板',     cat: 'training', desc: '含培训主题/机构/费用/发票号',                 fields: 4,  downloads: 96  },
    { id: 'm7', name: '💊 员工体检模板',     cat: 'medical',  desc: '含体检机构/项目/金额/发票号',                 fields: 4,  downloads: 67  },
  ]
}

const filteredMarket = computed(() => {
  if (marketCategory.value === 'all') return marketTemplates.value
  return marketTemplates.value.filter(t => t.cat === marketCategory.value)
})

// 按模板类别生产一套真实可用的字段定义（label/key/type/required/aiSupport 全对）
function buildMarketFields(cat: string): any[] {
  const map: Record<string, any[]> = {
    travel: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '价税合计', key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '税率',     key: 'taxRate',     type: 'rate',   required: false, aiSupport: true },
      { label: '税额',     key: 'taxAmount',   type: 'amount', required: false, aiSupport: true },
      { label: '不含税金额', key: 'amountExclTax', type: 'amount', required: false, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user',  required: true,  aiSupport: false },
      { label: '部门',     key: 'departmentId', type: 'text', required: false, aiSupport: false },
      { label: '差旅事由', key: 'travelPurpose', type: 'textarea', required: true, aiSupport: false },
    ],
    office: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '价税合计', key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '销售方',   key: 'sellerName',  type: 'text', required: true, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
      { label: '部门',     key: 'departmentId', type: 'text', required: false, aiSupport: false },
      { label: '关联项目', key: 'projectId',   type: 'ref', refType: 'project', required: false, aiSupport: false },
      { label: '费用类型', key: 'expenseType', type: 'text', required: false, aiSupport: false },
      { label: '备注',     key: 'remark',      type: 'textarea', required: false, aiSupport: false, full: true },
    ],
    catering: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '价税合计', key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '销售方',   key: 'sellerName',  type: 'text', required: true, aiSupport: true },
      { label: '客户名称', key: 'buyerName',   type: 'text', required: true, aiSupport: true },
      { label: '陪同人数', key: 'attendeeCount', type: 'text', required: false, aiSupport: false },
      { label: '餐厅',     key: 'restaurant',  type: 'text', required: false, aiSupport: false },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
      { label: '备注',     key: 'remark',      type: 'textarea', required: false, aiSupport: false, full: true },
    ],
    taxi: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '上车时间', key: 'pickupTime',  type: 'date', required: false, aiSupport: true },
      { label: '下车时间', key: 'dropoffTime', type: 'date', required: false, aiSupport: true },
      { label: '起止地点', key: 'route',       type: 'text', required: false, aiSupport: true },
      { label: '金额',     key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
    ],
    hotel: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '入住日期', key: 'checkInDate', type: 'date', required: true, aiSupport: true },
      { label: '离店日期', key: 'checkOutDate', type: 'date', required: true, aiSupport: true },
      { label: '酒店',     key: 'hotelName',   type: 'text', required: true, aiSupport: true },
      { label: '房型',     key: 'roomType',    type: 'text', required: false, aiSupport: true },
      { label: '金额',     key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
    ],
    training: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '培训主题', key: 'topic',       type: 'text', required: true, aiSupport: false },
      { label: '培训机构', key: 'org',         type: 'text', required: true, aiSupport: true },
      { label: '金额',     key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
    ],
    medical: [
      { label: '发票类型', key: 'invoiceType', type: 'text', required: true, aiSupport: true },
      { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, aiSupport: true },
      { label: '开票日期', key: 'issueDate',   type: 'date', required: true, aiSupport: true },
      { label: '体检机构', key: 'org',         type: 'text', required: true, aiSupport: true },
      { label: '体检项目', key: 'item',        type: 'text', required: false, aiSupport: true },
      { label: '金额',     key: 'totalAmount', type: 'amount', required: true, aiSupport: true },
      { label: '报销人',   key: 'reimburserId', type: 'user', required: true, aiSupport: false },
    ],
  }
  return map[cat] || map.travel
}

async function importFromMarket(m: any) {
  try {
    const cleanName = m.name.replace(/^[\u{1F000}-\u{1FFFF}]\s*/u, '')
    await invoiceTemplateApi.create({
      name: cleanName,
      category: m.cat,
      description: m.desc,
      defaultTaxRate: 6,
      icon: '✨',
      iconColors: '#4F6BFF,#7C3AED',
      fields: buildMarketFields(m.cat),
    } as any)
    ElMessage.success(`已导入「${cleanName}」到我的模板`)
    await loadData()
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message
    ElMessage.error('导入失败：' + (typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : '未知错误')))
  }
}


</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>发票模板</h1>
        <p class="page-desc">发票字段模板管理与复用 · 当前 {{ templates.length }} 个模板</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="openMarket">📦 模板市场</el-button>
        <el-button type="primary" :icon="'Plus'" @click="gotoCreate">新建模板</el-button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row fade-up">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-label">
          <span>{{ s.label }}</span>
          <span class="stat-icon" :style="{ background: s.iconBg, color: s.iconColor }">{{ s.icon }}</span>
        </div>
        <div class="stat-value">{{ s.value }} <span class="unit">{{ s.unit }}</span></div>
        <div class="stat-delta">{{ s.delta }}</div>
      </div>
    </div>

    <!-- 4 类 filter-chip -->
    <div class="page-card">
      <div class="filter-bar">
        <a v-for="t in cats" :key="t.key" href="javascript:void(0)"
           :class="['filter-chip', { active: activeCat === t.key }]"
           @click="activeCat = t.key">
          {{ t.label }} ({{ t.count }})
        </a>
      </div>
    </div>

    <!-- tpl-card 3 列 -->
    <div class="tpl-grid fade-up">
      <div v-for="t in filtered" :key="t.id" :class="['tpl-card', t.status]" @click="gotoEdit(t)">
        <div :class="['tpl-head', t.color]">
          <div class="tpl-icon">{{ t.icon }}</div>
          <div class="tpl-info">
            <h4 class="tpl-name">{{ t.name }}</h4>
            <span :class="['tpl-status', t.status]">{{ t.status === 'active' ? '启用中' : '已停用' }}</span>
          </div>
        </div>
        <div class="tpl-tags">
          <span :class="['tpl-tag', `tag-${t.color}`]">{{ t.catLabel }}</span>
          <span class="tpl-tag">📋 {{ t.fields }} 个字段</span>
        </div>
        <div class="tpl-stats">
          <div class="tpl-stat">
            <span class="l">使用次数</span>
            <span class="v">{{ t.useCount }}</span>
          </div>
          <div class="tpl-stat">
            <span class="l">创建人</span>
            <span class="v">{{ t.creator }}</span>
          </div>
        </div>
        <div class="tpl-actions">
          <button class="btn btn-outline btn-sm" @click.stop="gotoPreview(t)">👁 预览</button>
          <button class="btn btn-outline btn-sm" @click.stop="duplicateTemplate(t)">📋 复制</button>
          <button class="btn btn-primary btn-sm" @click.stop="gotoEdit(t)">✎ 编辑</button>
        </div>
        <div class="tpl-creator">{{ t.creator }} 创建</div>
      </div>
    </div>
  </div>

  <!-- 模板预览抽屉 -->
  <el-drawer
    v-model="previewVisible"
    :title="previewTemplate ? `👁 预览 · ${previewTemplate.name}` : '模板预览'"
    direction="rtl"
    size="560px"
  >
    <div v-if="previewTemplate" class="pv-wrap">
      <div class="pv-meta">
        <span class="pv-tag">{{ previewTemplate.catLabel }}</span>
        <span :class="['pv-status', previewTemplate.status]">{{ previewTemplate.status === 'active' ? '启用中' : '已停用' }}</span>
        <span class="pv-fields">📋 {{ previewTemplate.fields }} 个字段</span>
      </div>

      <div class="pv-canvas">
        <div class="pv-section">
          <div class="pv-title">📌 票面信息（OCR 自动识别）</div>
          <div class="pv-grid">
            <div class="pv-field"><span class="pv-l">发票类型</span><span class="pv-v">增值税电子普通发票</span><span class="ai-badge">AI</span></div>
            <div class="pv-field"><span class="pv-l">发票代码</span><span class="pv-v mono">011002600611</span><span class="ai-badge">AI</span></div>
            <div class="pv-field"><span class="pv-l">发票号码</span><span class="pv-v mono">25113300000012345678</span><span class="ai-badge">AI</span></div>
            <div class="pv-field"><span class="pv-l">开票日期</span><span class="pv-v">2026-06-08</span><span class="ai-badge">AI</span></div>
            <div class="pv-field"><span class="pv-l">销售方</span><span class="pv-v">上海数智信息技术有限公司</span><span class="ai-badge">AI</span></div>
            <div class="pv-field"><span class="pv-l">购买方</span><span class="pv-v">万象科技有限公司</span><span class="ai-badge">AI</span></div>
          </div>
        </div>

        <div class="pv-section">
          <div class="pv-title">💰 金额信息</div>
          <div class="pv-grid">
            <div class="pv-field"><span class="pv-l">价税合计</span><span class="pv-v amount">¥ 28,000.00</span></div>
            <div class="pv-field"><span class="pv-l">税率</span><span class="pv-v">6%</span></div>
            <div class="pv-field"><span class="pv-l">税额</span><span class="pv-v">¥ 1,584.91</span></div>
            <div class="pv-field"><span class="pv-l">不含税金额</span><span class="pv-v">¥ 26,415.09</span></div>
          </div>
        </div>

        <div class="pv-section">
          <div class="pv-title">📋 业务信息（人工填写）</div>
          <div class="pv-grid">
            <div class="pv-field"><span class="pv-l">报销人 <b class="req">*</b></span><span class="pv-v placeholder">请选择报销人</span></div>
            <div class="pv-field"><span class="pv-l">部门</span><span class="pv-v placeholder">请选择部门</span></div>
            <div class="pv-field"><span class="pv-l">关联合同</span><span class="pv-v placeholder">请选择合同</span></div>
            <div class="pv-field"><span class="pv-l">关联项目</span><span class="pv-v placeholder">请选择项目</span></div>
          </div>
        </div>
      </div>

      <div class="pv-footer">
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="gotoEdit(previewTemplate)">✎ 编辑模板</el-button>
      </div>
    </div>
  </el-drawer>

  <!-- 模板市场 -->
  <el-dialog v-model="marketVisible" title="📦 模板市场 · 公共模板库" width="820px" :close-on-click-modal="false" append-to-body>
    <p style="margin: 0 0 12px 0; color: #64748B; font-size: 13px">浏览系统预设的常用模板，点击「导入」即可添加到「我的模板」</p>
    <div class="market-cats">
      <a v-for="c in marketCats" :key="c.key" href="javascript:void(0)"
         :class="['market-cat', { active: marketCategory === c.key }]"
         @click="marketCategory = c.key">{{ c.label }}</a>
    </div>
    <div class="market-grid">
      <div v-for="m in filteredMarket" :key="m.id" class="market-card">
        <div class="mc-name">{{ m.name }}</div>
        <div class="mc-desc">{{ m.desc }}</div>
        <div class="mc-meta">
          <span class="mc-fields">📋 {{ m.fields }} 字段</span>
          <span class="mc-dl">⬇ {{ m.downloads }} 次使用</span>
        </div>
        <el-button type="primary" size="small" @click="importFromMarket(m)">导入</el-button>
      </div>
      <div v-if="!filteredMarket.length" class="empty-tip">该分类暂无模板</div>
    </div>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }

// 4 KPI
.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  @include stat-card;
  .stat-label {
    font-size: 12.5px; color: $color-text-secondary;
    display: flex; justify-content: space-between; align-items: center;
    position: relative; z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px; border-radius: 8px;
    display: grid; place-items: center; font-size: 16px; font-weight: 600;
  }
  .stat-value {
    font-size: 26px; font-weight: 700; color: $color-text-primary;
    font-family: $font-family-mono; margin: 6px 0;
    position: relative; z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; position: relative; z-index: 1; }
}

.filter-bar {
  display: flex; gap: 8px; flex-wrap: wrap; padding: 4px 0;
}
.filter-chip {
  padding: 6px 14px; border-radius: 9999px;
  font-size: 12.5px; color: $color-text-secondary;
  background: #fff; border: 1px solid $color-border;
  cursor: pointer; transition: all 0.15s; font-weight: 500;
  text-decoration: none;
  &:hover { border-color: $color-primary; color: $color-primary; }
  &.active { background: $gradient-brand; color: #fff; border-color: transparent; }
}

// tpl-grid 3 列卡片
.tpl-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
  @media (max-width: 700px)  { grid-template-columns: 1fr; }
}
.tpl-card {
  background: #fff;
  border-radius: $radius-lg;
  border: 1px solid $color-border;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-md;
  }
  &.inactive { opacity: 0.6; }
}
.tpl-head {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  background: $gradient-brand-soft;
  border-bottom: 1px solid $color-border;
  &.info    { background: rgba(79,107,255,0.08); }
  &.primary { background: rgba(79,107,255,0.08); }
  &.success { background: rgba(16,185,129,0.08); }
  &.warning { background: rgba(245,158,11,0.08); }
  &.purple  { background: rgba(124,58,237,0.08); }
  .tpl-icon {
    width: 48px; height: 48px;
    border-radius: 12px;
    background: #fff;
    display: grid; place-items: center;
    font-size: 22px;
    box-shadow: $shadow-sm;
  }
  .tpl-info { flex: 1; min-width: 0; }
  .tpl-name {
    font-size: 15px; font-weight: 600;
    color: $color-text-primary;
    margin: 0 0 4px 0;
  }
  .tpl-status {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 500;
    &.active   { background: rgba(16,185,129,0.15); color: #10B981; }
    &.inactive { background: $color-bg; color: $color-text-tertiary; }
  }
}
.tpl-tags {
  display: flex;
  gap: 6px;
  padding: 12px 20px;
  flex-wrap: wrap;
}
.tpl-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: $color-bg;
  color: $color-text-secondary;
  &.tag-primary { background: #E0E6FF; color: #4F6BFF; }
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-purple  { background: #FAE8FF; color: #86198F; }
}
.tpl-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 0 20px 12px;
  .tpl-stat {
    background: $color-bg;
    padding: 8px 12px;
    border-radius: 6px;
    text-align: center;
    .l { display: block; font-size: 11px; color: $color-text-tertiary; margin-bottom: 2px; }
    .v { display: block; font-size: 13px; font-weight: 600; color: $color-text-primary; font-family: $font-family-mono; }
  }
}
.tpl-actions {
  display: flex;
  gap: 8px;
  padding: 0 20px 12px;
  .btn { flex: 1; }
}
.tpl-creator {
  padding: 8px 20px;
  font-size: 11px;
  color: $color-text-tertiary;
  text-align: right;
  border-top: 1px solid $color-border;
}

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 4px; padding: 0 12px;
  font-size: 12px; font-weight: 500;
  border-radius: $radius-sm; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-sm { height: 28px; }
}

// 模板预览抽屉
.pv-wrap { padding: 0 4px; }
.pv-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid $color-border; }
.pv-tag { font-size: 12px; padding: 3px 10px; background: $color-primary-bg; color: $color-primary; border-radius: 9999px; font-weight: 500; }
.pv-status { font-size: 11px; padding: 2px 8px; border-radius: 9999px; background: rgba(16,185,129,0.1); color: #10B981; &.inactive { background: rgba(148,163,184,0.15); color: #94A3B8; } }
.pv-fields { font-size: 12px; color: $color-text-tertiary; margin-left: auto; }
.pv-canvas { background: #FCFCFD; border: 1.5px dashed $color-border-strong; border-radius: $radius-md; padding: 16px; }
.pv-section { margin-bottom: 16px; &:last-child { margin-bottom: 0; } }
.pv-title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid $color-border; }
.pv-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; @media (max-width: 480px) { grid-template-columns: 1fr; } }
.pv-field { display: flex; flex-direction: column; gap: 4px; padding: 8px 10px; background: #fff; border: 1px solid $color-border; border-radius: $radius-sm; }
.pv-l { font-size: 11.5px; color: $color-text-tertiary; .req { color: $color-danger; margin-left: 2px; } }
.pv-v { font-size: 12.5px; color: $color-text-primary; font-weight: 500; &.mono { font-family: $font-family-mono; font-size: 11.5px; } &.amount { color: $color-primary; font-weight: 600; } &.placeholder { color: #CBD5E1; font-style: italic; } }
.ai-badge { display: inline-block; width: fit-content; font-size: 9.5px; padding: 1px 5px; background: $gradient-brand; color: #fff; border-radius: 9999px; font-weight: 600; letter-spacing: 0.3px; margin-top: 2px; }
.pv-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 20px; margin-top: 20px; border-top: 1px solid $color-border; }
/* 模板市场 */
.market-cats { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.market-cat { padding: 4px 12px; font-size: 12px; border-radius: 9999px; background: #fff; border: 1px solid #E2E8F0; color: #64748B; cursor: pointer; transition: all 0.15s; }
.market-cat:hover { border-color: #4F6BFF; color: #4F6BFF; }
.market-cat.active { background: linear-gradient(135deg, #4F6BFF, #7C3AED); color: #fff; border-color: transparent; }
.market-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; max-height: 480px; overflow-y: auto; }
.market-card { padding: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; transition: all 0.15s; }
.market-card:hover { border-color: #4F6BFF; box-shadow: 0 4px 12px rgba(79,107,255,0.12); }
.mc-name { font-size: 14px; font-weight: 600; color: #0F172A; margin-bottom: 6px; }
.mc-desc { font-size: 12px; color: #64748B; margin-bottom: 10px; line-height: 1.5; }
.mc-meta { display: flex; gap: 12px; font-size: 11px; color: #94A3B8; margin-bottom: 10px; }
.empty-tip { text-align: center; color: #94A3B8; padding: 40px 0; grid-column: 1/-1; }
</style>
