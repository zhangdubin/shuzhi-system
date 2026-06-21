<script setup lang="ts">
/**
 * ClientDetail · 客户详情页
 * - 顶部概要：客户编号 / 名称 / 等级 / 状态
 * - 4 KPI：合同数 / 合同金额 / 项目数 / 待回款
 * - 5 区块：档案 / 联系人 / 财务 / 合同 / 项目 / 回款
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clientApi, type Client } from '@/api/client'

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const loading = ref(false)
const client = ref<Client | null>(null)
const contracts = ref<any[]>([])
const projects = ref<any[]>([])
const receivables = ref<any[]>([])

// 等级映射
const LEVEL_META: Record<string, { label: string; color: string }> = {
  A: { label: 'VIP 战略', color: 'warning' },
  B: { label: '金牌',     color: 'warning' },
  C: { label: '银牌',     color: 'info' },
  D: { label: '普通',     color: 'gray' },
}
function levelLabel(l?: string) { return LEVEL_META[l || 'D']?.label || '普通' }
function levelColor(l?: string) { return LEVEL_META[l || 'D']?.color || 'gray' }

// 合同 type 中文
const CONTRACT_TYPE: Record<string, string> = {
  sales: '销售', purchase: '采购', service: '服务', framework: '框架',
}
function contractTypeLabel(t?: string) { return CONTRACT_TYPE[t || ''] || t || '-' }

// 合同状态颜色
function statusColor(s?: string) {
  if (!s) return 'gray'
  if (s === 'draft') return 'gray'
  if (s === 'approving') return 'warning'
  if (['approved', 'signed', 'executed'].includes(s)) return 'success'
  if (s === 'expired') return 'danger'
  if (s === 'archived') return 'info'
  return 'gray'
}
function statusLabel(s?: string) {
  const m: Record<string, string> = {
    draft: '草稿', approving: '审批中', approved: '已通过',
    signed: '已签订', executed: '执行中', expired: '已到期', archived: '已归档',
  }
  return m[s || ''] || s || '-'
}

// 应收状态
function recvStatusLabel(s?: string) {
  const m: Record<string, string> = {
    pending: '待回款', partial: '部分回款', completed: '已完成',
    overdue: '已逾期', cancelled: '已取消',
  }
  return m[s || ''] || s || '-'
}
function recvStatusColor(s?: string) {
  if (s === 'completed') return 'success'
  if (s === 'partial') return 'warning'
  if (s === 'overdue') return 'danger'
  if (s === 'cancelled') return 'gray'
  return 'info'
}

// 项目状态
function projStatusLabel(s?: string) {
  const m: Record<string, string> = {
    planning: '规划中', in_progress: '进行中', finishing: '即将完成',
    completed: '已完成', paused: '已暂停', cancelled: '已取消',
  }
  return m[s || ''] || s || '-'
}
function projStatusColor(s?: string) {
  if (s === 'completed') return 'success'
  if (s === 'in_progress' || s === 'finishing') return 'primary'
  if (s === 'paused') return 'info'
  return 'gray'
}

function fmtAmount(n?: number | null) {
  if (n == null) return '¥ 0'
  if (n >= 10000) return '¥ ' + (n / 10000).toFixed(2) + '万'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadAll() {
  if (!id.value) return
  loading.value = true
  try {
    const c: any = await clientApi.detail(id.value)
    client.value = c
    // 三个子端点并发
    const [cc, pp, rr] = await Promise.all([
      clientApi.contracts(id.value).catch(() => []),
      clientApi.projects(id.value).catch(() => []),
      clientApi.receivables(id.value).catch(() => []),
    ])
    contracts.value = Array.isArray(cc) ? cc : []
    projects.value = Array.isArray(pp) ? pp : []
    receivables.value = Array.isArray(rr) ? rr : []
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || '未知错误'
    ElMessage.error('客户详情加载失败：' + msg)
  } finally {
    loading.value = false
  }
}

function gotoList() { router.push('/client/list') }
function gotoEdit() { router.push({ path: '/client/create', query: { id: String(id.value) } }) }
function gotoCreate() { router.push('/client/create') }

onMounted(loadAll)
</script>

<template>
  <div class="page-container">
    <!-- 顶栏：面包屑 + 返回 -->
    <div class="detail-topbar">
      <a class="back-link" @click="gotoList">← 返回客户列表</a>
    </div>

    <div v-if="!client && !loading" class="empty">
      <div class="ico">😶</div>
      <div>客户不存在或已被删除</div>
      <el-button style="margin-top: 12px" @click="gotoList">返回列表</el-button>
    </div>

    <template v-else-if="client">
      <!-- 头部概要 -->
      <div class="detail-hero page-card">
        <div class="hero-left">
          <div class="hero-avatar">{{ (client.name || '?').slice(0, 1) }}</div>
          <div class="hero-info">
            <div class="hero-name">
              {{ client.name }}
              <span v-if="!client.isActive" class="badge-inactive">已停用</span>
            </div>
            <div class="hero-meta">
              <span class="cell-mono">{{ client.code }}</span>
              <span v-if="client.shortName" class="dot-sep">·</span>
              <span v-if="client.shortName">{{ client.shortName }}</span>
              <span v-if="client.taxNo" class="dot-sep">·</span>
              <span v-if="client.taxNo" class="cell-mono taxno">税号 {{ client.taxNo }}</span>
            </div>
            <div class="hero-tags">
              <span :class="['tag', `tag-${levelColor(client.level)}`]">★ {{ levelLabel(client.level) }}</span>
              <span v-if="client.industry" class="tag tag-info">{{ client.industry }}</span>
              <span v-if="client.legalPerson" class="tag tag-gray">法人 {{ client.legalPerson }}</span>
            </div>
          </div>
        </div>
        <div class="hero-actions">
          <el-button @click="gotoEdit">✎ 编辑</el-button>
          <el-button type="primary" @click="gotoCreate">+ 新建客户</el-button>
        </div>
      </div>

      <!-- 4 KPI -->
      <div class="kpi-row">
        <div class="stat-card">
          <div class="stat-label">合同数 <span class="stat-icon" style="background: rgba(79,107,255,0.12); color: #4F6BFF">📄</span></div>
          <div class="stat-value">{{ client.contractCount || 0 }}<span class="unit">份</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">合同金额 <span class="stat-icon" style="background: rgba(124,58,237,0.12); color: #7C3AED">¥</span></div>
          <div class="stat-value">{{ fmtAmount(client.contractAmount) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">项目数 <span class="stat-icon" style="background: rgba(16,185,129,0.12); color: #10B981">▥</span></div>
          <div class="stat-value">{{ client.projectCount || 0 }}<span class="unit">个</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">待回款 <span class="stat-icon" style="background: rgba(245,158,11,0.12); color: #F59E0B">⏱</span></div>
          <div class="stat-value">{{ fmtAmount(client.pendingAmount) }}</div>
          <div class="stat-delta">已收 {{ fmtAmount(client.receivedAmount) }}</div>
        </div>
      </div>

      <!-- 档案 + 联系人 + 财务 -->
      <div class="grid-2">
        <div class="page-card">
          <h3 class="section-title">📋 基础档案</h3>
          <div class="kv">
            <div class="k">客户编号</div><div class="v cell-mono">{{ client.code }}</div>
            <div class="k">客户名称</div><div class="v">{{ client.name }}</div>
            <div class="k">客户简称</div><div class="v">{{ client.shortName || '—' }}</div>
            <div class="k">纳税人识别号</div><div class="v cell-mono">{{ client.taxNo || '—' }}</div>
            <div class="k">法定代表人</div><div class="v">{{ client.legalPerson || '—' }}</div>
            <div class="k">所属行业</div><div class="v">{{ client.industry || '—' }}</div>
            <div class="k">客户等级</div><div class="v"><span :class="['tag', `tag-${levelColor(client.level)}`]">★ {{ levelLabel(client.level) }}</span></div>
            <div class="k">状态</div><div class="v">
              <span :class="['tag', client.isActive ? 'tag-success' : 'tag-gray']">{{ client.isActive ? '启用' : '停用' }}</span>
            </div>
          </div>
        </div>

        <div class="page-card">
          <h3 class="section-title">👤 主要联系人</h3>
          <div class="kv">
            <div class="k">联系人姓名</div><div class="v">{{ client.contactName || '—' }}</div>
            <div class="k">联系电话</div><div class="v cell-mono">{{ client.contactPhone || '—' }}</div>
            <div class="k">邮箱</div><div class="v cell-mono">{{ client.contactEmail || '—' }}</div>
            <div class="k">地址</div><div class="v">{{ client.address || '—' }}</div>
            <div class="k">备注</div><div class="v">{{ client.remark || '—' }}</div>
          </div>
        </div>
      </div>

      <div class="page-card">
        <h3 class="section-title">💰 财务信息</h3>
        <div class="kv kv-4">
          <div class="k">开户银行</div><div class="v">{{ client.bankName || '—' }}</div>
          <div class="k">银行账号</div><div class="v cell-mono">{{ client.bankAccount || '—' }}</div>
          <div class="k">客户等级</div><div class="v"><span :class="['tag', `tag-${levelColor(client.level)}`]">★ {{ levelLabel(client.level) }}</span></div>
          <div class="k">创建时间</div><div class="v">{{ client.createdAt ? client.createdAt.slice(0, 19).replace('T', ' ') : '—' }}</div>
        </div>
      </div>

      <!-- 合同 -->
      <div class="page-card">
        <div class="card-head-row">
          <h3 class="section-title">📄 关联合同 <span class="muted">({{ contracts.length }})</span></h3>
        </div>
        <table class="ct-table" v-if="contracts.length">
          <thead>
            <tr>
              <th>合同编号</th><th>合同名称</th><th>类型</th><th>状态</th>
              <th class="col-amount">金额</th><th>签订日期</th><th>到期日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in contracts" :key="c.id">
              <td><span class="cell-mono">{{ c.code }}</span></td>
              <td>{{ c.name }}</td>
              <td><span class="tag tag-info">{{ contractTypeLabel(c.type) }}</span></td>
              <td><span :class="['tag', `tag-${statusColor(c.status)}`]">{{ statusLabel(c.status) }}</span></td>
              <td class="cell-amount">{{ fmtAmount(c.amount) }}</td>
              <td>{{ c.signDate || '—' }}</td>
              <td>{{ c.expireDate || '—' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-row">暂无关联合同</div>
      </div>

      <!-- 项目 -->
      <div class="page-card">
        <div class="card-head-row">
          <h3 class="section-title">▥ 关联项目 <span class="muted">({{ projects.length }})</span></h3>
        </div>
        <table class="ct-table" v-if="projects.length">
          <thead>
            <tr>
              <th>项目编号</th><th>项目名称</th><th>状态</th>
              <th class="col-progress">进度</th><th>开始日期</th><th>结束日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in projects" :key="p.id">
              <td><span class="cell-mono">{{ p.code }}</span></td>
              <td>{{ p.name }}</td>
              <td><span :class="['tag', `tag-${projStatusColor(p.status)}`]">{{ projStatusLabel(p.status) }}</span></td>
              <td>
                <div class="progress-bar"><div class="progress-fill" :style="{ width: (p.progress || 0) + '%' }"></div></div>
                <span class="progress-text">{{ Math.round(p.progress || 0) }}%</span>
              </td>
              <td>{{ p.startDate || '—' }}</td>
              <td>{{ p.endDate || '—' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-row">暂无关联项目</div>
      </div>

      <!-- 回款 -->
      <div class="page-card">
        <div class="card-head-row">
          <h3 class="section-title">💵 关联回款 <span class="muted">({{ receivables.length }})</span></h3>
        </div>
        <table class="ct-table" v-if="receivables.length">
          <thead>
            <tr>
              <th>回款编号</th><th>类型</th><th>状态</th>
              <th class="col-amount">计划金额</th><th class="col-amount">已收</th>
              <th>计划日期</th><th>实际日期</th><th>逾期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in receivables" :key="r.id">
              <td><span class="cell-mono">{{ r.code }}</span></td>
              <td>{{ r.type || '—' }}</td>
              <td><span :class="['tag', `tag-${recvStatusColor(r.status)}`]">{{ recvStatusLabel(r.status) }}</span></td>
              <td class="cell-amount">{{ fmtAmount(r.planAmount) }}</td>
              <td class="cell-amount">{{ fmtAmount(r.receivedAmount) }}</td>
              <td>{{ r.planDate || '—' }}</td>
              <td>{{ r.actualDate || '—' }}</td>
              <td>
                <span v-if="r.overdueDays > 0" class="overdue">{{ r.overdueDays }} 天</span>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-row">暂无关联回款</div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/mixins.scss' as *;

.detail-topbar { margin-bottom: 12px; }
.back-link {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; color: $color-text-secondary;
  cursor: pointer; user-select: none;
  &:hover { color: $color-primary; }
}

.empty {
  text-align: center; padding: 80px 0; color: $color-text-tertiary;
  .ico { font-size: 56px; margin-bottom: 12px; }
}

.detail-hero {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; margin-bottom: 16px;
  background: linear-gradient(135deg, rgba(79,107,255,0.04) 0%, rgba(124,58,237,0.04) 100%);
  border: 1px solid rgba(79,107,255,0.12);
}
.hero-left { display: flex; align-items: center; gap: 16px; }
.hero-avatar {
  width: 64px; height: 64px; border-radius: 16px;
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 600; box-shadow: 0 4px 12px rgba(79,107,255,0.25);
}
.hero-name {
  font-size: 22px; font-weight: 600; color: $color-text-primary;
  display: flex; align-items: center; gap: 8px;
}
.hero-meta {
  font-size: 13px; color: $color-text-secondary; margin-top: 4px;
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.hero-tags { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.dot-sep { color: $color-text-tertiary; }
.taxno { font-size: 12px; }
.badge-inactive {
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  background: #94A3B8; color: #fff; font-size: 11px; font-weight: 500;
}
.hero-actions { display: flex; gap: 8px; }

.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  margin-bottom: 16px;
}
.stat-card { @include stat-card; }

.grid-2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
  margin-bottom: 16px;
}
.page-card { @include page-card; margin-bottom: 12px; }
.section-title {
  font-size: 14px; font-weight: 600; color: $color-text-primary; margin: 0 0 12px 0;
  .muted { color: $color-text-tertiary; font-weight: 400; font-size: 12px; }
}
.card-head-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }

.kv {
  display: grid; grid-template-columns: 110px 1fr; gap: 8px 16px;
  font-size: 13px;
  .k { color: $color-text-tertiary; }
  .v { color: $color-text-primary; word-break: break-all; }
  &.kv-4 { grid-template-columns: 110px 1fr 110px 1fr; }
}

.ct-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  thead th {
    text-align: left; padding: 8px 10px;
    color: $color-text-tertiary; font-weight: 500;
    border-bottom: 1px solid $color-border; background: $color-bg;
  }
  tbody td {
    padding: 10px; border-bottom: 1px solid $color-border;
    color: $color-text-primary;
  }
  tbody tr:hover { background: $color-bg; }
  .cell-mono { font-family: $font-family-mono; font-size: 12px; }
  .cell-amount { text-align: right; font-variant-numeric: tabular-nums; }
  .col-amount { text-align: right; }
  .col-progress { width: 180px; }
}
.progress-bar {
  display: inline-block; width: 120px; height: 6px;
  background: $color-border; border-radius: 3px; overflow: hidden;
  vertical-align: middle; margin-right: 8px;
}
.progress-fill { height: 100%; background: linear-gradient(90deg, #4F6BFF, #7C3AED); transition: width 0.3s; }
.progress-text { font-size: 12px; color: $color-text-secondary; }
.overdue { color: #EF4444; font-weight: 600; font-size: 12px; }
.empty-row {
  padding: 40px; text-align: center; color: $color-text-tertiary; font-size: 13px;
}
.tag {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 500;
  &.tag-warning { background: rgba(245,158,11,0.12); color: #F59E0B; }
  &.tag-info    { background: rgba(79,107,255,0.12); color: #4F6BFF; }
  &.tag-success { background: rgba(16,185,129,0.12); color: #10B981; }
  &.tag-danger  { background: rgba(239,68,68,0.12);  color: #EF4444; }
  &.tag-gray    { background: #F1F5F9;                color: #64748B; }
  &.tag-primary { background: rgba(79,107,255,0.12); color: #4F6BFF; }
}
</style>
