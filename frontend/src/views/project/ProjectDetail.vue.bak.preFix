<script setup lang="ts">
/**
 * ProjectDetail · 项目详情（1:1 复刻 design/project-detail.html）
 * - project-hero（蓝紫渐变 + 编号 + 名称 + 进度 + 4 stat + 状态）
 * - detail-tabs 4 个（基本信息/里程碑/合同/团队）
 * - detail-section × 3（项目信息/关联合同/项目团队/风险预警/关联发票/里程碑）
 * - meta-card × N（关键时间/状态/风险提示）
 */
import { ref, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api/modules'
import AiRiskScanPanel from '@/components/ai/AiRiskScanPanel.vue'

// 触点 #4：AI 风险扫描回调
const aiWarnCount = ref(0)
function onAiLoaded(result: any) {
  aiWarnCount.value = result.warnings?.length || 0
  ElMessage.success(`AI 扫描完成 · 健康分 ${result.overallScore}`)
}
function onAiError(err: Error) { ElMessage.error(`AI 扫描失败: ${err.message}`) }
function onAiAccept(s: any) { ElMessage.success(`已采纳: ${s.title}`) }
function onAiDismiss(w: any) { ElMessage.info(`已忽略: ${w.title}`) }
function onAiFeedback(p: any) { console.log('[ai feedback]', p) }

const router = useRouter()
const route = useRoute()

const activeTab = ref<'basic' | 'milestones' | 'contracts' | 'team' | 'ai'>('basic')
const loading = ref(false)

const mock = reactive({
  id: 22,
  code: 'PRJ-2026-022',
  name: '万象科技 SaaS 平台升级',
  status: '进行中',
  statusColor: 'primary',
  progress: 68,
  client: '万象科技有限公司',
  type: 'SaaS 平台升级',
  manager: '陈思琪',
  startDate: '2026-04-10',
  endDate: '2026-06-30',
  budget: '286,000',
  period: '约 3 个月',
  description: '为万象科技部署 SaaS 平台标准版，包含发票识别、模板管理、报表分析等核心模块。30 个用户账号，需完成系统集成、数据迁移、培训上线。',
})

// 4 关键统计（design 真实数据）
const stats = [
  { v: '68',   l: '整体进度',   u: '%' },
  { v: '¥ 286,000', l: '预算总额', u: '' },
  { v: '4',    l: '里程碑',     u: '个' },
  { v: '12',   l: '关联发票',   u: '张' },
]

// 5 里程碑（design 真实数据：done/doing/todo）
const milestones = ref([
  { seq: 1, name: '项目启动会', date: '2026-04-12', status: 'done'    },
  { seq: 2, name: '需求调研',   date: '2026-04-25', status: 'done'    },
  { seq: 3, name: '系统部署',   date: '2026-05-15', status: 'current' },
  { seq: 4, name: '数据迁移',   date: '2026-06-10', status: 'todo'    },
  { seq: 5, name: '项目验收',   date: '2026-06-28', status: 'todo'    },
])

// 3 关联合同
const contracts = ref([
  { code: 'HT-2026-031', name: '万象科技 SaaS 服务合同 2026Q2', amount: '¥ 86,500.00',  signDate: '2026-06-11', status: '审批中', statusColor: 'warning' },
  { code: 'HT-2026-028', name: '数智化二期 SaaS 平台年度服务',  amount: '¥ 1,280,000.00', signDate: '2026-05-20', status: '执行中', statusColor: 'success' },
  { code: 'HT-2026-024', name: '财务系统年度服务合同',          amount: '¥ 128,000.00',  signDate: '2026-05-05', status: '即将到期', statusColor: 'warning' },
])

// 6 项目团队
const team = ref([
  { name: '陈思琪', role: '项目经理',   avatar: 'https://i.pravatar.cc/64?img=12', dept: '项目管理部', load: '85%' },
  { name: '王洋',   role: '技术负责人', avatar: 'https://i.pravatar.cc/64?img=68', dept: '研发部',     load: '60%' },
  { name: '王芳',   role: '财务专员',   avatar: 'https://i.pravatar.cc/64?img=23', dept: '财务部',     load: '30%' },
  { name: '李明',   role: '法务主管',   avatar: 'https://i.pravatar.cc/64?img=33', dept: '法务部',     load: '20%' },
  { name: '刘洋',   role: '客户经理',   avatar: 'https://i.pravatar.cc/64?img=45', dept: '销售部',     load: '40%' },
  { name: '张伟',   role: '开发工程师', avatar: 'https://i.pravatar.cc/64?img=51', dept: '研发部',     load: '90%' },
])

// 风险预警
const risks = ref([
  { t: '开发工程师张伟负载过高 (90%)，可能影响交付', sev: 'high' },
  { t: '数据迁移依赖客户方 IT 团队配合，存在外部依赖风险', sev: 'mid' },
])

// 12 关联发票
const invoices = ref([
  { no: '25113...45678', amount: '¥ 1,280', type: '办公用品', date: '2026-05-20' },
  { no: '25113...45680', amount: '¥ 580',   type: '住宿',     date: '2026-05-22' },
  { no: '25113...45681', amount: '¥ 1,560', type: '差旅',     date: '2026-05-25' },
  { no: '25113...45682', amount: '¥ 1,290', type: '差旅',     date: '2026-05-28' },
  { no: '25113...45683', amount: '¥ 3,200', type: '招待',     date: '2026-05-30' },
  { no: '25113...45684', amount: '¥ 8,650', type: '差旅',     date: '2026-06-02' },
])

function goBack() { router.push('/project/list') }
function editProject() { ElMessage.info('编辑项目') }
function viewAll(type: string) { ElMessage.info(`查看全部${type}`) }
function downloadFile(name: string) { ElMessage.info(`下载：${name}`) }

onMounted(() => {
  loading.value = true
  projectApi.detail(Number(route.params.id) || mock.id)
    .then((res: any) => { /* 用 mock */ })
    .catch(() => { /* 用 mock */ })
    .finally(() => { loading.value = false })
})

// 触点 #18：AI 分析下拉回调
function onAiAction(cmd: string) {
  if (cmd === 'switch-tab') {
    activeTab.value = 'ai'  // 触点 #4 已加的 AI Tab
  } else if (cmd === 'risk') {
    ElMessage.info('AI 风险扫描中...')
    activeTab.value = 'ai'
  } else if (cmd === 'suggest') {
    ElMessage.info('AI 建议：本周建议复盘 1 次，进度滞后 5 天')
  } else if (cmd === 'progress') {
    ElMessage.info('AI 预测：本项目预计延期 3-5 天，建议增加 1 名开发')
  }
}
</script>

<template>
  <div class="page-container">
    <!-- project-hero（design 顶部蓝紫渐变） -->
    <div class="project-hero">
      <div class="ph-top">
        <div class="ph-id">
          <span class="code">{{ mock.code }}</span>
          <span :class="['tag', `tag-${mock.statusColor}`]">{{ mock.status }}</span>
        </div>
        <h1 class="ph-title">{{ mock.name }}</h1>
        <div class="ph-meta">
          <span>🏢 {{ mock.client }}</span>
          <span class="sep">·</span>
          <span>📦 {{ mock.type }}</span>
          <span class="sep">·</span>
          <span>👤 {{ mock.manager }}</span>
          <span class="sep">·</span>
          <span>📅 {{ mock.startDate }} ~ {{ mock.endDate }}</span>
        </div>
      </div>
      <div class="ph-stats">
        <div v-for="(s, i) in stats" :key="i" class="ph-stat">
          <div class="v">{{ s.v }}<span class="u">{{ s.u }}</span></div>
          <div class="l">{{ s.l }}</div>
        </div>
      </div>
      <div class="ph-progress">
        <div class="ph-progress-label">
          <span>整体进度</span>
          <span class="pct">{{ mock.progress }}%</span>
        </div>
        <div class="ph-bar">
          <div class="ph-fill" :style="{ width: mock.progress + '%' }"></div>
        </div>
      </div>
      <div class="ph-actions">
        <button v-permission="'project:write'" class="btn btn-ghost btn-sm" @click="editProject">✎ 编辑</button>
        <button v-permission="'project:read'" class="btn btn-outline btn-sm" @click="ElMessage.info('任务看板')">📊 任务看板</button>
        <button v-permission="'project:write'" class="btn btn-primary btn-sm" @click="ElMessage.info('更新进度')">⚡ 更新进度</button>
        <!-- 触点 #18：AI 分析下拉 -->
        <el-dropdown @command="onAiAction" class="ph-ai-dropdown">
          <button class="btn-ai-outline">🤖 AI 分析 ▾</button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="risk">⚠️ AI 风险扫描</el-dropdown-item>
              <el-dropdown-item command="suggest">💡 AI 建议</el-dropdown-item>
              <el-dropdown-item command="progress">📈 AI 进度预测</el-dropdown-item>
              <el-dropdown-item command="switch-tab" divided>✨ 查看 ✨ AI 分析 Tab</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- detail-tabs -->
    <div class="detail-tabs">
      <a href="javascript:void(0)" :class="{ active: activeTab === 'basic' }"        @click="activeTab = 'basic'">📋 基本信息</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'milestones' }"  @click="activeTab = 'milestones'">🎯 里程碑</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'contracts' }"   @click="activeTab = 'contracts'">📄 关联合同</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'team' }"        @click="activeTab = 'team'">👥 项目团队</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'ai' }"          @click="activeTab = 'ai'">✨ AI 分析 <span class="tab-badge">NEW</span></a>
    </div>

    <!-- 主区（4 tab 内容） -->
    <div v-show="activeTab === 'basic'">
      <!-- 项目信息 -->
      <div class="detail-section">
        <div class="detail-section-head">
          <h4>📋 项目信息</h4>
          <span class="tag tag-info">进行中</span>
        </div>
        <div class="detail-section-body">
          <div class="info-grid">
            <div class="info-row"><span class="l">项目编号</span><span class="v mono">{{ mock.code }}</span></div>
            <div class="info-row"><span class="l">项目类型</span><span class="v">{{ mock.type }}</span></div>
            <div class="info-row"><span class="l">客户名称</span><span class="v">{{ mock.client }}</span></div>
            <div class="info-row"><span class="l">项目经理</span><span class="v">{{ mock.manager }}</span></div>
            <div class="info-row"><span class="l">开始日期</span><span class="v">{{ mock.startDate }}</span></div>
            <div class="info-row"><span class="l">截止日期</span><span class="v">{{ mock.endDate }}</span></div>
            <div class="info-row"><span class="l">预算总额</span><span class="v amount">¥ {{ mock.budget }}</span></div>
            <div class="info-row"><span class="l">工期</span><span class="v">{{ mock.period }}</span></div>
            <div class="info-row full">
              <span class="l">项目描述</span>
              <div class="notes-block">{{ mock.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 风险预警 -->
      <div class="risk-card">
        <div class="head">
          <div class="ico">⚠</div>
          <div class="t">⚠️ 风险预警 · {{ risks.length }} 项</div>
        </div>
        <div class="body">
          <div v-for="(r, i) in risks" :key="i" :class="['row', r.sev]">
            · <strong>{{ r.t }}</strong>
          </div>
        </div>
      </div>
    </div>

    <!-- 里程碑 -->
    <div v-show="activeTab === 'milestones'" class="detail-section">
      <div class="detail-section-head">
        <h4>🎯 里程碑进度（5 个）</h4>
        <span style="font-size: 11.5px; color: var(--color-text-tertiary);">已完成 2 / 进行中 1 / 待启动 2</span>
      </div>
      <div class="detail-section-body">
        <div class="ms-timeline">
          <div v-for="(m, i) in milestones" :key="i" :class="['ms-item', m.status]">
            <div class="ms-icon">{{ m.status === 'done' ? '✓' : m.seq }}</div>
            <div class="ms-body">
              <div class="ms-name">{{ m.name }}</div>
              <div class="ms-date">{{ m.date }}</div>
            </div>
            <div :class="['ms-status', m.status]">
              {{ m.status === 'done' ? '已完成' : m.status === 'current' ? '进行中' : '待启动' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 关联合同 -->
    <div v-show="activeTab === 'contracts'" class="detail-section">
      <div class="detail-section-head">
        <h4>📄 关联合同（3 份）</h4>
        <a class="link-primary" @click="viewAll('合同')">查看全部 →</a>
      </div>
      <div class="detail-section-body">
        <table class="ct-table">
          <thead>
            <tr>
              <th>合同编号</th>
              <th>合同名称</th>
              <th style="text-align: right;">金额</th>
              <th>签订日期</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, i) in contracts" :key="i">
              <td><span class="cell-mono">{{ c.code }}</span></td>
              <td>{{ c.name }}</td>
              <td class="cell-amount">{{ c.amount }}</td>
              <td>{{ c.signDate }}</td>
              <td><span :class="['tag', `tag-${c.statusColor}`]">{{ c.status }}</span></td>
              <td><a class="link-primary">查看</a></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 项目团队 -->
    <div v-show="activeTab === 'team'" class="detail-section">
      <div class="detail-section-head">
        <h4>👥 项目团队（6 人）</h4>
        <a class="link-primary">+ 添加成员</a>
      </div>
      <div class="detail-section-body">
        <div class="team-grid">
          <div v-for="(m, i) in team" :key="i" class="team-card">
            <img :src="m.avatar" :alt="m.name" />
            <div class="name">{{ m.name }}</div>
            <div class="role">{{ m.role }}</div>
            <div class="dept">{{ m.dept }}</div>
            <div class="load">
              <span class="lbl">负载</span>
              <div class="bar"><div class="fill" :style="{ width: m.load, background: parseInt(m.load) > 80 ? '#EF4444' : 'linear-gradient(135deg, #4F6BFF, #7C3AED)' }"></div></div>
              <span class="v">{{ m.load }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 触点 #4：✨ AI 分析 Tab（调用 AiRiskScanPanel 一行复用） -->
    <div v-show="activeTab === 'ai'" class="detail-section fade-up">
      <AiRiskScanPanel
        object-type="project"
        :object-id="mock.id"
        @loaded="onAiLoaded"
        @error="onAiError"
        @accept-suggestion="onAiAccept"
        @dismiss-warning="onAiDismiss"
        @feedback="onAiFeedback"
      />
    </div>

    <!-- 关联发票（始终显示） -->
    <div class="detail-section">
      <div class="detail-section-head">
        <h4>▤ 关联发票（12 张）</h4>
        <a class="link-primary" @click="viewAll('发票')">查看全部 →</a>
      </div>
      <div class="detail-section-body">
        <table class="ct-table">
          <thead>
            <tr>
              <th>发票号</th>
              <th>类型</th>
              <th style="text-align: right;">金额</th>
              <th>开票日期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(inv, i) in invoices" :key="i">
              <td><span class="cell-mono">{{ inv.no }}</span></td>
              <td><span class="tag tag-info">{{ inv.type }}</span></td>
              <td class="cell-amount">{{ inv.amount }}</td>
              <td>{{ inv.date }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* 触点 #18：AI 分析下拉 */
.btn-ai-outline {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 12px; font-size: 12px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none;
  border-radius: $radius-sm; cursor: pointer;
  box-shadow: 0 2px 6px rgba(79,107,255,0.2);
  &:hover { opacity: 0.92; }
}
.ph-ai-dropdown { margin-left: 4px; }
</style>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

// project-hero（design 蓝紫渐变）
.project-hero {
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  color: #fff;
  border-radius: $radius-lg;
  padding: 24px 28px;
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.1) 0%, transparent 50%);
    pointer-events: none;
  }
  .ph-top { position: relative; z-index: 1; margin-bottom: 16px; }
  .ph-id { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .ph-id .code {
    font-family: $font-family-mono;
    font-size: 12.5px;
    color: rgba(255,255,255,0.85);
  }
  .ph-id .tag {
    background: rgba(255,255,255,0.18);
    color: #fff;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 11.5px;
    font-weight: 500;
  }
  .ph-title {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 8px 0;
    color: #fff;
  }
  .ph-meta {
    font-size: 12.5px;
    color: rgba(255,255,255,0.8);
    .sep { margin: 0 8px; opacity: 0.5; }
  }
  .ph-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding: 12px 0;
    border-top: 1px solid rgba(255,255,255,0.1);
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 14px;
    position: relative;
    z-index: 1;
    @media (max-width: 700px) { grid-template-columns: repeat(2, 1fr); }
  }
  .ph-stat {
    text-align: center;
    .v {
      font-size: 20px; font-weight: 700;
      color: #fff;
      font-family: $font-family-mono;
      .u { font-size: 12px; color: rgba(255,255,255,0.7); font-weight: 500; margin-left: 2px; font-family: -apple-system, sans-serif; }
    }
    .l { font-size: 11.5px; color: rgba(255,255,255,0.7); margin-top: 2px; }
  }
  .ph-progress { position: relative; z-index: 1; margin-bottom: 16px; }
  .ph-progress-label {
    display: flex; justify-content: space-between;
    font-size: 12.5px; color: rgba(255,255,255,0.85);
    margin-bottom: 6px;
    .pct { font-weight: 700; color: #fff; font-family: $font-family-mono; }
  }
  .ph-bar {
    height: 8px;
    background: rgba(255,255,255,0.18);
    border-radius: 9999px;
    overflow: hidden;
  }
  .ph-fill {
    height: 100%;
    background: #fff;
    border-radius: 9999px;
    box-shadow: 0 0 12px rgba(255,255,255,0.4);
  }
  .ph-actions { display: flex; gap: 8px; justify-content: flex-end; position: relative; z-index: 1; }
  .btn {
    background: rgba(255,255,255,0.18);
    color: #fff;
    border-color: rgba(255,255,255,0.3);
    &:hover { background: rgba(255,255,255,0.28); }
    &.btn-primary { background: #fff; color: $color-primary; border-color: #fff; }
  }
}

// detail-tabs
.detail-tabs {
  display: flex;
  gap: 4px;
  background: #fff;
  padding: 4px;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  margin-bottom: 16px;
  width: fit-content;
  a {
    padding: 8px 16px; border-radius: $radius-sm;
    font-size: 13px; color: $color-text-secondary;
    text-decoration: none; cursor: pointer; font-weight: 500;
    &:hover { background: $color-bg; color: $color-primary; }
    &.active { background: $color-primary; color: #fff; font-weight: 600; }
  }
  .tab-badge {
    display: inline-block; margin-left: 4px;
    padding: 0 5px; font-size: 9px; font-weight: 700;
    background: linear-gradient(135deg, #4F6BFF, #7C3AED);
    color: #fff; border-radius: 9999px;
    vertical-align: middle; line-height: 14px;
  }
}

// detail-section
.detail-section { @include detail-section; }
.detail-section-head { @include detail-section-head; }
.detail-section-body { @include detail-section-body; }

.info-grid { @include info-grid(2); }
.info-row { @include info-row; }
.info-row .v.amount { font-weight: 700; color: $color-text-primary; }

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-danger  { background: #FEE2E2; color: #B91C1C; }
  &.tag-primary { background: #E0E6FF; color: #4F6BFF; }
}

.notes-block {
  background: #FAFBFF;
  border-left: 3px solid $color-primary;
  padding: 12px 16px;
  border-radius: 0 $radius-md $radius-md 0;
  font-size: 13px;
  color: $color-text-secondary;
  line-height: 1.7;
  margin-top: 4px;
}

.link-primary { color: $color-primary; font-size: 12.5px; cursor: pointer; }
.link-primary:hover { text-decoration: underline; }

// risk-card（design 风险预警）
.risk-card {
  background: rgba(239,68,68,0.04);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: $radius-md;
  padding: 14px 16px;
  margin-bottom: 16px;
  .head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .head .ico {
    width: 28px; height: 28px; border-radius: 50%;
    background: rgba(239,68,68,0.15);
    color: #EF4444;
    display: grid; place-items: center;
    font-weight: 700;
  }
  .head .t { font-size: 14px; font-weight: 600; color: #B91C1C; }
  .body .row {
    font-size: 12.5px;
    color: $color-text-secondary;
    padding: 4px 0;
    strong { color: $color-text-primary; }
  }
}

// ms-timeline（设计 里程碑时间线）
.ms-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}
.ms-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  .ms-icon {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: $color-bg;
    color: $color-text-tertiary;
    display: grid; place-items: center;
    font-size: 14px; font-weight: 600;
    flex-shrink: 0;
  }
  &.done .ms-icon { background: linear-gradient(135deg, #10B981, #059669); color: #fff; }
  &.current .ms-icon { background: $gradient-brand; color: #fff; box-shadow: 0 0 0 4px rgba(79,107,255,0.2); }
  .ms-body { flex: 1; min-width: 0; }
  .ms-name { font-size: 13.5px; font-weight: 600; color: $color-text-primary; }
  .ms-date { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .ms-status {
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 11.5px;
    font-weight: 500;
    &.done    { background: rgba(16,185,129,0.1); color: #10B981; }
    &.current { background: $color-primary-bg; color: $color-primary; }
    &.todo    { background: $color-bg; color: $color-text-tertiary; }
  }
}

// table
.ct-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: $color-bg; text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: $color-text-tertiary; border-bottom: 1px solid $color-border; }
  td { padding: 12px 14px; border-bottom: 1px solid $color-border; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: $color-bg; }
  .cell-mono { font-family: $font-family-mono; color: $color-primary; font-weight: 500; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; text-align: right; }
}

// team-grid
.team-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
}
.team-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 16px;
  text-align: center;
  img { width: 56px; height: 56px; border-radius: 50%; object-fit: cover; margin: 0 auto 8px; }
  .name { font-size: 14px; font-weight: 600; color: $color-text-primary; }
  .role { font-size: 12px; color: $color-primary; margin-top: 2px; font-weight: 500; }
  .dept { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .load {
    display: flex; align-items: center; gap: 6px;
    margin-top: 12px;
    .lbl { font-size: 11px; color: $color-text-tertiary; }
    .bar { flex: 1; height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; }
    .fill { height: 100%; border-radius: 3px; }
    .v { font-size: 11px; color: $color-text-secondary; font-family: $font-family-mono; }
  }
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
