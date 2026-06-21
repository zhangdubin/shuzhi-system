<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, type Project } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<Project | null>(null)
const activeTab = ref('basic')

// 项目详情（design/project-detail.html 同款）
const detail = ref({
  code: 'PRJ-2026-018',
  name: '数智化二期',
  customerName: '万象科技有限公司',
  customerContact: '李建国（CTO）· 138****8888',
  manager: '陈思琪',
  type: 'SaaS 平台升级',
  status: '进行中',
  budget: 280000,
  actualCost: 186500,
  grossMargin: 33.4,
  startDate: '2026-03-15',
  endDate: '2026-08-30',
  progress: 68,
  createdAt: '2026-03-15',
  description: '在数智化一期基础上扩展发票识别模块，新增回款管理、项目管理、合同管理三大业务模块，实现企业财务全流程在线化。包含 AI 智能识别、可视化驾驶舱、多端协同能力，预计上线后客户财务效率提升 40%。',
})

// 里程碑（横向 5 节点：启动 / 需求 / 开发 / 验收 / 交付）
const milestones = [
  { lbl: '项目启动', node: '✓', state: 'done', meta: ['陈思琪', '2026-03-20 完成'] },
  { lbl: '需求调研', node: '✓', state: 'done', meta: ['陈思琪 / 王芳', '2026-04-15 完成'] },
  { lbl: '开发实施', node: '✓', state: 'done', meta: ['王洋 / 李明', '2026-06-05 完成'] },
  { lbl: 'UAT 验收', node: '4', state: 'current', meta: ['陈思琪', '进行中 · 45%'] },
  { lbl: '正式交付', node: '5', state: 'pending', meta: ['待开始', '计划 2026-08-30'] },
]

// 团队成员
const team = ref([
  { name: '陈思琪', role: '项目经理', hours: 320, joinedAt: '2026-03-15' },
  { name: '王芳', role: '财务专员', hours: 180, joinedAt: '2026-03-20' },
  { name: '李明', role: '法务主管', hours: 64, joinedAt: '2026-04-01' },
  { name: '刘洋', role: '销售经理', hours: 96, joinedAt: '2026-03-25' },
  { name: '王洋', role: '技术负责人', hours: 480, joinedAt: '2026-03-15' },
  { name: '张明', role: 'PMO', hours: 40, joinedAt: '2026-03-15' },
])

// 关联合同
const contracts = ref([
  { code: 'HT-2026-028', name: '数智化二期 SaaS 平台年度服务', amount: 1280000, signedAt: '2026-05-20', status: '执行中' },
  { code: 'HT-2026-031', name: '万象科技 SaaS 服务合同 2026Q2', amount: 86500, signedAt: '2026-06-11', status: '已签订' },
  { code: 'HT-2026-023', name: '数智化一期验收补充协议', amount: 56000, signedAt: '2026-05-01', status: '已归档' },
])

// 关联费用
const expenses = ref([
  { code: 'FY-2026-018', category: '人力成本', amount: 120000, applicant: '陈思琪', applicantAt: '2026-05-30', status: '已入账' },
  { code: 'FY-2026-022', category: '软件许可', amount: 36000, applicant: '王洋', applicantAt: '2026-04-15', status: '已入账' },
  { code: 'FY-2026-028', category: '差旅实施', amount: 30500, applicant: '刘洋', applicantAt: '2026-06-08', status: '审批中' },
])

// 关联回款
const receivables = ref([
  { code: 'HK-2026-Q2-001', contractCode: 'HT-2026-028', amount: 320000, received: 320000, dueDate: '2026-06-30', status: '已回款' },
  { code: 'HK-2026-Q3-001', contractCode: 'HT-2026-028', amount: 320000, received: 0, dueDate: '2026-09-30', status: '待回款' },
  { code: 'HK-2026-Q2-002', contractCode: 'HT-2026-031', amount: 21625, received: 21625, dueDate: '2026-06-15', status: '已回款' },
])

