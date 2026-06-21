<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contractApi, type Contract } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<Contract | null>(null)
const activeTab = ref('basic')

// 模拟详情数据（design/contract-detail.html 同款）
const detail = ref({
  contractNo: 'HT-2026-031',
  contractType: '销售合同',
  customerName: '万象科技有限公司',
  customerTaxNo: '91310000MA1FL01X9G',
  signDate: '2026-06-11',
  effectiveDate: '2026-06-15',
  expireDate: '2027-06-10',
  period: '12 个月',
  paymentMethod: '季付（每季度初 5 个工作日内）',
  paymentTerm: '30 天',
  currency: '人民币 (CNY)',
  projectLink: 'PRJ-2026-022 · 万象科技 SaaS 部署',
  summary: '万象科技 2026 年 Q2 SaaS 平台服务合同，涵盖发票识别、模板管理、报表分析等核心模块。包含季度版本升级、技术支持 SLA、专属客户经理等增值服务。',
  amount: 86500,
  status: '审批中',
})

// 审批流（横向 6 节点）
const flowSteps = [
  { lbl: '起草', node: '✓', state: 'done', meta: ['李明', '2026-06-11 10:23'] },
  { lbl: '法务审核', node: '✓', state: 'done', meta: ['王律师', '2026-06-11 14:30'] },
  { lbl: '财务审核', node: '3', state: 'current', meta: ['张明', '审核中 · 待处理'] },
  { lbl: '总经理审批', node: '4', state: 'pending', meta: ['待提交', '金额 ≥ 5 万触发'] },
  { lbl: '电子签', node: '5', state: 'pending', meta: ['未开始', ''] },
  { lbl: '归档', node: '6', state: 'pending', meta: ['未开始', ''] },
]

// 关键条款
const terms = [
  { t: '1. 服务内容', d: 'SaaS 平台标准版 30 个用户账号，含发票识别、模板管理、报表分析、API 对接等核心功能。' },
  { t: '2. 付款条款', d: '合同总金额 ¥ 86,500，分 4 期支付，每季度 ¥ 21,625。每期发票在付款前 5 个工作日开具。' },
  { t: '3. SLA 保障', d: '系统可用性 ≥ 99.9%，故障响应时间 ≤ 30 分钟，重大故障恢复时间 ≤ 4 小时。月度可用性低于 99% 时，按月费的 10% 抵扣下月费用。' },
  { t: '4. 知识产权', d: '平台软件著作权归乙方所有，甲方在合同期内享有非独占、不可转让的使用权。客户数据所有权归甲方，乙方负有保密义务。' },
  { t: '5. 违约责任', d: '任意一方违约，应承担守约方因此产生的合理费用（包括但不限于律师费、诉讼费、差旅费）。赔偿总额不超过本合同年度总金额的 200%。' },
  { t: '6. 终止条款', d: '任一方可在提前 30 天书面通知对方后终止本合同。终止后双方应进行对账结算，已开具发票的费用不予退还。' },
]

// 签章
const sign = {
  partyA: { name: '万象科技有限公司', signed: true, time: '2026-06-12 09:30' },
  partyB: { name: '上海数智信息技术有限公司', signed: false, time: '待签' },
}

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const r: any = await contractApi.detail(id).catch(() => null)
    if (r) {
      data.value = r
      // 把后端数据映射到 detail（后端字段是合同编号 code/客户名 clientName 等）
      detail.value = {
        contractNo: r.code || detail.value.contractNo,
        contractType: typeLabel(r.type),
        customerName: r.clientName || detail.value.customerName,
        customerTaxNo: '—（后端未提供）',
        signDate: (r.signDate || '').slice(0, 10),
        effectiveDate: (r.effectiveDate || '').slice(0, 10),
        expireDate: (r.expireDate || '').slice(0, 10),
        period: '12 个月',
        paymentMethod: '季付（默认）',
        paymentTerm: '30 天',
        currency: r.currency || 'CNY',
        projectLink: r.projectName ? `${r.projectName}` : '—',
        summary: r.description || '合同主要约定双方权利义务，详见合同条款。',
        amount: Number(r.amount) || 0,
        status: statusLabel(r.status),
      }
    }
  } finally {
    loading.value = false
  }
}

