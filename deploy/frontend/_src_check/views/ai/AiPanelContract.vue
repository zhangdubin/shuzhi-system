<script setup lang="ts">
/**
 * AI 合同体检面板（独立路由页面）
 *
 * 设计稿：design/ai-panel-contract.html
 * 路由：/ai/panel/contract
 *
 * 用于：从合同列表/详情右上角"🤖 AI 体检"按钮进入
 */
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'
import AiDrawer from '@/components/AiDrawer.vue'

const router = useRouter()

const contract = ref({
  code: 'HT-2026-031',
  name: '万象科技 SaaS 服务合同 2026Q2',
  customerName: '万象科技有限公司',
  amount: 86500,
  period: '2026-06-11 ~ 2027-06-10',
  status: '审批中',
})

// 综合评分
const score = ref(72)
const riskLevel = ref<'medium' | 'high' | 'low'>('medium')
const riskText = ref('中风险 · 建议补充 2 项条款')

// 5 维评分（含行业基准 marker）
const dims = ref([
  { icon: '📋', name: '条款完整', score: 78, warn: false },
  { icon: '💰', name: '付款条件', score: 55, warn: true },
  { icon: '⚖️', name: '法务合规', score: 62, warn: true },
  { icon: '💵', name: '金额风险', score: 88, warn: false },
  { icon: '🤝', name: '客户资质', score: 92, warn: false },
])

// 风险预警
const warnings = ref([
  {
    level: 'high',
    title: '付款周期短于行业平均 33%',
    desc: '约定"月结 30 天"，行业 SaaS 合同平均为 45 天。客户付款压力大 → 我方回款风险增加。',
    evidence: '📍 依据：第 3.2 条 付款方式  |  行业基准：45 天',
    actions: ['📝 一键生成协商邮件', '查看条款'],
  },
  {
    level: 'high',
    title: '未约定违约金条款',
    desc: '逾期付款无任何约束。一旦客户拖欠 3 个月以上，维权成本（诉讼+利息）可能超过合同金额本身。',
    evidence: '📍 依据：第 3.2 条 付款方式（无违约条款）',
    actions: ['📝 补充违约金条款', '查看法务模板'],
  },
  {
    level: 'medium',
    title: '数据归属与保密期未约定',
    desc: '涉及客户业务数据归属、保密期限不明确。服务终止后，可能产生数据迁移纠纷。',
    evidence: '📍 依据：第 5 章 知识产权（未提及数据归属）',
    actions: ['📝 补充数据条款'],
  },
])

// AI 建议
const suggestions = ref([
  {
    n: 1,
    cls: '',
    title: '与客户协商付款周期延至 45 天',
    desc: '基于 12 个相似 SaaS 合同，付款周期从 30 → 45 天，<strong>回款及时率提升 22%</strong>，且不影响签约率（下降仅 3%）。',
    actions: ['📝 AI 起草协商邮件', '查看相似合同'],
  },
  {
    n: 2,
    cls: 'warning',
    title: '补充"逾期 0.05%/天"违约金条款',
    desc: '参考法务部标准条款库 v3.2。AI 已生成 v2 合同草稿，新增第 3.3 条。',
    actions: ['✓ 查看 v2 草稿', '发法务复核'],
  },
  {
    n: 3,
    cls: '',
    title: '补充"数据归属 + 3 年保密期"条款',
    desc: '客户业务数据归客户所有，我方留存 90 天用于服务支持，保密期 3 年。参考模板：法务库 v3.2 通用 SaaS 模板。',
    actions: ['📝 应用条款'],
  },
])

// 关键条款体检
const clauses = ref([
  { name: '服务范围', text: 'SaaS 平台标准版 · 50 个席位 · 12 个月', status: 'success', label: '✓ 完整' },
  { name: '付款方式', text: '合同签订后 7 日内支付 50%，验收后 30 日内支付 50%', status: 'warning', label: '⚠ 周期偏短' },
  { name: '违约金', text: '—（未约定）', status: 'danger', label: '✗ 缺失' },
  { name: '知识产权', text: '平台代码归我方所有；客户数据 <strong>未明确归属</strong>', status: 'warning', label: '⚠ 需补充' },
  { name: '保密条款', text: '双方对商业秘密承担保密义务', status: 'warning', label: '⚠ 无期限' },
  { name: '争议解决', text: '提交北京仲裁委员会仲裁', status: 'success', label: '✓ 完整' },
])

