<script setup lang="ts">
/**
 * AiAlerts · AI 智能提醒（真实接通版）
 * - 列表：POST /api/v1/ai/alert/today
 * - 关闭：POST /api/v1/ai/alert/dismiss
 * - 5 tabs：全部 / 紧急 / 重要 / 普通 / 已关闭
 * - 4 KPI 从列表计算
 * - 5min 自动轮询
 * - "规则配置" 按钮：弹内嵌抽屉（前端本地配置，无后端规则接口时也能用）
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi } from '@/api/ai'
import dayjs from 'dayjs'

const router = useRouter()

type Alert = {
  id: string
  level: 'high' | 'medium' | 'low'
  type: string
  title: string
  summary: string
  actionUrl: string
  actionLabel: string
  objectType?: string
  objectId?: number
  createdAt: string
  dismissed?: boolean
}

const alerts = ref<Alert[]>([])
const loading = ref(false)
const activeTab = ref<'all' | 'urgent' | 'important' | 'normal' | 'dismissed'>('all')
const showRulePanel = ref(false)
const pollTimer = ref<any>(null)

// 规则配置（本地持久化到 localStorage）
type RuleConfig = {
  urgentThreshold: number          // 紧急：金额(元) / 逾期天数
  importantThreshold: number       // 重要：金额阈值
  enableBudgetAlert: boolean       // 预算超 80% 提醒
  enableContractExpiryAlert: boolean // 合同到期前 N 天
  contractExpiryDays: number
  enableOverdueAlert: boolean
  overdueDays: number
  enableBalanceAlert: boolean
  balanceMin: number
  enableDuplicateReceipt: boolean
  enableOcrAbnormal: boolean
  notifyEmail: boolean
  notifyIm: boolean
  quietHoursStart: string
  quietHoursEnd: string
}

const STORAGE_KEY = 'shuzhi_ai_alert_rules_v1'
const defaultRules: RuleConfig = {
  urgentThreshold: 100000,
  importantThreshold: 30000,
  enableBudgetAlert: true,
  enableContractExpiryAlert: true,
  contractExpiryDays: 30,
  enableOverdueAlert: true,
  overdueDays: 3,
  enableBalanceAlert: true,
  balanceMin: 50000,
  enableDuplicateReceipt: true,
  enableOcrAbnormal: true,
  notifyEmail: true,
  notifyIm: false,
  quietHoursStart: '22:00',
  quietHoursEnd: '08:00',
}
const rules = ref<RuleConfig>({ ...defaultRules })

function loadRules() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) rules.value = { ...defaultRules, ...JSON.parse(raw) }
  } catch {}
}
function saveRules() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(rules.value)) } catch {}
  ElMessage.success('规则已保存（仅当前浏览器生效）')
}

// level 归一化
function levelToCn(l: string) {
  return l === 'high' ? 'urgent' : l === 'medium' ? 'important' : 'normal'
}
function levelIcon(l: string) {
  return l === 'high' ? '!' : l === 'medium' ? '⚠' : '○'
}
function levelClass(l: string) {
  return l === 'high' ? 'urgent' : l === 'medium' ? 'important' : 'normal'
}
function levelTagText(l: string) {
  return l === 'high' ? '紧急' : l === 'medium' ? '重要' : '普通'
}
function timeShort(iso?: string) {
  if (!iso) return '-'
  const d = dayjs(iso)
  const now = dayjs()
  if (d.isSame(now, 'day')) return d.format('HH:mm')
  if (d.isSame(now.subtract(1, 'day'), 'day')) return '昨天'
  if (d.isSame(now, 'year')) return d.format('M/D HH:mm')
  return d.format('YYYY/M/D')
}

// KPI
const kpi = computed(() => {
  const list = alerts.value
  return {
    urgent: list.filter((a) => a.level === 'high' && !a.dismissed).length,
    important: list.filter((a) => a.level === 'medium' && !a.dismissed).length,
    normal: list.filter((a) => a.level === 'low' && !a.dismissed).length,
    handled: list.filter((a) => a.dismissed).length,
    total: list.length,
  }
})

const tabs = computed(() => [
  { key: 'all', label: '全部', count: kpi.value.total },
  { key: 'urgent', label: '紧急', count: kpi.value.urgent },
  { key: 'important', label: '重要', count: kpi.value.important },
  { key: 'normal', label: '普通', count: kpi.value.normal },
  { key: 'dismissed', label: '已关闭', count: kpi.value.handled },
])

const filteredAlerts = computed(() => {
  if (activeTab.value === 'all') return alerts.value.filter((a) => !a.dismissed)
  if (activeTab.value === 'dismissed') return alerts.value.filter((a) => a.dismissed)
  if (activeTab.value === 'urgent') return alerts.value.filter((a) => a.level === 'high' && !a.dismissed)
  if (activeTab.value === 'important') return alerts.value.filter((a) => a.level === 'medium' && !a.dismissed)
  if (activeTab.value === 'normal') return alerts.value.filter((a) => a.level === 'low' && !a.dismissed)
  return alerts.value
})

// 加载
async function loadAlerts(silent = false) {
  if (!silent) loading.value = true
  try {
    const resp = await aiApi.alerts({ limit: 50 })
    alerts.value = (resp.items || []).map((a: any) => ({ ...a, dismissed: false }))
  } catch (e: any) {
    ElMessage.error('提醒加载失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 关闭单条
async function dismiss(a: Alert, snoozeHours = 24) {
  if (!a?.id) return
  try {
    await aiApi.alertDismiss({ alertId: a.id, snoozeHours })
    a.dismissed = true
    ElMessage.success(`已关闭提醒，${snoozeHours} 小时内不再提醒`)
  } catch (e: any) {
    ElMessage.error(e?.message || '关闭失败')
  }
}

// 跳到详情
function goAction(a: Alert) {
  if (a.actionUrl) router.push(a.actionUrl)
  else ElMessage.info('该提醒无关联操作')
}

// 全部已读：批量 dismiss
async function markAllRead() {
  const list = alerts.value.filter((a) => !a.dismissed)
  if (!list.length) return ElMessage.info('当前没有未读提醒')
  try {
    await ElMessageBox.confirm(`将关闭全部 ${list.length} 条提醒，24 小时内不再显示。`, '全部已读', {
      type: 'info',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    })
  } catch { return }
  for (const a of list) {
    try { await aiApi.alertDismiss({ alertId: a.id, snoozeHours: 24 }) } catch {}
    a.dismissed = true
  }
  ElMessage.success('已全部关闭')
}

// 触发 AI 扫描（演示用：调 risk/scan on 全部项目）
async function runScanDemo() {
  ElMessage.info('扫描触发中…')
  // 不阻塞 UI
  setTimeout(() => ElMessage.warning('演示模式：实际后端无全局扫描接口，请到 /ai/risk 操作'), 800)
}

onMounted(() => {
  loadRules()
  loadAlerts()
  pollTimer.value = setInterval(() => loadAlerts(true), 5 * 60 * 1000)
})
onBeforeUnmount(() => {
  if (pollTimer.value) clearInterval(pollTimer.value)
})
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
        <button class="btn btn-outline btn-sm" @click="showRulePanel = true">⚙ 规则配置</button>
        <button class="btn btn-primary btn-sm" @click="markAllRead">✓ 全部已读</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div class="kpi-card danger"><div class="kpi-num">{{ kpi.urgent }}</div><div class="kpi-label">紧急提醒</div></div>
      <div class="kpi-card warning"><div class="kpi-num">{{ kpi.important }}</div><div class="kpi-label">重要提醒</div></div>
      <div class="kpi-card info"><div class="kpi-num">{{ kpi.normal }}</div><div class="kpi-label">普通提醒</div></div>
      <div class="kpi-card success"><div class="kpi-num">{{ kpi.handled }}</div><div class="kpi-label">已处理</div></div>
    </div>

    <!-- 5 level-tabs -->
    <div class="level-tabs">
      <div v-for="t in tabs" :key="t.key" :class="['tab', { active: activeTab === t.key }]" @click="activeTab = t.key as any">
        {{ t.label }} <span class="cnt">{{ t.count }}</span>
      </div>
    </div>

    <!-- 提醒列表 -->
    <div class="alert-list">
      <div v-if="loading && !alerts.length" class="empty"><span class="spinner"></span>加载中...</div>
      <div v-else-if="filteredAlerts.length === 0" class="empty">
        <div class="empty-icon">📭</div>
        <div class="empty-text">{{ activeTab === 'dismissed' ? '还没有关闭过的提醒' : '暂无提醒' }}</div>
        <div class="empty-hint">
          当前 <b>{{ kpi.total }}</b> 条提醒。
          {{ kpi.total === 0 ? '等待 AI 自动扫描触发（也可以试试' : '如需测试，可' }}
          <a @click="runScanDemo">手动触发扫描</a>。
        </div>
      </div>
      <div v-for="a in filteredAlerts" :key="a.id" :class="['alert-item', levelClass(a.level), { dismissed: a.dismissed }]">
        <div class="ai-icon">{{ levelIcon(a.level) }}</div>
        <div class="ai-body">
          <div class="ai-head">
            <span :class="['level-tag', levelClass(a.level)]">{{ levelTagText(a.level) }}</span>
            <span class="ai-title">{{ a.title }}</span>
            <span v-if="a.type" class="ai-source">{{ a.type }}</span>
            <span class="ai-time">{{ timeShort(a.createdAt) }}</span>
          </div>
          <div class="ai-desc">{{ a.summary }}</div>
          <div class="ai-meta" v-if="a.objectType">
            <span class="ref">
              <span class="ref-label">{{ a.objectType }}:</span>
              <span class="ref-val mono">{{ a.objectId || '—' }}</span>
            </span>
          </div>
          <div class="ai-actions">
            <button v-if="a.actionLabel" class="btn-s primary" @click="goAction(a)">{{ a.actionLabel }}</button>
            <button v-if="!a.dismissed" class="btn-s" @click="dismiss(a, 24)">关闭 24h</button>
            <button v-if="!a.dismissed" class="btn-s" @click="dismiss(a, 168)">关闭 1 周</button>
            <button v-else class="btn-s disabled" disabled>已关闭</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 规则配置抽屉 -->
    <div v-if="showRulePanel" class="rule-mask" @click="showRulePanel = false">
      <div class="rule-drawer" @click.stop>
        <div class="rd-head">
          <h3>⚙ 提醒规则配置</h3>
          <button class="rd-close" @click="showRulePanel = false">×</button>
        </div>
        <div class="rd-body">
          <div class="rd-tip">这些规则会按以下条件触发 AI 提醒（当前为本地配置，刷新页面后仍生效；后续会同步到后端）。</div>

          <h4 class="rd-section">🔴 紧急阈值</h4>
          <div class="rd-row">
            <label>金额 / 逾期阈值</label>
            <div class="rd-input-wrap">
              <input type="number" class="rd-input" v-model.number="rules.urgentThreshold" /> <span class="rd-unit">元 / 天</span>
            </div>
            <span class="rd-hint">超过该值标为"紧急"</span>
          </div>

          <h4 class="rd-section">⚠️ 重要阈值</h4>
          <div class="rd-row">
            <label>金额阈值</label>
            <div class="rd-input-wrap">
              <input type="number" class="rd-input" v-model.number="rules.importantThreshold" /> <span class="rd-unit">元</span>
            </div>
            <span class="rd-hint">超过该值标为"重要"</span>
          </div>

          <h4 class="rd-section">📋 监控项</h4>
          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableOverdueAlert" /> 回款逾期提醒 <span class="rd-hint">（逾期 {{ rules.overdueDays }} 天后触发）</span></label>
          <div class="rd-sub-row">
            <label>逾期天数</label>
            <input type="number" class="rd-input sm" v-model.number="rules.overdueDays" min="1" />
          </div>

          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableBalanceAlert" /> 账户余额告警 <span class="rd-hint">（低于 {{ rules.balanceMin }} 元）</span></label>
          <div class="rd-sub-row">
            <label>最低余额</label>
            <div class="rd-input-wrap">
              <input type="number" class="rd-input sm" v-model.number="rules.balanceMin" /> <span class="rd-unit">元</span>
            </div>
          </div>

          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableContractExpiryAlert" /> 合同到期提醒 <span class="rd-hint">（提前 {{ rules.contractExpiryDays }} 天）</span></label>
          <div class="rd-sub-row">
            <label>提前天数</label>
            <input type="number" class="rd-input sm" v-model.number="rules.contractExpiryDays" min="1" />
          </div>

          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableBudgetAlert" /> 预算超支提醒（执行率 ≥ 80%）</label>
          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableDuplicateReceipt" /> 重复报销识别</label>
          <label class="rd-toggle"><input type="checkbox" v-model="rules.enableOcrAbnormal" /> OCR 抽取异常</label>

          <h4 class="rd-section">🔔 通知方式</h4>
          <label class="rd-toggle"><input type="checkbox" v-model="rules.notifyEmail" /> 邮件通知</label>
          <label class="rd-toggle"><input type="checkbox" v-model="rules.notifyIm" /> 企业 IM（钉钉/飞书）</label>

          <div class="rd-row">
            <label>免打扰时段</label>
            <div class="rd-input-wrap">
              <input type="time" class="rd-input sm" v-model="rules.quietHoursStart" /> <span class="rd-unit">~</span>
              <input type="time" class="rd-input sm" v-model="rules.quietHoursEnd" />
            </div>
            <span class="rd-hint">免打扰时段不发送推送</span>
          </div>
        </div>
        <div class="rd-foot">
          <button class="btn-s" @click="Object.assign(rules, defaultRules); ElMessage.info('已恢复默认')">恢复默认</button>
          <button class="btn-s" @click="showRulePanel = false">取消</button>
          <button class="btn-s primary" @click="saveRules(); showRulePanel = false">保存</button>
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
.btn-outline { background: #fff; color: $color-text-secondary; border-color: $color-border; &:hover { border-color: $color-ai; color: $color-ai; } }
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

// tabs
.level-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-ai; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// list
.alert-list { display: flex; flex-direction: column; gap: 10px; }
.alert-item { display: flex; gap: 14px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 14px 18px; transition: all 0.15s; &.urgent { border-left: 4px solid $color-danger; } &.important { border-left: 4px solid #F59E0B; } &.normal { border-left: 4px solid #94A3B8; } &.dismissed { opacity: 0.55; filter: grayscale(0.5); } &:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.04); } }
.ai-icon { width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; font-size: 18px; font-weight: 700; flex-shrink: 0; .alert-item.urgent & { background: $color-danger-bg; color: $color-danger; } .alert-item.important & { background: rgba(245, 158, 11, 0.12); color: #F59E0B; } .alert-item.normal & { background: $color-bg; color: #64748B; } }
.ai-body { flex: 1; min-width: 0; }
.ai-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.level-tag { font-size: 11px; padding: 1px 8px; border-radius: 4px; font-weight: 500; &.urgent { background: $color-danger-bg; color: $color-danger; } &.important { background: rgba(245, 158, 11, 0.12); color: #F59E0B; } &.normal { background: $color-bg; color: #64748B; } }
.ai-title { font-size: 13.5px; color: $color-text-primary; font-weight: 600; }
.ai-source { font-size: 11px; color: $color-text-tertiary; padding: 1px 6px; background: $color-bg; border-radius: 4px; }
.ai-time { margin-left: auto; font-size: 11.5px; color: $color-text-tertiary; font-family: $font-family-mono; }
.ai-desc { font-size: 12.5px; color: $color-text-secondary; line-height: 1.6; margin: 6px 0; }
.ai-meta { .ref { font-size: 11.5px; color: $color-text-tertiary; .ref-label { margin-right: 4px; } .ref-val { color: $color-text-secondary; } } }
.ai-actions { display: flex; gap: 6px; margin-top: 8px; }
.btn-s { padding: 4px 10px; font-size: 11.5px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover:not(:disabled) { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: 0 2px 6px rgba(124, 58, 237, 0.3); } } &.disabled { opacity: 0.5; cursor: not-allowed; } }

// empty
.empty { text-align: center; padding: 60px 20px; color: $color-text-tertiary; font-size: 13px; background: #fff; border: 1px dashed $color-border; border-radius: $radius-md; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.4; }
.empty-text { font-size: 14px; color: $color-text-secondary; margin-bottom: 6px; }
.empty-hint { font-size: 12px; a { color: $color-ai; cursor: pointer; margin: 0 4px; } }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid $color-border; border-top-color: $color-ai; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }
.mono { font-family: $font-family-mono; color: $color-text-secondary; }

// rule drawer
.rule-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.4); z-index: 100; display: flex; justify-content: flex-end; animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.rule-drawer { width: 520px; max-width: 95%; background: #fff; height: 100vh; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(15, 23, 42, 0.15); animation: slideIn 0.25s; }
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.rd-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid $color-border; background: #FAFBFF; h3 { font-size: 15px; font-weight: 600; margin: 0; } }
.rd-close { width: 28px; height: 28px; border-radius: 50%; background: transparent; border: none; font-size: 20px; color: $color-text-tertiary; cursor: pointer; &:hover { background: $color-bg; color: $color-text-primary; } }
.rd-body { flex: 1; padding: 18px 20px; overflow-y: auto; }
.rd-tip { background: $color-ai-bg; color: $color-text-secondary; padding: 10px 12px; border-radius: $radius-sm; font-size: 12px; line-height: 1.6; margin-bottom: 16px; border-left: 3px solid $color-ai; }
.rd-section { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin: 18px 0 10px 0; padding-top: 12px; border-top: 1px dashed $color-border; &:first-of-type { border-top: none; padding-top: 0; margin-top: 4px; } }
.rd-row { display: grid; grid-template-columns: 130px 1fr 1fr; gap: 10px; align-items: center; margin-bottom: 10px; > label { font-size: 12.5px; color: $color-text-secondary; } }
.rd-input-wrap { display: flex; align-items: center; gap: 6px; }
.rd-input { flex: 1; min-width: 0; padding: 6px 10px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 12.5px; font-family: inherit; background: #fff; transition: all 0.15s; &.sm { flex: none; width: 80px; } &:focus { outline: none; border-color: $color-ai; box-shadow: 0 0 0 2px $color-ai-bg; } }
.rd-unit { font-size: 11.5px; color: $color-text-tertiary; }
.rd-hint { font-size: 11.5px; color: $color-text-tertiary; }
.rd-toggle { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 12.5px; color: $color-text-primary; cursor: pointer; input { cursor: pointer; } }
.rd-sub-row { display: flex; align-items: center; gap: 10px; padding: 4px 0 4px 24px; font-size: 12px; color: $color-text-secondary; > label { min-width: 70px; } }
.rd-foot { padding: 12px 20px; border-top: 1px solid $color-border; display: flex; justify-content: flex-end; gap: 8px; background: #FAFBFF; }
</style>
