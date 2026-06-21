<script setup lang="ts">
/**
 * ContractDetail · 合同详情（1:1 复刻 design/contract-detail.html）
 * - 顶部 contract-hero（编号 + 名称 + meta + 金额 + 状态）
 * - detail-tabs（基本信息/合同条款/审批流程/履约情况）
 * - 左主区：detail-section × 3（合同信息/关键条款/电子签章）
 * - 右主区：meta-card × 4（当前节点/审批历史/履约情况/附件文档）
 */
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractApi, type Contract } from '@/api/modules'

// 触点 #8：AI 合同体检 Drawer（复用 AiRiskScanPanel）
const aiDrawerVisible = ref(false)

// 5 维健康度 mock
const healthDims = ref([
  { label: '条款完整性', score: 92, status: 'success' as const },
  { label: '付款合理性', score: 68, status: 'warning' as const },
  { label: '风险控制',   score: 75, status: 'warning' as const },
  { label: '履约能力',   score: 88, status: 'success' as const },
  { label: '合规性',     score: 80, status: 'success' as const },
])
// 3 项风险预警 mock
const warnings = ref([
  { icon: '⚠️', level: 'medium', title: '付款条款偏严', desc: '30 天账期较短，建议与客户协商延长至 45 天' },
  { icon: '⏰', level: 'low',    title: '验收节点靠后', desc: '尾款 30% 验收后支付，建议分 2 次验收释放风险' },
  { icon: '🔒', level: 'low',    title: '保密条款可加强', desc: '建议补充保密期限（建议 3 年）和违约金条款' },
])
// 3 条 AI 建议 mock
const suggestions = ref([
  '在合同正文"付款方式"段落添加分段验收节点（建议 30%/40%/30% 三期）',
  '将"违约责任"段落违约金比例从 30% 调整至行业标准 20%',
  '补充"不可抗力"条款：列明自然灾害、政策变化等 6 类情形',
])

const router = useRouter()
const route = useRoute()

const activeTab = ref<'basic' | 'terms' | 'flow' | 'fulfill'>('basic')
const loading = ref(false)
const detail = ref<Contract | null>(null)

// 合同详情 mock（design 真实示例：HT-2026-031 万象科技 SaaS 2026Q2）
const mock = reactive({
  id: 31,
  code: 'HT-2026-031',
  name: '万象科技 SaaS 服务合同 2026Q2',
  client: '万象科技有限公司',
  type: '销售合同',
  status: '审批中',
  statusColor: 'warning',
  amount: '86,500.00',
  currency: 'CNY',
  period: '12 个月',
  signDate: '2026-06-11',
  startDate: '2026-06-15',
  endDate: '2027-06-14',
  contact: '李建国（CTO）',
  contactPhone: '138-****-5689',
  taxNo: '91310000MA1FL3X9G',
  payMethod: '分期付款',
  payTerm: '30 天',
  manager: '陈思琪（项目经理）',
  project: 'PRJ-2026-022',
  summary: '万象科技 2026 年 Q2 SaaS 平台服务合同，涵盖发票识别、模板管理、报表分析等核心模块。',
  createdAt: '2026-06-11 10:23',
  createdBy: '李明',
  // 履约
  fulfillProgress: 25,
  invoiced: '21,625',
  received: '21,625',
  pending: '64,875',
})

// 5 关键条款（design 真实示例）
const terms = ref([
  { t: '1. 服务内容', d: 'SaaS 平台标准版 30 个用户账号，含发票识别、模板管理、报表分析、API 对接等核心功能。' },
  { t: '2. 付款条款', d: '合同总金额 ¥ 86,500，分 4 期支付，每季度 ¥ 21,625。每期发票在付款前 5 个工作日开具。' },
  { t: '3. SLA 保障', d: '系统可用性 ≥ 99.9%，故障响应时间 ≤ 30 分钟，重大故障恢复时间 ≤ 4 小时。月度可用性低于 99% 时，按月费的 10% 抵扣下月费用。' },
  { t: '4. 保密条款', d: '双方对在合作中获取的对方商业秘密负有保密义务，保密期限为合同终止后 3 年。' },
  { t: '5. 违约责任', d: '任一方违约，应赔偿对方因此遭受的直接经济损失，违约金不超过合同总金额的 30%。' },
])

