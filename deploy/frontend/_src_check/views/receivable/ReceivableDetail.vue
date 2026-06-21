<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { receivableApi, type Receivable } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const data = ref<Receivable | null>(null)
const activeTab = ref('basic')

// 模拟详情数据（design/receivable-detail.html 同款：HK-2026-018）
const detail = ref({
  id: 18,
  code: 'HK-2026-018',
  contractCode: 'HT-2026-030',
  contractTitle: '万象科技 2026Q1 服务费尾款',
  customerName: '万象科技有限公司',
  receivableType: '合同尾款',
  amount: 28000,
  receivedAmount: 0,
  dueDate: '2026-06-04',
  actualDate: '',
  paymentTerm: '30 天',
  overdueDays: 8,
  owner: '陈思琪（销售部）',
  bankAccount: '招行 6225 **** **** 1234',
  status: '逾期',
  statusLabel: '逾期 8 天',
  remarks: '客户已确认本次尾款，但因内部审批流程延迟，预计本周内可安排付款。已与客户李建国（CTO）沟通确认到账时间约 2026-06-15。',
})

// 回款计划
const schedule = ref([
  { seq: 1, name: '首期款', amount: 14000, planDate: '2026-03-15', actualDate: '2026-03-15', status: '已收' },
  { seq: 2, name: '中期款', amount: 14000, planDate: '2026-04-30', actualDate: '2026-04-29', status: '已收' },
  { seq: 3, name: '尾款', amount: 28000, planDate: '2026-06-04', actualDate: '', status: '逾期' },
])

// 到账记录
const records = ref([
  { date: '2026-04-29', amount: 14000, flowNo: '20260429B0021', operator: '张明' },
  { date: '2026-03-15', amount: 14000, flowNo: '20260315B0011', operator: '张明' },
])

// 关联发票
const invoices = ref([
  { code: '25113300000012345678', type: '电子普通发票', date: '2026-06-02', amount: 28000, status: '已认证' },
  { code: '25113300000012345120', type: '电子普通发票', date: '2026-04-20', amount: 14000, status: '已认证' },
])

// 客户信息
const customer = ref({
  name: '万象科技有限公司',
  contact: '李建国（CTO）',
  phone: '138 **** 8888',
  email: 'lijianguo@wx-tech.cn',
  history: '5/6 按期回款（83%）',
})

// 客户回款历史
const history = ref([
  { code: 'HK-2026-009', date: '2026-03-15', status: '按期', statusType: 'success', amount: 86500 },
  { code: 'HK-2025-118', date: '2025-12-30', status: '提前 1 天', statusType: 'success', amount: 86500 },
  { code: 'HK-2025-082', date: '2025-09-28', status: '按期', statusType: 'success', amount: 86500 },
  { code: 'HK-2025-045', date: '2025-06-30', status: '逾期 3 天', statusType: 'warning', amount: 56000 },
])

// 催收记录
const reminds = ref([
  {
    icon: '📞',
    type: '电话催收',
    summary: '陈思琪 → 李建国（CTO）',
    time: '2026-06-11 14:30 · 通话 8 分钟',
    detail: '客户反馈：因内部季度结算，付款流程延迟至本周。承诺 2026-06-15 之前安排。已发送书面付款提醒邮件至客户财务部。',
  },
  {
    icon: '📧',
    type: '邮件催收',
    summary: '发送至客户财务部',
    time: '2026-06-09 09:15 · 由陈思琪发起',
    detail: '邮件主题：「关于 2026Q1 尾款 ¥ 28,000 的付款提醒」\n附件：付款通知单.pdf · 合同副本.pdf',
  },
])

const receivedPct = computed(() => {
  if (!detail.value.amount) return 0
  return Math.round((detail.value.receivedAmount / detail.value.amount) * 100)
})

const pendingAmount = computed(() => detail.value.amount - detail.value.receivedAmount)

const heroClass = computed(() => {
  if (detail.value.status === '逾期') return 'detail-hero--overdue'
  if (detail.value.status === '已收') return 'detail-hero--done'
  return 'detail-hero--normal'
})

