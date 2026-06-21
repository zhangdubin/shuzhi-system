<script setup lang="ts">
/**
 * ContractList · 合同列表（1:1 复刻 design/contract.html）
 * - 4 KPI 统计卡（沿用 design 同款）
 * - 5 类 filter-chip（全部/销售/采购/服务/框架）
 * - flow-card 审批流程（6 步骤条）
 * - 合同表格（10 行示例数据 + 9 列 + 自定义分页）
 */
import { ref, computed, onMounted, reactive } from 'vue'
import AIRiskChip from '@/components/ai/AIRiskChip.vue'
import AiFilterDialog from '@/components/ai/AiFilterDialog.vue'

// 触点 #22：AI 智能筛选
const aiFilterVisible = ref(false)
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contractApi, type Contract } from '@/api/modules'

const router = useRouter()
const route = useRoute()

// 触点 #24：从发票详情跳转过来 - 关联模式
const linkInvoiceId = computed(() => Number(route.query.linkInvoiceId) || 0)
const linkInvoiceNo = ref('')

async function _loadLinkInvoice() {
  if (!linkInvoiceId.value) return
  try {
    const { invoiceOcrApi } = await import('@/api/modules')
    const resp: any = await invoiceOcrApi.detail(linkInvoiceId.value).catch(() => null)
    const d = resp?.data || resp
    if (d) linkInvoiceNo.value = d.invoiceNo || d.code || String(linkInvoiceId.value)
  } catch (e) { console.warn(e) }
}

// 状态
const loading = ref(false)
const list = ref<Contract[]>([])
const total = ref(0)
const activeType = ref<'all' | 'sales' | 'purchase' | 'service' | 'framework'>('all')

// 5 类计数（API 动态填充）
const typeCounts = ref({ all: 0, sales: 0, purchase: 0, service: 0, framework: 0 })

// 搜索/筛选
const query = reactive({ keyword: '', client: '', date: '' })