// 6 步骤审批流
const flowSteps = ref([
  { state: 'done',    label: '起草',       meta: '李明 · 06-11 10:23' },
  { state: 'done',    label: '法务审核',   meta: '王律师 · 06-11 14:30' },
  { state: 'current', label: '财务审核',   meta: '张明 · 审核中' },
  { state: 'todo',    label: '总经理审批', meta: '待提交' },
  { state: 'todo',    label: '电子签',     meta: '未开始' },
  { state: 'todo',    label: '归档',       meta: '未开始' },
])

// 4 期付款计划
const payPlans = ref([
  { period: '第 1 期', amount: '21,625.00', date: '2026-06-15', status: 'paid' },
  { period: '第 2 期', amount: '21,625.00', date: '2026-09-15', status: 'pending' },
  { period: '第 3 期', amount: '21,625.00', date: '2026-12-15', status: 'pending' },
  { period: '第 4 期', amount: '21,625.00', date: '2027-03-15', status: 'pending' },
])

// 审批历史
const history = ref([
  { t: '法务审核通过', m: '王律师 · 2026-06-11 14:30', d: '合同条款符合规范，无重大风险，已补充保密条款。', done: true },
  { t: '合同起草完成', m: '李明 · 2026-06-11 10:23', d: '使用「销售合同」模板自动生成。', done: true },
  { t: '客户报价确认', m: '刘洋 · 2026-06-10 16:48', d: '客户口头同意 ¥ 86,500 总价方案。', done: true },
])

// 附件
const attachments = ref([
  { icon: '📄', name: '合同主文件.pdf', size: '1.2 MB · 已生成' },
  { icon: '📄', name: 'SLA 补充协议.pdf', size: '320 KB' },
  { icon: '📄', name: '客户营业执照.pdf', size: '680 KB' },
])

function goBack() { router.push('/contract/list') }
function approve() { ElMessage.success('已审批通过') }
function reject() { ElMessage.warning('已驳回') }
function reassign() { ElMessage.info('转交他人') }
function download(att: any) { ElMessage.info(`下载: ${att.name}`) }
function goEdit() { ElMessage.info('编辑合同') }
function goAiPanel() { aiDrawerVisible.value = true }
function goSign() { ElMessage.info('发起电子签') }

