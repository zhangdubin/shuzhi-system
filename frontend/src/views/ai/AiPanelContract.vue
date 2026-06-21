<script setup lang="ts">
/**
 * AiPanelContract · AI 合同体检（1:1 复刻 design/ai-panel-contract.html 791 行）
 * - 顶部 contract-hero 蓝紫渐变（HT-2026-031 编号 + 合同名 + 客户 + 金额）
 * - 7 detail-tabs（基本信息/条款/审批/附件/履约/发票回款/AI 体检）最后 active
 * - 6 大区块：
 *   1. ai-overview 综合评分 72 + AI 摘要（3 风险）
 *   2. 5 维健康度（条款/付款/法务/金额/客户，2 行 warn 行业基准 75）
 *   3. ai-grid-2 双栏：3 风险预警 + AI 3 建议（采纳回执 + 置信度 91%）
 *   4. 关键条款体检 6 行（服务/付款/违约金/知识产权/保密/争议）
 *   5. ai-grid-2 双栏：相似合同对比表（4 行）+ AI 异常 timeline（5 节点）
 *   6. 反馈条（👍/👎 + 下载报告）
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 5 维健康度
const dims = ref([
  { name: '📋 条款完整', score: 78, warn: false },
  { name: '💰 付款条件', score: 55, warn: true },
  { name: '⚖️ 法务合规', score: 62, warn: true },
  { name: '💵 金额风险', score: 88, warn: false },
  { name: '🤝 客户资质', score: 92, warn: false },
])

// 3 风险预警
const risks = ref([
  {
    level: 'high', icon: '!', title: '付款周期短于行业平均 33%',
    desc: '约定"月结 30 天"，行业 SaaS 合同平均为 45 天。客户付款压力大 → 我方回款风险增加。',
    evidence: '📍 依据：第 3.2 条 付款方式  |  行业基准：45 天',
    actions: ['📝 一键生成协商邮件', '查看条款', '忽略'],
  },
  {
    level: 'high', icon: '!', title: '未约定违约金条款',
    desc: '逾期付款无任何约束。一旦客户拖欠 3 个月以上，维权成本（诉讼+利息）可能超过合同金额本身。',
    evidence: '📍 依据：第 3.2 条 付款方式（无违约条款）',
    actions: ['📝 补充违约金条款', '查看法务模板', '忽略'],
  },
  {
    level: 'medium', icon: '⚠', title: '数据归属与保密期未约定',
    desc: '涉及客户业务数据归属、保密期限不明确。服务终止后，可能产生数据迁移纠纷。',
    evidence: '📍 依据：第 5 章 知识产权（未提及数据归属）',
    actions: ['📝 补充数据条款', '忽略'],
  },
])

// AI 3 建议
const suggestions = ref([
  { idx: 1, title: '与客户协商付款周期延至 45 天', desc: '基于 12 个相似 SaaS 合同，付款周期从 30 → 45 天，<strong>回款及时率提升 22%</strong>，且不影响签约率（下降仅 3%）。', actions: ['📝 AI 起草协商邮件', '查看相似合同'] },
  { idx: 2, warning: true, title: '补充"逾期 0.05%/天"违约金条款', desc: '参考法务部标准条款库 v3.2。AI 已生成 v2 合同草稿，新增第 3.3 条。', actions: ['✓ 查看 v2 草稿', '发法务复核'] },
  { idx: 3, title: '补充"数据归属 + 3 年保密期"条款', desc: '客户业务数据归客户所有，我方留存 90 天用于服务支持，保密期 3 年。参考模板：法务库 v3.2 通用 SaaS 模板。', actions: ['📝 应用条款'] },
])

// 关键条款体检
const clauses = ref([
  { name: '服务范围', text: 'SaaS 平台标准版 · 50 个席位 · 12 个月', status: 'success', label: '✓ 完整' },
  { name: '付款方式', text: '合同签订后 7 日内支付 50%，验收后 30 日内支付 50%', status: 'warning', label: '⚠ 周期偏短' },
  { name: '违约金',   text: '— （未约定）',  status: 'danger',  label: '✗ 缺失' },
  { name: '知识产权', text: '平台代码归我方所有；客户数据 <span style="color:#F59E0B;font-weight:500">未明确归属</span>', status: 'warning', label: '⚠ 需补充' },
  { name: '保密条款', text: '双方对商业秘密承担保密义务', status: 'warning', label: '⚠ 无期限' },
  { name: '争议解决', text: '提交北京仲裁委员会仲裁', status: 'success', label: '✓ 完整' },
])

// 相似合同
const similar = ref([
  { code: 'HT-2026-031（当前）', amount: '¥86,500',  pay: '30 天', breach: '—',           score: 72, current: true,  scoreColor: 'warning' },
  { code: 'HT-2025-118（万象科技）', amount: '¥92,000', pay: '45 天', breach: '0.05%/天',  score: 88, current: false, scoreColor: 'success' },
  { code: 'HT-2025-203（智云科技）', amount: '¥78,000', pay: '60 天', breach: '0.1%/天',   score: 91, current: false, scoreColor: 'success' },
  { code: 'HT-2026-089（远见数据）', amount: '¥95,000', pay: '30 天', breach: '—',           score: 68, current: false, scoreColor: 'danger' },
])

// AI 异常时间线
const events = ref([
  { time: '2 小时前', text: '⚠️ 销售 <strong>王芳</strong> 提交合同时，付款周期从 45 → 30 天（<span style="color:#EF4444">-15 天</span>）' },
  { time: '3 小时前', text: '📉 与去年同期合同 HT-2025-118 对比，<strong>违约金条款被删除</strong>' },
  { time: '昨天',    text: '🤖 AI 完成首次扫描，识别出 3 个中高风险' },
  { time: '2 天前',  text: '📝 商务 <strong>王芳</strong> 创建合同（来自销售线索 L-2026-128）' },
  { time: '1 周前',  text: '✅ 客户<strong>万象科技</strong>信用评级：A（基于 3 年合作历史）' },
])

const overallScore = 72
function handleTab(t: string) {
  if (t === 'AI') return
  router.push(`/contract/1/${t === '基本信息' ? '' : t === '合同条款' ? 'clauses' : t === '审批流' ? 'approval' : t === '附件' ? 'files' : t === '履约记录' ? 'performance' : 'finance'}`)
}
function handleAction(act: string) { ElMessage.success(`已操作: ${act}`) }
function feedback(v: 'up' | 'down') { ElMessage.success(v === 'up' ? '感谢反馈' : 'AI 会持续优化') }
</script>

<template>
  <div class="page-container">
    <!-- contract-hero 蓝紫渐变 -->
    <div class="contract-hero">
      <div class="ch-left">
        <div class="ch-id">HT-2026-031</div>
        <h2>万象科技 SaaS 服务合同 2026Q2</h2>
        <div class="ch-meta">客户：<strong>万象科技有限公司</strong> · 销售合同 · 2026-06-11 ~ 2027-06-10</div>
      </div>
      <div class="ch-right">
        <div class="ch-amount-l">合同总金额</div>
        <div class="ch-amount">¥ 86,500.00</div>
      </div>
    </div>

    <!-- 7 detail-tabs，AI 体检 active -->
    <div class="detail-tabs">
      <div class="tab" @click="handleTab('基本信息')">📋 基本信息</div>
      <div class="tab" @click="handleTab('合同条款')">📜 合同条款</div>
      <div class="tab" @click="handleTab('审批流')">🔁 审批流</div>
      <div class="tab" @click="handleTab('附件')">📎 附件</div>
      <div class="tab" @click="handleTab('履约记录')">✓ 履约记录</div>
      <div class="tab" @click="handleTab('发票回款')">💰 发票/回款</div>
      <div class="tab active">✨ AI 体检 <span class="ai-badge">3 风险</span></div>
    </div>

    <div class="ai-panel">
      <!-- 1. 综合评分 + AI 摘要 -->
      <div class="ai-overview">
        <div class="ai-score-big">
          <div class="num">{{ overallScore }}</div>
          <div class="label">综合健康分</div>
          <div class="risk-tag medium"><span class="dot"></span>中风险</div>
        </div>
        <div class="ai-summary-area">
          <div class="h">
            <span class="ai-badge">AI 摘要</span>
            <span>本合同的 3 个关键风险</span>
          </div>
          <div class="text">
            合同整体条款基本完整，但存在 <strong>3 个中等风险</strong>：(1) 付款周期 30 天，短于行业平均的 45 天；<br>
            (2) 缺少违约金条款，逾期风险敞口大；<strong>(3) 未约定数据归属与保密期</strong>，法务复核建议补充。<br>
            整体可签，但建议<strong>先与客户协商</strong>以下 2 项条款（详见下方"AI 建议"）。
          </div>
        </div>
      </div>

      <!-- 2. 5 维健康度 -->
      <div class="card">
        <div class="card-head">
          <h3>5 维健康度</h3>
          <span class="muted">AI 评分 · 0-100 · 行业基准 75</span>
        </div>
        <div class="card-body">
          <div v-for="d in dims" :key="d.name" :class="['ai-dim-bar', { warn: d.warn }]">
            <span class="name">{{ d.name }}</span>
            <div class="bar">
              <div class="fill" :style="{ width: d.score + '%' }"></div>
              <div class="marker" style="left: 75%" data-val="行业"></div>
            </div>
            <span class="score">{{ d.score }}</span>
          </div>
        </div>
      </div>

      <!-- 3. 双栏：3 风险预警 + AI 3 建议 -->
      <div class="ai-grid-2">
        <!-- 左：风险预警 -->
        <div class="card">
          <div class="card-head">
            <h3>⚠️ 风险预警 <span class="ai-badge danger">3</span></h3>
            <span class="muted">按严重程度排序</span>
          </div>
          <div class="card-body">
            <div v-for="(r, i) in risks" :key="i" :class="['ai-warn', r.level]">
              <div class="ico">{{ r.icon }}</div>
              <div class="body">
                <div class="head">
                  <div class="title">{{ r.title }}</div>
                  <span :class="['ai-risk-chip', r.level]"><span class="dot"></span>{{ r.level === 'high' ? '高' : '中' }}</span>
                </div>
                <div class="desc">{{ r.desc }}</div>
                <div class="evidence" v-html="r.evidence"></div>
                <div class="actions">
                  <button v-for="(a, ai) in r.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '', ai === r.actions.length - 1 ? 'ignore' : '']" @click="handleAction(a)">{{ a }}</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右：采纳回执 + AI 建议 -->
        <div>
          <div class="ai-accept-bar">
            <div class="ico">✓</div>
            <div>
              <strong>已采纳：</strong>补充违约金条款 · AI 已生成 v2 草稿并发送至商务 <strong>王芳</strong> 复核
              <span class="undo" @click="handleAction('撤销')">撤销</span>
            </div>
          </div>
          <div class="card elevated">
            <div class="card-head">
              <h4>💡 AI 给你的 3 条建议</h4>
              <span class="ai-confidence high">置信度 91%</span>
            </div>
            <div class="card-body">
              <div v-for="s in suggestions" :key="s.idx" :class="['ai-suggestion', { warning: s.warning }]">
                <div class="ai-s-icon">{{ s.idx }}</div>
                <div class="ai-s-body">
                  <div class="ai-s-title">{{ s.title }}</div>
                  <div class="ai-s-desc" v-html="s.desc"></div>
                  <div class="ai-s-actions">
                    <button v-for="(a, ai) in s.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '']" @click="handleAction(a)">{{ a }}</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. 关键条款体检 -->
      <div class="card">
        <div class="card-head">
          <h3>📋 关键条款体检</h3>
          <span class="muted">与行业标准对比 · 6 项</span>
        </div>
        <div class="clauses">
          <div v-for="(c, i) in clauses" :key="i" class="clause-row">
            <div class="ck-name">{{ c.name }}</div>
            <div class="ck-text" v-html="c.text"></div>
            <div class="ck-status">
              <span :class="['tag', c.status]">{{ c.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. 双栏：相似合同 + AI 异常时间线 -->
      <div class="ai-grid-2">
        <!-- 左：相似合同 -->
        <div class="card">
          <div class="card-head">
            <h3>📊 相似合同参考</h3>
            <span class="muted">基于金额 + 客户行业匹配 3 个</span>
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
              <tr v-for="(s, i) in similar" :key="i" :class="{ current: s.current }">
                <td>{{ s.code }}</td>
                <td class="v">{{ s.amount }}</td>
                <td :class="['v', s.pay === '45 天' || s.pay === '60 天' ? 'success' : s.pay === '30 天' && !s.current ? 'warning' : '']">{{ s.pay }}</td>
                <td :class="['v', s.breach.includes('%') ? 'success' : '']">{{ s.breach }}</td>
                <td :class="['v', s.scoreColor]">{{ s.score }}</td>
              </tr>
            </tbody>
          </table>
          <div class="insight">
            💡 <strong>洞察：</strong>与万象科技去年的合作合同（HT-2025-118）相比，付款周期缩短了 15 天，且去掉了违约金条款。AI 推测是销售为冲业绩的让步。
          </div>
        </div>

        <!-- 右：AI 异常时间线 -->
        <div class="card">
          <div class="card-head">
            <h3>📅 AI 异常事件时间线</h3>
            <span class="muted">最近 30 天</span>
          </div>
          <div class="card-body">
            <div class="ai-timeline">
              <div v-for="(e, i) in events" :key="i" class="at-item">
                <div class="at-time">{{ e.time }}</div>
                <div class="at-text" v-html="e.text"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 6. 反馈条 -->
      <div class="ai-feedback-bar">
        <span>这次 AI 体检对你有帮助吗？</span>
        <div class="fb-actions">
          <div class="ai-feedback">
            <button class="up" title="有用" @click="feedback('up')">👍</button>
            <button title="没用" @click="feedback('down')">👎</button>
          </div>
          <a class="link-ai" @click="handleAction('下载完整报告')">下载完整报告 →</a>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

$color-ai: #7C3AED;
$color-ai-2: #4F6BFF;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-bg: rgba(124, 58, 237, 0.05);
$color-ai-border: rgba(124, 58, 237, 0.25);
$gradient-ai-soft: linear-gradient(135deg, rgba(79, 107, 255, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%);

// contract-hero
.contract-hero { background: $gradient-ai; border-radius: $radius-lg; padding: 24px 32px; margin-bottom: 16px; color: #fff; display: flex; justify-content: space-between; align-items: center; }
.ch-left { flex: 1; .ch-id { font-family: $font-family-mono; font-size: 12px; background: rgba(255, 255, 255, 0.2); display: inline-block; padding: 2px 10px; border-radius: 9999px; margin-bottom: 6px; } h2 { font-size: 22px; font-weight: 700; margin: 0 0 6px 0; } .ch-meta { font-size: 12.5px; color: rgba(255, 255, 255, 0.85); strong { color: #fff; font-weight: 600; } } }
.ch-right { text-align: right; .ch-amount-l { font-size: 11px; color: rgba(255, 255, 255, 0.7); } .ch-amount { font-size: 28px; font-weight: 700; font-family: $font-family-mono; } }

// detail-tabs
.detail-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 8px 16px; border-radius: $radius-md; font-size: 13px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; &:hover { color: $color-text-primary; background: $color-bg; } &.active { background: $color-primary-bg; color: $color-primary; font-weight: 500; } }
.ai-badge { display: inline-block; padding: 1px 6px; background: $gradient-ai; color: #fff; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 4px; vertical-align: middle; &.danger { background: $color-danger; } }

.muted { color: $color-text-tertiary; font-size: 11px; }
.link-ai { font-size: 12px; color: $color-ai; cursor: pointer; &:hover { text-decoration: underline; } }

// ai-overview
.ai-panel { display: flex; flex-direction: column; gap: 16px; }
.ai-overview { display: flex; gap: 20px; background: $gradient-ai-soft; border: 1px solid $color-ai-border; border-radius: $radius-lg; padding: 20px 24px; }
.ai-score-big { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 160px; padding: 16px; background: #fff; border-radius: $radius-md; border: 1px solid $color-ai-border; .num { font-size: 56px; font-weight: 700; color: $color-ai; line-height: 1; font-family: $font-family-mono; } .label { font-size: 12px; color: $color-text-secondary; margin: 4px 0 8px 0; } }
.risk-tag { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; &.medium { background: rgba(245, 158, 11, 0.1); color: #B45309; } .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; } }
.ai-summary-area { flex: 1; .h { display: flex; align-items: center; gap: 8px; font-size: 13px; color: $color-text-primary; margin-bottom: 10px; } .text { font-size: 13px; line-height: 1.7; color: $color-text-secondary; strong { color: $color-text-primary; } } }

// card
.card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; &.elevated { box-shadow: 0 4px 16px rgba(124, 58, 237, 0.08); } }
.card-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 22px; border-bottom: 1px solid $color-border; h3 { font-size: 14px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 6px; } h4 { font-size: 14px; font-weight: 600; margin: 0; } }
.card-body { padding: 12px 22px 16px; }

// 5 维
.ai-dim-bar { display: grid; grid-template-columns: 110px 1fr 40px; gap: 12px; align-items: center; padding: 8px 0; .name { font-size: 12.5px; color: $color-text-primary; } .bar { position: relative; height: 8px; background: $color-bg; border-radius: 9999px; overflow: visible; .fill { height: 100%; background: $gradient-ai; border-radius: 9999px; transition: width 0.3s; } .marker { position: absolute; top: -3px; width: 2px; height: 14px; background: $color-text-tertiary; &::after { content: '行业'; position: absolute; top: -16px; left: -10px; font-size: 9px; color: $color-text-tertiary; } } } &.warn .fill { background: linear-gradient(135deg, #F59E0B, #EF4444); } .score { font-size: 13px; font-weight: 700; color: $color-text-primary; font-family: $font-family-mono; text-align: right; } }

// ai-grid-2
.ai-grid-2 { display: grid; grid-template-columns: 1.1fr 1fr; gap: 16px; @media (max-width: 1100px) { grid-template-columns: 1fr; } }

// ai-warn
.ai-warn { display: flex; gap: 12px; padding: 12px 14px; background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; margin-bottom: 10px; &:last-child { margin-bottom: 0; } &.high { border-left-color: $color-danger; .ico { background: $color-danger-bg; color: $color-danger; } } &.medium { border-left-color: #F59E0B; .ico { background: rgba(245, 158, 11, 0.1); color: #F59E0B; } } }
.ico { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }
.ai-warn .body { flex: 1; min-width: 0; .head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; } .title { font-size: 13px; font-weight: 600; color: $color-text-primary; } .desc { font-size: 12px; line-height: 1.6; color: $color-text-secondary; margin-bottom: 6px; } .evidence { font-size: 11px; color: $color-text-tertiary; margin-bottom: 8px; font-family: $font-family-mono; } .actions { display: flex; gap: 6px; flex-wrap: wrap; } }
.ai-risk-chip { display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 9999px; font-size: 10.5px; font-weight: 600; &.high { background: $color-danger-bg; color: $color-danger; } &.medium { background: rgba(245, 158, 11, 0.1); color: #B45309; } .dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; } }
.btn-s { padding: 4px 10px; font-size: 11.5px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } } &.ignore { margin-left: auto; color: $color-text-tertiary; } }

// ai-accept-bar
.ai-accept-bar { display: flex; gap: 10px; padding: 12px 16px; background: $color-success-bg; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: $radius-md; margin-bottom: 12px; font-size: 12.5px; color: $color-text-primary; align-items: center; .ico { width: 24px; height: 24px; border-radius: 50%; background: $color-success; color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; flex-shrink: 0; } strong { color: $color-text-primary; } .undo { margin-left: auto; color: $color-primary; cursor: pointer; font-size: 12px; } }

// ai-suggestion
.ai-suggestion { display: flex; gap: 12px; padding: 12px 14px; background: #fff; border: 1px solid $color-ai-border; border-left: 4px solid $color-ai; border-radius: $radius-md; margin-bottom: 10px; &:last-child { margin-bottom: 0; } &.warning { border-left-color: #F59E0B; background: rgba(245, 158, 11, 0.04); } .ai-s-icon { width: 28px; height: 28px; border-radius: 50%; background: $gradient-ai; color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; flex-shrink: 0; } }
.ai-suggestion.warning .ai-s-icon { background: linear-gradient(135deg, #F59E0B, #EF4444); }
.ai-s-body { flex: 1; min-width: 0; .ai-s-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; } .ai-s-desc { font-size: 12px; line-height: 1.6; color: $color-text-secondary; margin-bottom: 8px; strong { color: $color-primary; } } .ai-s-actions { display: flex; gap: 6px; } }
.ai-confidence { padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; &.high { background: rgba(16, 185, 129, 0.12); color: #047857; } }

// clauses
.clauses { padding: 0; }
.clause-row { display: grid; grid-template-columns: 100px 1fr 100px; gap: 16px; align-items: center; padding: 12px 22px; border-bottom: 1px solid $color-border; &:last-child { border-bottom: none; } .ck-name { font-size: 13px; font-weight: 500; color: $color-text-primary; } .ck-text { font-size: 12.5px; color: $color-text-secondary; line-height: 1.5; } }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; &.success { background: $color-success-bg; color: $color-success; } &.warning { background: rgba(245, 158, 11, 0.1); color: #B45309; } &.danger { background: $color-danger-bg; color: $color-danger; } }

// ai-similar
.ai-similar { width: 100%; border-collapse: collapse; font-size: 12.5px; th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; } td { padding: 10px 12px; border-bottom: 1px solid $color-border; } tbody tr.current { background: $color-ai-bg; font-weight: 600; } tbody tr:hover { background: $color-bg; } .v { font-family: $font-family-mono; color: $color-text-primary; } .v.success { color: $color-success; } .v.warning { color: #F59E0B; } .v.danger { color: $color-danger; } }
.insight { padding: 10px 22px; font-size: 11.5px; color: $color-text-tertiary; background: #FAFBFF; strong { color: $color-text-primary; } }

// ai-timeline
.ai-timeline { padding: 4px 0; }
.at-item { position: relative; padding: 8px 0 8px 16px; border-left: 2px dashed $color-border; margin-left: 4px; &:last-child { padding-bottom: 0; } .at-time { font-size: 11px; color: $color-text-tertiary; font-family: $font-family-mono; margin-bottom: 2px; } .at-text { font-size: 12.5px; line-height: 1.5; color: $color-text-primary; strong { color: $color-text-primary; } } }

// ai-feedback-bar
.ai-feedback-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #F8FAFC; border-radius: $radius-md; font-size: 12.5px; color: $color-text-secondary; }
.fb-actions { display: flex; align-items: center; gap: 12px; }
.ai-feedback { display: flex; gap: 6px; button { width: 32px; height: 32px; border-radius: 50%; background: #fff; border: 1px solid $color-border; font-size: 14px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; } &.up { background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); } } }
</style>
