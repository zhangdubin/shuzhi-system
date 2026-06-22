<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/expense/list')">业务</a>
          <span class="sep">/</span>
          <span class="current">报销中心</span>
        </div>
        <h1>🧾 报销中心</h1>
        <p class="page-desc">从销售费用生成报销单，打印 / 录入实际报销后自动回写费用状态</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadData">↻ 刷新</el-button>
        <el-button :disabled="!selectedIds.length" @click="batchDelete">🗑 批量删除 <span v-if="selectedIds.length" class="badge-count">{{ selectedIds.length }}</span></el-button>
        <el-button :disabled="!selectedIds.length" @click="aiReviewSelected">🤖 AI 复核 <span v-if="selectedIds.length" class="badge-count">{{ selectedIds.length }}</span></el-button>
        <el-button @click="exportCsv">📥 导出</el-button>
        <el-button type="primary" @click="router.push('/reimbursement/create')">+ 新建报销单</el-button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">报销单数</div>
        <div class="kpi-value">{{ stats.total }}</div>
        <div class="kpi-delta">累计</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">草稿</div>
        <div class="kpi-value" style="color:#94A3B8">{{ stats.draft }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已打印</div>
        <div class="kpi-value" style="color:#7C3AED">{{ stats.printed }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已完成</div>
        <div class="kpi-value" style="color:#10B981">{{ stats.done }}</div>
      </div>
      <div class="kpi-card highlight">
        <div class="kpi-label">报销总金额</div>
        <div class="kpi-value">¥{{ fmtMoney(stats.totalAmount) }}</div>
        <div class="kpi-delta">实际报销</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="page-card filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索报销单号 / 标题" clearable style="width:260px" @keyup.enter="loadData" @clear="loadData" />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:140px" @change="loadData">
        <el-option label="草稿" value="draft" />
        <el-option label="已打印" value="printed" />
        <el-option label="已报销" value="reimbursed" />
        <el-option label="已完成" value="done" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filters.templateType" placeholder="全部模板" clearable style="width:160px" @change="loadData">
        <el-option v-for="t in templates" :key="t.code" :label="t.name" :value="t.code" />
      </el-select>
      <el-button @click="loadData">搜索</el-button>
    </div>

    <!-- 列表 -->
    <div class="page-card">
      <el-table :data="filtered" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="46" />
        <el-table-column prop="formNo" label="报销单号" width="180">
          <template #default="{ row }">
            <a class="link" @click="gotoDetail(row)">{{ row.formNo }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="模板" width="120">
          <template #default="{ row }">{{ templateName(row.templateType) }}</template>
        </el-table-column>
        <el-table-column label="报销人" width="100">
          <template #default="{ row }">{{ row.applicant?.name || '—' }}</template>
        </el-table-column>
        <el-table-column label="费用笔数" width="80" align="center">
          <template #default="{ row }">{{ row.detailCount }}</template>
        </el-table-column>
        <el-table-column label="报销金额" width="120" align="right">
          <template #default="{ row }">
            <span class="money">¥{{ fmtMoney(row.totalAmount) }}</span>
            <div v-if="row.actualAmount > 0" class="actual">实报 ¥{{ fmtMoney(row.actualAmount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="凭证号" width="140">
          <template #default="{ row }">{{ row.voucherNo || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="['tag', statusClass(row.status)]">{{ row.statusLabel }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ fmtDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <a class="act-link" @click="gotoDetail(row)">查看</a>
              <a v-if="row.status === 'draft'" class="act-link" @click="onEdit(row)">编辑</a>
              <a class="act-link" @click="aiReviewOne(row)">🤖 AI复核</a>
              <a v-if="row.status !== 'done'" class="act-link act-danger" @click="onDelete(row)">删除</a>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && filtered.length === 0" class="empty">
        暂无报销单，<a class="link" @click="router.push('/reimbursement/create')">立即创建</a>
      </div>
    </div>

    <!-- AI 复核弹窗：纯自定义 HTML，无标题栏、无默认按钮 -->
    <el-dialog
      v-model="aiReviewVisible"
      :show-close="false"
      :width="720"
      :top="'8vh'"
      align-center
      destroy-on-close
      class="ai-review-dialog"
      :modal-class="'ai-review-modal'"
    >
      <div v-html="aiReviewHtml"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reimburseApi } from '@/api/modules'

const router = useRouter()
const loading = ref(false)
const list = ref<any[]>([])
const templates = ref<any[]>([])

const filters = reactive({
  keyword: '',
  status: '',
  templateType: '',
})

const filtered = computed(() => {
  // 已经在后端做分页，但前端也兜底筛
  return list.value
})

const aiReviewVisible = ref(false)
const aiReviewHtml = ref('')

const selectedIds = ref<number[]>([])
function onSelectionChange(rows: any[]) {
  selectedIds.value = rows.map(r => r.formId).filter(Boolean)
}

const stats = computed(() => {
  const draft = list.value.filter(x => x.status === 'draft').length
  const printed = list.value.filter(x => x.status === 'printed').length
  const done = list.value.filter(x => x.status === 'done').length
  const totalAmount = list.value.reduce((s, x) => s + (x.actualAmount || x.totalAmount || 0), 0)
  return { total: list.value.length, draft, printed, done, totalAmount }
})

function templateName(code: string) {
  return templates.value.find(t => t.code === code)?.name || code
}

function statusClass(s: string) {
  return {
    draft: 'tag-info', printed: 'tag-warning', reimbursed: 'tag-primary',
    done: 'tag-success', cancelled: 'tag-danger',
  }[s] || 'tag-info'
}

function fmtMoney(v: number) { return ((v || 0) / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmtDate(s?: string) { return s ? s.substring(0, 16).replace('T', ' ') : '—' }

async function loadData() {
  loading.value = true
  try {
    const r: any = await reimburseApi.list({ page: 1, pageSize: 50, keyword: filters.keyword, filters: { status: filters.status, templateType: filters.templateType } })
    list.value = r?.list || r?.data?.list || []
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const r: any = await reimburseApi.templates()
    templates.value = r || r?.data || []
  } catch (e) {
    console.warn('templates load failed', e)
  }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除报销单「${row.formNo}」？删除后关联费用将恢复未报销状态。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await reimburseApi.delete(row.formId)
    ElMessage.success('已删除')
    loadData()
  } catch (e: any) {
    ElMessage.error('删除失败：' + (e?.message || ''))
  }
}

async function batchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确认批量删除选中的 ${selectedIds.value.length} 张报销单？已打印/已完成/已报销的会被跳过。`, '批量删除', { type: 'warning' })
  } catch { return }
  try {
    const r: any = await reimburseApi.batchDelete(selectedIds.value)
    const data = r?.data || r
    let msg = `已删除 ${data.deleted ?? 0} 张`
    if (data.skipped?.length) msg += `，跳过 ${data.skipped.length} 张（状态不可删除）`
    ElMessage.success(msg)
    selectedIds.value = []
    loadData()
  } catch (e: any) {
    ElMessage.error('批量删除失败：' + (e?.response?.data?.msg || e?.message || ''))
  }
}

async function aiReviewOne(row: any) {
  await runAiReview([row.formId], [row])
}
async function aiReviewSelected() {
  if (!selectedIds.value.length) return
  await runAiReview(selectedIds.value)
}
async function runAiReview(formIds: number[], presetRows: any[] = []) {
  const reviews: any[] = []
  for (const fid of formIds) {
    const pre = presetRows.find(r => r.formId === fid)
    try {
      const d: any = await reimburseApi.detail(fid)
      const detail = d?.data || d
      const expenseIds = (detail?.details || []).map((x: any) => x.expenseId).filter(Boolean)
      if (!expenseIds.length) {
        reviews.push({ formNo: pre?.formNo || detail.formNo || `ID=${fid}`, level: 'unknown', reasons: ['该报销单无关联费用'] })
        continue
      }
      const r: any = await reimburseApi.aiRisk({ expenseIds, formId: fid })
      reviews.push({ formNo: pre?.formNo || detail.formNo || `ID=${fid}`, level: r?.level || r?.data?.level || 'low', reasons: r?.reasons || r?.data?.reasons || [] })
    } catch (e: any) {
      reviews.push({ formNo: pre?.formNo || `ID=${fid}`, level: 'error', reasons: [e?.message || '复核失败'] })
    }
  }
  // 弹窗：Modern Dashboard Modal（深色 hero + 大号 risk score + 4 个 KPI tile + 卡片列表）
  // 整体包 try-catch，防止内部报错导致整个弹窗静默失败
  try {
  const palette: Record<string, {bg: string; text: string; border: string; icon: string; label: string; desc: string; score: number}> = {
    high:    { bg: '#fef2f2', text: '#dc2626', border: '#fca5a5', icon: '🚨', label: '高风险', desc: '建议立即人工核查', score: 85 },
    medium:  { bg: '#fffbeb', text: '#d97706', border: '#fcd34d', icon: '⚠️', label: '中风险', desc: '建议关注并复核',  score: 55 },
    low:     { bg: '#f0fdf4', text: '#16a34a', border: '#86efac', icon: '✅', label: '低风险', desc: '各项指标正常',       score: 15 },
    unknown: { bg: '#f8fafc', text: '#64748b', border: '#cbd5e1', icon: '🔍', label: '无异常', desc: '未发现风险信号',     score: 0  },
    error:   { bg: '#f1f5f9', text: '#475569', border: '#cbd5e1', icon: '⚠️', label: '复核失败', desc: '接口异常，请稍后再试', score: 0 },
  }
  const styleOf = (lv: string) => palette[lv] || palette.unknown
  const count = reviews.length
  const high = reviews.filter(r => r.level === 'high').length
  const med  = reviews.filter(r => r.level === 'medium').length
  const low  = reviews.filter(r => r.level === 'low').length
  const unk  = reviews.filter(r => r.level === 'unknown' || r.level === 'error').length
  // 整体风险判定
  const overall = high > 0 ? 'high' : med > 0 ? 'medium' : low > 0 ? 'low' : 'unknown'
  const overallS = styleOf(overall)
  // 平均分
  const avgScore = count > 0 ? Math.round(reviews.reduce((s, r) => s + (styleOf(r.level).score || 0), 0) / count) : 0

  // 顶部 hero：深色渐变 + 弹性 row + 4 个 KPI tile（每 tile 数字独占一行）
  const hero = `
    <div style="position:relative;padding:28px 32px 24px;background:linear-gradient(135deg,#1e293b 0%,#0f172a 50%,#1e1b4b 100%);border-radius:14px 14px 0 0;overflow:hidden;">
      <div style="position:absolute;top:-60px;right:-40px;width:220px;height:220px;background:radial-gradient(circle, ${overallS.text}33 0%, transparent 70%);pointer-events:none;"></div>
      <div style="position:absolute;bottom:-50px;left:30%;width:160px;height:160px;background:radial-gradient(circle, #6366f133 0%, transparent 70%);pointer-events:none;"></div>
      <div style="display:flex;align-items:center;gap:20px;position:relative;min-width:0;">
        <div style="width:64px;height:64px;border-radius:18px;background:linear-gradient(135deg, ${overallS.text} 0%, #6366f1 100%);display:flex;align-items:center;justify-content:center;font-size:32px;box-shadow:0 8px 24px ${overallS.text}66;flex-shrink:0;">${overallS.icon}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:11px;color:#94a3b8;letter-spacing:1.8px;text-transform:uppercase;margin-bottom:6px;font-weight:600;">AI RISK REVIEW</div>
          <div style="font-size:22px;font-weight:700;color:#f1f5f9;line-height:1.3;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${count} 张报销单复核完成</div>
          <div style="font-size:13px;color:#cbd5e1;line-height:1.5;">整体判定：<b style="color:${overallS.text === '#64748b' ? '#cbd5e1' : overallS.text};">${overallS.label}</b> · ${overallS.desc}</div>
        </div>
        <div style="text-align:right;flex-shrink:0;padding-left:16px;border-left:1px solid rgba(255,255,255,0.1);min-width:90px;">
          <div style="font-size:52px;font-weight:800;line-height:1;color:${overallS.text};font-family:-apple-system,BlinkMacSystemFont,sans-serif;letter-spacing:-1px;">${avgScore}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:8px;letter-spacing:0.8px;font-weight:500;">综合风险分</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:22px;position:relative;">
        <div style="background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:14px 16px;">
          <div style="font-size:24px;font-weight:800;color:#fca5a5;line-height:1;">${high}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:6px;letter-spacing:0.3px;">高风险</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:14px 16px;">
          <div style="font-size:24px;font-weight:800;color:#fcd34d;line-height:1;">${med}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:6px;letter-spacing:0.3px;">中风险</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:14px 16px;">
          <div style="font-size:24px;font-weight:800;color:#86efac;line-height:1;">${low}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:6px;letter-spacing:0.3px;">低风险</div>
        </div>
        <div style="background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:14px 16px;">
          <div style="font-size:24px;font-weight:800;color:#cbd5e1;line-height:1;">${unk}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:6px;letter-spacing:0.3px;">无异常</div>
        </div>
      </div>
    </div>
  `

  const cardOf = (r: any, idx: number) => {
    const s = styleOf(r.level)
    const reasons = (r.reasons || []).filter(Boolean)
    return `
      <div style="display:grid;grid-template-columns:48px 1fr 80px;gap:16px;padding:16px 18px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;align-items:start;transition:all 0.2s;">
        <div style="width:48px;height:48px;border-radius:12px;background:${s.bg};border:1px solid ${s.border};display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;">${s.icon}</div>
        <div style="min-width:0;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
            <span style="font-size:14px;font-weight:600;color:#0f172a;font-family:'SF Mono',Menlo,monospace;letter-spacing:-0.3px;">${r.formNo}</span>
            <span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;background:${s.bg};color:${s.text};border:1px solid ${s.border};border-radius:6px;font-size:11px;font-weight:600;">${s.label}</span>
            <span style="font-size:11px;color:#94a3b8;">#${idx + 1} / ${count}</span>
          </div>
          <div style="font-size:12px;color:${s.text};font-weight:500;margin-bottom:8px;">${s.desc}</div>
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;">
            ${reasons.length
              ? reasons.map((x: string) => `<div style="display:flex;align-items:flex-start;gap:8px;padding:2px 0;font-size:12.5px;color:#475569;line-height:1.55;"><span style="color:${s.text};font-weight:700;flex-shrink:0;">›</span><span>${x}</span></div>`).join('')
              : `<div style="display:flex;align-items:center;gap:6px;font-size:12.5px;color:#94a3b8;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span>未发现异常</span></div>`}
          </div>
        </div>
        <div style="text-align:center;padding:8px;background:${s.bg};border:1px solid ${s.border};border-radius:10px;flex-shrink:0;">
          <div style="font-size:28px;font-weight:800;color:${s.text};line-height:1;font-family:-apple-system,sans-serif;">${s.score}</div>
          <div style="font-size:10px;color:${s.text};margin-top:4px;letter-spacing:0.5px;font-weight:600;opacity:0.7;">RISK</div>
        </div>
      </div>
    `
  }

  const body = `
    <div style="padding:20px 24px;background:#f8fafc;max-height:480px;overflow-y:auto;">
      <div style="display:flex;flex-direction:column;gap:10px;">${reviews.map((r, i) => cardOf(r, i)).join('')}</div>
    </div>
  `

  const footer = `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:14px 24px;background:#fff;border-top:1px solid #e2e8f0;border-radius:0 0 14px 14px;">
      <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:#94a3b8;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        <span>由 AI 自动复核 · 仅供参考，最终以财务审核为准</span>
      </div>
      <span style="display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:10px;background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);color:#fff;font-size:13px;font-weight:600;box-shadow:0 2px 8px rgba(79,70,229,0.3);">点击空白处关闭</span>
    </div>
  `

  const html = `<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;padding:0;border-radius:14px;overflow:hidden;">${hero}${body}${footer}</div>`
  // 写入 ref，由 template 中的 el-dialog 用 v-html 渲染（无标题栏、无默认按钮）
  aiReviewHtml.value = html
  aiReviewVisible.value = true
  } catch (e: any) {
    console.error('[AI 复核弹窗错误]', e)
    ElMessage.error('AI 复核弹窗渲染失败：' + (e?.message || e))
  }
}

async function exportCsv() {
  try {
    const r: any = await reimburseApi.exportList({ keyword: filters.keyword, filters: { status: filters.status, templateType: filters.templateType } })
    const data = r?.data || r
    if (!data?.csv) { ElMessage.warning('无数据可导出'); return }
    const blob = new Blob(['\ufeff' + data.csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = data.filename || '报销单列表.csv'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success("已导出 " + data.count + " 张报销单")
  } catch (e: any) {
    ElMessage.error('导出失败：' + (e?.response?.data?.msg || e?.message || ''))
  }
}

function onEdit(row: any) {
  ElMessage.info('编辑功能请在详情页操作（暂未提供独立编辑页）')
  router.push(`/reimbursement/${row.formId}`)
}

function gotoDetail(row: any) {
  router.push(`/reimbursement/${row.formId}`)
}

onMounted(() => {
  loadTemplates()
  loadData()
})
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }
.row-actions { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }
.row-actions .act-link { color: var(--brand-500, #4F6BFF); cursor: pointer; font-size: 13px; white-space: nowrap; }
.row-actions .act-link:hover { opacity: 0.75; }
.row-actions .act-link.act-danger { color: #EF4444; }

.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card {
  background: #fff; border: 1px solid $color-border; border-radius: $radius-lg;
  padding: 16px 20px;
  .kpi-label { font-size: 12px; color: $color-text-tertiary; }
  .kpi-value { font-size: 26px; font-weight: 700; color: $color-text-primary; margin: 4px 0 2px; }
  .kpi-delta { font-size: 11px; color: $color-text-tertiary; }
  &.highlight { background: linear-gradient(135deg, #4F6BFF08, #7C3AED08); border-color: rgba(79,107,255,0.2); }
}

.filter-bar { display: flex; gap: 8px; align-items: center; padding: 14px 16px; margin-bottom: 12px; }
.page-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 16px; margin-bottom: 12px; }

.link { color: $color-primary; cursor: pointer; }
.link:hover { text-decoration: underline; }
.money { font-weight: 600; color: #DC2626; }
.actual { font-size: 11px; color: $color-text-tertiary; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.tag-success { background: rgba(16,185,129,0.1); color: #10B981; }
.tag-warning { background: rgba(245,158,11,0.1); color: #F59E0B; }
.tag-primary { background: rgba(79,107,255,0.1); color: #4F6BFF; }
.tag-info    { background: rgba(148,163,184,0.15); color: #64748B; }
.tag-danger  { background: rgba(239,68,68,0.1);  color: #EF4444; }
.empty { padding: 40px; text-align: center; color: $color-text-tertiary; }
.badge-count {
  display: inline-block;
  margin-left: 4px;
  padding: 0 6px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  background: #fff;
  color: inherit;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
}
.badge-count {
  display: inline-block;
  margin-left: 4px;
  padding: 0 6px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  background: #fff;
  color: inherit;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
}
</style>