onMounted(() => {
  loading.value = true
  contractApi.detail(Number(route.params.id) || mock.id)
    .then((res: any) => { if (res) detail.value = res })
    .catch(() => { /* 用 mock */ })
    .finally(() => { loading.value = false })
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部 contract-hero（design） -->
    <div class="contract-hero">
      <div class="ch-left">
        <div class="ch-id">
          <span class="code">{{ mock.code }}</span>
          <span :class="['tag', `tag-${mock.statusColor}`]">{{ mock.status }}</span>
        </div>
        <h1 class="ch-name">{{ mock.name }}</h1>
        <div class="ch-meta">
          <span>📋 {{ mock.type }}</span>
          <span class="sep">·</span>
          <span>👥 {{ mock.client }}</span>
          <span class="sep">·</span>
          <span>👤 {{ mock.manager }}</span>
          <span class="sep">·</span>
          <span>📅 {{ mock.signDate }} ~ {{ mock.endDate }}</span>
        </div>
      </div>
      <div class="ch-right">
        <div class="ch-amount-l">合同总金额</div>
        <div class="ch-amount">¥ {{ mock.amount }}</div>
        <div class="ch-amount-c">人民币 · 分 4 期</div>
        <div class="ch-actions">
          <button v-permission="'contract:write'" class="btn btn-ghost btn-sm" @click="goEdit">✎ 编辑</button>
          <button v-permission="'contract:read'" class="btn btn-outline btn-sm" @click="goAiPanel">🤖 AI 体检</button>
          <button v-permission="'contract:approve'" class="btn btn-primary btn-sm" @click="goSign">✍ 发起签署</button>
        </div>
      </div>
    </div>

    <!-- detail-tabs（design） -->
    <div class="detail-tabs">
      <a href="javascript:void(0)" :class="{ active: activeTab === 'basic' }"  @click="activeTab = 'basic'">📋 基本信息</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'terms' }"  @click="activeTab = 'terms'">📜 合同条款</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'flow' }"   @click="activeTab = 'flow'">🔄 审批流程</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'fulfill' }" @click="activeTab = 'fulfill'">📊 履约情况</a>
    </div>

    <!-- 主区（左 3 section + 右 4 meta-card） -->
    <div class="detail-layout">
      <!-- 左侧主区 -->
      <div>
        <!-- 基本信息 -->
        <div v-show="activeTab === 'basic'">
          <div class="detail-section">
            <div class="detail-section-head">
              <h4>📋 合同信息</h4>
              <span style="font-size: 11.5px; color: var(--color-text-tertiary);">由 {{ mock.createdBy }} 于 {{ mock.createdAt }} 创建</span>
            </div>
            <div class="detail-section-body">
              <div class="info-grid">
                <div class="info-row"><span class="l">合同编号</span><span class="v mono">{{ mock.code }}</span></div>
                <div class="info-row"><span class="l">合同类型</span><span class="v">{{ mock.type }}</span></div>
                <div class="info-row"><span class="l">客户名称</span><span class="v">{{ mock.client }}</span></div>
                <div class="info-row"><span class="l">客户联系人</span><span class="v">{{ mock.contact }}</span></div>
                <div class="info-row"><span class="l">联系电话</span><span class="v">{{ mock.contactPhone }}</span></div>
                <div class="info-row"><span class="l">纳税人识别号</span><span class="v mono">{{ mock.taxNo }}</span></div>
                <div class="info-row"><span class="l">合同金额</span><span class="v amount">¥ {{ mock.amount }}</span></div>
                <div class="info-row"><span class="l">币种</span><span class="v">{{ mock.currency }}</span></div>
                <div class="info-row"><span class="l">合同期限</span><span class="v">{{ mock.period }}</span></div>
                <div class="info-row"><span class="l">付款方式</span><span class="v">{{ mock.payMethod }} · {{ mock.payTerm }}</span></div>
                <div class="info-row"><span class="l">签订日期</span><span class="v">{{ mock.signDate }}</span></div>
                <div class="info-row"><span class="l">生效日期</span><span class="v">{{ mock.startDate }}</span></div>
                <div class="info-row"><span class="l">到期日期</span><span class="v">{{ mock.endDate }}</span></div>
                <div class="info-row"><span class="l">关联项目</span><span class="v mono">{{ mock.project }}</span></div>
                <div class="info-row full">
                  <span class="l">合同摘要</span>
                  <div class="notes-block">{{ mock.summary }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 合同条款 -->
        <div v-show="activeTab === 'terms'" class="detail-section">
          <div class="detail-section-head">
            <h4>📜 关键条款</h4>
          </div>
          <div class="detail-section-body">
            <div v-for="(t, i) in terms" :key="i" class="term-block">
              <div class="t">{{ t.t }}</div>
              <div class="d">{{ t.d }}</div>
            </div>
          </div>
        </div>

        <!-- 审批流程 -->
        <div v-show="activeTab === 'flow'" class="flow-card">
          <h3>当前审批流程 · {{ mock.code }}</h3>
          <div class="flow-sub">由 {{ mock.createdBy }} 于 {{ mock.createdAt }} 提交，预计今日 18:00 前完成全部审批</div>
          <div class="flow-row">
            <template v-for="(step, i) in flowSteps" :key="i">
              <div :class="['flow-step', step.state]">
                <div class="node">{{ step.state === 'done' ? '✓' : (i + 1) }}</div>
                <div class="lbl">{{ step.label }}</div>
                <div class="meta">{{ step.meta }}</div>
              </div>
              <div v-if="i < flowSteps.length - 1" :class="['flow-line', step.state === 'done' ? 'done' : '']"></div>
            </template>
          </div>
        </div>

        <!-- 履约情况 -->
        <div v-show="activeTab === 'fulfill'">
          <div class="detail-section">
            <div class="detail-section-head"><h4>💰 付款计划（4 期）</h4></div>
            <div class="detail-section-body">
              <table class="pay-table">
                <thead><tr><th>期次</th><th>金额</th><th>计划日期</th><th>状态</th></tr></thead>
                <tbody>
                  <tr v-for="(p, i) in payPlans" :key="i">
                    <td><strong>{{ p.period }}</strong></td>
                    <td class="cell-amount">¥ {{ p.amount }}</td>
                    <td>{{ p.date }}</td>
                    <td><span :class="['tag', p.status === 'paid' ? 'tag-success' : 'tag-info']">{{ p.status === 'paid' ? '已支付' : '待支付' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧 meta-card（design 4 个） -->
      <div>
        <!-- 当前节点 -->
        <div class="meta-card">
          <h4>📌 当前节点</h4>
          <div class="current-node">
            <div class="n-title">财务审核</div>
            <div class="n-meta">由 <strong>张明</strong> 处理</div>
            <div class="n-time">2026-06-12 09:23 到达 · 已等待 12 小时</div>
          </div>
          <div class="node-actions">
            <button v-permission="'contract:approve'" class="btn btn-primary btn-sm" @click="approve">✓ 审批通过</button>
            <button v-permission="'contract:approve'" class="btn btn-outline btn-sm danger" @click="reject">✕ 驳回</button>
            <button v-permission="'contract:approve'" class="btn btn-ghost btn-sm" @click="reassign">↻ 转交他人</button>
          </div>
        </div>

        <!-- 审批历史 -->
        <div class="meta-card">
          <h4>📜 审批历史</h4>
          <div class="timeline-det">
            <div v-for="(h, i) in history" :key="i" :class="['timeline-det-item', { done: h.done }]">
              <div class="t">{{ h.t }}</div>
              <div class="m">{{ h.m }}</div>
              <div class="d">{{ h.d }}</div>
            </div>
          </div>
        </div>

        <!-- 履约情况 -->
        <div class="meta-card">
          <h4>📊 履约情况</h4>
          <div class="info-grid compact">
            <div class="info-row"><span class="l">履约进度</span><span class="v">{{ mock.fulfillProgress }}%</span></div>
            <div class="info-row"><span class="l">已开票</span><span class="v">¥ {{ mock.invoiced }}</span></div>
            <div class="info-row"><span class="l">已回款</span><span class="v success">¥ {{ mock.received }}</span></div>
            <div class="info-row"><span class="l">待回款</span><span class="v">¥ {{ mock.pending }}</span></div>
          </div>
          <div class="fulfill-bar">
            <div class="fill" :style="{ width: mock.fulfillProgress + '%' }"></div>
          </div>
        </div>

        <!-- 附件 -->
        <div class="meta-card">
          <h4>📎 附件文档</h4>
          <div v-for="(a, i) in attachments" :key="i" class="rel-item">
            <div class="ico">{{ a.icon }}</div>
            <div class="body">
              <div class="t">{{ a.name }}</div>
              <div class="m">{{ a.size }}</div>
            </div>
            <a class="link-primary" @click="download(a)">下载</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 触点 #8：AI 合同体检 Drawer（内嵌摘要 + 跳 AI 中心） -->
    <el-drawer v-model="aiDrawerVisible" title="🤖 AI 合同体检" direction="rtl" size="520px">
      <div class="ai-checkup-drawer">
        <div class="ai-checkup-hero">
          <div class="ai-checkup-score">
            <div class="ai-score-num">78</div>
            <div class="ai-score-label">健康度</div>
          </div>
          <div class="ai-checkup-meta">
            <h3>本合同整体健康</h3>
            <p>检测时间：{{ new Date().toLocaleString('zh-CN') }}</p>
            <p>检测模型：ernie-3.5 · 风险扫描</p>
          </div>
        </div>

        <h4 class="ai-section-title">📊 5 维健康度</h4>
        <div class="ai-health-grid">
          <div v-for="d in healthDims" :key="d.label" class="ai-health-row">
            <span class="ai-health-label">{{ d.label }}</span>
            <el-progress :percentage="d.score" :stroke-width="6" :status="d.status" />
            <span class="ai-health-score">{{ d.score }}</span>
          </div>
        </div>

        <h4 class="ai-section-title">⚠️ 3 项风险预警</h4>
        <div class="ai-warning-list">
          <div v-for="w in warnings" :key="w.title" class="ai-warning-item">
            <span class="ai-warn-icon" :class="`ai-warn-${w.level}`">{{ w.icon }}</span>
            <div class="ai-warn-body">
              <h5>{{ w.title }}</h5>
              <p>{{ w.desc }}</p>
            </div>
          </div>
        </div>

        <h4 class="ai-section-title">💡 3 条 AI 建议</h4>
        <div class="ai-suggest-list">
          <div v-for="(s, i) in suggestions" :key="i" class="ai-suggest-item">
            <span class="ai-suggest-num">{{ i + 1 }}</span>
            <p>{{ s }}</p>
          </div>
        </div>

        <div class="ai-checkup-actions">
          <el-button type="primary" @click="router.push('/ai/panel/contract')">查看完整 AI 报告 →</el-button>
          <el-button @click="aiDrawerVisible = false">关闭</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

/* 触点 #8：AI 合同体检 Drawer */
.ai-checkup-drawer { padding: 0 4px; }
.ai-checkup-hero {
  display: flex; gap: 16px; align-items: center; padding: 16px;
  background: linear-gradient(135deg, rgba(79,107,255,0.05) 0%, rgba(124,58,237,0.05) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-md; margin-bottom: 16px;
}
.ai-checkup-score {
  width: 80px; height: 80px; border-radius: 50%;
  background: $gradient-brand; color: #fff; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(79,107,255,0.3);
  .ai-score-num { font-size: 28px; font-weight: 700; line-height: 1; }
  .ai-score-label { font-size: 10px; opacity: 0.9; margin-top: 2px; }
}
.ai-checkup-meta h3 { font-size: 16px; font-weight: 600; color: $color-text-primary; margin-bottom: 6px; }
.ai-checkup-meta p { font-size: 11px; color: $color-text-secondary; margin-bottom: 2px; }

.ai-section-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin: 16px 0 10px; }
.ai-health-grid { display: flex; flex-direction: column; gap: 8px; }
.ai-health-row { display: grid; grid-template-columns: 90px 1fr 36px; gap: 8px; align-items: center; }
.ai-health-label { font-size: 12px; color: $color-text-secondary; }
.ai-health-score { font-size: 12px; font-weight: 600; color: $color-text-primary; text-align: right; font-family: $font-family-mono; }

.ai-warning-list, .ai-suggest-list { display: flex; flex-direction: column; gap: 8px; }
.ai-warning-item {
  display: flex; gap: 10px; padding: 10px 12px;
  background: #fff; border: 1px solid $color-border; border-radius: $radius-sm;
}
.ai-warn-icon { font-size: 18px; line-height: 1; flex-shrink: 0; }
.ai-warn-body h5 { font-size: 12px; font-weight: 600; color: $color-text-primary; margin-bottom: 2px; }
.ai-warn-body p { font-size: 11px; color: $color-text-secondary; line-height: 1.5; }
.ai-suggest-item {
  display: flex; gap: 8px; padding: 8px 12px;
  background: linear-gradient(90deg, rgba(124,58,237,0.05), transparent);
  border-left: 3px solid #7C3AED;
  border-radius: 0 $radius-sm $radius-sm 0;
  p { font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
}
.ai-suggest-num {
  flex-shrink: 0; width: 18px; height: 18px;
  background: $gradient-brand; color: #fff; font-size: 10px; font-weight: 700;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.ai-checkup-actions { display: flex; gap: 8px; margin-top: 20px; }

// contract-hero（design）
.contract-hero {
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
    background: radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%);
    pointer-events: none;
  }
  .ch-left { position: relative; z-index: 1; flex: 1; min-width: 0; }
  .ch-id {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 8px;
    .code {
      font-family: $font-family-mono;
      font-size: 12.5px;
      color: rgba(255,255,255,0.85);
      letter-spacing: 0.5px;
    }
    .tag {
      background: rgba(255,255,255,0.18);
      color: #fff;
      padding: 2px 10px;
      border-radius: 9999px;
      font-size: 11.5px;
      font-weight: 500;
    }
  }
  .ch-name {
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 10px 0;
    color: #fff;
  }
  .ch-meta {
    font-size: 12.5px;
    color: rgba(255,255,255,0.8);
    .sep { margin: 0 8px; opacity: 0.5; }
  }
  .ch-right { text-align: right; position: relative; z-index: 1; flex-shrink: 0; }
  .ch-amount-l { font-size: 12px; color: rgba(255,255,255,0.75); margin-bottom: 4px; }
  .ch-amount {
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    font-family: $font-family-mono;
    letter-spacing: -0.5px;
  }
  .ch-amount-c { font-size: 11.5px; color: rgba(255,255,255,0.6); margin-bottom: 16px; }
  .ch-actions { display: flex; gap: 8px; justify-content: flex-end; }
  .btn {
    background: rgba(255,255,255,0.18);
    color: #fff;
    border-color: rgba(255,255,255,0.3);
    &:hover { background: rgba(255,255,255,0.28); }
    &.btn-primary { background: #fff; color: $color-primary; border-color: #fff; &:hover { background: rgba(255,255,255,0.92); } }
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
    padding: 8px 16px;
    border-radius: $radius-sm;
    font-size: 13px;
    color: $color-text-secondary;
    text-decoration: none;
    cursor: pointer;
    font-weight: 500;
    &:hover { background: $color-bg; color: $color-primary; }
    &.active { background: $color-primary; color: #fff; font-weight: 600; }
  }
}

// detail-layout（左 + 右）
.detail-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
  @media (max-width: 1100px) { grid-template-columns: 1fr; }
}

// detail-section
.detail-section {
  @include detail-section;
}
.detail-section-head { @include detail-section-head; }
.detail-section-body { @include detail-section-body; }

.info-grid { @include info-grid(2); }
.info-grid.compact { gap: 8px 12px; }
.info-row { @include info-row; }
.info-row .v.amount { font-weight: 700; color: $color-text-primary; }
.info-row .v.success { color: $color-success; font-weight: 600; }

// term-block（合同条款）
.term-block {
  padding: 12px 14px;
  background: #FAFBFF;
  border-left: 3px solid $color-primary;
  border-radius: 0 $radius-md $radius-md 0;
  margin-bottom: 10px;
  .t { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  .d { font-size: 12.5px; color: $color-text-secondary; line-height: 1.6; }
}

// flow-card（审批流）
.flow-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 24px 28px;
  h3 { font-size: 15px; font-weight: 600; margin: 0 0 6px 0; }
  .flow-sub { font-size: 12.5px; color: $color-text-tertiary; margin-bottom: 24px; }
  .flow-row { display: flex; align-items: flex-start; gap: 0; }
  .flow-step {
    display: flex; flex-direction: column; align-items: center;
    position: relative; flex: 1; min-width: 80px;
    .node {
      width: 40px; height: 40px; border-radius: 50%;
      background: $color-bg; color: $color-text-tertiary;
      display: grid; place-items: center;
      font-size: 14px; font-weight: 600;
      border: 2px solid $color-border-strong;
      z-index: 1;
    }
    &.done .node { background: linear-gradient(135deg, #10B981, #059669); color: #fff; border-color: transparent; }
    &.current .node {
      background: $gradient-brand; color: #fff; border-color: transparent;
      box-shadow: 0 0 0 4px rgba(79,107,255,0.2);
    }
    .lbl { margin-top: 8px; font-size: 12.5px; color: $color-text-tertiary; font-weight: 500; text-align: center; }
    &.done .lbl, &.current .lbl { color: $color-text-primary; }
    .meta { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; text-align: center; }
  }
  .flow-line {
    flex: 1; height: 2px;
    background: $color-border-strong;
    margin: 0 -8px; align-self: center;
    position: relative; top: -10px;
    &.done { background: linear-gradient(90deg, #10B981, #059669); }
  }
}

// meta-card（右侧 4 卡片）
.meta-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  margin-bottom: 14px;
  h4 { font-size: 13.5px; font-weight: 600; margin: 0 0 12px 0; display: flex; align-items: center; gap: 6px; }
}
.current-node {
  background: $color-primary-bg;
  border-radius: $radius-md;
  padding: 14px;
  margin-bottom: 12px;
  .n-title { font-size: 13.5px; font-weight: 600; color: $color-primary; }
  .n-meta { font-size: 11.5px; color: $color-text-secondary; margin-top: 4px; }
  .n-time { font-size: 11.5px; color: $color-text-tertiary; margin-top: 4px; }
}
.node-actions { display: flex; flex-direction: column; gap: 8px; }

// timeline-det
.timeline-det {
  position: relative;
  padding-left: 28px;
  &::before {
    content: '';
    position: absolute;
    left: 11px; top: 14px; bottom: 14px;
    width: 1.5px;
    background: $color-border;
  }
}
.timeline-det-item {
  position: relative;
  padding-bottom: 16px;
  &::before {
    content: '';
    position: absolute;
    left: -22px; top: 6px;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2.5px solid $color-primary;
  }
  &.done::before { background: $color-primary; }
  &:last-child { padding-bottom: 0; }
  .t { font-size: 13px; font-weight: 500; color: $color-text-primary; }
  .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .d { font-size: 12px; color: $color-text-secondary; margin-top: 4px; line-height: 1.5; }
}

// fulfill-bar
.fulfill-bar {
  margin-top: 12px;
  height: 6px;
  background: $color-bg;
  border-radius: 9999px;
  overflow: hidden;
  .fill {
    height: 100%;
    background: linear-gradient(90deg, #10B981, #059669);
    border-radius: 9999px;
  }
}

// rel-item（附件）
.rel-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid $color-border;
  &:last-child { border-bottom: none; }
  .ico { font-size: 24px; }
  .body { flex: 1; min-width: 0; }
  .t { font-size: 12.5px; color: $color-text-primary; font-weight: 500; }
  .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
}

// pay-table
.pay-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: $color-bg; text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: $color-text-tertiary; border-bottom: 1px solid $color-border; }
  td { padding: 12px 14px; border-bottom: 1px solid $color-border; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; color: $color-text-primary; }
}

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

.link-primary { color: $color-primary; font-size: 12px; cursor: pointer; }
.link-primary:hover { text-decoration: underline; }

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } &.danger { color: $color-danger; border-color: rgba(239,68,68,0.3); &:hover { border-color: $color-danger; background: rgba(239,68,68,0.06); } } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 12px; font-size: 12px; }
}
</style>
