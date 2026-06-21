<script setup lang="ts">
/**
 * AiRisk · AI 风险识别（无 design，按 ai-panel-contract 风险评分 pattern 自造）
 * - 4 KPI（高/中/低/已处理）
 * - 风险列表（4 列卡：合同/项目/发票/凭证，每条含等级、影响、建议）
 * - 右侧详情：选中风险项的 5 维健康度 + 异常事件 timeline
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 4 KPI
const kpis = ref([
  { label: '高风险事项', num: 5,  color: 'danger',  trend: '↑ 2 较上周' },
  { label: '中风险事项', num: 12, color: 'warning', trend: '↓ 3 较上周' },
  { label: '低风险事项', num: 23, color: 'info',    trend: '→ 持平' },
  { label: '本月已处理', num: 18, color: 'success', trend: '↑ 5 较上周' },
])

// 4 类筛选
const types = ref([
  { key: 'all',      label: '全部',    count: 40 },
  { key: 'contract', label: '合同风险', count: 12 },
  { key: 'project',  label: '项目风险', count: 8 },
  { key: 'invoice',  label: '发票风险', count: 15 },
  { key: 'voucher',  label: '凭证风险', count: 5 },
])
const activeType = ref('all')

// 风险列表
const risks = ref([
  { id: 1, type: '合同风险', name: 'HT-2026-123 合同逾期未签字', level: '高',  amount: 1580000, ref: 'C-2024-123', created: '2026-06-10',  desc: '合同已逾期 3 天未签字，金额 158 万，建议立即催办客户法务' },
  { id: 2, type: '合同风险', name: 'HT-2026-128 付款条款异常',   level: '高',  amount: 286000,  ref: 'C-2024-128', created: '2026-06-11',  desc: '付款周期超出标准 60 天，疑似风险条款' },
  { id: 3, type: '项目风险', name: 'PRJ-2026-018 项目严重超期',  level: '高',  amount: 128000,  ref: 'PRJ-018',    created: '2026-06-12',  desc: '项目预计完工日已过 5 天，里程碑完成率仅 68%' },
  { id: 4, type: '发票风险', name: '3 张增值税专用发票税率异常', level: '中',  amount: 86400,   ref: 'FP-2026-Q2-031~033', created: '2026-06-11', desc: 'OCR 识别税率 3% 与发票实际 13% 不符，建议人工复核' },
  { id: 5, type: '发票风险', name: '5 张发票重复报销',           level: '中',  amount: 42500,   ref: 'FP-2026-Q2-*', created: '2026-06-10',  desc: '检测到 5 张发票在多个报销单中出现，可能存在重复入账' },
  { id: 6, type: '项目风险', name: 'PRJ-2026-022 客户回款延迟',  level: '中',  amount: 96500,   ref: 'PRJ-022',    created: '2026-06-09',  desc: '客户云汇信息回款延迟 3 天，建议财务部催收' },
  { id: 7, type: '凭证风险', name: '凭证 PR-2026-0512 借贷不平', level: '低',  amount: 12800,   ref: 'PR-0512',    created: '2026-06-08',  desc: '凭证借贷方金额差 0.02 元，建议检查制单' },
  { id: 8, type: '合同风险', name: 'HT-2026-031 违约金条款缺失', level: '低',  amount: 42000,   ref: 'C-2024-031', created: '2026-06-08',  desc: '合同条款未含违约金约定，存在履约风险' },
])

const selectedRisk = ref(risks.value[0])

const filteredRisks = computed(() => {
  if (activeType.value === 'all') return risks.value
  const map: any = { contract: '合同风险', project: '项目风险', invoice: '发票风险', voucher: '凭证风险' }
  return risks.value.filter(r => r.type === map[activeType.value])
})

// 健康度 5 维（demo 数据）
const health = ref([
  { name: '履约进度',  score: 78, color: 'success' },
  { name: '付款健康',  score: 62, color: 'warning' },
  { name: '条款合规',  score: 85, color: 'success' },
  { name: '变更频率',  score: 45, color: 'danger'  },
  { name: '对方信用',  score: 72, color: 'warning' },
])

// 异常事件 timeline
const events = ref([
  { time: '2026-06-12 14:23', level: 'high',   text: '合同 C-2024-123 签字超时 3 天，触发高风险预警' },
  { time: '2026-06-11 09:15', level: 'medium', text: 'HT-2026-128 付款周期异常，系统标记为中风险' },
  { time: '2026-06-10 16:40', level: 'medium', text: '3 张发票税率识别有误，进入人工复核' },
  { time: '2026-06-08 11:20', level: 'low',    text: 'PR-2026-0512 借贷差 0.02 元，提示会计核对' },
])

function selectRisk(r: any) { selectedRisk.value = r }
function setType(t: any) { activeType.value = t.key }
function handleRisk(action: string) { ElMessage.success(`已操作: ${action}`) }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/dashboard')">首页</a>
          <span class="sep">/</span>
          <a @click="router.push('/ai/center')">数智（AI）</a>
          <span class="sep">/</span>
          <span class="current">风险识别</span>
        </div>
        <h1>⚠️ AI 风险识别</h1>
        <p class="page-desc">智能识别合同/项目/发票/凭证的潜在风险</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/ai/center')">← 返回</button>
        <button class="btn btn-primary btn-sm" @click="handleRisk('全量扫描')">🔍 全量扫描</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-num">{{ k.num }}</div>
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-trend">{{ k.trend }}</div>
      </div>
    </div>

    <!-- 类型筛选 -->
    <div class="type-tabs">
      <div v-for="t in types" :key="t.key" :class="['type-tab', { active: activeType === t.key }]" @click="setType(t)">
        {{ t.label }} <span class="cnt">({{ t.count }})</span>
      </div>
    </div>

    <!-- 双栏：左风险列表 + 右详情 -->
    <div class="risk-grid">
      <div class="risk-list">
        <div v-for="r in filteredRisks" :key="r.id" :class="['risk-item', r.level.toLowerCase(), { active: selectedRisk.id === r.id }]" @click="selectRisk(r)">
          <div class="ri-head">
            <span :class="['risk-tag', r.level.toLowerCase()]">{{ r.level }}风险</span>
            <span class="ri-type">{{ r.type }}</span>
            <span class="ri-time">{{ r.created }}</span>
          </div>
          <div class="ri-name">{{ r.name }}</div>
          <div class="ri-desc">{{ r.desc }}</div>
          <div class="ri-foot">
            <span class="ri-ref mono">{{ r.ref }}</span>
            <span class="ri-amount">¥ {{ r.amount.toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <!-- 右：详情 -->
      <div class="risk-detail" v-if="selectedRisk">
        <div class="detail-head">
          <div>
            <h3>{{ selectedRisk.name }}</h3>
            <div class="d-meta">
              <span :class="['risk-tag', selectedRisk.level.toLowerCase()]">{{ selectedRisk.level }}风险</span>
              <span>{{ selectedRisk.type }}</span>
              <span class="mono">{{ selectedRisk.ref }}</span>
            </div>
          </div>
          <div class="d-actions">
            <button class="btn-s" @click="handleRisk('标记已处理')">✓ 已处理</button>
            <button class="btn-s primary" @click="handleRisk('查看详情')">查看详情</button>
          </div>
        </div>

        <!-- 5 维健康度 -->
        <div class="detail-card">
          <div class="dc-title">5 维健康度评分</div>
          <div class="health-grid">
            <div v-for="h in health" :key="h.name" class="health-item">
              <div class="hi-name">{{ h.name }}</div>
              <div class="hi-score" :class="h.color">{{ h.score }}</div>
              <div class="hi-bar"><div :class="['fill', h.color]" :style="{ width: h.score + '%' }"></div></div>
            </div>
          </div>
        </div>

        <!-- 异常事件 timeline -->
        <div class="detail-card">
          <div class="dc-title">📅 异常事件时间线</div>
          <div class="timeline">
            <div v-for="(e, i) in events" :key="i" class="tl-row">
              <div :class="['tl-dot', e.level]"></div>
              <div class="tl-content">
                <div class="tl-time">{{ e.time }}</div>
                <div class="tl-text">{{ e.text }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- AI 建议 -->
        <div class="detail-card ai-suggest">
          <div class="dc-title">💡 AI 建议（3 条）</div>
          <ol>
            <li>立即联系客户法务催办签字，必要时发送正式催办函</li>
            <li>财务部暂扣该合同相关付款，避免进一步损失</li>
            <li>建立同类合同 30 天自动催办机制，预防逾期</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

$color-ai: #7C3AED;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-bg: rgba(124, 58, 237, 0.08);
$color-ai-border: rgba(124, 58, 237, 0.25);

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-ai; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } }
.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-ai-bg; color: $color-ai; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// KPI
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 16px 18px; }
.kpi-card.danger { border-left-color: $color-danger; .kpi-num { color: $color-danger; } }
.kpi-card.warning { border-left-color: #F59E0B; .kpi-num { color: #F59E0B; } }
.kpi-card.info { border-left-color: #64748B; .kpi-num { color: #64748B; } }
.kpi-card.success { border-left-color: $color-success; .kpi-num { color: $color-success; } }
.kpi-num { font-size: 26px; font-weight: 700; line-height: 1.2; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; margin-top: 4px; }
.kpi-trend { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

// type tabs
.type-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.type-tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 2px; } &:hover { background: $color-bg; } &.active { background: $gradient-ai; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// risk grid
.risk-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; @media (max-width: 1100px) { grid-template-columns: 1fr; } }

// risk list
.risk-list { display: flex; flex-direction: column; gap: 8px; max-height: 800px; overflow-y: auto; padding-right: 4px; }
.risk-item { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 12px 14px; cursor: pointer; transition: all 0.15s; &.active { border-color: $color-ai; box-shadow: 0 0 0 2px $color-ai-bg; } }
.risk-item.高 { border-left-color: $color-danger; }
.risk-item.中 { border-left-color: #F59E0B; }
.risk-item.低 { border-left-color: $color-ai; }
.ri-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 11px; }
.risk-tag { font-size: 10.5px; padding: 1px 6px; border-radius: 9999px; font-weight: 600; }
.risk-tag.高 { background: $color-danger-bg; color: $color-danger; }
.risk-tag.中 { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.risk-tag.低 { background: $color-ai-bg; color: $color-ai; }
.ri-type { color: $color-text-tertiary; }
.ri-time { color: $color-text-tertiary; margin-left: auto; font-family: $font-family-mono; }
.ri-name { font-size: 13.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
.ri-desc { font-size: 12px; color: $color-text-secondary; line-height: 1.5; margin-bottom: 8px; }
.ri-foot { display: flex; justify-content: space-between; font-size: 11.5px; }
.ri-ref { color: $color-text-tertiary; }
.ri-amount { color: $color-ai; font-weight: 600; font-family: $font-family-mono; }

// detail
.risk-detail { display: flex; flex-direction: column; gap: 12px; }
.detail-head { display: flex; justify-content: space-between; align-items: flex-start; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 14px 16px; h3 { font-size: 15px; font-weight: 600; margin: 0 0 6px 0; } .d-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: $color-text-secondary; } }
.d-actions { display: flex; gap: 6px; }
.btn-s { padding: 6px 12px; font-size: 12px; background: #fff; border: 1px solid $color-border; color: $color-text-primary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; } }
.detail-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 14px 16px; }
.dc-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 12px; }
.ai-suggest { background: $color-ai-bg; border-color: $color-ai-border; }
.ai-suggest ol { margin: 0; padding-left: 20px; color: $color-text-primary; font-size: 12.5px; line-height: 1.8; }

// health
.health-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.health-item { text-align: center; }
.hi-name { font-size: 11.5px; color: $color-text-tertiary; margin-bottom: 4px; }
.hi-score { font-size: 22px; font-weight: 700; line-height: 1.2; }
.hi-score.success { color: $color-success; }
.hi-score.warning { color: #F59E0B; }
.hi-score.danger { color: $color-danger; }
.hi-bar { height: 4px; background: $color-bg; border-radius: 2px; overflow: hidden; margin-top: 6px; }
.hi-bar .fill { height: 100%; border-radius: 2px; }
.hi-bar .fill.success { background: $color-success; }
.hi-bar .fill.warning { background: #F59E0B; }
.hi-bar .fill.danger { background: $color-danger; }

// timeline
.timeline { padding-left: 14px; border-left: 2px dashed $color-border; }
.tl-row { position: relative; padding: 4px 0 4px 16px; }
.tl-dot { position: absolute; left: -7px; top: 8px; width: 12px; height: 12px; border-radius: 50%; background: $color-ai; box-shadow: 0 0 0 3px #fff; }
.tl-dot.high { background: $color-danger; }
.tl-dot.medium { background: #F59E0B; }
.tl-dot.low { background: $color-ai; }
.tl-time { font-size: 11px; color: $color-text-tertiary; font-family: $font-family-mono; margin-bottom: 2px; }
.tl-text { font-size: 12.5px; color: $color-text-primary; line-height: 1.5; }
</style>
