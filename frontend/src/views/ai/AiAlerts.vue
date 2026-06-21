<script setup lang="ts">
/**
 * AiAlerts · AI 智能提醒（无 design，按 ai-center 今日提醒 + 列表 pattern 自造）
 * - 顶部 4 KPI（紧急/重要/普通/已处理）
 * - 5 level-tabs（全部/紧急/重要/普通/已忽略）
 * - 提醒列表：左侧图标 + 等级 + 标题 + 描述 + 关联单据 + 时间 + 建议操作
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const kpis = ref([
  { label: '紧急提醒', num: 3,  color: 'danger' },
  { label: '重要提醒', num: 8,  color: 'warning' },
  { label: '普通提醒', num: 12, color: 'info' },
  { label: '已处理',   num: 28, color: 'success' },
])

const tabs = ref([
  { key: 'all',       label: '全部',     count: 51 },
  { key: 'urgent',    label: '紧急',     count: 3 },
  { key: 'important', label: '重要',     count: 8 },
  { key: 'normal',    label: '普通',     count: 12 },
  { key: 'ignored',   label: '已忽略',   count: 0 },
])
const activeTab = ref('all')

const alerts = ref([
  { id: 1, level: 'urgent',    icon: '!', title: '合同 C-2024-123 已逾期 3 天未签字',     desc: '金额 158 万，建议立即催办客户法务',                  ref: 'C-2024-123',     refLabel: '合同', time: '5 分钟前',  actions: ['立即处理', '稍后提醒'], source: '合同风险扫描' },
  { id: 2, level: 'urgent',    icon: '!', title: '银行账户余额低于安全线',                 desc: '基本户余额 ¥ 32,000，低于 5 万安全线，建议转账',     ref: 'ACC-MAIN-001',   refLabel: '账户', time: '30 分钟前', actions: ['立即处理', '稍后提醒'], source: '财务监控' },
  { id: 3, level: 'urgent',    icon: '!', title: '项目 PRJ-2026-018 客户回款逾期 5 天',   desc: '金额 128,000，建议财务部发催收函',                   ref: 'PRJ-2026-018',   refLabel: '项目', time: '1 小时前',  actions: ['立即处理', '稍后提醒'], source: '回款监控' },
  { id: 4, level: 'important', icon: '⚠', title: '发票 OCR 抽取异常',                       desc: '3 张增值税专用发票税率识别有误，建议人工复核',        ref: 'FP-2026-Q2-031~033', refLabel: '发票', time: '2 小时前',  actions: ['去复核', '忽略'], source: 'OCR 异常监控' },
  { id: 5, level: 'important', icon: '⚠', title: '5 张发票疑似重复报销',                     desc: '检测到 5 张发票在多个报销单中出现，可能存在重复入账', ref: 'FP-2026-Q2-*',   refLabel: '发票', time: '3 小时前',  actions: ['去核查', '忽略'], source: 'OCR 异常监控' },
  { id: 6, level: 'important', icon: '⚠', title: 'HT-2026-128 付款条款异常',                  desc: '付款周期超出标准 60 天，疑似风险条款',                 ref: 'C-2024-128',     refLabel: '合同', time: '5 小时前',  actions: ['查看', '忽略'], source: '合同风险扫描' },
  { id: 7, level: 'important', icon: '⚠', title: 'Q3 预算执行率已达 78%',                    desc: 'Q3 销售费用预算 ¥86.5 万，已使用 ¥67.5 万',            ref: 'BUDGET-Q3-2026', refLabel: '预算', time: '昨天',     actions: ['查看', '忽略'], source: '预算监控' },
  { id: 8, level: 'important', icon: '⚠', title: '客户云汇信息连续 2 月回款延迟',            desc: '建议评估客户信用等级',                                ref: 'CL-2026-002',    refLabel: '客户', time: '昨天',     actions: ['查看', '忽略'], source: '回款监控' },
  { id: 9, level: 'normal',    icon: '○', title: '本周回款匹配完成 124 笔',                  desc: '匹配率 91%，另有 11 笔需人工确认',                    ref: 'MATCH-2026-W24', refLabel: '匹配', time: '今天',     actions: ['查看报告'], source: '回款匹配' },
  { id: 10, level: 'normal',  icon: '○', title: '项目 PRJ-2026-022 里程碑完成 80%',          desc: '下一里程碑：联调测试 (6/20)，按计划推进',             ref: 'PRJ-2026-022',   refLabel: '项目', time: '今天',     actions: ['查看'], source: '项目跟踪' },
  { id: 11, level: 'normal',  icon: '○', title: '客户万象科技续约谈判提醒',                  desc: '原合同 6/30 到期，建议提前 30 天启动续签',             ref: 'CL-2026-001',    refLabel: '客户', time: '今天',     actions: ['查看'], source: '合同到期' },
  { id: 12, level: 'normal',  icon: '○', title: '财务月度结账日 6/30 即将到来',               desc: '建议提前 3 天准备关账数据',                            ref: 'CLOSE-2026-06',  refLabel: '结账', time: '今天',     actions: ['查看'], source: '结账提醒' },
])

const filteredAlerts = computed(() => {
  if (activeTab.value === 'all') return alerts.value
  if (activeTab.value === 'ignored') return []
  return alerts.value.filter(a => a.level === activeTab.value)
})

function handleAction(act: string, a: any) { ElMessage.success(`已操作: ${act} (${a.title})`) }
function viewRef(a: any) { ElMessage.info(`查看 ${a.refLabel}: ${a.ref}`) }
function markAll() { ElMessage.success('已全部标记为已读') }
function configure() { ElMessage.info('配置提醒规则') }
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
          <span class="current">AI 提醒</span>
        </div>
        <h1>🔔 AI 智能提醒</h1>
        <p class="page-desc">AI 自动识别的关键业务提醒，含紧急/重要/普通分级</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/ai/center')">← 返回</button>
        <button class="btn btn-outline btn-sm" @click="configure">⚙ 规则配置</button>
        <button class="btn btn-primary btn-sm" @click="markAll">✓ 全部已读</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-num">{{ k.num }}</div>
        <div class="kpi-label">{{ k.label }}</div>
      </div>
    </div>

    <!-- 5 level-tabs -->
    <div class="level-tabs">
      <div v-for="t in tabs" :key="t.key" :class="['tab', { active: activeTab === t.key }]" @click="activeTab = t.key">
        {{ t.label }} <span class="cnt">{{ t.count }}</span>
      </div>
    </div>

    <!-- 提醒列表 -->
    <div class="alert-list">
      <div v-for="a in filteredAlerts" :key="a.id" :class="['alert-item', a.level]">
        <div class="ai-icon">{{ a.icon }}</div>
        <div class="ai-body">
          <div class="ai-head">
            <span :class="['level-tag', a.level]">{{ a.level === 'urgent' ? '紧急' : a.level === 'important' ? '重要' : '普通' }}</span>
            <span class="ai-title">{{ a.title }}</span>
            <span class="ai-source">{{ a.source }}</span>
            <span class="ai-time">{{ a.time }}</span>
          </div>
          <div class="ai-desc">{{ a.desc }}</div>
          <div class="ai-meta">
            <span class="ref" @click="viewRef(a)">
              <span class="ref-label">{{ a.refLabel }}:</span>
              <span class="ref-val mono">{{ a.ref }}</span>
            </span>
          </div>
          <div class="ai-actions">
            <button v-for="act in a.actions" :key="act" :class="['btn-s', act === a.actions[0] ? 'primary' : '']" @click="handleAction(act, a)">{{ act }}</button>
          </div>
        </div>
      </div>
      <div v-if="filteredAlerts.length === 0" class="empty">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无相关提醒</div>
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
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-ai; color: $color-ai; } }
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

// level tabs
.level-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-ai; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// alert list
.alert-list { display: flex; flex-direction: column; gap: 10px; }
.alert-item { display: flex; gap: 14px; background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 14px 18px; transition: all 0.15s; &:hover { box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06); } }
.alert-item.urgent { border-left-color: $color-danger; }
.alert-item.important { border-left-color: #F59E0B; }
.alert-item.normal { border-left-color: $color-ai; }
.ai-icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font-size: 16px; font-weight: 700; flex-shrink: 0; }
.alert-item.urgent .ai-icon { background: $color-danger-bg; color: $color-danger; }
.alert-item.important .ai-icon { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.alert-item.normal .ai-icon { background: $color-ai-bg; color: $color-ai; }

.ai-body { flex: 1; min-width: 0; }
.ai-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.level-tag { font-size: 10.5px; padding: 1px 6px; border-radius: 9999px; font-weight: 600; }
.level-tag.urgent { background: $color-danger-bg; color: $color-danger; }
.level-tag.important { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.level-tag.normal { background: $color-ai-bg; color: $color-ai; }
.ai-title { font-size: 13.5px; font-weight: 600; color: $color-text-primary; }
.ai-source { font-size: 11px; color: $color-text-tertiary; padding: 1px 6px; background: $color-bg; border-radius: 9999px; }
.ai-time { font-size: 11px; color: $color-text-tertiary; margin-left: auto; font-family: $font-family-mono; }
.ai-desc { font-size: 12.5px; color: $color-text-secondary; line-height: 1.6; margin-bottom: 8px; }
.ai-meta { margin-bottom: 10px; }
.ref { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: $color-bg; border-radius: $radius-sm; cursor: pointer; transition: all 0.15s; &:hover { background: $color-ai-bg; .ref-val { color: $color-ai; } } .ref-label { font-size: 11.5px; color: $color-text-tertiary; } .ref-val { font-size: 12px; color: $color-text-primary; } }
.ai-actions { display: flex; gap: 6px; }
.btn-s { padding: 4px 10px; font-size: 12px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; } }
.mono { font-family: $font-family-mono; }

// empty
.empty { text-align: center; padding: 40px 20px; background: #fff; border: 1px dashed $color-border; border-radius: $radius-md; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.5; }
.empty-text { font-size: 13px; color: $color-text-tertiary; }
</style>