const statusTagClass = computed(() => {
  const s = detail.value.status
  if (s === '已收') return 'tag-success'
  if (s === '部分') return 'tag-warning'
  if (s === '逾期') return 'tag-danger'
  return 'tag-info'
})

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const r: any = await receivableApi.detail(id).catch(() => null)
    if (r) {
      data.value = r
      detail.value = {
        id: r.receivableId || r.id,
        code: r.code || detail.value.code,
        contractCode: r.contractCode || '—',
        contractTitle: r.contractName || '—',
        customerName: r.clientName || detail.value.customerName,
        receivableType: typeLabel(r.type),
        amount: Number(r.planAmount) || 0,
        receivedAmount: Number(r.receivedAmount) || 0,
        dueDate: (r.planDate || '').slice(0, 10),
        actualDate: (r.actualDate || '').slice(0, 10),
        paymentTerm: '30 天',
        overdueDays: Number(r.overdueDays) || 0,
        owner: r.managerName || detail.value.owner,
        bankAccount: '招行 6225 **** **** 1234（后端未提供）',
        status: statusLabel(r.status),
        statusLabel: statusLabel(r.status) + ((Number(r.overdueDays) || 0) > 0 ? ` ${r.overdueDays} 天` : ''),
        remarks: '回款进度可继续跟踪。',
      }
    }
  } finally {
    loading.value = false
  }
}

function typeLabel(t?: string) {
  return { prepayment: '预付款', progress: '进度款', final: '尾款', warranty: '质保金' }[t || ''] || (t || '—')
}
function statusLabel(s?: string) {
  return { pending: '待回款', partial: '部分回款', received: '已回款', overdue: '逾期', cancelled: '已取消' }[s || ''] || (s || '—')
}