function typeLabel(t?: string) {
  return { sales: '销售合同', purchase: '采购合同', service: '服务合同', framework: '框架协议' }[t || ''] || (t || '—')
}
function statusLabel(s?: string) {
  return { draft: '草稿', pending: '待审批', approving: '审批中', approved: '已签订', rejected: '已驳回', signed: '已签订' }[s || ''] || (s || '—')
}

function gotoBack() { router.push('/contract/list') }
function gotoAiPanel() { router.push('/ai/panel/contract') }

async function handleApprove() {
  const d: any = detail.value
  if (!d?.id) return
  try {
    await ElMessageBox.confirm(`确定审批通过合同「${d.code}」？`, '审批合同', { type: 'success' })
  } catch { return }
  const r: any = await contractApi.approve(d.id, { action: 'approve' }).catch((e: any) => ({ message: e?.message || '网络错误' }))
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
    const res: any = await ElMessageBox.prompt('请输入驳回原因', '驳回合同', {
      inputType: 'textarea',
      inputValidator: (v: string) => (v && v.length >= 2) ? true : '至少 2 个字',
    })
    comment = res.value
  } catch { return }
  const r: any = await contractApi.approve(d.id, { action: 'reject', comment }).catch((e: any) => ({ message: e?.message || '网络错误' }))
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
          业务 / <router-link to="/contract/list" style="color: var(--color-text-tertiary)">合同管理</router-link> / {{ detail.contractNo }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          合同详情
          <span class="tag tag-warning">{{ detail.status }}</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button :icon="'Download'">下载 PDF</el-button>
        <el-button :icon="'Share'">分享</el-button>
        <el-button style="background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%); color: #fff; border: none" @click="gotoAiPanel">🤖 AI 体检</el-button>
        <el-button style="color: var(--color-danger); border-color: rgba(239,68,68,0.3)" @click="handleReject">✕ 驳回</el-button>
        <el-button type="primary" @click="handleApprove">✓ 审批通过</el-button>
      </div>
    </div>

    <!-- Hero（与 design/contract-detail.html 1:1） -->
    <div class="detail-hero">
      <div class="dh-left">
        <div class="dh-id">{{ detail.contractNo }}</div>
        <h2>{{ data?.name || '合同详情' }}</h2>
        <div class="dh-meta">客户：<strong style="color: #fff">{{ detail.customerName }}</strong> · {{ detail.contractType }} · {{ detail.signDate }} ~ {{ detail.expireDate }}</div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">合同总金额</div>
        <div class="dh-amount">¥ {{ detail.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
      </div>
    </div>

    <!-- Tabs（与 design 1:1：基本信息/合同条款/审批流/附件/履约记录/发票回款）-->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">基本信息</a>
      <a :class="{ active: activeTab === 'terms' }" @click="activeTab = 'terms'">合同条款</a>
      <a :class="{ active: activeTab === 'flow' }" @click="activeTab = 'flow'">审批流</a>
      <a :class="{ active: activeTab === 'attach' }" @click="activeTab = 'attach'">附件</a>
      <a :class="{ active: activeTab === 'fulfill' }" @click="activeTab = 'fulfill'">履约记录</a>
      <a :class="{ active: activeTab === 'invoice' }" @click="activeTab = 'invoice'">发票/回款</a>
    </div>

    <!-- 审批流（横 6 节点）-->
    <div v-if="activeTab === 'flow' || activeTab === 'basic'" class="flow-horizontal">
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
        <h4>📋 合同基本信息</h4>
      </div>
      <div class="detail-section-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">合同编号</span><span class="v mono">{{ detail.contractNo }}</span></div>
          <div class="info-row"><span class="l">合同类型</span><span class="v">{{ detail.contractType }}</span></div>
          <div class="info-row"><span class="l">客户名称</span><span class="v">{{ detail.customerName }}</span></div>
          <div class="info-row"><span class="l">客户纳税人识别号</span><span class="v mono" style="font-size: 12.5px">{{ detail.customerTaxNo }}</span></div>
          <div class="info-row"><span class="l">签订日期</span><span class="v">{{ detail.signDate }}</span></div>
          <div class="info-row"><span class="l">生效日期</span><span class="v">{{ detail.effectiveDate }}</span></div>
          <div class="info-row"><span class="l">到期日期</span><span class="v">{{ detail.expireDate }}</span></div>
          <div class="info-row"><span class="l">合同期限</span><span class="v">{{ detail.period }}</span></div>
          <div class="info-row"><span class="l">付款方式</span><span class="v">{{ detail.paymentMethod }}</span></div>
          <div class="info-row"><span class="l">付款账期</span><span class="v">{{ detail.paymentTerm }}</span></div>
          <div class="info-row"><span class="l">币种</span><span class="v">{{ detail.currency }}</span></div>
          <div class="info-row"><span class="l">项目</span><span class="v"><a href="javascript:;" style="color: var(--color-primary)">{{ detail.projectLink }}</a></span></div>
          <div class="info-row full">
            <span class="l">合同摘要</span>
            <div class="term-block">
              <div class="d">{{ detail.summary }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 合同条款 -->
    <div v-if="activeTab === 'terms'" class="detail-section">
      <div class="detail-section-head">
        <h4>📑 关键条款</h4>
      </div>
      <div class="detail-section-body">
        <div v-for="(t, i) in terms" :key="i" class="term-block">
          <div class="t">{{ t.t }}</div>
          <div class="d">{{ t.d }}</div>
        </div>

        <!-- 签章区 -->
        <div class="sign-area">
          <div :class="['sign-box', sign.partyA.signed ? 'signed' : '']">
            <div class="l">甲方签章</div>
            <div class="n">{{ sign.partyA.name }}</div>
            <div class="s">{{ sign.partyA.signed ? `已签 · ${sign.partyA.time}` : '待签' }}</div>
          </div>
          <div :class="['sign-box', sign.partyB.signed ? 'signed' : '']">
            <div class="l">乙方签章</div>
            <div class="n">{{ sign.partyB.name }}</div>
            <div class="s">{{ sign.partyB.signed ? `已签 · ${sign.partyB.time}` : '待签' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 附件 -->
    <div v-if="activeTab === 'attach'" class="detail-section">
      <div class="detail-section-head"><h4>📎 附件（3）</h4></div>
      <div class="detail-section-body">
        <el-table :data="[
          { name: 'HT-2026-031_主合同.pdf', size: '1.2 MB', uploader: '李明', at: '2026-06-11 10:25' },
          { name: '技术方案_v2.docx', size: '580 KB', uploader: '王律师', at: '2026-06-11 14:20' },
          { name: '客户资质.zip', size: '3.4 MB', uploader: '李明', at: '2026-06-11 10:28' },
        ]">
          <el-table-column prop="name" label="文件名" />
          <el-table-column prop="size" label="大小" width="120" />
          <el-table-column prop="uploader" label="上传人" width="100" />
          <el-table-column prop="at" label="时间" width="180" />
          <el-table-column label="操作" width="120">
            <template #default><el-button type="primary" link>下载</el-button></template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 履约记录 -->
    <div v-if="activeTab === 'fulfill'" class="detail-section">
      <div class="detail-section-head"><h4>📈 履约记录</h4></div>
      <div class="detail-section-body">
        <el-empty description="暂无履约记录" />
      </div>
    </div>

    <!-- 发票/回款 -->
    <div v-if="activeTab === 'invoice'" class="detail-section">
      <div class="detail-section-head"><h4>💰 发票/回款</h4></div>
      <div class="detail-section-body">
        <el-table :data="[
          { code: 'FP-2026-Q2-001', amount: 21625, status: '已开票', date: '2026-06-15' },
          { code: 'FP-2026-Q3-001', amount: 21625, status: '待开票', date: '2026-09-15' },
        ]">
          <el-table-column prop="code" label="发票号" width="160" />
          <el-table-column prop="amount" label="金额" width="120" align="right" />
          <el-table-column prop="date" label="开票日期" width="120" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '已开票' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }
</style>