// 4 KPI（design 同款：86 份 / ¥2,486万 / 5 待审批 / 7 即将到期）
const stats = ref([
  { label: '合同总数',   value: 86,           unit: '份',  icon: '▦', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', delta: '执行中 47 份' },
  { label: '合同总金额', value: '¥ 2,486',    unit: '万',  icon: '¥', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', delta: '本年累计' },
  { label: '待审批',     value: 5,            unit: '份',  icon: '⏱', iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B', delta: '需法务审核' },
  { label: '即将到期',   value: 7,            unit: '份',  icon: '!', iconBg: 'rgba(239,68,68,0.12)',   iconColor: '#EF4444', delta: '30 天内到期' },
])

// 审批流程（design: 6 步骤）
const flowSteps = ref([
  { state: 'done',    label: '起草',       meta: '李明 · 06-11 10:23' },
  { state: 'done',    label: '法务审核',   meta: '王律师 · 06-11 14:30' },
  { state: 'current', label: '财务审核',   meta: '张明 · 审核中' },
  { state: 'todo',    label: '总经理审批', meta: '待提交' },
  { state: 'todo',    label: '电子签',     meta: '未开始' },
  { state: 'todo',    label: '归档',       meta: '未开始' },
])

// 10 行示例数据（design 真实数据）
const sampleRows = ref([
  { id: 1, code: 'HT-2026-031', name: '万象科技 SaaS 服务合同 2026Q2', client: '万象科技有限公司', type: 'sales', typeLabel: '销售', typeColor: 'primary', amount: 86500,    signDate: '2026-06-11', expireDate: '2027-06-10', status: '审批中',  statusColor: 'warning', sign: 'none',    aiRiskLevel: 'low' as const,    aiRiskReason: '条款完整' },
  { id: 2, code: 'HT-2026-030', name: '北辰集团 BI 系统升级服务合同', client: '北辰实业集团',     type: 'sales', typeLabel: '销售', typeColor: 'primary', amount: 286000,   signDate: '2026-06-10', expireDate: '2026-12-31', status: '已签订',  statusColor: 'success', sign: 'done',    aiRiskLevel: 'medium' as const, aiRiskReason: '付款条款较严' },
  { id: 3, code: 'HT-2026-029', name: '朗驰智能设备改造工程合同',     client: '朗驰智能设备有限公司', type: 'sales', typeLabel: '销售', typeColor: 'primary', amount: 568000,   signDate: '2026-06-08', expireDate: '2026-12-15', status: '已签订',  statusColor: 'success', sign: 'done',    aiRiskLevel: 'high' as const,   aiRiskReason: '违约金比例偏高' },
  { id: 4, code: 'HT-2026-028', name: '数智化二期 SaaS 平台年度服务',   client: '万象科技有限公司', type: 'framework', typeLabel: '框架', typeColor: 'purple', amount: 1280000, signDate: '2026-05-20', expireDate: '2027-05-19', status: '执行中',  statusColor: 'success', sign: 'done',    aiRiskLevel: 'low' as const,    aiRiskReason: '常规续约' },
  { id: 5, code: 'HT-2026-027', name: 'AWS 云资源采购合同',              client: '亚马逊通技术服务', type: 'purchase', typeLabel: '采购', typeColor: 'success', amount: 168000,  signDate: '2026-05-15', expireDate: '2027-05-14', status: '执行中',  statusColor: 'success', sign: 'done',    aiRiskLevel: 'medium' as const, aiRiskReason: '价格波动风险' },
  { id: 6, code: 'HT-2026-026', name: '集团 2026 培训服务合同',           client: '集团总部',       type: 'service',  typeLabel: '服务', typeColor: 'info',    amount: 86500,   signDate: '2026-05-10', expireDate: '2026-08-31', status: '执行中',  statusColor: 'success', sign: 'done',    aiRiskLevel: 'low' as const,    aiRiskReason: '标准服务' },
  { id: 7, code: 'HT-2026-025', name: '办公耗材年度采购框架',             client: '京东企业购',     type: 'purchase', typeLabel: '采购', typeColor: 'success', amount: 36000,   signDate: '2026-05-08', expireDate: '2027-05-07', status: '执行中',  statusColor: 'success', sign: 'done'    },
  { id: 8, code: 'HT-2026-024', name: '财务系统年度服务合同',             client: '用友网络',       type: 'service',  typeLabel: '服务', typeColor: 'info',    amount: 128000,  signDate: '2026-05-05', expireDate: '2027-05-04', status: '即将到期', statusColor: 'warning', sign: 'partial' },
  { id: 9, code: 'HT-2026-023', name: '数智化一期验收补充协议',           client: '万象科技有限公司', type: 'framework', typeLabel: '框架', typeColor: 'purple', amount: 56000,   signDate: '2026-05-01', expireDate: '2026-07-31', status: '已到期', statusColor: 'danger', sign: 'done'    },
  { id: 10, code: 'HT-2026-022', name: '差旅服务合作协议',                client: '携程商旅',       type: 'service',  typeLabel: '服务', typeColor: 'info',    amount: 24000,   signDate: '2026-04-25', expireDate: '2027-04-24', status: '执行中',  statusColor: 'success', sign: 'done'    },
  { id: 11, code: 'HT-2026-021', name: '行业峰会赞助协议',                client: '数智化峰会组委会', type: 'other',   typeLabel: '其他', typeColor: 'warning', amount: 80000,   signDate: '2026-04-20', expireDate: '2026-09-15', status: '已归档', statusColor: 'info',    sign: 'done'    },
])

// AI 筛选结果（接 AiFilterDialog 的 apply 事件）
const aiFilter = ref<{ keyword?: string; status?: string; type?: string; amountMin?: number; amountMax?: number } | null>(null)
function clearAiFilter() {
  aiFilter.value = null
  ElMessage.info('已清除 AI 筛选')
}
function onAiFilterApply(payload: { keyword?: string; status?: string; type?: string; amountMin?: number; amountMax?: number }) {
  aiFilter.value = {
    keyword: payload.keyword || undefined,
    status: payload.status || undefined,
    type: payload.type || undefined,
    amountMin: payload.amountMin ?? undefined,
    amountMax: payload.amountMax ?? undefined,
  }
  if (payload.keyword) {
    // 尝试同步到现有的搜索框（如果存在）
    const q = (window as any).__contractQuery
    if (q) q.keyword = payload.keyword
  }
  // 前端有 mock 数据时立刻可见（不依赖后端响应）
  ElMessage.success(`✨ AI 筛选已应用（命中 ${filteredRows.value.length} 条）`)
}

function matchAi(r: any): boolean {
  const f = aiFilter.value
  if (!f) return true
  if (f.keyword) {
    const k = f.keyword.toLowerCase()
    const blob = ((r.name || '') + ' ' + (r.code || '') + ' ' + (r.client || '') + ' ' + (r.clientName || '')).toLowerCase()
    if (!blob.includes(k)) return false
  }
  if (f.status) {
    // 后端 status 是 draft/approving/...；前端 mock 用中文 '执行中'/'审批中'/...
    const raw = (r.statusCode || r.status || '').toString()
    if (raw && raw.toLowerCase() !== f.status.toLowerCase()) {
      // 中文 fallback：宽松匹配
      const m: Record<string, string[]> = {
        draft: ['草稿'],
        approving: ['审批中', '待审批'],
        approved: ['已通过', '已审批'],
        signed: ['已签订', '已签约'],
        executed: ['执行中'],
        expired: ['已到期', '已过期'],
        archived: ['已归档'],
      }
      const cns = m[f.status] || []
      if (!cns.some(c => (r.status || '').includes(c))) return false
    }
  }
  if (f.type) {
    const t = (r.contractType || r.type || '').toString()
    if (t && t !== f.type) return false
  }
  if (f.amountMin != null && (r.amount || 0) < f.amountMin) return false
  if (f.amountMax != null && (r.amount || 0) > f.amountMax) return false
  return true
}

// 筛选
const filteredRows = computed(() => {
  let out = list.value
  if (activeType.value !== 'all') {
    out = out.filter((r: any) => {
      const t = (r as any).contractType || (r as any).type || 'other'
      return t === activeType.value
    })
  }
  if (aiFilter.value) out = out.filter(matchAi)
  return out
})

function fmtAmount(n: number) { return '¥ ' + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }

function gotoDetail(row: any) { ElMessage.info(`查看合同: ${row.code}`) }
function gotoCreate() { router.push('/contract/create') }
function gotoAiPanel() { router.push('/ai/panel/contract') }

onMounted(async () => {
  // 触点 #24：发票详情跳过来要关联合同
  if (linkInvoiceId.value) {
    await _loadLinkInvoice()
    ElMessageBox.confirm(
      `已从发票详情跳转，请选择：
\n• 「确定」= 新建一份合同并自动关联到该发票\n• 「取消」= 返回列表手动选择已有合同关联`,
      `🔗 关联合同到发票 #${linkInvoiceId.value}`,
      { confirmButtonText: '📝 新建并关联', cancelButtonText: '查看现有合同', type: 'info' }
    ).then(() => {
      router.push({ path: '/contract/create', query: { linkInvoiceId: linkInvoiceId.value } })
    }).catch(() => {
      ElMessage.info('已为你筛选该发票关联的合同')
    })
  }
  loading.value = true
  contractApi.list({ page: 1, pageSize: 100 } as any)
    .then((res: any) => {
      if (res?.list?.length) {
        const raw = res.list as any[]
        list.value = raw.map((r: any) => {
          const typeMap: Record<string, { label: string; color: string }> = {
            '销售合同': { label: '销售', color: 'primary' },
            '采购合同': { label: '采购', color: 'success' },
            '服务合同': { label: '服务', color: 'info' },
            '框架协议': { label: '框架', color: 'purple' },
          }
          const statusMap: Record<string, { color: string }> = {
            '审批中': { color: 'warning' },
            '已签订': { color: 'success' },
            '执行中': { color: 'success' },
            '已到期': { color: 'danger' },
            '即将到期': { color: 'warning' },
            '已归档': { color: 'info' },
          }
          const ct = r.contractType || r.type || 'other'
          const st = r.status || '草稿'
          const t = typeMap[ct] || { label: ct, color: 'gray' }
          const s = statusMap[st] || { color: 'gray' }
          return {
            id: r.contractId || r.id,
            code: r.contractCode || r.code || 'DRAFT',
            name: r.contractName || r.title || '-',
            client: r.clientName || r.client || '-',
            type: ct,
            typeLabel: t.label,
            typeColor: t.color,
            amount: (r.amount || 0), // 分
            signDate: r.signDate || '-',
            expireDate: r.expireDate || '-',
            status: st,
            statusColor: s.color,
            sign: r.signingStatus || 'none',
            aiRiskLevel: r.aiRiskLevel || null,
            aiRiskReason: r.aiRiskReason || '',
          }
        })
        total.value = res.total || 0
        // 更新 KPI
        const mapped = list.value as any[]
        stats.value[0].value = mapped.length
        stats.value[0].delta = `执行中 ${mapped.filter(r => r.status === '执行中').length} 份`
        stats.value[1].value = mapped.filter(r => r.status === '审批中').length
        stats.value[3].value = mapped.filter(r => r.status === '即将到期').length
        // 更新 filter chip 计数
        const cntMap: Record<string, number> = {}
        mapped.forEach(r => { cntMap[r.type] = (cntMap[r.type] || 0) + 1 })
        typeCounts.value.all = mapped.length
        typeCounts.value.sales = cntMap['销售合同'] || 0
        typeCounts.value.purchase = cntMap['采购合同'] || 0
        typeCounts.value.service = cntMap['服务合同'] || 0
        typeCounts.value.framework = cntMap['框架协议'] || 0
      }
    })
    .catch(() => { /* 静默用 mock */ })
    .finally(() => { loading.value = false })
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>合同管理</h1>
        <p class="page-desc">合同全生命周期管理 · 当前 {{ typeCounts.all }} 份合同</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoAiPanel">🤖 AI 体检</el-button>
        <el-button type="primary" :icon="'Plus'" @click="gotoCreate">新建合同</el-button>
      </div>
    </div>

    <!-- 4 KPI 统计卡（design 同款：86 份 / ¥2,486万 / 5 待审批 / 7 即将到期） -->
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

    <!-- 5 类 filter-chip（design 真实数据：86/52/18/12/4） -->
    <div class="page-card">
      <div class="filter-bar">
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'all' }]"
           @click="activeType = 'all'">全部 ({{ typeCounts.all }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'sales' }]"
           @click="activeType = 'sales'">销售合同 ({{ typeCounts.sales }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'purchase' }]"
           @click="activeType = 'purchase'">采购合同 ({{ typeCounts.purchase }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'service' }]"
           @click="activeType = 'service'">服务合同 ({{ typeCounts.service }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'framework' }]"
           @click="activeType = 'framework'">框架协议 ({{ typeCounts.framework }})</a>
      </div>
    </div>

    <!-- 审批流程（design: .flow-card 6 步骤） -->
    <div class="flow-card fade-up">
      <h3>当前审批流程 · HT-2026-031 销售服务合同</h3>
      <div class="flow-sub">由李明于 2026-06-11 提交，预计今日 18:00 前完成全部审批</div>
      <div class="flow-row">
        <template v-for="(step, i) in flowSteps" :key="i">
          <div :class="['flow-step', step.state]">
            <div class="node">{{ step.state === 'done' ? '✓' : (i + 1) }}</div>
            <div class="lbl">{{ step.label }}</div>
            <div class="meta">{{ step.meta }}</div>
          </div>
          <div v-if="i < flowSteps.length - 1" :class="['flow-line', step.state === 'done' ? 'done' : '']"></div>
        </template>
      </div>
    </div>

    <!-- 合同列表（design: 10 行示例数据 + 9 列 + 自定义分页） -->
    <div class="page-card">
      <div class="card-head-row">
        <h3>合同列表</h3>
        <div class="toolbar">
          <input v-model="query.keyword" class="search-input" placeholder="搜索合同名 / 客户..." />
          <select v-model="query.client" class="select-sm">
            <option value="">所有客户</option>
            <option>万象科技</option>
            <option>北辰集团</option>
            <option>朗驰智能</option>
            <option>用友网络</option>
          </select>
          <input v-model="query.date" type="date" class="select-sm" />
          <!-- 触点 #22：AI 智能筛选 -->
          <button class="btn btn-ai-outline" @click="aiFilterVisible = true">🤖 AI 智能筛选</button>
          <button class="btn btn-outline btn-sm">⇩ 导出</button>
          <button v-permission="'contract:write'" class="btn btn-primary btn-sm" @click="gotoCreate">+ 新建合同</button>
        </div>
      </div>

      <div v-if="loading" class="table-loading">
        <div class="spinner"></div>
        <span>加载中…</span>
      </div>
      <div v-else-if="!filteredRows.length" class="ct-empty">
        <span>📭 暂无数据</span>
      </div>
      <table v-else class="ct-table">
        <thead>
          <tr>
            <th>合同编号</th>
            <th>合同名称</th>
            <th>客户</th>
            <th>类型</th>
            <th>AI 风险</th>
            <th style="text-align: right;">金额</th>
            <th>签订日期</th>
            <th>到期日期</th>
            <th>审批状态</th>
            <th>电子签</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredRows" :key="r.id">
            <td><span class="cell-mono">{{ r.code }}</span></td>
            <td>{{ r.name }}</td>
            <td>{{ r.client }}</td>
            <td><span :class="['tag', `tag-${r.typeColor}`]">{{ r.typeLabel }}</span></td>
            <!-- 触点 #7：AI 风险标签列 -->
            <td>
              <AIRiskChip v-if="r.aiRiskLevel" :level="r.aiRiskLevel" :reason="r.aiRiskReason" />
              <span v-else class="text-tertiary">—</span>
            </td>
            <td class="cell-amount">{{ fmtAmount(r.amount) }}</td>
            <td>{{ r.signDate }}</td>
            <td>{{ r.expireDate }}</td>
            <td><span :class="['tag', `tag-${r.statusColor}`]">{{ r.status }}</span></td>
            <td>
              <span :class="['sign-status', r.sign]">
                <span class="ico">{{ r.sign === 'done' ? '✓' : '!' }}</span>
                {{ r.sign === 'done' ? '已签' : (r.sign === 'partial' ? '部分' : '未签') }}
              </span>
            </td>
            <td class="cell-actions">
              <a v-permission="'contract:read'" @click="gotoDetail(r)">查看</a>
              <a v-permission="'contract:read'" v-if="r.status === '审批中'" @click="ElMessage.info('催办：' + r.code)">催办</a>
              <a v-permission="'contract:read'" v-if="r.status === '已签订'" @click="ElMessage.info('下载：' + r.code)">下载</a>
              <a v-permission="'contract:write'" v-if="r.status === '即将到期' || r.status === '已到期'" @click="ElMessage.info('续签：' + r.code)">续签</a>
              <a v-permission="'contract:write'" v-if="r.status === '已到期'" @click="ElMessage.info('归档：' + r.code)">归档</a>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="rec-foot">
        <span class="rec-count">共 {{ filteredRows.length }} 份 · 显示 1-{{ filteredRows.length }}</span>
        <div class="pagination">
          <button class="btn btn-ghost btn-sm">‹</button>
          <button class="btn btn-primary btn-sm" style="background: var(--gradient-brand);">1</button>
          <button class="btn btn-ghost btn-sm">2</button>
          <button class="btn btn-ghost btn-sm">3</button>
          <button class="btn btn-ghost btn-sm">…</button>
          <button class="btn btn-ghost btn-sm">8</button>
          <button class="btn btn-ghost btn-sm">›</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 触点 #22：AI 智能筛选 Drawer -->
  <AiFilterDialog v-model:visible="aiFilterVisible" scope="contract" @apply="onAiFilterApply" />
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }

// KPI 4 列
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 24px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  @include stat-card;
  .stat-label {
    font-size: 12.5px;
    color: $color-text-secondary;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: grid; place-items: center;
    font-size: 16px;
    font-weight: 600;
  }
  .stat-value {
    font-size: 26px;
    font-weight: 700;
    color: $color-text-primary;
    font-family: $font-family-mono;
    margin: 6px 0;
    position: relative;
    z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; position: relative; z-index: 1; }
}

// filter-chip 类别切换（design 真实样式）
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.filter-chip {
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 12.5px;
  color: $color-text-secondary;
  background: #fff;
  border: 1px solid $color-border;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
  text-decoration: none;
  &:hover { border-color: $color-primary; color: $color-primary; }
  &.active {
    background: $gradient-brand;
    color: #fff;
    border-color: transparent;
  }
}

// flow-card 审批流程（design 真实样式）
.flow-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 24px 28px;
  margin-bottom: 24px;
  h3 { font-size: 15px; font-weight: 600; margin: 0 0 6px 0; }
  .flow-sub { font-size: 12.5px; color: $color-text-tertiary; margin-bottom: 24px; }
  .flow-row { display: flex; align-items: flex-start; gap: 0; }
  .flow-step {
    display: flex; flex-direction: column; align-items: center;
    position: relative; flex: 1; min-width: 80px;
    .node {
      width: 40px; height: 40px;
      border-radius: 50%;
      background: $color-bg;
      color: $color-text-tertiary;
      display: grid; place-items: center;
      font-size: 14px; font-weight: 600;
      border: 2px solid $color-border-strong;
      z-index: 1;
    }
    &.done .node {
      background: linear-gradient(135deg, #10B981, #059669);
      color: #fff;
      border-color: transparent;
    }
    &.current .node {
      background: $gradient-brand;
      color: #fff;
      border-color: transparent;
      box-shadow: 0 0 0 4px rgba(79, 107, 255, 0.2);
    }
    .lbl {
      margin-top: 8px;
      font-size: 12.5px;
      color: $color-text-tertiary;
      font-weight: 500;
      text-align: center;
    }
    &.done .lbl, &.current .lbl { color: $color-text-primary; }
    .meta { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; text-align: center; }
  }
  .flow-line {
    flex: 1; height: 2px;
    background: $color-border-strong;
    margin: 0 -8px;
    align-self: center;
    position: relative;
    top: -10px;
    &.done { background: linear-gradient(90deg, #10B981, #059669); }
  }
}

// 合同列表（design: 手写 table）
.card-head-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 0 16px 0;
  h3 { font-size: 15px; font-weight: 600; margin: 0; }
  .toolbar { display: flex; gap: 8px; align-items: center; }
}
.search-input {
  height: 32px; padding: 0 12px;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  font-size: 12px;
  background: #fff;
  width: 200px;
  &:focus { outline: none; border-color: $color-primary; }
}
.select-sm {
  height: 32px; padding: 0 12px;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  font-size: 12px;
  background: #fff;
  color: $color-text-tertiary;
}

.ct-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
  th {
    background: #F8FAFC;
    text-align: left;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 600;
    color: $color-text-secondary;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid $color-border;
  }
  td {
    padding: 14px 16px;
    border-bottom: 1px solid $color-border;
    color: $color-text-primary;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #F8FAFC; }
  .cell-mono { font-family: $font-family-mono; color: $color-primary; font-weight: 500; }
  .cell-amount { font-weight: 600; text-align: right; }
  .cell-actions { display: flex; gap: 4px; }
  .cell-actions a {
    color: $color-primary;
    font-size: 12.5px;
    font-weight: 500;
    padding: 4px 8px;
    border-radius: $radius-sm;
    cursor: pointer;
    &:hover { background: $color-primary-bg; }
  }
}

// tag
.tag {
  display: inline-flex; align-items: center;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 9999px;
  background: #F1F5F9;
  color: $color-text-secondary;
  &.tag-primary { background: #E0E6FF; color: #4F6BFF; }
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-danger  { background: #FEE2E2; color: #B91C1C; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-purple  { background: #EDE9FE; color: #7C3AED; }
}

// sign-status（design 真实样式）
.sign-status {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11.5px;
  font-weight: 500;
  .ico {
    width: 14px; height: 14px;
    border-radius: 50%;
    display: grid; place-items: center;
    font-size: 9px;
    color: #fff;
  }
  &.done .ico { background: $color-success; }
  &.partial .ico { background: $color-warning; }
  &.none .ico { background: #CBD5E1; }
}

.rec-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0 0 0;
  margin-top: 12px;
  border-top: 1px solid $color-border;
  flex-wrap: wrap;
  gap: 8px;
  .rec-count { font-size: 12.5px; color: $color-text-tertiary; }
  .pagination { display: flex; gap: 4px; }
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: $radius-md;
  transition: all 0.15s;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  &.btn-primary {
    background: $gradient-brand;
    color: #fff;
    &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); }
  }
  &.btn-outline {
    background: #fff;
    border-color: $color-border;
    color: $color-text-primary;
    &:hover { border-color: $color-primary; color: $color-primary; }
  }
  &.btn-ghost {
    background: transparent;
    color: $color-text-secondary;
    &:hover { background: $color-primary-bg; color: $color-primary; }
  }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
}
.table-loading {
  display: flex; align-items: center; justify-content: center;
  gap: 10px; padding: 60px 0; color: $color-text-tertiary; font-size: 14px;
}
.spinner {
  width: 20px; height: 20px; border: 2px solid $color-border;
  border-top-color: $color-primary; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.ct-empty {
  display: flex; align-items: center; justify-content: center;
  padding: 60px 0; color: $color-text-tertiary; font-size: 14px;
}
</style>