// 相似合同
const similars = ref([
  { name: 'HT-2026-031（当前）', amount: '¥86,500', term: '30 天', penalty: '—', score: 72, current: true, cls: 'warn' },
  { name: 'HT-2025-118（万象科技）', amount: '¥92,000', term: '45 天', penalty: '0.05%/天', score: 88, current: false, cls: 'good' },
  { name: 'HT-2025-203（智云科技）', amount: '¥78,000', term: '60 天', penalty: '0.1%/天', score: 91, current: false, cls: 'good' },
  { name: 'HT-2026-089（远见数据）', amount: '¥95,000', term: '30 天', penalty: '—', score: 68, current: false, cls: 'bad' },
])

// AI 异常事件时间线
const timeline = ref([
  { time: '2 小时前', text: '⚠️ 销售 <strong>王芳</strong> 提交合同时，付款周期从 45 → 30 天（<span style="color:var(--color-danger);">-15 天</span>）' },
  { time: '3 小时前', text: '📉 与去年同期合同 HT-2025-118 对比，<strong>违约金条款被删除</strong>' },
  { time: '昨天', text: '🤖 AI 完成首次扫描，识别出 3 个中高风险' },
  { time: '2 天前', text: '📝 商务 <strong>王芳</strong> 创建合同（来自销售线索 L-2026-128）' },
  { time: '1 周前', text: '✅ 客户<strong>万象科技</strong>信用评级：A（基于 3 年合作历史）' },
])

// Tab 状态
const tabs = ['基本信息', '合同条款', '审批流', '附件', '履约记录', '发票/回款']
const activeTab = ref('ai')

// Drawer
const drawerOpen = ref(false)
function openDrawer() {
  drawerOpen.value = true
}

function gotoBack() { router.push('/contract/list') }
function handleAcceptAll() { ElMessage.success('已采纳全部建议（演示）') }
function handleAction(action: string) { ElMessage.success(`已执行：${action}`) }
function handleUndo() { ElMessage.info('已撤销采纳') }
function handleFeedback(v: 'up' | 'down') {
  ElMessage.success(v === 'up' ? '已记录：本次分析有帮助' : '已记录：本次分析无帮助')
}