function gotoBack() { router.push('/receivable/list') }
function handleExport() { ElMessage.success('已导出回款明细（演示）') }
async function handleRecord() {
  if (!detail.value?.id) return
  let amount = 0
  try {
    const res: any = await ElMessageBox.prompt(
      `本次到账金额（元）\n剩余未收：¥ ${((detail.value.amount - (detail.value.receivedAmount || 0)) / 100).toFixed(2)}`,
      '登记到账',
      {
        inputType: 'number',
        inputValue: String(((detail.value.amount - (detail.value.receivedAmount || 0)) / 100).toFixed(2)),
        inputValidator: (v: string) => {
          const n = Number(v)
          if (isNaN(n) || n <= 0) return '请输入正数'
          return true
        },
      },
    )
    amount = Number(res.value)
  } catch { return }
  const r: any = await receivableApi.receive(detail.value.id, { receivedAmount: amount, receivedDate: new Date().toISOString().slice(0, 10) }).catch((e: any) => ({ message: e?.message || '网络错误' }))
  if (r?.code === 0 || r?.id) {
    ElMessage.success('已登记到账')
    load()
  } else {
    ElMessage.error(r?.message || '登记失败')
  }
}
async function handleRemind() {
  if (!detail.value?.id) return
  const r: any = await receivableApi.remind(detail.value.id).catch((e: any) => ({ message: e?.message || '网络错误' }))
  if (r?.code === 0 || r?.sent_at || r?.id) {
    ElMessage.success('已发起催收')
  } else {
    ElMessage.error(r?.message || '催收失败')
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
          业务 / <router-link to="/receivable/list" style="color: var(--color-text-tertiary)">回款管理</router-link> / {{ detail.code }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          回款详情
          <span :class="['tag', statusTagClass]">{{ detail.statusLabel }}</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button :icon="'Back'" @click="gotoBack">返回</el-button>
        <el-button :icon="'Download'" @click="handleExport">导出明细</el-button>
        <el-button type="primary" :icon="'Plus'" @click="handleRecord">+ 登记到账</el-button>
      </div>
    </div>

    <!-- Hero（与 design/receivable-detail.html 1:1，走 detail-hero token + --receivable 变体）-->
    <div :class="['detail-hero', 'detail-hero--receivable', heroClass]">
      <div class="dh-left">
        <div class="dh-id">{{ detail.code }}</div>
        <h2>{{ detail.contractTitle }}</h2>
        <div class="dh-meta">关联合同：<strong style="color: #fff">{{ detail.contractCode }}</strong> · 负责人：{{ detail.owner }}</div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">待回款金额</div>
        <div class="dh-amount">¥ {{ pendingAmount.toLocaleString() }}.00</div>
      </div>
    </div>

    <!-- 逾期大告警（仅逾期时显示）-->
    <div v-if="detail.status === '逾期'" class="overdue-alert">
      <div class="ico">⚠</div>
      <div class="body">
        <div class="t">本笔回款已逾期 {{ detail.overdueDays }} 天</div>
        <div class="m">
          计划回款日：<strong>{{ detail.dueDate }}</strong> · 已超 {{ detail.overdueDays }} 天<br />
          客户：<strong>{{ customer.name }}</strong> · 客户联系人：<strong>{{ customer.contact }} · {{ customer.phone }}</strong><br />
          历史回款记录：客户过往 5 笔均按期回款，本次为首笔逾期，建议优先电话沟通。
        </div>
      </div>
      <div class="actions">
        <div class="days">
          <div class="v">{{ detail.overdueDays }}</div>
          <div class="l">逾期天数</div>
        </div>
        <el-button type="primary" size="small" @click="handleRemind">📞 立即催收</el-button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'basic' }" @click="activeTab = 'basic'">基本信息</a>
      <a :class="{ active: activeTab === 'schedule' }" @click="activeTab = 'schedule'">回款计划</a>
      <a :class="{ active: activeTab === 'records' }" @click="activeTab = 'records'">到账记录</a>
      <a :class="{ active: activeTab === 'invoices' }" @click="activeTab = 'invoices'">发票</a>
    </div>

    <!-- 两栏布局：左侧主内容 / 右侧元信息 -->
    <div class="detail-layout">
      <!-- 左 -->
      <div>
        <!-- 回款进度 -->
        <div class="re-progress-big">
          <div class="re-progress-head">
            <span class="t">回款进度</span>
            <span class="pct">{{ receivedPct }}%</span>
          </div>
          <div class="re-progress-bar-big">
            <div class="fill" :style="{ width: receivedPct + '%' }">
              <span v-if="receivedPct > 4" class="label">{{ receivedPct }}%</span>
            </div>
          </div>
          <div class="re-progress-legend">
            <div class="item">
              <span class="dot" style="background: #10B981"></span>
              <span>已回款</span>
              <span class="v">¥ {{ detail.receivedAmount.toLocaleString() }}</span>
            </div>
            <div class="item">
              <span class="dot" style="background: #EF4444"></span>
              <span>待回款</span>
              <span class="v">¥ {{ pendingAmount.toLocaleString() }}</span>
            </div>
            <div class="item">
              <span class="dot" style="background: #94A3B8"></span>
              <span>计划金额</span>
              <span class="v">¥ {{ detail.amount.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <!-- 基本信息 -->
        <div v-if="activeTab === 'basic'" class="detail-section">
          <div class="detail-section-head">
            <h4>💰 回款信息</h4>
          </div>
          <div class="detail-section-body">
            <div class="info-grid">
              <div class="info-row"><span class="l">回款编号</span><span class="v mono">{{ detail.code }}</span></div>
              <div class="info-row"><span class="l">关联合同</span><span class="v"><a href="javascript:;" style="color: var(--color-primary)">{{ detail.contractCode }} · {{ detail.contractTitle }}</a></span></div>
              <div class="info-row"><span class="l">客户</span><span class="v">{{ detail.customerName }}</span></div>
              <div class="info-row"><span class="l">回款类型</span><span class="v">{{ detail.receivableType }}</span></div>
              <div class="info-row"><span class="l">应收金额</span><span class="v amount">¥ {{ detail.amount.toLocaleString() }}.00</span></div>
              <div class="info-row"><span class="l">已回金额</span><span class="v amount" style="color: var(--color-danger)">¥ {{ detail.receivedAmount.toLocaleString() }}.00</span></div>
              <div class="info-row"><span class="l">计划回款日</span><span class="v">{{ detail.dueDate }}</span></div>
              <div class="info-row"><span class="l">实际回款日</span><span class="v" style="color: var(--color-text-tertiary)">{{ detail.actualDate || '—' }}</span></div>
              <div class="info-row"><span class="l">账期</span><span class="v">{{ detail.paymentTerm }}</span></div>
              <div class="info-row"><span class="l">逾期天数</span><span class="v" style="color: var(--color-danger); font-weight: 700">{{ detail.overdueDays }} 天</span></div>
              <div class="info-row"><span class="l">负责人</span><span class="v">{{ detail.owner }}</span></div>
              <div class="info-row"><span class="l">收款账户</span><span class="v" style="font-family: $font-family-mono; font-size: 12.5px">{{ detail.bankAccount }}</span></div>
              <div class="info-row full">
                <span class="l">备注</span>
                <div class="notes-block">{{ detail.remarks }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 回款计划 -->
        <div v-if="activeTab === 'schedule'" class="detail-section">
          <div class="detail-section-head"><h4>📅 回款计划（{{ schedule.length }} 期）</h4></div>
          <div class="detail-section-body" style="padding: 0">
            <el-table :data="schedule">
              <el-table-column label="期次" width="80" align="center">
                <template #default="{ row }"><span class="seq-badge">{{ row.seq }}</span></template>
              </el-table-column>
              <el-table-column prop="name" label="分期名称" min-width="140" />
              <el-table-column prop="amount" label="应收金额" width="140" align="right">
                <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}.00</template>
              </el-table-column>
              <el-table-column prop="planDate" label="计划日期" width="120" />
              <el-table-column prop="actualDate" label="实际日期" width="120">
                <template #default="{ row }">
                  <span v-if="row.actualDate">{{ row.actualDate }}</span>
                  <span v-else style="color: var(--color-text-tertiary)">—</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <span :class="['tag', row.status === '已收' ? 'tag-success' : row.status === '逾期' ? 'tag-danger' : 'tag-info']">{{ row.status }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 到账记录 -->
        <div v-if="activeTab === 'records'" class="detail-section">
          <div class="detail-section-head"><h4>💵 到账记录（{{ records.length }} 条）</h4></div>
          <div class="detail-section-body" style="padding: 0">
            <el-table :data="records">
              <el-table-column prop="date" label="到账日期" width="140" />
              <el-table-column label="金额" width="160" align="right">
                <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}.00</template>
              </el-table-column>
              <el-table-column prop="flowNo" label="银行流水号" min-width="200">
                <template #default="{ row }"><span style="font-family: $font-family-mono; font-size: 12.5px">{{ row.flowNo }}</span></template>
              </el-table-column>
              <el-table-column prop="operator" label="录入人" width="120" />
            </el-table>
            <div v-if="!records.length" style="padding: 20px"><el-empty description="暂无到账记录" /></div>
          </div>
        </div>

        <!-- 发票 -->
        <div v-if="activeTab === 'invoices'" class="detail-section">
          <div class="detail-section-head"><h4>▤ 关联发票（{{ invoices.length }} 张）</h4></div>
          <div class="detail-section-body" style="padding: 0">
            <el-table :data="invoices">
              <el-table-column label="发票号" min-width="200">
                <template #default="{ row }"><span style="font-family: $font-family-mono; font-size: 12.5px; color: var(--color-primary)">{{ row.code }}</span></template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="160" />
              <el-table-column prop="date" label="开票日期" width="120" />
              <el-table-column label="金额" width="140" align="right">
                <template #default="{ row }">¥ {{ row.amount.toLocaleString() }}.00</template>
              </el-table-column>
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <span class="tag tag-success">{{ row.status }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default><el-button type="primary" link>查看</el-button></template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- 右 -->
      <div>
        <!-- 客户信息 -->
        <div class="meta-card">
          <h4>👤 客户信息</h4>
          <div class="meta-info-grid">
            <div class="mi-row full"><span class="l">客户名称</span><span class="v">{{ customer.name }}</span></div>
            <div class="mi-row full"><span class="l">主要联系人</span><span class="v">{{ customer.contact }}</span></div>
            <div class="mi-row"><span class="l">手机</span><span class="v mono">{{ customer.phone }}</span></div>
            <div class="mi-row"><span class="l">邮箱</span><span class="v" style="font-size: 12.5px">{{ customer.email }}</span></div>
            <div class="mi-row full"><span class="l">付款历史</span><span class="v" style="color: var(--color-success)">{{ customer.history }}</span></div>
          </div>
        </div>

        <!-- 客户回款历史 -->
        <div class="meta-card">
          <h4>📊 客户回款历史</h4>
          <div class="rel-list">
            <div v-for="(h, i) in history" :key="i" class="rel-item">
              <div :class="['ico', h.statusType]">{{ h.statusType === 'success' ? '✓' : '!' }}</div>
              <div class="body">
                <div class="t" style="font-size: 12.5px">{{ h.code }}</div>
                <div class="m">{{ h.date }} · {{ h.status }}</div>
              </div>
              <div class="v" style="font-size: 12.5px">¥ {{ h.amount.toLocaleString() }}</div>
            </div>
          </div>
        </div>

        <!-- 风险评估 -->
        <div class="meta-card">
          <h4>🎯 风险评估</h4>
          <div class="risk-row">
            <div class="risk-grade">中</div>
            <div class="risk-meta">
              <div class="risk-name">中度风险</div>
              <div class="risk-desc">客户信用良好但本次逾期</div>
            </div>
          </div>
          <div class="risk-ai">
            <strong>AI 分析：</strong>该客户历史回款准时率 83%，本次为首笔严重逾期，但客户已主动沟通承诺到账时间，建议持续跟进，无需升级法务。
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="meta-card">
          <h4>⚡ 快捷操作</h4>
          <div class="quick-actions">
            <el-button type="primary" size="small" class="block" @click="handleRemind">📞 立即催收</el-button>
            <el-button size="small" class="block">📧 发送催收邮件</el-button>
            <el-button size="small" class="block">💬 微信通知</el-button>
            <el-button size="small" class="block" @click="handleRecord">+ 登记到账</el-button>
            <el-button size="small" class="block danger">⊗ 标记坏账</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

// 逾期大告警
.overdue-alert {
  background: linear-gradient(135deg, rgba(239,68,68,0.06), rgba(245,158,11,0.06));
  border: 1px solid rgba(239,68,68,0.25);
  border-radius: $radius-lg;
  padding: 20px 24px;
  margin-bottom: 20px;
  display: flex; gap: 16px; align-items: center;
  .ico {
    width: 56px; height: 56px;
    border-radius: 50%;
    background: rgba(239,68,68,0.15);
    color: $color-danger;
    display: grid; place-items: center;
    font-size: 28px;
    flex-shrink: 0;
  }
  .body { flex: 1; }
  .body .t {
    font-size: 16px; font-weight: 600;
    color: $color-danger;
    margin-bottom: 4px;
  }
  .body .m {
    font-size: 13px;
    color: $color-text-secondary;
    line-height: 1.6;
    strong { color: $color-danger; }
  }
  .actions { display: flex; flex-direction: column; gap: 8px; }
  .days {
    text-align: center;
    background: $color-danger;
    color: #fff;
    border-radius: $radius-md;
    padding: 14px 20px;
    .v { font-size: 32px; font-weight: 800; line-height: 1; }
    .l { font-size: 11px; margin-top: 4px; }
  }
}

// 回款进度大字
.re-progress-big {
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 24px;
  margin-bottom: 20px;
}
.re-progress-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 14px;
  .t { font-size: 14px; font-weight: 600; }
  .pct { font-size: 24px; font-weight: 700; color: $color-primary; }
}
.re-progress-bar-big {
  height: 14px;
  background: #F1F5F9;
  border-radius: 999px;
  overflow: hidden;
  position: relative;
  margin-bottom: 12px;
  .fill {
    height: 100%;
    background: $gradient-brand;
    border-radius: 999px;
    position: relative;
    transition: width 0.4s ease;
  }
  .label {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: #fff;
    font-weight: 700;
    padding: 0 8px;
  }
}
.re-progress-legend {
  display: flex; justify-content: space-between;
  font-size: 12.5px;
  color: $color-text-secondary;
  .item { display: flex; align-items: center; gap: 6px; }
  .item .v { font-weight: 700; color: $color-text-primary; }
  .item .dot { width: 8px; height: 8px; border-radius: 50%; }
}

// 信息行 amount 高亮
.info-grid .info-row .v.amount {
  font-weight: 700;
  color: $color-text-primary;
}

// 备注块（design 1:1）
.notes-block {
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 12px 14px;
  font-size: 12.5px;
  color: $color-text-secondary;
  line-height: 1.7;
}

// 期次序号圆点
.seq-badge {
  display: inline-grid; place-items: center;
  width: 26px; height: 26px;
  border-radius: 50%;
  background: $gradient-brand;
  color: #fff;
  font-size: 12px; font-weight: 600;
}

// 两栏布局
.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 20px;
  @media (max-width: 1100px) {
    grid-template-columns: 1fr;
  }
}

// 右侧元信息卡片
.meta-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  margin-bottom: 20px;
  h4 { font-size: 13.5px; font-weight: 600; margin: 0 0 14px 0; display: flex; align-items: center; gap: 8px; }
}
.meta-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  .mi-row {
    display: flex; align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid $color-border;
    &:nth-last-child(-n+2) { border-bottom: none; }
    .l { width: 88px; color: $color-text-tertiary; font-size: 12.5px; flex-shrink: 0; }
    .v { color: $color-text-primary; font-size: 12.5px; flex: 1; word-break: break-all; &.mono { font-family: $font-family-mono; } }
    &.full { grid-column: 1 / -1; }
  }
}

// 关联项（design 1:1）
.rel-list { display: flex; flex-direction: column; gap: 0; }
.rel-item {
  display: flex; gap: 10px; align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid $color-border;
  &:last-child { border-bottom: none; }
  .ico {
    width: 30px; height: 30px;
    border-radius: 50%;
    display: grid; place-items: center;
    font-size: 13px; font-weight: 700;
    flex-shrink: 0;
    &.success { background: rgba(16,185,129,0.1); color: $color-success; }
    &.warning { background: rgba(245,158,11,0.1); color: $color-warning; }
  }
  .body { flex: 1; min-width: 0; }
  .body .t { font-size: 13px; font-weight: 500; color: $color-text-primary; }
  .body .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .v { font-weight: 600; color: $color-text-primary; }
}

// 风险评估
.risk-row {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 10px;
}
.risk-grade {
  font-size: 32px; font-weight: 800;
  color: $color-warning;
  line-height: 1;
}
.risk-meta { flex: 1; }
.risk-name { font-size: 12.5px; font-weight: 500; }
.risk-desc { font-size: 11.5px; color: $color-text-tertiary; }
.risk-ai {
  font-size: 11.5px;
  color: $color-text-secondary;
  line-height: 1.6;
  padding-top: 10px;
  border-top: 1px solid $color-border;
  strong { color: $color-primary; }
}

// 快捷操作
.quick-actions {
  display: flex; flex-direction: column; gap: 8px;
  .block { width: 100%; justify-content: center; }
  .danger { color: $color-danger; border-color: rgba(239,68,68,0.3); }
  .danger:hover { background: $color-danger-bg; border-color: $color-danger; }
}
</style>