// 关联发票
const invoices = ref([
  { no: '25113300...12345678', amount: 28000, issueDate: '2026-06-08', status: '已入账' },
  { no: '25113300...55443322', amount: 142300, issueDate: '2026-06-06', status: '已关联合同' },
  { no: '25113300...99887766', amount: 86500, issueDate: '2026-05-28', status: '已入账' },
])

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const r: any = await projectApi.detail(id).catch(() => null)
    if (r) {
      data.value = r
      detail.value = {
        code: r.code || detail.value.code,
        name: r.name || detail.value.name,
        customerName: r.clientName || detail.value.customerName,
        customerContact: r.clientContact || '—（后端未提供）',
        manager: r.managerName || detail.value.manager,
        type: r.type || detail.value.type,
        status: statusLabel(r.status),
        budget: Number(r.budget) || detail.value.budget,
        actualCost: Number(r.spent) || detail.value.actualCost,
        grossMargin: detail.value.grossMargin,
        startDate: (r.startDate || '').slice(0, 10) || detail.value.startDate,
        endDate: (r.endDate || '').slice(0, 10) || detail.value.endDate,
        progress: Number(r.progress) || 0,
        createdAt: (r.createdAt || '').slice(0, 10) || detail.value.createdAt,
        description: r.description || detail.value.description,
      }
    }
  } finally {
    loading.value = false
  }
}

function statusLabel(s?: string) {
  return { planning: '规划中', in_progress: '进行中', active: '进行中', completed: '已完成', paused: '已暂停', cancelled: '已取消' }[s || ''] || (s || '—')
}

function gotoBack() { router.push('/project/list') }
function gotoEdit() { router.push(`/project/${route.params.id}/edit`) }
function gotoAiPanel() { router.push('/ai/panel/project') }
async function handleArchive() {
  try {
    await ElMessageBox.confirm('归档后项目将进入只读状态，确定继续？', '归档项目', { type: 'warning' })
    ElMessage.success('已归档（演示）')
  } catch { /* cancel */ }
}
function gotoAddMilestone() { ElMessage.info('打开添加里程碑抽屉（演示）') }