async function load() {
  await Promise.all([
    aiApi.tasks({ pageSize: 5 }).catch(() => null),
    aiApi.alerts({ limit: 5 }).catch(() => null),
  ])
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/contract/list" style="color: var(--color-text-tertiary)">合同管理</router-link> /
          <span style="color: var(--color-text-tertiary)">{{ contract.code }}</span> /
          <span style="color: var(--color-ai); font-weight: 600">AI 体检</span>
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          合同详情
          <span class="tag tag-warning">{{ contract.status }}</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button>⇩ 下载 PDF</el-button>
        <el-button>📤 分享</el-button>
        <el-button style="color: var(--color-danger); border-color: rgba(239,68,68,0.3)">✕ 驳回</el-button>
        <el-button type="primary" @click="openDrawer">🤖 AI 智能分析</el-button>
        <el-button type="success">✓ 审批通过</el-button>
      </div>
    </div>

    <!-- design/ai-panel-contract.html 实际无合同 hero banner。
         顶部直接是 ai-alert-bar。删掉占位以避免无样式 hero 块显示白底白字 bug。 -->

    <!-- Tabs -->
    <div class="detail-tabs">
      <a v-for="t in tabs" :key="t" :class="{ active: activeTab === t }" @click="activeTab = t">{{ t }}</a>
      <a class="active" @click="activeTab = 'ai'">
        ✨ AI 体检
        <span class="ai-badge" style="font-size: 9.5px; padding: 1px 5px; margin-left: 4px">3 风险</span>
      </a>
    </div>

    <!-- AI 体检主区 -->
    <div class="ai-fade-up">
      <!-- 1. 综合评分 + 智能摘要 -->
      <div class="ai-overview">
        <div class="ai-score-big">
          <div class="num">{{ score }}</div>
          <div class="label">综合健康分</div>
          <div :class="['risk-tag', riskLevel]">
            <span class="dot" /> {{ riskText }}
          </div>
        </div>
        <div class="ai-summary-area">
          <div class="h">
            <span class="ai-badge">AI 摘要</span>
            <span>本合同的 3 个关键风险</span>
          </div>
          <div class="text">
            合同整体条款基本完整，但存在 <strong>3 个中等风险</strong>：(1) 付款周期 30 天，短于行业平均的 45 天；
            (2) 缺少违约金条款，逾期风险敞口大；<strong>(3) 未约定数据归属与保密期</strong>，法务复核建议补充。
            整体可签，但建议<strong>先与客户协商</strong>以下 2 项条款（详见下方"AI 建议"）。
          </div>
        </div>
      </div>

      <!-- 2. 5 维评分 -->
      <div class="detail-section" style="margin-bottom: 16px">
        <div class="detail-section-head">
          <h4>5 维健康度</h4>
          <span class="text-tertiary" style="font-size: 11px">AI 评分 · 0-100 · 行业基准 75</span>
        </div>
        <div style="padding: 6px 22px 14px">
          <div v-for="d in dims" :key="d.name" :class="['ai-dim-bar', d.warn ? 'warn' : '']">
            <span class="name">{{ d.icon }} {{ d.name }}</span>
            <div class="bar">
              <div class="fill" :style="{ width: d.score + '%' }" />
              <div class="marker" style="left: 75%" data-val="行业" />
            </div>
            <span class="score">{{ d.score }}</span>
          </div>
        </div>
      </div>

      <!-- 3. 风险预警 + AI 建议（双栏） -->
      <div class="ai-grid-2" style="margin-bottom: 16px">
        <!-- 左：风险预警 -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>⚠️ 风险预警 <span class="ai-badge" style="background: var(--color-danger); font-size: 10px; padding: 2px 8px">{{ warnings.length }}</span></h4>
            <span class="text-tertiary" style="font-size: 11px">按严重程度排序</span>
          </div>
          <div style="padding: 8px 22px 16px">
            <div v-for="(w, i) in warnings" :key="i" :class="['ai-warn', w.level]">
              <div :class="['ico', w.level]">{{ w.level === 'high' ? '!' : '⚠' }}</div>
              <div class="body">
                <div class="head">
                  <div class="title">{{ w.title }}</div>
                  <span :class="['ai-risk-chip', w.level]"><span class="dot" />{{ ({ high: '高', medium: '中', low: '低' })[w.level] }}</span>
                </div>
                <div class="desc">{{ w.desc }}</div>
                <div class="evidence">📍 依据：{{ w.evidence }}</div>
                <div class="actions">
                  <el-button v-for="a in w.actions" :key="a" size="small" :type="a.includes('📝') || a.includes('✓') ? 'primary' : 'default'" @click="handleAction(a)">
                    {{ a }}
                  </el-button>
                  <el-button size="small" style="margin-left: auto; color: var(--color-text-tertiary)" @click="ElMessage.info('已忽略')">忽略</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右：采纳回执 + AI 建议 -->
        <div>
          <!-- 采纳回执 -->
          <div class="ai-accept-bar">
            <div class="ico">✓</div>
            <div>
              <strong>已采纳：</strong>补充违约金条款 · AI 已生成 v2 草稿并发送至商务 <strong>王芳</strong> 复核
              <span class="undo" @click="handleUndo">撤销</span>
            </div>
          </div>

          <div class="ai-card elevated">
            <div class="ai-card-head">
              <h4>💡 AI 给你的 3 条建议</h4>
              <span class="ai-confidence high">置信度 91%</span>
            </div>
            <div class="ai-card-body">
              <div v-for="s in suggestions" :key="s.n" :class="['ai-suggestion', s.cls]">
                <div class="ai-s-icon">{{ s.n }}</div>
                <div class="ai-s-body">
                  <div class="ai-s-title">{{ s.title }}</div>
                  <div class="ai-s-desc" v-html="s.desc" />
                  <div class="ai-s-actions">
                    <el-button v-for="a in s.actions" :key="a" size="small" :type="a.includes('📝') || a.includes('✓') ? 'primary' : 'default'" @click="handleAction(a)">
                      {{ a }}
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. 条款体检 -->
      <div class="detail-section" style="margin-bottom: 16px">
        <div class="detail-section-head">
          <h4>📋 关键条款体检</h4>
          <span class="text-tertiary" style="font-size: 11px">与行业标准对比 · 6 项</span>
        </div>
        <div style="padding: 0 22px 16px">
          <div v-for="c in clauses" :key="c.name" class="clause-row">
            <div class="ck-name">{{ c.name }}</div>
            <div class="ck-text" v-html="c.text" />
            <div class="ck-status">
              <span :class="['tag', `tag-${c.status}`]">{{ c.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. 相似合同 + AI 异常时间线（双栏） -->
      <div class="ai-grid-2" style="margin-bottom: 16px">
        <!-- 左：相似合同 -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>📊 相似合同参考</h4>
            <span class="text-tertiary" style="font-size: 11px">基于金额 + 客户行业匹配 3 个</span>
          </div>
          <table class="ai-similar">
            <thead>
              <tr>
                <th>合同</th>
                <th>金额</th>
                <th>付款周期</th>
                <th>违约金</th>
                <th>健康分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(s, i) in similars" :key="i" :class="s.current ? 'current' : ''">
                <td>{{ s.name }}</td>
                <td class="v">{{ s.amount }}</td>
                <td class="v" :style="{ color: `var(--color-${s.cls === 'good' ? 'success' : s.cls === 'bad' ? 'danger' : 'warning'})` }">{{ s.term }}</td>
                <td class="v" :style="{ color: `var(--color-${s.cls === 'good' ? 'success' : s.cls === 'bad' ? 'danger' : 'warning'})` }">{{ s.penalty }}</td>
                <td class="v" :style="{ color: `var(--color-${s.cls === 'good' ? 'success' : s.cls === 'bad' ? 'danger' : 'warning'})`, fontWeight: 600 }">{{ s.score }}</td>
              </tr>
            </tbody>
          </table>
          <div style="padding: 10px 22px; font-size: 11.5px; color: var(--color-text-tertiary)">
            💡 <strong>洞察：</strong>与万象科技去年的合作合同（HT-2025-118）相比，付款周期缩短了 15 天，且去掉了违约金条款。AI 推测是销售为冲业绩的让步。
          </div>
        </div>

        <!-- 右：AI 异常事件时间线 -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>📅 AI 异常事件时间线</h4>
            <span class="text-tertiary" style="font-size: 11px">最近 30 天</span>
          </div>
          <div style="padding: 8px 22px 16px">
            <div class="ai-timeline">
              <div v-for="(t, i) in timeline" :key="i" class="at-item">
                <div class="at-time">{{ t.time }}</div>
                <div class="at-text" v-html="t.text" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 6. 反馈条 -->
      <div class="ai-feedback-bar">
        <span>这次 AI 体检对你有帮助吗？</span>
        <div style="display: flex; align-items: center; gap: 10px">
          <div class="ai-feedback">
            <button class="up" title="有用" @click="handleFeedback('up')">👍</button>
            <button title="没用" @click="handleFeedback('down')">👎</button>
          </div>
          <a href="javascript:;" style="color: var(--color-ai); font-size: 12px" @click="ElMessage.info('下载完整报告（演示）')">下载完整报告 →</a>
        </div>
      </div>
    </div>

    <!-- 通用 AI 抽屉 -->
    <AiDrawer v-model="drawerOpen" domain="contract" :trigger="contract" />
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

.ai-fade-up { margin-top: 20px; }

/* AI 综合评分卡（design 同款） */
.ai-overview {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 24px;
  background: linear-gradient(135deg, #F5F3FF 0%, #fff 100%);
  border: 1px solid var(--color-ai-border);
  border-radius: $radius-lg;
  padding: 24px;
  margin-bottom: 20px;
  align-items: center;
  position: relative;
  overflow: hidden;
  &::before {
    content: '✦';
    position: absolute;
    right: -10px; bottom: -30px;
    font-size: 140px;
    color: rgba(124,58,237,0.06);
    font-weight: 700;
    pointer-events: none;
  }
  @media (max-width: 720px) { grid-template-columns: 1fr; }
}
.ai-score-big {
  text-align: center;
  padding: 0 24px;
  border-right: 1px solid var(--color-ai-border);
  .num {
    font-size: 56px;
    font-weight: 700;
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: $font-family-mono;
    line-height: 1;
  }
  .label {
    font-size: 12px;
    color: $color-text-tertiary;
    margin-top: 4px;
  }
  .risk-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-top: 10px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    .dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: currentColor;
    }
    &.high { background: $color-danger-bg; color: $color-danger; }
    &.medium { background: $color-warning-bg; color: $color-warning; }
    &.low { background: $color-success-bg; color: $color-success; }
  }
}
.ai-summary-area {
  flex: 1;
  .h {
    font-size: 14px;
    font-weight: 600;
    color: $color-text-primary;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .text {
    font-size: 13px;
    color: $color-text-secondary;
    line-height: 1.75;
    :deep(strong) { color: var(--color-ai); }
  }
}

/* 5 维评分（design 同款） */
.ai-dim-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  font-size: 12.5px;
  .name {
    width: 80px;
    color: $color-text-secondary;
    display: flex; align-items: center; gap: 4px;
  }
  .bar {
    flex: 1;
    height: 8px;
    background: #F1F5F9;
    border-radius: 999px;
    overflow: hidden;
    position: relative;
    .fill {
      height: 100%;
      background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
      border-radius: 999px;
      transition: width 0.6s ease;
    }
    .marker {
      position: absolute;
      top: -3px; bottom: -3px;
      width: 2px;
      background: $color-text-tertiary;
      &::after {
        content: attr(data-val);
        position: absolute;
        top: -16px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 9px;
        color: $color-text-tertiary;
        font-family: $font-family-mono;
      }
    }
  }
  .score {
    width: 38px;
    text-align: right;
    font-family: $font-family-mono;
    font-weight: 600;
    color: $color-text-primary;
  }
  &.warn .fill { background: $color-warning; }
  &.danger .fill { background: $color-danger; }
}

/* 双栏布局 */
.ai-grid-2 {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 16px;
  @media (max-width: 980px) { grid-template-columns: 1fr; }
}

/* 风险预警卡片（design 同款，含 evidence + actions） */
.ai-warn {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: $color-warning-bg;
  border-left: 3px solid $color-warning;
  border-radius: $radius-md;
  margin-bottom: 10px;
  transition: all 0.2s;
  &:hover { transform: translateX(2px); box-shadow: $shadow-sm; }
  &.high { background: $color-danger-bg; border-left-color: $color-danger; }
  &.low { background: $color-success-bg; border-left-color: $color-success; }
  .ico {
    width: 32px; height: 32px;
    background: $color-warning;
    color: #fff;
    border-radius: $radius-sm;
    display: grid; place-items: center;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
    &.high { background: $color-danger; }
    &.low { background: $color-success; }
  }
  .body { flex: 1; min-width: 0; }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }
  .title {
    font-size: 13.5px;
    font-weight: 600;
    color: $color-text-primary;
  }
  .desc {
    font-size: 12.5px;
    color: $color-text-secondary;
    line-height: 1.6;
    margin-bottom: 8px;
  }
  .evidence {
    font-size: 11.5px;
    color: $color-text-tertiary;
    background: rgba(255,255,255,0.6);
    padding: 6px 10px;
    border-radius: $radius-sm;
    margin-bottom: 8px;
    font-family: $font-family-mono;
  }
  .actions {
    display: flex;
    gap: 8px;
  }
}

/* 采纳回执（design 同款） */
.ai-accept-bar {
  background: $color-success-bg;
  border: 1px solid $color-success;
  border-radius: $radius-md;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #047857;
  .ico {
    width: 24px; height: 24px;
    background: $color-success;
    color: #fff;
    border-radius: 50%;
    display: grid; place-items: center;
    font-size: 13px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .undo {
    margin-left: auto;
    color: $color-success;
    text-decoration: underline;
    cursor: pointer;
    font-size: 12px;
  }
}

/* 条款体检行（design 同款） */
.clause-row {
  display: grid;
  grid-template-columns: 100px 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border-radius: $radius-sm;
  margin-bottom: 6px;
  background: #F8FAFC;
  transition: all 0.2s;
  &:hover { background: #F1F5F9; }
  .ck-name {
    font-size: 12.5px;
    font-weight: 500;
    color: $color-text-primary;
  }
  .ck-text {
    font-size: 12px;
    color: $color-text-secondary;
    line-height: 1.5;
    :deep(strong) { color: $color-warning; font-weight: 500; }
  }
  .ck-status { flex-shrink: 0; }
}

/* 相似合同表（design 同款） */
.ai-similar {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  th, td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid $color-border;
  }
  th {
    background: #F8FAFC;
    font-size: 11.5px;
    color: $color-text-tertiary;
    font-weight: 600;
  }
  td.v { font-family: $font-family-mono; }
  tr.current {
    background: linear-gradient(135deg, rgba(79,107,255,0.08) 0%, rgba(124,58,237,0.08) 100%);
    td { font-weight: 600; color: var(--color-ai); }
    td:first-child::before { content: '📌 '; }
  }
}

/* 反馈条 */
.ai-feedback-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #F8FAFC;
  border-radius: $radius-md;
  margin-top: 16px;
  font-size: 12.5px;
  color: $color-text-secondary;
}
</style>