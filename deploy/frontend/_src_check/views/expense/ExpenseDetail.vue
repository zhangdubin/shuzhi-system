<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { expenseApi, type Expense } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<Expense | null>(null)
const activeTab = ref('basic')

// 模拟详情数据（与 design/sales-expense.html 列表行 + sales-expense-create.html 同源）
const detail = ref({
  code: 'EX-2026-0612-001',
  category: '差旅',
  amount: 4820,
  status: '审批中',
  applicant: '陈思琪',
  department: '销售部',
  applicantAt: '2026-06-12 09:23',
  projectLink: 'PRJ-2026-022 · 万象科技 SaaS 部署',
  projectNo: 'PRJ-2026-022',
  purpose: '上海-北京客户拜访（北辰集团）',
  description: '北京北辰集团 Q2 项目对接会，含 3 名销售团队 + 2 名技术专家。含机票（往返）、酒店 2 晚、当地打车。',
  amountCn: '肆仟捌佰贰拾元整',
  paymentMethod: '对公转账',
  payee: '陈思琪（招商银行 6225****1234）',
})

// 费用明细（与设计稿同款：机票 / 酒店 / 打车 / 餐补）
const items = ref([
  { id: 1, date: '2026-06-10', subCategory: '机票', amount: 2860, remark: '上海-北京往返 MU5102 / MU5103' },
  { id: 2, date: '2026-06-10', subCategory: '酒店', amount: 1280, remark: '北京希尔顿 2 晚（6/10-6/12）' },
  { id: 3, date: '2026-06-11', subCategory: '打车/交通', amount: 380, remark: '机场往返 + 客户拜访打车' },
  { id: 4, date: '2026-06-11', subCategory: '餐补/其他', amount: 300, remark: '差旅餐补 3 天 × 100' },
])

// 审批流（提交 → 部门经理 → 财务 → 出纳，金额 ≥ 5000 触发总经理）
const flowSteps = ref<{ lbl: string; node: string; state: string; meta: string[] }[]>([
  { lbl: '提交', node: '✓', state: 'done', meta: ['陈思琪', '2026-06-12 09:23'] },
  { lbl: '部门经理', node: '✓', state: 'done', meta: ['王芳', '2026-06-12 11:08'] },
  { lbl: '财务审核', node: '3', state: 'current', meta: ['张明', '审核中 · 待处理'] },
  { lbl: '出纳支付', node: '4', state: 'pending', meta: ['未开始', '财务通过后触发'] },
])

// 附件
const attachments = [
  { name: '机票行程单.pdf', size: '128 KB', uploader: '陈思琪', at: '2026-06-12 09:20' },
  { name: '酒店发票.pdf', size: '86 KB', uploader: '陈思琪', at: '2026-06-12 09:21' },
  { name: '打车明细截图.png', size: '420 KB', uploader: '陈思琪', at: '2026-06-12 09:22' },
]

// 类别 chip 配色
function categoryTagClass(c: string) {
  if (c === '差旅') return 'tag tag-primary'
  if (c === '招待') return 'tag'  // 紫色（自定义内联）
  if (c === '办公') return 'tag'  // 绿色
  if (c === '推广') return 'tag'  // 橙色
  return 'tag tag-info'
}
function categoryStyle(c: string) {
  if (c === '招待') return 'background: #EDE9FE; color: #7C3AED;'
  if (c === '办公') return 'background: #D1FAE5; color: #047857;'
  if (c === '推广') return 'background: #FEF3C7; color: #B45309;'
  return ''
}

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const r: any = await expenseApi.detail(id).catch(() => null)
    if (r) {
      data.value = r
      detail.value = {
        code: r.code || detail.value.code,
        category: r.category || '—',
        amount: Number(r.amount) || 0,
        status: statusLabel(r.status),
        applicant: r.applicantName || '—',
        department: r.departmentName || '—',
        applicantAt: (r.submitAt || r.createdAt || '').slice(0, 16).replace('T', ' '),
        projectLink: r.projectName || '—',
        projectNo: r.projectCode || '—',
        purpose: r.title || '—',
        description: r.description || '—',
        amountCn: '—',
        paymentMethod: '对公转账',
        payee: r.applicantName || '—',
      }
    }
  } finally {
    loading.value = false
  }
}

