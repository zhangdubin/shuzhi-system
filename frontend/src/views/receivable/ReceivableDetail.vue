<script setup lang="ts">
/**
 * ReceivableDetail · 回款详情（1:1 复刻 design/receivable-detail.html）
 * - receivable-hero 蓝紫渐变 + 编号 + 客户 + 金额 + 进度
 * - 4 detail-tabs（回款信息/催收记录/客户回款历史/风险评估）
 * - 左主区：回款信息 + 4 期付款计划 + 催收记录 + 关联发票
 * - 右主区：客户信息 + 客户回款历史 + 风险评估 + 快捷操作
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { receivableApi } from '@/api/modules'

const router = useRouter()
const route = useRoute()

const activeTab = ref<'basic' | 'reminder' | 'history' | 'risk'>('basic')
const loading = ref(false)

const mock = reactive({
  id: 24,
  code: 'HK-2026-024',
  client: '万象科技有限公司',
  contract: 'HT-2026-031 · 万象科技 SaaS 服务合同 2026Q2',
  status: '已完成',
  statusColor: 'success',
  totalAmount: '199,500.00',
  receivedAmount: '199,500.00',
  pendingAmount: '0.00',
  progress: 100,
  expectedDate: '2026-06-12',
  actualDate: '2026-06-12',
  method: '银行转账',
  account: '6225 1234 5678 9012',
  manager: '王芳',
  project: 'PRJ-2026-022',
})

// 4 期付款计划（设计稿真实数据）
const schedules = ref([
  { seq: 1, name: '首期款（30%）', planned: '59,850.00', actual: '59,850.00',  date: '2026-03-15', status: 'paid'    },
  { seq: 2, name: '二期款（30%）', planned: '59,850.00', actual: '59,850.00',  date: '2026-04-30', status: 'paid'    },
  { seq: 3, name: '三期款（20%）', planned: '39,900.00', actual: '39,900.00',  date: '2026-05-25', status: 'paid'    },
  { seq: 4, name: '尾款（20%）',   planned: '39,900.00', actual: '39,900.00',  date: '2026-06-12', status: 'paid'    },
])

// 2 催收记录
const reminders = ref([
  { date: '2026-06-05', type: '邮件', content: '尾款 ¥39,900 将于 7 天后到期，请安排付款。', sender: '王芳', response: '客户已确认财务流程中' },
  { date: '2026-06-10', type: '电话', content: '与客户财务确认：6/12 已打款 ¥39,900。', sender: '王芳', response: '已确认到账' },
])

// 1 关联发票
const invoices = ref([
  { code: '25113...45678', amount: '¥ 199,500.00', type: '销售服务费', date: '2026-06-12', status: '已核销', statusColor: 'success' },
])

// 客户信息
const client = reactive({
  name: '万象科技有限公司',
  level: 'VIP',
  levelColor: 'warning',
  contact: '李建国（CTO）',
  phone: '138-****-5689',
  email: 'likj@wxiang.com',
  taxNo: '91310000MA1FL3X9G',
  creditRating: 'AAA',
  totalReceived: '2,860,000',
  totalAmount: '3,260,000',
  avgDays: 32,
})

// 5 行客户回款历史
const clientHistory = ref([
  { contract: 'HT-2025-098', amount: '¥ 286,000',  date: '2025-12-10', days: 28, status: '已结清', statusColor: 'success' },
  { contract: 'HT-2025-085', amount: '¥ 168,000',  date: '2025-09-15', days: 30, status: '已结清', statusColor: 'success' },
  { contract: 'HT-2025-072', amount: '¥ 86,500',   date: '2025-07-20', days: 25, status: '已结清', statusColor: 'success' },
  { contract: 'HT-2025-068', amount: '¥ 1,280,000', date: '2025-05-10', days: 45, status: '已结清', statusColor: 'success' },
  { contract: 'HT-2025-055', amount: '¥ 56,000',   date: '2025-03-08', days: 22, status: '已结清', statusColor: 'success' },
])

// 4 风险评估项
const risks = ref([
  { t: '回款及时性',  status: 'pass', desc: '近 12 笔回款均按期到账，无逾期' },
  { t: '客户信用',    status: 'pass', desc: '信用等级 AAA，账期 30 天内' },
  { t: '金额匹配',    status: 'pass', desc: '回款总金额 = 合同总金额，无差额' },
  { t: '单据完整性',  status: 'pass', desc: '合同 / 发票 / 银行回单齐全，可入账' },
])

function goBack() { router.push('/receivable/list') }
function editReceivable() { ElMessage.info('编辑回款') }
function newReminder() { ElMessage.info('新建催收') }
function confirmReceipt() { ElMessage.success('已确认到账') }
function downloadInvoice() { ElMessage.info('下载发票') }
function downloadContract() { ElMessage.info('下载合同') }

onMounted(() => {
  loading.value = true
  receivableApi.detail(Number(route.params.id) || mock.id)
    .then(() => { /* mock */ })
    .catch(() => { /* mock */ })
    .finally(() => { loading.value = false })
})
</script>

