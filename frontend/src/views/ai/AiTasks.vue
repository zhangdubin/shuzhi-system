<script setup lang="ts">
/**
 * AiTasks · AI 任务中心（无 design，按 ai-center 任务列表 + 状态时间线 pattern 自造）
 * - 4 KPI（总任务/进行中/已完成/失败）
 * - 5 status-tabs（全部/进行中/已完成/失败/排队）
 * - 任务表格（任务名/类型/进度/状态/创建时间/操作）
 * - 详情抽屉：选中任务显示进度 + 子步骤 timeline
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const kpis = ref([
  { label: '总任务',   num: 142,  color: 'info' },
  { label: '进行中',   num: 8,    color: 'ai' },
  { label: '已完成',   num: 128,  color: 'success' },
  { label: '失败',     num: 6,    color: 'danger' },
])

const tabs = ref([
  { key: 'all',      label: '全部',    count: 142 },
  { key: 'running',  label: '进行中',  count: 8 },
  { key: 'done',     label: '已完成',  count: 128 },
  { key: 'failed',   label: '失败',    count: 6 },
  { key: 'pending',  label: '排队',    count: 0 },
])
const activeTab = ref('all')

const tasks = ref([
  { id: 1, name: '批量发票识别 - 差旅报销 5月',    type: 'OCR',    icon: '📷', progress: 40,  status: 'running', created: '14:23', desc: '处理中 · 23/58', eta: '12 秒' },
  { id: 2, name: '合同风险扫描 - 数智化二期',      type: '风险扫描', icon: '📄', progress: 65, status: 'running', created: '14:20', desc: '分析中',          eta: '8 秒' },
  { id: 3, name: '银行流水匹配 - 6月第2周',         type: '匹配',   icon: '🔗', progress: 80, status: 'running', created: '14:18', desc: '匹配中',          eta: '5 秒' },
  { id: 4, name: '日报生成 - 6 月 12 日',            type: '生成',   icon: '✓',  progress: 100, status: 'done',    created: '14:15', desc: '已完成 · 2 分钟前', eta: '-' },
  { id: 5, name: '回款逾期分析',                     type: '分析',   icon: '⚠',  progress: 0,   status: 'failed',  created: '14:10', desc: '失败 · 模型超时',  eta: '-' },
  { id: 6, name: '客户画像更新 - 168 家',            type: '画像',   icon: '👥', progress: 100, status: 'done',    created: '13:50', desc: '已完成 · 30 分钟前', eta: '-' },
  { id: 7, name: '销售费用自动归类 - 6月',            type: '分类',   icon: '📊', progress: 100, status: 'done',    created: '12:30', desc: '已完成 · 1 小时前', eta: '-' },
  { id: 8, name: '合同相似度检测 - 86 份',             type: '检测',   icon: '🔍', progress: 100, status: 'done',    created: '11:20', desc: '已完成 · 2 小时前', eta: '-' },
  { id: 9, name: '月报生成 - 2026-05',                type: '生成',   icon: '📝', progress: 0,   status: 'failed',  created: '09:00', desc: '失败 · 数据源缺失', eta: '-' },
  { id: 10, name: '凭证审核 - PR-2026-0512',          type: '审核',   icon: '✓', progress: 100, status: 'done',   created: '昨天',   desc: '已完成',          eta: '-' },
])

const selectedTask = ref<any>(null)

const filteredTasks = computed(() => {
  if (activeTab.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === activeTab.value)
})

function selectTask(t: any) { selectedTask.value = t }
function closeDetail() { selectedTask.value = null }
function retryTask(t: any) { ElMessage.success(`已重试: ${t.name}`) }
function cancelTask(t: any) { ElMessage.info(`已取消: ${t.name}`) }
function viewReport(t: any) { ElMessage.success(`查看报告: ${t.name}`) }
function createTask() { ElMessage.info('新建任务') }
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
          <span class="current">任务中心</span>
        </div>
        <h1>⚡ AI 任务中心</h1>
        <p class="page-desc">查看所有 AI 任务运行状态，支持重试/取消/详情</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/ai/center')">← 返回</button>
        <button class="btn btn-primary btn-sm" @click="createTask">+ 新建任务</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-num">{{ k.num }}</div>
        <div class="kpi-label">{{ k.label }}</div>
      </div>
    </div>

    <!-- 5 status-tabs -->
    <div class="status-tabs">
      <div v-for="t in tabs" :key="t.key" :class="['tab', { active: activeTab === t.key }]" @click="activeTab = t.key">
        {{ t.label }} <span class="cnt">{{ t.count }}</span>
      </div>
    </div>

    <!-- 任务表格 -->
    <div class="task-card">
      <table class="tpl-table">
        <thead>
          <tr>
            <th style="width: 40px;"></th>
            <th>任务名</th>
            <th>类型</th>
            <th>进度</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>预计耗时</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in filteredTasks" :key="t.id" :class="{ active: selectedTask?.id === t.id }" @click="selectTask(t)">
            <td><span class="t-icon">{{ t.icon }}</span></td>
            <td>
              <div class="t-name">{{ t.name }}</div>
              <div class="t-desc">{{ t.desc }}</div>
            </td>
            <td><span class="t-type">{{ t.type }}</span></td>
            <td>
              <div class="progress">
                <div class="progress-bg"><div :class="['progress-fill', t.status]" :style="{ width: t.progress + '%' }"></div></div>
                <span class="progress-num">{{ t.progress }}%</span>
              </div>
            </td>
            <td>
              <span :class="['tag', t.status]">
                <span v-if="t.status === 'running'" class="dots"><span></span><span></span><span></span></span>
                {{ t.status === 'running' ? '进行中' : t.status === 'done' ? '已完成' : t.status === 'failed' ? '失败' : '排队' }}
              </span>
            </td>
            <td><span class="mono">{{ t.created }}</span></td>
            <td><span class="mono">{{ t.eta }}</span></td>
            <td>
              <div class="t-actions">
                <button v-if="t.status === 'failed'" class="ta-btn retry" @click.stop="retryTask(t)">↻ 重试</button>
                <button v-if="t.status === 'running'" class="ta-btn" @click.stop="cancelTask(t)">取消</button>
                <button v-if="t.status === 'done'" class="ta-btn" @click.stop="viewReport(t)">查看</button>
                <button v-else class="ta-btn" @click.stop="selectTask(t)">详情</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 详情抽屉（覆盖层） -->
    <div v-if="selectedTask" class="detail-mask" @click="closeDetail">
      <div class="detail-drawer" @click.stop>
        <div class="drawer-head">
          <h3>{{ selectedTask.name }}</h3>
          <button class="drawer-close" @click="closeDetail">×</button>
        </div>
        <div class="drawer-body">
          <div class="d-meta">
            <span :class="['tag', selectedTask.status]">
              {{ selectedTask.status === 'running' ? '进行中' : selectedTask.status === 'done' ? '已完成' : '失败' }}
            </span>
            <span>{{ selectedTask.type }}</span>
            <span class="mono">ID: {{ selectedTask.id }}</span>
            <span class="mono">{{ selectedTask.created }}</span>
          </div>
          <div class="d-progress">
            <div class="dp-bar"><div :class="['dp-fill', selectedTask.status]" :style="{ width: selectedTask.progress + '%' }"></div></div>
            <span class="dp-num">{{ selectedTask.progress }}%</span>
          </div>
          <h4 class="sub-title">任务步骤</h4>
          <div class="step-timeline">
            <div class="step done">
              <div class="step-dot">✓</div>
              <div class="step-content">
                <div class="step-name">任务创建</div>
                <div class="step-time">{{ selectedTask.created }}</div>
              </div>
            </div>
            <div class="step done">
              <div class="step-dot">✓</div>
              <div class="step-content">
                <div class="step-name">参数校验</div>
                <div class="step-time">{{ selectedTask.created }}</div>
              </div>
            </div>
            <div class="step" :class="selectedTask.status === 'running' ? 'active' : selectedTask.status === 'failed' ? 'failed' : 'done'">
              <div class="step-dot">{{ selectedTask.status === 'failed' ? '✕' : '●' }}</div>
              <div class="step-content">
                <div class="step-name">模型推理</div>
                <div class="step-time">{{ selectedTask.status === 'running' ? '进行中...' : selectedTask.status === 'done' ? '已完成' : '失败 · 模型超时' }}</div>
              </div>
            </div>
            <div class="step" :class="selectedTask.status === 'done' ? 'done' : 'pending'">
              <div class="step-dot">4</div>
              <div class="step-content">
                <div class="step-name">结果入库</div>
                <div class="step-time">{{ selectedTask.status === 'done' ? '已完成' : '等待中' }}</div>
              </div>
            </div>
          </div>
          <h4 class="sub-title">任务参数</h4>
          <div class="param-list">
            <div class="param"><span>模型</span><span>PaddleOCR v3.2</span></div>
            <div class="param"><span>并发</span><span>4</span></div>
            <div class="param"><span>超时</span><span>30 秒</span></div>
            <div class="param"><span>回调</span><span class="mono">/api/ai/task/callback</span></div>
          </div>
        </div>
        <div class="drawer-foot">
          <button class="btn-s" @click="closeDetail">关闭</button>
          <button v-if="selectedTask.status === 'failed'" class="btn-s primary" @click="retryTask(selectedTask)">↻ 重试</button>
          <button v-if="selectedTask.status === 'done'" class="btn-s primary" @click="viewReport(selectedTask)">查看报告</button>
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
.kpi-card.info { border-left-color: #64748B; .kpi-num { color: #64748B; } }
.kpi-card.ai { border-left-color: $color-ai; .kpi-num { color: $color-ai; } }
.kpi-card.success { border-left-color: $color-success; .kpi-num { color: $color-success; } }
.kpi-card.danger { border-left-color: $color-danger; .kpi-num { color: $color-danger; } }
.kpi-num { font-size: 26px; font-weight: 700; line-height: 1.2; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; margin-top: 4px; }

// status tabs
.status-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-ai; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// task table
.task-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; }
.tpl-table td { padding: 12px; border-bottom: 1px solid $color-border; }
.tpl-table tbody tr { cursor: pointer; transition: background 0.15s; &:hover { background: $color-bg; } &.active { background: $color-ai-bg; } }
.t-icon { font-size: 18px; }
.t-name { font-size: 13px; font-weight: 500; color: $color-text-primary; margin-bottom: 2px; }
.t-desc { font-size: 11.5px; color: $color-text-tertiary; }
.t-type { font-size: 11.5px; padding: 2px 8px; background: $color-ai-bg; color: $color-ai; border-radius: 9999px; }

// progress
.progress { display: flex; align-items: center; gap: 8px; }
.progress-bg { flex: 1; height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; min-width: 80px; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.progress-fill.running { background: $gradient-ai; }
.progress-fill.done { background: $color-success; }
.progress-fill.failed { background: $color-danger; }
.progress-num { font-size: 11px; font-family: $font-family-mono; color: $color-text-secondary; min-width: 32px; text-align: right; }

// tag
.tag { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.running { background: $color-ai-bg; color: $color-ai; }
.tag.done { background: $color-success-bg; color: $color-success; }
.tag.failed { background: $color-danger-bg; color: $color-danger; }
.tag.pending { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.dots { display: inline-flex; gap: 2px; }
.dots span { width: 4px; height: 4px; background: $color-ai; border-radius: 50%; animation: bounce 1.4s infinite; }
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

// actions
.t-actions { display: flex; gap: 4px; }
.ta-btn { padding: 3px 8px; font-size: 11.5px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.retry { color: $color-ai; border-color: $color-ai-border; &:hover { background: $color-ai; color: #fff; } } }
.mono { font-family: $font-family-mono; color: $color-text-secondary; }

// drawer
.detail-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.4); z-index: 100; display: flex; justify-content: flex-end; animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.detail-drawer { width: 480px; max-width: 90%; background: #fff; height: 100vh; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(15, 23, 42, 0.15); animation: slideIn 0.25s; }
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.drawer-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid $color-border; background: #FAFBFF; h3 { font-size: 15px; font-weight: 600; margin: 0; } }
.drawer-close { width: 28px; height: 28px; border-radius: 50%; background: transparent; border: none; font-size: 20px; color: $color-text-tertiary; cursor: pointer; &:hover { background: $color-bg; color: $color-text-primary; } }
.drawer-body { flex: 1; padding: 18px 20px; overflow-y: auto; }
.drawer-foot { padding: 12px 20px; border-top: 1px solid $color-border; display: flex; justify-content: flex-end; gap: 8px; background: #FAFBFF; }
.btn-s { padding: 6px 12px; font-size: 12.5px; background: #fff; border: 1px solid $color-border; color: $color-text-primary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; } }
.d-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: $color-text-secondary; margin-bottom: 12px; }
.d-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; .dp-bar { flex: 1; height: 8px; background: $color-bg; border-radius: 4px; overflow: hidden; } .dp-fill { height: 100%; border-radius: 4px; } .dp-fill.running { background: $gradient-ai; } .dp-fill.done { background: $color-success; } .dp-fill.failed { background: $color-danger; } .dp-num { font-size: 13px; font-weight: 600; font-family: $font-family-mono; } }
.sub-title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin: 16px 0 10px 0; }
.step-timeline { padding-left: 14px; border-left: 2px dashed $color-border; }
.step { position: relative; padding: 4px 0 4px 18px; }
.step-dot { position: absolute; left: -10px; top: 4px; width: 18px; height: 18px; border-radius: 50%; background: $color-bg; color: $color-text-tertiary; display: grid; place-items: center; font-size: 11px; font-weight: 600; }
.step.done .step-dot { background: $color-success; color: #fff; }
.step.active .step-dot { background: $gradient-ai; color: #fff; animation: pulse 1.4s infinite; }
.step.failed .step-dot { background: $color-danger; color: #fff; }
.step.pending .step-dot { background: $color-bg; color: $color-text-tertiary; }
@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.5); } 50% { box-shadow: 0 0 0 6px rgba(124, 58, 237, 0); } }
.step-content { .step-name { font-size: 12.5px; color: $color-text-primary; } .step-time { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; font-family: $font-family-mono; } }
.param-list { background: $color-bg; border-radius: $radius-md; padding: 10px 14px; }
.param { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; .mono { font-family: $font-family-mono; } > span:first-child { color: $color-text-tertiary; } > span:last-child { color: $color-text-primary; } }
</style>