function statusLabel(s?: string) {
  return { draft: '草稿', pending: '待审批', approving: '审批中', approved: '已批准', rejected: '已驳回', paid: '已支付' }[s || ''] || (s || '—')
}

function gotoBack() { router.push('/expense/list') }
function gotoProject() {
  if (detail.value.projectNo) router.push(`/project/${detail.value.projectNo}`)
}

async function handleApprove() {
  const d: any = detail.value
  if (!d?.id) return
  try {
    await ElMessageBox.confirm(`确定审批通过费用「${d.code}」？`, '审批费用', { type: 'success' })
  } catch { return }
  const r: any = await expenseApi.approve(d.id, { action: 'approve' }).catch((e: any) => ({ message: e?.message || '网络错误' }))
  if (r?.code === 0 || r?.id) {
    ElMessage.success('已审批通过')
    load()
  } else {
    ElMessage.error(r?.message || '审批失败')
  }
}
async function handleReject() {
  const d: any = detail.value
  if (!d?.id) return
  let comment = ''
  try {
    const res: any = await ElMessageBox.prompt('请输入驳回原因', '驳回费用', {
      inputType: 'textarea',
      inputValidator: (v: string) => (v && v.length >= 2) ? true : '至少 2 个字',
    })
    comment = res.value
  } catch { return }
  const r: any = await expenseApi.approve(d.id, { action: 'reject', comment }).catch((e: any) => ({ message: e?.message || '网络错误' }))
  if (r?.code === 0 || r?.id) {
    ElMessage.success('已驳回')
    load()
  } else {
    ElMessage.error(r?.message || '驳回失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/expense/list" style="color: var(--color-text-tertiary)">销售费用</router-link> / {{ detail.code }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          费用详情
          <span :class="categoryTagClass(detail.category)" :style="categoryStyle(detail.category)">{{ detail.category }}</span>
          <span class="tag tag-warning">{{ detail.status }}</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">← 返回列表</el-button>
        <el-button style="color: var(--color-danger); border-color: rgba(239,68,68,0.3)" @click="handleReject">✕ 驳回</el-button>
        <el-button type="primary" @click="handleApprove">✓ 审批通过</el-button>
      </div>
    </div>

    <!-- Hero（与 design 列表行 1:1：单号 / 类别 / 金额红字 / 申请人 / 时间 / 状态） -->
    <div class="detail-hero">
      <div class="dh-left">
        <div class="dh-id">{{ detail.code }}</div>
        <h2>{{ detail.purpose }}</h2>
        <div class="dh-meta">
          申请人：<strong style="color: #fff">{{ detail.applicant }}</strong>
          · {{ detail.department }}
          · 申请时间 {{ detail.applicantAt }}
        </div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">报销金额</div>
        <div class="dh-amount" style="color: #FECACA; text-shadow: 0 0 16px rgba(254,202,202,0.3)">
          ¥ {{ detail.amount.toLocaleString() }}
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">基本信息</a>
      <a :class="{ active: activeTab === 'items' }" @click="activeTab = 'items'">费用明细</a>
      <a :class="{ active: activeTab === 'flow' }" @click="activeTab = 'flow'">审批流</a>
      <a :class="{ active: activeTab === 'attach' }" @click="activeTab = 'attach'">附件</a>
    </div>

    <!-- 审批流（横 4 节点：提交 → 部门经理 → 财务 → 出纳） -->
    <div v-if="activeTab === 'flow'" class="flow-horizontal">
      <h4>🔄 审批流</h4>
      <div class="fh-row">
        <template v-for="(s, i) in flowSteps" :key="i">
          <div :class="['fh-step', s.state]">
            <div class="node">{{ s.node }}</div>
            <div class="lbl">{{ s.lbl }}</div>
            <div class="meta">
              <span class="name">{{ s.meta[0] }}</span><br />{{ s.meta[1] }}
            </div>
          </div>
          <div v-if="i < flowSteps.length - 1" :class="['fh-line', s.state === 'done' ? 'done' : '']" />
        </template>
      </div>
    </div>

    <!-- 基本信息 -->
    <div v-if="activeTab === 'basic'" class="detail-section">
      <div class="detail-section-head">
        <h4>📋 费用基本信息</h4>
      </div>
      <div class="detail-section-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">费用单号</span><span class="v mono">{{ detail.code }}</span></div>
          <div class="info-row"><span class="l">费用类别</span><span class="v">
            <span :class="categoryTagClass(detail.category)" :style="categoryStyle(detail.category)">{{ detail.category }}</span>
          </span></div>
          <div class="info-row"><span class="l">关联项目</span><span class="v">
            <a href="javascript:;" style="color: var(--color-primary)" @click="gotoProject">{{ detail.projectLink }}</a>
          </span></div>
          <div class="info-row"><span class="l">申请人</span><span class="v">{{ detail.applicant }}</span></div>
          <div class="info-row"><span class="l">申请部门</span><span class="v">{{ detail.department }}</span></div>
          <div class="info-row"><span class="l">申请时间</span><span class="v">{{ detail.applicantAt }}</span></div>
          <div class="info-row"><span class="l">报销金额</span><span class="v" style="color: var(--color-danger); font-weight: 700; font-size: 15px">
            ¥ {{ detail.amount.toLocaleString() }}
          </span></div>
          <div class="info-row"><span class="l">金额大写</span><span class="v" style="font-family: var(--font-family-mono, monospace)">{{ detail.amountCn }}</span></div>
          <div class="info-row"><span class="l">支付方式</span><span class="v">{{ detail.paymentMethod }}</span></div>
          <div class="info-row"><span class="l">收款信息</span><span class="v" style="font-size: 12.5px">{{ detail.payee }}</span></div>
          <div class="info-row full">
            <span class="l">费用摘要</span>
            <div class="term-block">
              <div class="d">{{ detail.description }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 费用明细 -->
    <div v-if="activeTab === 'items'" class="detail-section">
      <div class="detail-section-head">
        <h4>💰 费用明细（4 项）</h4>
        <span class="req" style="font-size: 12.5px; color: var(--color-text-tertiary)">
          合计：<strong style="color: var(--color-danger); font-size: 14px">¥ {{ detail.amount.toLocaleString() }}</strong>
        </span>
      </div>
      <div class="detail-section-body">
        <el-table :data="items" stripe>
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="date" label="费用日期" width="130" />
          <el-table-column prop="subCategory" label="子项类别" width="140" />
          <el-table-column prop="amount" label="金额（元）" width="140" align="right">
            <template #default="{ row }">
              <span style="font-weight: 600">¥ {{ row.amount.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="280" show-overflow-tooltip />
        </el-table>

        <div class="tip-box" style="margin-top: 16px">
          <div class="ico">ℹ</div>
          <div>
            <strong>说明：</strong>本次费用单笔 ¥{{ detail.amount.toLocaleString() }}，未触发"财务总监审批"门槛（单笔 ≥ ¥ 5,000）。
          </div>
        </div>
      </div>
    </div>

    <!-- 附件 -->
    <div v-if="activeTab === 'attach'" class="detail-section">
      <div class="detail-section-head"><h4>📎 附件（{{ attachments.length }}）</h4></div>
      <div class="detail-section-body">
        <el-table :data="attachments">
          <el-table-column prop="name" label="文件名" />
          <el-table-column prop="size" label="大小" width="120" />
          <el-table-column prop="uploader" label="上传人" width="100" />
          <el-table-column prop="at" label="时间" width="180" />
          <el-table-column label="操作" width="160">
            <template #default>
              <el-button type="primary" link>预览</el-button>
              <el-button type="primary" link>下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="att-area" style="margin-top: 16px">
          <div class="ico">📎</div>
          <div class="t">点击或拖拽上传补充附件</div>
          <div class="m">支持 PDF / 图片 / 发票扫描件，单文件 ≤ 10 MB</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }
</style>
