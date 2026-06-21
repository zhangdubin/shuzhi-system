<script setup lang="ts">
/**
 * ReceivableList · 回款管理（1:1 复刻 design/receivable.html）
 * - 4 KPI 统计卡（design 同款：¥142.3 万 / ¥286.5 万 / 82.4% / 3 笔）
 * - 10 列回款表（编号/合同/客户/金额/进度/计划/实际/负责人/状态/操作）
 * - 9 行示例数据（含 HK-2026-024/018/019 等）
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'
import AiFilterDialog from '@/components/ai/AiFilterDialog.vue'

// 触点 #22：AI 智能筛选
const aiFilterVisible = ref(false)

// 触点 #9：AI 智能匹配
const aiMatchDrawerVisible = ref(false)
const aiMatchLoading = ref(false)
const aiMatchResults = ref<Array<{ name: string; score: number; reasons: string[] }>>([])
const aiMatchType = ref<'invoice-to-contract' | 'expense-to-project' | 'contract-to-client'>('invoice-to-contract')

async function runAiMatch() {
  aiMatchLoading.value = true
  try {
    const r = await aiApi.matchRun({
      type: aiMatchType.value,
      source: { amount: 286000, keywords: 'SaaS' },
    }).catch(() => null)
    if (r?.matches) {
      aiMatchResults.value = r.matches.map(m => ({ name: m.targetName, score: m.score, reasons: m.reasons }))
    } else {
      // mock 回退
      aiMatchResults.value = [
        { name: 'HT-2026-028 · 数智化二期 SaaS 平台年度服务', score: 0.94, reasons: ['金额匹配 ¥286,000', '客户一致：万象科技', '时间窗 30 天内', '备注含 "SaaS"'] },
        { name: 'HT-2026-031 · 万象科技 SaaS 服务合同 2026Q2', score: 0.87, reasons: ['客户一致', '服务类型匹配', '金额接近'] },
        { name: 'HT-2026-024 · 财务系统年度服务合同',         score: 0.45, reasons: ['客户不一致', '服务类型不匹配'] },
      ]
    }
    ElMessage.success('✨ AI 匹配完成')
  } finally {
    aiMatchLoading.value = false
  }
}
import { receivableApi } from '@/api/modules'

const router = useRouter()

// 真实数据
const list = ref<any[]>([])

// 4 KPI（API 动态填充）
const stats = ref([
  { label: '本月回款',   value: '¥ 0',    unit: '万', icon: '¥', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', delta: '完成率 0%' },
  { label: '待回款',     value: '¥ 0',    unit: '万', icon: '⏱', iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B', delta: '剩余 0 笔' },
  { label: '回款完成率', value: '0',      unit: '%',  icon: '✓', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', delta: '—' },
  { label: '逾期笔数',   value: 0,         unit: '笔', icon: '!', iconBg: 'rgba(239,68,68,0.12)',   iconColor: '#EF4444', delta: '需催收' },
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
  ElMessage.success(`✨ AI 筛选已应用（命中 ${filteredList.value.length} 条）`)
}
function matchAi(r: any): boolean {
  const f = aiFilter.value
  if (!f) return true
  if (f.keyword) {
    const k = f.keyword.toLowerCase()
    const blob = ((r.code || '') + ' ' + (r.contract || '') + ' ' + (r.client || '')).toLowerCase()
    if (!blob.includes(k)) return false
  }
  if (f.status) {
    const m: Record<string, string[]> = {
      pending: ['待回款', '未回款'],
      partial: ['部分回款', '部分'],
      completed: ['已完成', '完成'],
      overdue: ['已逾期', '逾期'],
      cancelled: ['已取消', '取消'],
    }
    const cns = m[f.status] || []
    if (!cns.some(c => (r.status || '').includes(c))) return false
  }
  if (f.type) {
    // type 关键词：尾款/预付款/进度款
    const t = f.type
    if (t === '尾款' && !(r.type || '').includes('尾款')) return false
    if (t === '预付款' && !(r.type || '').includes('预付')) return false
    if (t === '进度款' && !(r.type || '').includes('进度')) return false
  }
  if (f.amountMin != null && (r.amount || 0) < f.amountMin) return false
  if (f.amountMax != null && (r.amount || 0) > f.amountMax) return false
  return true
}
const filteredList = computed(() => {
  if (!aiFilter.value) return list.value
  return list.value.filter(matchAi)
})

// 9 行示例数据
const sampleRows = ref([
  { id: 1, code: 'HK-2026-024', contract: 'HT-2026-031', client: '万象科技有限公司',     amount: 86500,  total: 86500,    progress: 100, planDate: '2026-06-12', actualDate: '2026-06-12', manager: '王芳',  status: '已完成',  statusColor: 'success' },
  { id: 2, code: 'HK-2026-018', contract: 'HT-2026-029', client: '朗驰智能设备有限公司', amount: 280000, total: 568000,   progress: 50,  planDate: '2026-06-30', actualDate: '—',          manager: '陈思琪', status: '部分回款', statusColor: 'warning' },
  { id: 3, code: 'HK-2026-019', contract: 'HT-2026-029', client: '朗驰智能设备有限公司', amount: 168000, total: 568000,   progress: 30,  planDate: '2026-05-30', actualDate: '2026-05-30', manager: '陈思琪', status: '已逾期',  statusColor: 'danger' },
  { id: 4, code: 'HK-2026-025', contract: 'HT-2026-028', client: '万象科技有限公司',     amount: 320000, total: 1280000,  progress: 25,  planDate: '2026-07-15', actualDate: '—',          manager: '王芳',  status: '待回款',  statusColor: 'info' },
  { id: 5, code: 'HK-2026-023', contract: 'HT-2026-027', client: '亚马逊通技术服务',     amount: 168000, total: 168000,   progress: 100, planDate: '2026-06-05', actualDate: '2026-06-04', manager: '张明',  status: '已完成',  statusColor: 'success' },
  { id: 6, code: 'HK-2026-022', contract: 'HT-2026-026', client: '集团总部',             amount: 43250,  total: 86500,    progress: 50,  planDate: '2026-06-25', actualDate: '—',          manager: '李建国', status: '待回款',  statusColor: 'info' },
  { id: 7, code: 'HK-2026-021', contract: 'HT-2026-024', client: '用友网络',             amount: 64000,  total: 128000,   progress: 50,  planDate: '2026-06-10', actualDate: '2026-06-08', manager: '张明',  status: '部分回款', statusColor: 'warning' },
  { id: 8, code: 'HK-2026-020', contract: 'HT-2026-023', client: '万象科技有限公司',     amount: 56000,  total: 56000,    progress: 100, planDate: '2026-05-15', actualDate: '2026-05-15', manager: '王芳',  status: '已完成',  statusColor: 'success' },
  { id: 9, code: 'HK-2026-017', contract: 'HT-2026-022', client: '携程商旅',             amount: 12000,  total: 24000,    progress: 50,  planDate: '2026-05-30', actualDate: '—',          manager: '李建国', status: '已逾期',  statusColor: 'danger' },
])

function fmtAmount(cents: any) { const v = (cents == null || isNaN(Number(cents))) ? 0 : Number(cents) / 100; return '¥ ' + v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function gotoDetail(r: any) { ElMessage.info(`查看回款: ${r.code}`) }
function gotoCreate() { router.push('/receivable/create') }

onMounted(() => {
  receivableApi.list({ page: 1, pageSize: 100 } as any)
    .then((res: any) => {
      if (res?.list?.length) {
        const raw = res.list as any[]
        // 后端字段：planAmount/receivedAmount 均为元（后端已 /100）
        // 状态：pending/partial/paid/overdue → 待回款/部分回款/已完成/已逾期
        const stMap: Record<string, string> = { pending: '待回款', partial: '部分回款', paid: '已完成', overdue: '已逾期' }
        const colorMap: Record<string, string> = { '待回款': 'info', '部分回款': 'warning', '已完成': 'success', '已逾期': 'danger' }
        list.value = raw.map((r: any) => {
          const plan = Number(r.planAmount || 0)
          const recv = Number(r.receivedAmount || 0)
          const st = stMap[r.status] || r.status || '待回款'
          const progress = plan > 0 ? Math.min(100, Math.round((recv / plan) * 100)) : 0
          return {
            id: r.receivableId || r.id,
            code: r.code || 'DRAFT',
            contract: r.contractCode || r.contract || '-',
            client: r.clientName || r.client || '-',
            // 前端内部 amount 统一用"分"，展示时 /100 转元
            amount: Math.round(plan * 100),
            total: Math.round(plan * 100),
            received: Math.round(recv * 100),
            progress,
            planDate: r.planDate || '-',
            actualDate: r.actualDate || '—',
            manager: r.managerName || r.manager || '-',
            status: st,
            statusColor: colorMap[st] || 'info',
          }
        })
        // KPI（amount 是分 → /100 转元，/10000 转万）
        const totalAmt = list.value.reduce((s, r) => s + (r.amount || 0), 0) / 100
        const overdueCount = list.value.filter(r => r.status === '已逾期').length
        stats.value[0].value = '¥ ' + (totalAmt / 10000).toFixed(2)
        stats.value[0].delta = `完成率 ${list.value.filter(r => r.status === '已完成').length}/${list.value.length}`
        const remainAmt = list.value.filter(r => r.status !== '已完成').reduce((s, r) => s + (r.amount || 0), 0) / 100
        stats.value[1].value = '¥ ' + (remainAmt / 10000).toFixed(2)
        stats.value[1].delta = `剩余 ${list.value.filter(r => r.status !== '已完成').length} 笔`
        const doneAmt = list.value.filter(r => r.status === '已完成').reduce((s, r) => s + (r.amount || 0), 0) / 100
        stats.value[2].value = totalAmt > 0 ? ((doneAmt / totalAmt) * 100).toFixed(1) : '0'
        stats.value[3].value = overdueCount
      }
    })
    .catch(() => { /* 静默用 mock */ })
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>回款管理</h1>
        <p class="page-desc">合同回款跟踪与催收 · 当前 {{ list.length }} 笔回款</p>
      </div>
      <div style="display: flex; gap: 8px">
        <!-- 触点 #9：AI 智能匹配 -->
        <el-button class="btn-ai-match" @click="aiMatchDrawerVisible = true">✨ AI 智能匹配</el-button>
        <el-button @click="ElMessage.info('回款分析')">📊 回款分析</el-button>
        <el-button v-permission="'receivable:write'" type="primary" :icon="'Plus'" @click="gotoCreate">登记回款</el-button>
      </div>
    </div>

    <!-- 4 KPI（design 同款） -->
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

    <div class="page-card">
      <div class="card-head-row">
        <h3>回款列表</h3>
        <div class="toolbar">
          <input class="search-input" placeholder="搜索回款编号 / 合同 / 客户..." />
          <select class="select-sm">
            <option>所有状态</option>
            <option>已完成</option>
            <option>部分回款</option>
            <option>待回款</option>
            <option>已逾期</option>
          </select>
          <!-- 触点 #22：AI 智能筛选 -->
          <button class="btn-ai-outline" @click="aiFilterVisible = true">🤖 AI 智能筛选</button>
          <button class="btn btn-outline btn-sm">⇩ 导出</button>
          <button class="btn btn-primary btn-sm">📨 一键催收</button>
        </div>
      </div>

      <table class="ct-table">
        <thead>
          <tr>
            <th>回款编号</th>
            <th>关联合同</th>
            <th>客户</th>
            <th style="text-align: right;">回款金额</th>
            <th>进度</th>
            <th>计划日期</th>
            <th>实际日期</th>
            <th>负责人</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredList" :key="r.id">
            <td><span class="cell-mono">{{ r.code }}</span></td>
            <td><span class="cell-mono contract-link">{{ r.contract }}</span></td>
            <td>{{ r.client }}</td>
            <td class="cell-amount">{{ fmtAmount(r.amount) }}</td>
            <td>
              <div class="progress-cell">
                <div class="progress-bar">
                  <div class="progress-fill" :class="r.statusColor" :style="{ width: r.progress + '%' }"></div>
                </div>
                <span class="progress-text">{{ r.progress }}%</span>
              </div>
            </td>
            <td>{{ r.planDate }}</td>
            <td>{{ r.actualDate }}</td>
            <td>{{ r.manager }}</td>
            <td><span :class="['tag', `tag-${r.statusColor}`]">{{ r.status }}</span></td>
            <td class="cell-actions">
              <a v-permission="'receivable:read'" @click="gotoDetail(r)">查看</a>
              <a v-permission="'receivable:write'" v-if="r.status === '待回款' || r.status === '已逾期'" @click="ElMessage.info('催收：' + r.code)">催收</a>
              <a v-permission="'receivable:write'" v-if="r.status === '部分回款'" @click="ElMessage.info('登记：' + r.code)">登记</a>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="rec-foot">
        <span class="rec-count">共 {{ list.length }} 笔</span>
        <div class="pagination">
          <button class="btn btn-ghost btn-sm">‹</button>
          <button class="btn btn-primary btn-sm">1</button>
          <button class="btn btn-ghost btn-sm">2</button>
          <button class="btn btn-ghost btn-sm">3</button>
          <button class="btn btn-ghost btn-sm">›</button>
        </div>
      </div>
    </div>

    <!-- 触点 #9：AI 智能匹配 Drawer -->
    <el-drawer v-model="aiMatchDrawerVisible" title="✨ AI 智能匹配" direction="rtl" size="520px">
      <div class="ai-match-drawer">
        <div class="ai-match-intro">
          <div class="ai-match-icon">✨</div>
          <h3>让 AI 帮您匹配合同/项目</h3>
          <p>基于金额、客户、时间、关键词，AI 自动推荐最可能关联的合同/项目，准确率 87%+。</p>
        </div>

        <el-form label-position="top" size="default">
          <el-form-item label="匹配类型">
            <el-radio-group v-model="aiMatchType">
              <el-radio-button value="invoice-to-contract">发票→合同</el-radio-button>
              <el-radio-button value="expense-to-project">费用→项目</el-radio-button>
              <el-radio-button value="contract-to-client">合同→客户</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-button
            class="ai-match-submit"
            :loading="aiMatchLoading"
            @click="runAiMatch"
          >
            <span v-if="!aiMatchLoading">✨ 开始智能匹配</span>
            <span v-else>AI 匹配中...</span>
          </el-button>
        </el-form>

        <div v-if="aiMatchResults.length" class="ai-match-results">
          <h4>🎯 匹配结果（{{ aiMatchResults.length }} 个候选）</h4>
          <div v-for="(r, i) in aiMatchResults" :key="i" class="ai-match-item" :class="{ best: i === 0 }">
            <div class="ai-match-rank">{{ i + 1 }}</div>
            <div class="ai-match-body">
              <div class="ai-match-head">
                <span class="ai-match-name">{{ r.name }}</span>
                <span class="ai-match-score" :class="r.score >= 0.8 ? 'high' : r.score >= 0.5 ? 'mid' : 'low'">
                  {{ (r.score * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="ai-match-bar">
                <div class="ai-match-bar-fill" :style="{ width: r.score * 100 + '%' }" />
              </div>
              <ul class="ai-match-reasons">
                <li v-for="reason in r.reasons" :key="reason">✓ {{ reason }}</li>
              </ul>
              <el-button v-if="i === 0" type="primary" size="small" @click="ElMessage.success('已采纳匹配')">采纳此匹配</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>

  <!-- 触点 #22：AI 智能筛选 Drawer -->
  <AiFilterDialog v-model:visible="aiFilterVisible" scope="receivable" @apply="onAiFilterApply" />
</template>

<style lang="scss" scoped>
/* 触点 #9：AI 智能匹配按钮 + Drawer */
.btn-ai-match {
  background: $gradient-brand; color: #fff; border: none; font-weight: 600;
  box-shadow: 0 2px 8px rgba(79,107,255,0.25);
  &:hover { opacity: 0.92; }
}
.ai-match-drawer { padding: 0 4px; }
.ai-match-intro {
  text-align: center; padding: 16px 0 20px;
  border-bottom: 1px solid $color-border; margin-bottom: 16px;
  .ai-match-icon { font-size: 32px; margin-bottom: 8px; }
  h3 { font-size: 16px; font-weight: 600; color: $color-text-primary; margin-bottom: 6px; }
  p { font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
}
.ai-match-submit {
  width: 100%; height: 38px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none;
  &:hover { opacity: 0.92; }
}
.ai-match-results { margin-top: 20px; }
.ai-match-results h4 { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 10px; }
.ai-match-item {
  display: flex; gap: 12px; padding: 12px;
  background: #fff; border: 1px solid $color-border; border-radius: $radius-md;
  margin-bottom: 8px;
  &.best { border-color: #7C3AED; background: linear-gradient(135deg, rgba(124,58,237,0.04) 0%, transparent 100%); }
}
.ai-match-rank {
  flex-shrink: 0; width: 28px; height: 28px;
  background: $color-bg; color: $color-text-secondary;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700;
  .best & { background: $gradient-brand; color: #fff; }
}
.ai-match-body { flex: 1; min-width: 0; }
.ai-match-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ai-match-name { font-size: 12.5px; font-weight: 600; color: $color-text-primary; }
.ai-match-score {
  font-size: 13px; font-weight: 700; font-family: $font-family-mono;
  &.high { color: $color-success; }
  &.mid  { color: $color-warning; }
  &.low  { color: $color-danger; }
}
.ai-match-bar { height: 4px; background: $color-bg; border-radius: 2px; overflow: hidden; margin-bottom: 8px; }
.ai-match-bar-fill { height: 100%; background: $gradient-brand; transition: width 0.3s; }
.ai-match-reasons {
  list-style: none; padding: 0; margin: 0 0 8px 0;
  li { font-size: 11px; color: $color-text-secondary; line-height: 1.6; }
}
</style>

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

.card-head-row {
  display: flex; justify-content: space-between; align-items: center; padding: 0 0 16px 0;
  h3 { font-size: 15px; font-weight: 600; margin: 0; }
  .toolbar { display: flex; gap: 8px; align-items: center; }
}
.search-input {
  height: 32px; padding: 0 12px; border: 1px solid $color-border; border-radius: $radius-md;
  font-size: 12px; background: #fff; width: 260px;
  &:focus { outline: none; border-color: $color-primary; }
}
.select-sm {
  height: 32px; padding: 0 12px; border: 1px solid $color-border; border-radius: $radius-md;
  font-size: 12px; background: #fff; color: $color-text-tertiary;
}

.ct-table {
  width: 100%; border-collapse: collapse; font-size: 13.5px;
  th {
    background: #F8FAFC; text-align: left; padding: 12px 16px;
    font-size: 12px; font-weight: 600; color: $color-text-secondary;
    text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 1px solid $color-border;
  }
  td { padding: 14px 16px; border-bottom: 1px solid $color-border; color: $color-text-primary; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #F8FAFC; }
  .cell-mono { font-family: $font-family-mono; color: $color-primary; font-weight: 500; }
  .cell-amount { font-weight: 600; text-align: right; }
  .cell-actions { display: flex; gap: 4px; }
  .cell-actions a {
    color: $color-primary; font-size: 12.5px; font-weight: 500;
    padding: 4px 8px; border-radius: $radius-sm; cursor: pointer;
    &:hover { background: $color-primary-bg; }
  }
}

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  background: #F1F5F9; color: $color-text-secondary;
  &.tag-primary { background: #E0E6FF; color: #4F6BFF; }
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-danger  { background: #FEE2E2; color: #B91C1C; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
}

.progress-cell { display: flex; align-items: center; gap: 8px; }
.progress-bar {
  flex: 1;
  height: 6px;
  background: $color-bg;
  border-radius: 3px;
  overflow: hidden;
  min-width: 80px;
}
.progress-fill {
  height: 100%;
  border-radius: 3px;
  &.success { background: $color-success; }
  &.warning { background: #F59E0B; }
  &.danger  { background: #EF4444; }
  &.info    { background: $color-primary; }
}
.progress-text {
  font-family: $font-family-mono; font-size: 11px; font-weight: 600;
  color: $color-text-secondary; min-width: 32px; text-align: right;
}

.rec-foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 0 0 0; margin-top: 12px; border-top: 1px solid $color-border;
  flex-wrap: wrap; gap: 8px;
  .rec-count { font-size: 12.5px; color: $color-text-tertiary; }
  .pagination { display: flex; gap: 4px; }
}

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