<template>
  <div class="page-container">
    <!-- receivable-hero（design 顶部蓝紫渐变） -->
    <div class="receivable-hero">
      <div class="rh-left">
        <div class="rh-id">
          <span class="code">{{ mock.code }}</span>
          <span :class="['tag', `tag-${mock.statusColor}`]">{{ mock.status }}</span>
        </div>
        <h1 class="rh-title">{{ mock.contract }}</h1>
        <div class="rh-meta">
          <span>🏢 {{ mock.client }}</span>
          <span class="sep">·</span>
          <span>👤 {{ mock.manager }}</span>
          <span class="sep">·</span>
          <span>💳 {{ mock.method }}</span>
        </div>
      </div>
      <div class="rh-right">
        <div class="rh-amount-l">回款总额 · 已收 {{ mock.progress }}%</div>
        <div class="rh-amount-row">
          <div>
            <div class="rh-amount-l">已收金额</div>
            <div class="rh-amount received">¥ {{ mock.receivedAmount }}</div>
          </div>
          <div class="rh-amount-sep">/</div>
          <div>
            <div class="rh-amount-l">应收总额</div>
            <div class="rh-amount total">¥ {{ mock.totalAmount }}</div>
          </div>
        </div>
        <div class="re-progress-big">
          <div class="re-progress-bar-big">
            <div class="re-progress-fill" :style="{ width: mock.progress + '%' }"></div>
          </div>
        </div>
        <div class="rh-actions">
          <button v-permission="'receivable:write'" class="btn btn-ghost btn-sm" @click="editReceivable">✎ 编辑</button>
          <button v-permission="'receivable:write'" class="btn btn-outline btn-sm" @click="newReminder">📞 催收</button>
          <button v-permission="'receivable:write'" class="btn btn-primary btn-sm" @click="confirmReceipt">✓ 确认到账</button>
        </div>
      </div>
    </div>

    <!-- detail-tabs -->
    <div class="detail-tabs">
      <a href="javascript:void(0)" :class="{ active: activeTab === 'basic' }"    @click="activeTab = 'basic'">💰 回款信息</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'reminder' }" @click="activeTab = 'reminder'">📞 催收记录</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'history' }"  @click="activeTab = 'history'">📊 客户回款历史</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'risk' }"     @click="activeTab = 'risk'">🎯 风险评估</a>
    </div>

    <div class="detail-layout">
      <!-- 左主区 -->
      <div>
        <!-- 回款信息 -->
        <div v-show="activeTab === 'basic'">
          <div class="detail-section">
            <div class="detail-section-head">
              <h4>💰 回款信息</h4>
            </div>
            <div class="detail-section-body">
              <div class="info-grid">
                <div class="info-row"><span class="l">回款编号</span><span class="v mono">{{ mock.code }}</span></div>
                <div class="info-row"><span class="l">客户名称</span><span class="v">{{ mock.client }}</span></div>
                <div class="info-row"><span class="l">关联合同</span><span class="v mono">{{ mock.contract }}</span></div>
                <div class="info-row"><span class="l">关联项目</span><span class="v mono">{{ mock.project }}</span></div>
                <div class="info-row"><span class="l">应收总额</span><span class="v amount">¥ {{ mock.totalAmount }}</span></div>
                <div class="info-row"><span class="l">已收金额</span><span class="v success">¥ {{ mock.receivedAmount }}</span></div>
                <div class="info-row"><span class="l">待收金额</span><span class="v">¥ {{ mock.pendingAmount }}</span></div>
                <div class="info-row"><span class="l">回款方式</span><span class="v">{{ mock.method }}</span></div>
                <div class="info-row"><span class="l">收款账号</span><span class="v mono">{{ mock.account }}</span></div>
                <div class="info-row"><span class="l">计划回款日</span><span class="v">{{ mock.expectedDate }}</span></div>
                <div class="info-row"><span class="l">实际回款日</span><span class="v">{{ mock.actualDate }}</span></div>
                <div class="info-row"><span class="l">负责人</span><span class="v">{{ mock.manager }}</span></div>
              </div>
            </div>
          </div>

          <!-- 4 期付款计划 -->
          <div class="detail-section">
            <div class="detail-section-head">
              <h4>💰 付款计划（4 期 · 全部完成）</h4>
              <span class="tag tag-success">100% 已收</span>
            </div>
            <div class="detail-section-body">
              <table class="pay-table">
                <thead>
                  <tr><th>期次</th><th>名称</th><th style="text-align: right;">计划金额</th><th style="text-align: right;">实际到账</th><th>计划日</th><th>实际日</th><th>状态</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(s, i) in schedules" :key="i">
                    <td><strong>{{ s.seq }}</strong></td>
                    <td>{{ s.name }}</td>
                    <td class="cell-amount">¥ {{ s.planned }}</td>
                    <td class="cell-amount success">¥ {{ s.actual }}</td>
                    <td>{{ s.date }}</td>
                    <td>{{ s.date }}</td>
                    <td><span class="tag tag-success">已支付</span></td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr>
                    <td colspan="2"><strong>合计</strong></td>
                    <td class="cell-amount total">¥ {{ mock.totalAmount }}</td>
                    <td class="cell-amount total success">¥ {{ mock.receivedAmount }}</td>
                    <td colspan="3" style="font-size: 11px; color: var(--color-text-tertiary);">4 期全部按期到账，无逾期</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          <!-- 关联发票 -->
          <div class="detail-section">
            <div class="detail-section-head">
              <h4>▤ 关联发票（1 张）</h4>
            </div>
            <div class="detail-section-body">
              <table class="ct-table">
                <thead>
                  <tr><th>发票号</th><th>类型</th><th style="text-align: right;">金额</th><th>开票日期</th><th>状态</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(inv, i) in invoices" :key="i">
                    <td><span class="cell-mono">{{ inv.code }}</span></td>
                    <td><span class="tag tag-info">{{ inv.type }}</span></td>
                    <td class="cell-amount">{{ inv.amount }}</td>
                    <td>{{ inv.date }}</td>
                    <td><span :class="['tag', `tag-${inv.statusColor}`]">{{ inv.status }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 催收记录 -->
        <div v-show="activeTab === 'reminder'" class="detail-section">
          <div class="detail-section-head">
            <h4>📞 催收记录（{{ reminders.length }} 次）</h4>
            <button class="btn btn-primary btn-sm" @click="newReminder">+ 新建催收</button>
          </div>
          <div class="detail-section-body">
            <div class="timeline-det">
              <div v-for="(r, i) in reminders" :key="i" class="timeline-det-item done">
                <div class="t">{{ r.type }} · {{ r.date }}</div>
                <div class="m">{{ r.sender }} · {{ r.content }}</div>
                <div class="d">客户反馈：{{ r.response }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 客户回款历史 -->
        <div v-show="activeTab === 'history'" class="detail-section">
          <div class="detail-section-head">
            <h4>📊 客户回款历史（近 5 笔）</h4>
            <a class="link-primary">查看全部 →</a>
          </div>
          <div class="detail-section-body">
            <table class="ct-table">
              <thead>
                <tr><th>合同编号</th><th style="text-align: right;">金额</th><th>回款日期</th><th>账期（天）</th><th>状态</th></tr>
              </thead>
              <tbody>
                <tr v-for="(h, i) in clientHistory" :key="i">
                  <td><span class="cell-mono">{{ h.contract }}</span></td>
                  <td class="cell-amount">{{ h.amount }}</td>
                  <td>{{ h.date }}</td>
                  <td class="cell-num">{{ h.days }}</td>
                  <td><span :class="['tag', `tag-${h.statusColor}`]">{{ h.status }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 风险评估 -->
        <div v-show="activeTab === 'risk'" class="detail-section">
          <div class="detail-section-head">
            <h4>🎯 风险评估 · 4 项</h4>
            <span class="tag tag-success">✓ 全部通过</span>
          </div>
          <div class="detail-section-body">
            <div class="risk-grid">
              <div v-for="(c, i) in risks" :key="i" class="risk-row">
                <div class="check-status">✓</div>
                <div>
                  <div class="c-name">{{ c.t }}</div>
                  <div class="c-desc">{{ c.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右主区 meta-card -->
      <div>
        <!-- 客户信息 -->
        <div class="meta-card">
          <h4>👤 客户信息</h4>
          <div class="info-grid compact">
            <div class="info-row"><span class="l">客户名称</span><span class="v">{{ client.name }}</span></div>
            <div class="info-row"><span class="l">客户等级</span><span :class="['tag', `tag-${client.levelColor}`]">★ {{ client.level }}</span></div>
            <div class="info-row"><span class="l">联系人</span><span class="v">{{ client.contact }}</span></div>
            <div class="info-row"><span class="l">电话</span><span class="v">{{ client.phone }}</span></div>
            <div class="info-row"><span class="l">邮箱</span><span class="v">{{ client.email }}</span></div>
            <div class="info-row"><span class="l">税号</span><span class="v mono">{{ client.taxNo }}</span></div>
            <div class="info-row"><span class="l">信用等级</span><span class="v">{{ client.creditRating }}</span></div>
            <div class="info-row"><span class="l">平均账期</span><span class="v">{{ client.avgDays }} 天</span></div>
            <div class="info-row"><span class="l">累计已收</span><span class="v success">¥ {{ client.totalReceived }}</span></div>
            <div class="info-row"><span class="l">累计合同</span><span class="v">¥ {{ client.totalAmount }}</span></div>
          </div>
        </div>

        <!-- 风险评估卡片（始终显示） -->
        <div class="meta-card">
          <h4>🎯 风险评估</h4>
          <div v-for="(c, i) in risks" :key="i" class="check-row">
            <div :class="['dot', c.status]"></div>
            <span>{{ c.t }}</span>
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="meta-card">
          <h4>⚡ 快捷操作</h4>
          <div class="quick-actions">
            <button class="qa-btn" @click="newReminder">📞 发起催收</button>
            <button class="qa-btn" @click="downloadInvoice">📄 下载发票</button>
            <button class="qa-btn" @click="downloadContract">📑 下载合同</button>
            <button class="qa-btn" @click="ElMessage.info('核销入账')">✓ 核销入账</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

// receivable-hero（design 蓝紫渐变）
.receivable-hero {
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  color: #fff;
  border-radius: $radius-lg;
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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
  .rh-left { position: relative; z-index: 1; flex: 1; min-width: 0; }
  .rh-id { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .rh-id .code {
    font-family: $font-family-mono;
    font-size: 12.5px;
    color: rgba(255,255,255,0.85);
  }
  .rh-id .tag {
    background: rgba(255,255,255,0.18);
    color: #fff;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 11.5px;
    font-weight: 500;
  }
  .rh-title { font-size: 20px; font-weight: 700; margin: 0 0 8px 0; color: #fff; }
  .rh-meta { font-size: 12.5px; color: rgba(255,255,255,0.8); .sep { margin: 0 8px; opacity: 0.5; } }
  .rh-right { text-align: right; position: relative; z-index: 1; flex-shrink: 0; min-width: 360px; }
  .rh-amount-l { font-size: 11.5px; color: rgba(255,255,255,0.75); margin-bottom: 6px; }
  .rh-amount-row {
    display: flex; align-items: center; justify-content: flex-end;
    gap: 12px; margin-bottom: 8px;
  }
  .rh-amount-sep { font-size: 24px; color: rgba(255,255,255,0.5); }
  .rh-amount {
    font-size: 22px; font-weight: 700; color: #fff;
    font-family: $font-family-mono;
    &.received { color: #4ADE80; }
    &.total    { color: #fff; opacity: 0.85; }
  }
  .re-progress-big { margin-bottom: 12px; }
  .re-progress-bar-big {
    height: 8px;
    background: rgba(255,255,255,0.18);
    border-radius: 9999px;
    overflow: hidden;
  }
  .re-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4ADE80, #10B981);
    border-radius: 9999px;
    box-shadow: 0 0 12px rgba(74,222,128,0.5);
  }
  .rh-actions { display: flex; gap: 8px; justify-content: flex-end; }
  .btn {
    background: rgba(255,255,255,0.18);
    color: #fff;
    border-color: rgba(255,255,255,0.3);
    &:hover { background: rgba(255,255,255,0.28); }
    &.btn-primary { background: #fff; color: $color-primary; border-color: #fff; }
  }
}

.detail-tabs {
  display: flex; gap: 4px;
  background: #fff; padding: 4px; border-radius: $radius-md;
  box-shadow: $shadow-sm; margin-bottom: 16px; width: fit-content;
  a {
    padding: 8px 16px; border-radius: $radius-sm;
    font-size: 13px; color: $color-text-secondary;
    text-decoration: none; cursor: pointer; font-weight: 500;
    &:hover { background: $color-bg; color: $color-primary; }
    &.active { background: $color-primary; color: #fff; font-weight: 600; }
  }
}

.detail-layout {
  display: grid; grid-template-columns: 1fr 320px; gap: 16px; align-items: start;
  @media (max-width: 1100px) { grid-template-columns: 1fr; }
}

.detail-section { @include detail-section; }
.detail-section-head { @include detail-section-head; }
.detail-section-body { @include detail-section-body; }

.info-grid { @include info-grid(2); }
.info-grid.compact { gap: 8px 12px; }
.info-row { @include info-row; }
.info-row .v.amount { font-weight: 700; color: $color-text-primary; font-size: 15px; }
.info-row .v.success { color: $color-success; font-weight: 600; }

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
}

// pay-table
.pay-table, .ct-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: $color-bg; text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: $color-text-tertiary; border-bottom: 1px solid $color-border; }
  td { padding: 12px 14px; border-bottom: 1px solid $color-border; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: $color-bg; }
  tfoot td { background: $color-bg; border-bottom: none; font-weight: 600; }
  .cell-mono { font-family: $font-family-mono; color: $color-primary; font-weight: 500; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; text-align: right; }
  .cell-amount.success { color: $color-success; }
  .cell-num { text-align: center; font-family: $font-family-mono; }
  .total { color: $color-primary; font-size: 14px; }
}

// timeline-det
.timeline-det { position: relative; padding-left: 28px;
  &::before { content: ''; position: absolute; left: 11px; top: 14px; bottom: 14px; width: 1.5px; background: $color-border; }
}
.timeline-det-item {
  position: relative; padding-bottom: 16px;
  &::before { content: ''; position: absolute; left: -22px; top: 6px; width: 12px; height: 12px; border-radius: 50%; background: #fff; border: 2.5px solid $color-primary; }
  &.done::before { background: $color-primary; }
  &:last-child { padding-bottom: 0; }
  .t { font-size: 13px; font-weight: 500; color: $color-text-primary; }
  .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .d { font-size: 12px; color: $color-text-secondary; margin-top: 4px; line-height: 1.5; }
}

.risk-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;
  @media (max-width: 700px) { grid-template-columns: 1fr; }
}
.risk-row {
  display: flex; gap: 10px;
  padding: 12px 14px;
  background: rgba(16,185,129,0.05);
  border: 1px solid rgba(16,185,129,0.2);
  border-radius: $radius-md;
  .check-status {
    width: 24px; height: 24px; border-radius: 50%;
    display: grid; place-items: center;
    font-size: 12px; font-weight: 700;
    color: #fff;
    background: $color-success;
    flex-shrink: 0;
  }
  .c-name { font-size: 12.5px; font-weight: 600; color: $color-text-primary; }
  .c-desc { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
}

.meta-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  margin-bottom: 14px;
  h4 { font-size: 13.5px; font-weight: 600; margin: 0 0 12px 0; display: flex; align-items: center; gap: 6px; }
}
.check-row {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0;
  font-size: 12.5px;
  .dot { width: 8px; height: 8px; border-radius: 50%; background: $color-success; }
  .dot.fail { background: $color-danger; }
}

.quick-actions { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.qa-btn {
  padding: 10px 12px;
  background: $color-bg;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  font-size: 12.5px;
  color: $color-text-primary;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
  &:hover { background: $color-primary-bg; color: $color-primary; border-color: $color-primary; }
}

.link-primary { color: $color-primary; font-size: 12.5px; cursor: pointer; }
.link-primary:hover { text-decoration: underline; }

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
