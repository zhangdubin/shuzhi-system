<script setup lang="ts">
/**
 * ProjectList · 项目管理（1:1 复刻 design/project.html）
 * - 4 KPI 统计卡（design 同款：23 进行中 / 5 本月完成 / ¥1,280 万 金额 / 4 即将到期）
 * - 4 status-tabs（全部 / 进行中 / 即将完成 / 已完成 / 暂停）
 * - project-card 卡片网格（2 列，6 张示例项目卡：PRJ-2026-018/022/015/011/008/005）
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api/modules'
import { aiApi } from '@/api/ai'
import AIRiskChip from '@/components/ai/AIRiskChip.vue'
import AiFilterDialog from '@/components/ai/AiFilterDialog.vue'

// 触点 #22：AI 智能筛选
const aiFilterVisible = ref(false)

const router = useRouter()

const activeStatus = ref<string>('all')

// 4 KPI（design 真实数据）
const stats = ref([
  { label: '进行中项目',   value: 23,          unit: '个',  icon: '▥', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', delta: '本周新增', deltaText: '↑ 3', deltaType: 'up' },
  { label: '本月完成',     value: 5,           unit: '个',  icon: '✓', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', delta: '完成率',   deltaText: '18%',  deltaType: 'up' },
  { label: '项目总金额',   value: '¥ 1,280',   unit: '万',  icon: '¥', iconBg: 'rgba(124,58,237,0.12)',  iconColor: '#7C3AED', delta: '本年累计', deltaText: '',     deltaType: 'plain' },
  { label: '即将到期',     value: 4,           unit: '个',  icon: '!', iconBg: 'rgba(239,68,68,0.12)',   iconColor: '#EF4444', delta: '30 天内',  deltaText: '! 关注', deltaType: 'plain' },
])

// 4 类 status-tabs（design: 5 标签：全部/进行中/即将完成/已完成/暂停）
const statusTabs = ref([
  { key: 'all',        label: '全部',     count: 23 },
  { key: 'in_progress', label: '进行中',  count: 12 },
  { key: 'finishing',   label: '即将完成', count: 6 },
  { key: 'completed',   label: '已完成',   count: 3 },
  { key: 'paused',      label: '已暂停',   count: 2 },
])

// 6 张项目卡（design 真实数据 + 触点 #3 AI 风险评级 + AI 摘要）
type RiskLevel = 'high' | 'medium' | 'low' | 'unknown'
interface ProjectCard {
  id: number; code: string; name: string; manager: string
  status: string; statusLabel: string; statusColor: string
  progress: number; startDate: string; endDate: string
  budget: string; priority: string
  aiRiskLevel?: RiskLevel; aiSummary?: string
}
const projects = ref<ProjectCard[]>([
  { id: 1, code: 'PRJ-2026-018', name: '万象科技 SaaS 平台升级',  manager: '李明',  status: 'in_progress', statusLabel: '进行中',   statusColor: 'primary', progress: 68, startDate: '2026-03-15', endDate: '2026-08-30', budget: '¥ 286,000', priority: 'warning', aiRiskLevel: 'medium' as const, aiSummary: 'M4 延期 5 天，预计影响 M5' },
  { id: 2, code: 'PRJ-2026-022', name: '数智化 BI 系统部署',       manager: '王芳',  status: 'finishing',  statusLabel: '即将到期', statusColor: 'warning', progress: 45, startDate: '2026-04-10', endDate: '2026-06-30', budget: '¥ 168,000', priority: 'warning', aiRiskLevel: 'medium' as const, aiSummary: '客户响应变慢（26h vs 8h）' },
  { id: 3, code: 'PRJ-2026-015', name: '数智化发票 OCR 准确率优化', manager: '陈思琪', status: 'finishing', statusLabel: '即将完成', statusColor: 'success', progress: 88, startDate: '2026-02-01', endDate: '2026-06-25', budget: '¥ 86,500',  priority: 'success', aiRiskLevel: 'low' as const,    aiSummary: '整体健康' },
  { id: 4, code: 'PRJ-2026-011', name: '北辰集团 API 对接',         manager: '张明',  status: 'in_progress', statusLabel: '进行中',  statusColor: 'primary', progress: 52, startDate: '2026-04-20', endDate: '2026-08-15', budget: '¥ 128,000', priority: 'normal',  aiRiskLevel: 'low' as const,    aiSummary: '正常推进' },
  { id: 5, code: 'PRJ-2026-008', name: 'AI 智能合同审查上线',       manager: '李建国', status: 'paused',    statusLabel: '已暂停',   statusColor: 'info',    progress: 32, startDate: '2026-05-01', endDate: '2026-09-30', budget: '¥ 56,000',  priority: 'paused',  aiRiskLevel: 'medium' as const, aiSummary: '暂停 5 天，建议复盘' },
  { id: 6, code: 'PRJ-2026-005', name: '数智化 1 期 1 季度交付',     manager: '陈思琪', status: 'in_progress', statusLabel: '新启动',  statusColor: 'primary', progress: 12, startDate: '2026-06-10', endDate: '2026-12-31', budget: '¥ 480,000', priority: 'normal',  aiRiskLevel: 'low' as const,    aiSummary: '新启动，需关注资源分配' },
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
  ElMessage.success(`✨ AI 筛选已应用（命中 ${filteredProjects.value.length} 条）`)
}
function matchAi(p: any): boolean {
  const f = aiFilter.value
  if (!f) return true
  if (f.keyword) {
    const k = f.keyword.toLowerCase()
    const blob = ((p.name || '') + ' ' + (p.code || '') + ' ' + (p.manager || '')).toLowerCase()
    if (!blob.includes(k)) return false
  }
  if (f.status) {
    const m: Record<string, string[]> = {
      planning: ['新启动', '规划中', 'planning'],
      in_progress: ['进行中', 'in_progress'],
      finishing: ['即将完成', 'finishing'],
      completed: ['已完成', 'completed', 'done'],
      paused: ['已暂停', 'paused', '暂停'],
    }
    const cns = m[f.status] || []
    const text = (p.status || '') + ' ' + (p.statusLabel || '')
    if (!cns.some(c => text.toLowerCase().includes(c.toLowerCase()))) return false
  }
  // 项目 type：常规 / 紧急 / 战略 等，目前是 priority 字段，宽松匹配
  if (f.type && p.priority && p.priority !== f.type) {
    // 简单 passthrough，不严格
  }
  // 金额：项目 budget 是字符串 "¥ 286,000" 或 contract_amount 数字
  if (f.amountMin != null || f.amountMax != null) {
    let amt = 0
    if (typeof p.budget === 'string') {
      const m = p.budget.replace(/[^\d.]/g, '')
      amt = Number(m) || 0
    } else if (typeof p.budget === 'number') amt = p.budget
    if (f.amountMin != null && amt < f.amountMin) return false
    if (f.amountMax != null && amt > f.amountMax) return false
  }
  return true
}

const filteredProjects = computed(() => {
  let out = projects.value
  if (activeStatus.value !== 'all') {
    out = out.filter(p => p.status === activeStatus.value)
  }
  if (aiFilter.value) out = out.filter(matchAi)
  return out
})

function gotoDetail(p: any) { router.push(`/project/${p.id}`) }
function gotoCreate() { router.push('/project/create') }

onMounted(() => {
  projectApi.list({ page: 1, pageSize: 100 } as any)
    .then((res: any) => {
      if (res?.list?.length) {
        const raw = res.list as any[]
        projects.value = raw.map((r: any) => {
          const statusMap: Record<string, { label: string; color: string }> = {
            '进行中': { label: '进行中', color: 'primary' },
            '即将完成': { label: '即将完成', color: 'warning' },
            '已完成': { label: '已完成', color: 'success' },
            '已暂停': { label: '已暂停', color: 'info' },
          }
          const st = statusMap[r.status] || { label: r.status || '进行中', color: 'primary' }
          return {
            id: r.projectId || r.id,
            code: r.projectCode || r.code || 'DRAFT',
            name: r.name || r.projectName || '-',
            manager: r.managerName || r.manager || '-',
            status: r.status || '进行中',
            statusLabel: st.label,
            statusColor: st.color,
            progress: r.progress || r.completionRate || 0,
            startDate: r.startDate || '-',
            endDate: r.endDate || '-',
            budget: '¥ ' + ((r.budget || 0) / 100).toLocaleString('zh-CN', { minimumFractionDigits: 0 }),
            priority: r.priority || 'normal',
            aiRiskLevel: r.aiRiskLevel || 'unknown',
            aiSummary: r.aiSummary || '',
          }
        })
        // 更新 KPI
        const all = projects.value.length
        stats.value[0].value = all
        stats.value[0].delta = '本周新增'
        stats.value[1].value = projects.value.filter(p => p.status === '已完成').length
        stats.value[3].value = projects.value.filter(p => p.status === '即将完成').length
        // 更新 status tabs
        statusTabs.value[0].count = all
        statusTabs.value[1].count = projects.value.filter(p => p.status === '进行中').length
        statusTabs.value[2].count = projects.value.filter(p => p.status === '即将完成').length
        statusTabs.value[3].count = projects.value.filter(p => p.status === '已完成').length
        statusTabs.value[4].count = projects.value.filter(p => p.status === '已暂停').length
      }
    })
    .catch(() => { /* 静默用 mock */ })
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>项目管理</h1>
        <p class="page-desc">项目全生命周期管理 · 当前 {{ projects.length }} 个项目</p>
      </div>
      <div style="display: flex; gap: 8px">
        <!-- 触点 #22：AI 智能筛选 -->
        <el-button class="btn-ai-outline" @click="aiFilterVisible = true">🤖 AI 智能筛选</el-button>
        <el-button @click="router.push('/project/kanban')">📊 项目看板</el-button>
        <el-button v-permission="'project:write'" type="primary" :icon="'Plus'" @click="gotoCreate">新建项目</el-button>
      </div>
    </div>

    <!-- 4 KPI 统计卡（design 同款） -->
    <div class="kpi-row fade-up">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-label">
          <span>{{ s.label }}</span>
          <span class="stat-icon" :style="{ background: s.iconBg, color: s.iconColor }">{{ s.icon }}</span>
        </div>
        <div class="stat-value">{{ s.value }} <span class="unit">{{ s.unit }}</span></div>
        <div class="stat-delta">
          {{ s.delta }}
          <span v-if="s.deltaText" :class="['delta', s.deltaType]">{{ s.deltaText }}</span>
        </div>
      </div>
    </div>

    <!-- 4 类 status-tabs -->
    <div class="status-tabs">
      <a v-for="t in statusTabs" :key="t.key" href="javascript:void(0)"
         :class="['status-tab', { active: activeStatus === t.key }]"
         @click="activeStatus = t.key">
        {{ t.label }} <span class="num">{{ t.count }}</span>
      </a>
    </div>

    <!-- 项目卡片网格（design: 2 列） -->
    <div class="project-grid fade-up">
      <div v-for="p in filteredProjects" :key="p.id" :class="['project-card', p.priority]" @click="gotoDetail(p)">
        <div class="card-head">
          <div>
            <div class="p-id">{{ p.code }}</div>
            <h4 class="p-name">{{ p.name }}</h4>
            <div class="p-manager">负责人：{{ p.manager }}</div>
            <!-- 触点 #3：AI 风险评级 + AI 摘要（卡片内嵌） -->
            <div v-if="p.aiRiskLevel || p.aiSummary" class="ai-row">
              <AIRiskChip v-if="p.aiRiskLevel" :level="p.aiRiskLevel" />
              <span v-if="p.aiSummary" class="ai-summary-inline">{{ p.aiSummary }}</span>
            </div>
          </div>
          <span :class="['tag', `tag-${p.statusColor}`]">{{ p.statusLabel }}</span>
        </div>
        <div class="progress-row">
          <div class="progress-label">
            <span>整体进度</span>
            <span class="pct">{{ p.progress }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: p.progress + '%' }"></div>
          </div>
        </div>
        <div class="card-foot">
          <div class="d"><div class="l">开始日期</div><div class="v">{{ p.startDate }}</div></div>
          <div class="d"><div class="l">截止日期</div><div class="v">{{ p.endDate }}</div></div>
          <div class="d"><div class="l">预算</div><div class="v amount">{{ p.budget }}</div></div>
        </div>
      </div>
    </div>
  </div>

  <!-- 触点 #22：AI 智能筛选 Drawer -->
  <AiFilterDialog v-model:visible="aiFilterVisible" scope="project" @apply="onAiFilterApply" />
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }

// 4 KPI（design 同款）
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
    display: flex; justify-content: space-between; align-items: center;
    position: relative; z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: grid; place-items: center;
    font-size: 16px; font-weight: 600;
  }
  .stat-value {
    font-size: 26px; font-weight: 700;
    color: $color-text-primary;
    font-family: $font-family-mono;
    margin: 6px 0;
    position: relative; z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta {
    font-size: 12px; color: $color-text-tertiary;
    position: relative; z-index: 1;
    .delta.up { color: $color-success; font-weight: 600; margin-left: 4px; }
    .delta.plain { color: $color-text-tertiary; }
  }
}

// status-tabs（design 胶囊蓝紫）
.status-tabs {
  display: flex;
  gap: 4px;
  background: #fff;
  padding: 4px;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  margin-bottom: 16px;
  width: fit-content;
  flex-wrap: wrap;
}
.status-tab {
  padding: 8px 14px;
  border-radius: $radius-sm;
  font-size: 13px;
  color: $color-text-secondary;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  &:hover { background: $color-bg; color: $color-primary; }
  &.active {
    background: $color-primary;
    color: #fff;
    font-weight: 600;
    .num { background: rgba(255, 255, 255, 0.2); color: #fff; }
  }
  .num {
    margin-left: 4px;
    padding: 1px 6px;
    border-radius: 8px;
    background: $color-bg;
    color: $color-text-tertiary;
    font-size: 11px;
  }
}

// project-card 2 列网格
.project-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
  @media (max-width: 900px) { grid-template-columns: 1fr; }
}
.project-card {
  background: #fff;
  border-radius: $radius-lg;
  border: 1px solid $color-border;
  padding: 20px 22px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  &:hover {
    transform: translateY(-2px);
    box-shadow: $shadow-md;
  }
  &::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: $gradient-brand;
  }
  &.warning::before { background: linear-gradient(135deg, #F59E0B, #EF4444); }
  &.success::before { background: linear-gradient(135deg, #10B981, #059669); }
  &.paused::before { background: linear-gradient(135deg, #94A3B8, #64748B); }
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
  .p-id {
    font-size: 11px;
    color: $color-text-tertiary;
    font-family: $font-family-mono;
    margin-bottom: 4px;
  }
  .p-name {
    font-size: 15px;
    font-weight: 600;
    color: $color-text-primary;
    margin: 0 0 4px 0;
  }
  .p-manager {
    font-size: 12px;
    color: $color-text-secondary;
  }
  .ai-row {
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    margin-top: 6px;
  }
  .ai-summary-inline {
    font-size: 11px; color: $color-text-secondary;
    max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
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
  white-space: nowrap;
  &.tag-primary { background: $color-primary-bg; color: $color-primary; }
  &.tag-success { background: rgba(16, 185, 129, 0.1); color: $color-success; }
  &.tag-warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
  &.tag-info    { background: rgba(79, 107, 255, 0.08); color: $color-primary; }
}

// 进度条
.progress-row { margin-bottom: 16px; }
.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: $color-text-secondary;
  margin-bottom: 6px;
  .pct { font-weight: 700; color: $color-primary; font-family: $font-family-mono; }
}
.progress-bar {
  height: 6px;
  background: $color-bg;
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: $gradient-brand;
  border-radius: 3px;
  transition: width 0.3s;
}
.project-card.warning .progress-fill { background: linear-gradient(135deg, #F59E0B, #EF4444); }
.project-card.success .progress-fill { background: linear-gradient(135deg, #10B981, #059669); }
.project-card.paused .progress-fill   { background: linear-gradient(135deg, #94A3B8, #64748B); }

// 卡片底部
.card-foot {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid $color-border;
  .d { display: flex; flex-direction: column; gap: 4px; }
  .l { font-size: 11px; color: $color-text-tertiary; }
  .v { font-size: 12.5px; color: $color-text-primary; font-weight: 500; }
  .v.amount { color: $color-primary; font-weight: 600; }
}
</style>