onMounted(load)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/project/list" style="color: var(--color-text-tertiary)">项目管理</router-link> / {{ detail.code }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          项目详情
          <span class="tag tag-success">{{ detail.status }}</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">← 返回列表</el-button>
        <el-button @click="gotoAiPanel" style="background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%); color: #fff; border: none">🤖 AI 智能分析</el-button>
        <el-button @click="handleArchive" style="color: var(--color-text-secondary)">📦 归档项目</el-button>
        <el-button type="primary" @click="gotoEdit">✎ 编辑项目</el-button>
      </div>
    </div>

    <!-- Hero（与 design/project-detail.html 1:1：深色渐变 + 4 stats + 进度条）-->
    <div class="detail-hero">
      <div class="dh-left">
        <div class="dh-id">{{ detail.code }}</div>
        <h2>{{ detail.name }}</h2>
        <div class="dh-meta">客户：<strong style="color: #fff">{{ detail.customerName }}</strong> · {{ detail.status }} · {{ detail.startDate }} ~ {{ detail.endDate }}</div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">合同金额</div>
        <div class="dh-amount">¥ {{ detail.budget.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
      </div>
    </div>

    <!-- 项目专属统计条（在 Hero 下方，跟 design 一致） -->
    <div class="ph-stats-row">
      <div class="ph-stat-card">
        <div class="l">整体进度</div>
        <div class="v">{{ detail.progress }}%</div>
        <div class="d">+5% 本周</div>
      </div>
      <div class="ph-stat-card">
        <div class="l">已花预算</div>
        <div class="v sm">¥ {{ (detail.actualCost / 10000).toFixed(1) }} 万</div>
        <div class="d">总预算 ¥ {{ (detail.budget / 10000).toFixed(0) }} 万</div>
      </div>
      <div class="ph-stat-card">
        <div class="l">实际成本</div>
        <div class="v sm">¥ {{ detail.actualCost.toLocaleString() }}</div>
        <div class="d">毛利率 {{ detail.grossMargin }}%</div>
      </div>
      <div class="ph-stat-card">
        <div class="l">剩余天数</div>
        <div class="v">79 <span class="unit">天</span></div>
        <div class="d">截止 {{ detail.endDate }}</div>
      </div>
    </div>

    <!-- 进度条 -->
    <div class="ph-progress">
      <div class="label">
        <span>项目进度</span>
        <span class="pct">{{ detail.progress }}%</span>
      </div>
      <div class="bar"><div class="fill" :style="{ width: detail.progress + '%' }"></div></div>
    </div>

    <!-- Tabs（与 design 1:1）-->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">基本信息</a>
      <a :class="{ active: activeTab === 'milestone' }" @click="activeTab = 'milestone'">里程碑</a>
      <a :class="{ active: activeTab === 'team' }" @click="activeTab = 'team'">团队成员</a>
      <a :class="{ active: activeTab === 'contract' }" @click="activeTab = 'contract'">合同</a>
      <a :class="{ active: activeTab === 'expense' }" @click="activeTab = 'expense'">费用</a>
      <a :class="{ active: activeTab === 'receivable' }" @click="activeTab = 'receivable'">回款</a>
      <a :class="{ active: activeTab === 'invoice' }" @click="activeTab = 'invoice'">发票</a>
    </div>

    <!-- 里程碑（横 5 节点，复用 flow-horizontal）-->
    <div v-if="activeTab === 'basic' || activeTab === 'milestone'" class="flow-horizontal">
      <h4>🎯 项目里程碑（4 / 5 已完成）</h4>
      <div class="fh-row">
        <template v-for="(s, i) in milestones" :key="i">
          <div :class="['fh-step', s.state]">
            <div class="node">{{ s.node }}</div>
            <div class="lbl">{{ s.lbl }}</div>
            <div class="meta">
              <span class="name">{{ s.meta[0] }}</span><br />{{ s.meta[1] }}
            </div>
          </div>
          <div v-if="i < milestones.length - 1" :class="['fh-line', s.state === 'done' ? 'done' : '']" />
        </template>
      </div>
    </div>

    <!-- 基本信息 -->
    <div v-if="activeTab === 'basic'" class="detail-section">
      <div class="detail-section-head">
        <h4>📋 项目基本信息</h4>
        <el-button link type="primary" @click="gotoEdit">编辑</el-button>
      </div>
      <div class="detail-section-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">项目编号</span><span class="v mono">{{ detail.code }}</span></div>
          <div class="info-row"><span class="l">项目名称</span><span class="v">{{ detail.name }}</span></div>
          <div class="info-row"><span class="l">客户名称</span><span class="v">{{ detail.customerName }}</span></div>
          <div class="info-row"><span class="l">客户联系人</span><span class="v">{{ detail.customerContact }}</span></div>
          <div class="info-row"><span class="l">项目负责人</span><span class="v">{{ detail.manager }}</span></div>
          <div class="info-row"><span class="l">项目状态</span><span class="v"><span class="tag tag-success">{{ detail.status }}</span></span></div>
          <div class="info-row"><span class="l">项目类型</span><span class="v">{{ detail.type }}</span></div>
          <div class="info-row"><span class="l">项目预算</span><span class="v">¥ {{ detail.budget.toLocaleString() }}</span></div>
          <div class="info-row"><span class="l">实际成本</span><span class="v">¥ {{ detail.actualCost.toLocaleString() }}</span></div>
          <div class="info-row"><span class="l">毛利率</span><span class="v">{{ detail.grossMargin }}%</span></div>
          <div class="info-row"><span class="l">起始日期</span><span class="v">{{ detail.startDate }}</span></div>
          <div class="info-row"><span class="l">截止日期</span><span class="v">{{ detail.endDate }}</span></div>
          <div class="info-row"><span class="l">项目进度</span><span class="v">{{ detail.progress }}%</span></div>
          <div class="info-row"><span class="l">创建时间</span><span class="v">{{ detail.createdAt }}</span></div>
          <div class="info-row full">
            <span class="l">项目描述</span>
            <div class="term-block">
              <div class="d">{{ detail.description }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 里程碑详情 -->
    <div v-if="activeTab === 'milestone'" class="detail-section">
      <div class="detail-section-head">
        <h4>🎯 里程碑明细</h4>
        <el-button link type="primary" @click="gotoAddMilestone">+ 添加里程碑</el-button>
      </div>
      <div class="detail-section-body" style="padding: 6px 20px 14px">
        <div v-for="(m, i) in milestones" :key="i" class="ms-row">
          <div :class="['ms-icon', m.state === 'done' ? 'done' : m.state === 'current' ? 'current' : 'todo']">
            {{ m.state === 'done' ? '✓' : i + 1 }}
          </div>
          <div class="ms-body">
            <div class="t">M{{ i + 1 }} · {{ m.lbl }}</div>
            <div class="m">{{ m.meta[0] }} · {{ m.meta[1] }}</div>
          </div>
          <div :class="['ms-status', m.state === 'done' ? 'done' : m.state === 'current' ? 'current' : 'todo']">
            {{ m.state === 'done' ? '已完成' : m.state === 'current' ? '进行中' : '未开始' }}
          </div>
        </div>
      </div>
    </div>

    <!-- 团队成员 -->
    <div v-if="activeTab === 'team'" class="detail-section">
      <div class="detail-section-head">
        <h4>👥 团队成员（{{ team.length }} 人）</h4>
        <el-button link type="primary">+ 添加成员</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="team">
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="name" label="成员" width="120" />
          <el-table-column prop="role" label="角色" width="160">
            <template #default="{ row }">
              <el-tag size="small" :type="row.role.includes('项目') ? 'primary' : 'info'">{{ row.role }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hours" label="累计工时 (h)" width="140" align="right" />
          <el-table-column prop="joinedAt" label="加入时间" width="140" />
          <el-table-column label="操作" width="120">
            <template #default>
              <el-button link type="primary">查看</el-button>
              <el-button link type="danger">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 关联合同 -->
    <div v-if="activeTab === 'contract'" class="detail-section">
      <div class="detail-section-head">
        <h4>📄 关联合同（{{ contracts.length }} 份）</h4>
        <el-button link type="primary">查看全部</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="contracts">
          <el-table-column prop="code" label="合同编号" width="160" />
          <el-table-column prop="name" label="合同名称" />
          <el-table-column prop="amount" label="金额" width="140" align="right">
            <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="signedAt" label="签订日期" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '执行中' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default><el-button link type="primary">查看</el-button></template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 关联费用 -->
    <div v-if="activeTab === 'expense'" class="detail-section">
      <div class="detail-section-head">
        <h4>💸 关联费用（{{ expenses.length }} 条）</h4>
        <el-button link type="primary">查看全部</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="expenses">
          <el-table-column prop="code" label="费用编号" width="160" />
          <el-table-column prop="category" label="类别" width="120" />
          <el-table-column prop="amount" label="金额" width="120" align="right">
            <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="applicant" label="申请人" width="100" />
          <el-table-column prop="applicantAt" label="申请日期" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '已入账' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 关联回款 -->
    <div v-if="activeTab === 'receivable'" class="detail-section">
      <div class="detail-section-head">
        <h4>💰 关联回款（{{ receivables.length }} 条）</h4>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="receivables">
          <el-table-column prop="code" label="回款编号" width="160" />
          <el-table-column prop="contractCode" label="关联合同" width="160" />
          <el-table-column prop="amount" label="应收金额" width="140" align="right">
            <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="received" label="已收金额" width="140" align="right">
            <template #default="{ row }">¥ {{ row.received.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="dueDate" label="到期日" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '已回款' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 关联发票 -->
    <div v-if="activeTab === 'invoice'" class="detail-section">
      <div class="detail-section-head">
        <h4>🧾 关联发票（{{ invoices.length }} 张）</h4>
        <el-button link type="primary">查看全部</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="invoices">
          <el-table-column prop="no" label="发票号" />
          <el-table-column prop="amount" label="金额" width="140" align="right">
            <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="issueDate" label="开票日期" width="120" />
          <el-table-column label="状态" width="140">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '已入账' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

// ===== Hero 下方的 stats 行（design/project-detail.html 同款） =====
.ph-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.ph-stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  .l { font-size: 11.5px; color: var(--color-text-tertiary); margin-bottom: 6px; }
  .v { font-size: 22px; font-weight: 700; color: var(--color-text-primary); line-height: 1.2;
    .unit { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); }
    &.sm { font-size: 15px; }
  }
  .d { font-size: 11px; color: var(--color-text-tertiary); margin-top: 4px; }
}

// 进度条（design 同款）
.ph-progress {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 20px;
  .label {
    display: flex; justify-content: space-between;
    font-size: 12.5px; color: var(--color-text-secondary);
    .pct { font-weight: 700; color: var(--color-primary); font-size: 15px; }
  }
  .bar {
    height: 10px; background: #F1F5F9; border-radius: 999px;
    overflow: hidden; margin-top: 8px;
  }
  .fill {
    height: 100%;
    background: linear-gradient(90deg, #4F6BFF 0%, #7C3AED 50%, #EC4899 100%);
    border-radius: 999px;
    transition: width 0.4s;
  }
}

// ===== 里程碑明细行（design/project-detail.html 同款） =====
.ms-row {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
  &:last-child { border-bottom: none; }
}
.ms-icon {
  width: 32px; height: 32px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 14px; font-weight: 600;
  flex-shrink: 0;
  &.done { background: var(--color-success-bg); color: var(--color-success); }
  &.current {
    background: var(--color-primary-bg);
    color: var(--color-primary);
    border: 2px solid var(--color-primary);
  }
  &.todo { background: #F1F5F9; color: var(--color-text-tertiary); }
}
.ms-body { flex: 1; min-width: 0; }
.ms-body .t { font-size: 13.5px; font-weight: 500; }
.ms-body .m { font-size: 11.5px; color: var(--color-text-tertiary); margin-top: 2px; }
.ms-status { font-size: 12px; font-weight: 500; }
.ms-status.done { color: var(--color-success); }
.ms-status.current { color: var(--color-primary); }
.ms-status.todo { color: var(--color-text-tertiary); }
</style>