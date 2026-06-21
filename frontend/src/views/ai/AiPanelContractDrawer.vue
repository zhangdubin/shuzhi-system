<script setup lang="ts">
/**
 * AiPanelContractDrawer · AI 合同体检抽屉（1:1 复刻 ai-panel-contract-drawer.html 664 行）
 * - 背景是合同详情页（demo 暗色蒙层 dimmed 状态）
 * - 右侧抽屉：drawer-mask + drawer（head + body + foot）
 *   - head: ✦ AI 合同体检 + close ×
 *   - body: 综合评分 72 + 智能摘要 + 5 维评分 + 3 风险预警 + 3 AI 建议 + 相似合同 4 行 + 反馈
 *   - foot: 模型 + 成本 + 完整报告 + 采纳全部建议
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const drawerOpen = ref(true)  // 设计稿默认打开演示

// 5 维
const dims = ref([
  { name: '📋 条款完整', score: 78, warn: false },
  { name: '💰 付款条件', score: 55, warn: true },
  { name: '⚖️ 法务合规', score: 62, warn: true },
  { name: '💵 金额风险', score: 88, warn: false },
  { name: '🤝 客户资质', score: 92, warn: false },
])

// 3 风险预警
const risks = ref([
  { level: 'high',   title: '付款周期短于行业', desc: '约定 30 天，行业平均 45 天。回款及时率可能下降 22%。', actions: ['📝 协商邮件', '查看条款'] },
  { level: 'high',   title: '未约定违约金',     desc: '逾期无任何约束。维权成本可能超过合同金额。',     actions: ['📝 补充条款'] },
  { level: 'medium', title: '数据归属未约定',   desc: '服务终止后可能产生数据迁移纠纷。',               actions: ['📝 应用模板'] },
])

// 3 建议
const suggestions = ref([
  { idx: 1, warning: true, title: '付款周期延至 45 天', desc: '基于 12 个相似合同，回款及时率提升 22%。', actions: ['📝 起草邮件'] },
  { idx: 2, title: '补充违约金条款', desc: '法务库 v3.2 模板，AI 已生成 v2 草稿。', actions: ['✓ 查看草稿'] },
  { idx: 3, success: true, title: '数据归属 + 3 年保密', desc: '参考法务库 v3.2 通用模板。', actions: ['应用'] },
])

// 相似合同
const similar = ref([
  { name: '📌 HT-2026-031（当前）', pay: '30天', breach: '—',         score: 72, scoreClass: 'warn', current: true },
  { name: 'HT-2025-118（万象续约）', pay: '45天', breach: '0.05%/天',  score: 88, scoreClass: 'good', current: false },
  { name: 'HT-2025-203（智云）',     pay: '60天', breach: '0.1%/天',   score: 91, scoreClass: 'good', current: false },
  { name: 'HT-2026-089（远见）',     pay: '30天', breach: '—',         score: 68, scoreClass: 'bad',  current: false },
])

function closeDrawer() { drawerOpen.value = false; setTimeout(() => router.push('/ai/panel/contract'), 200) }
function openDrawer() { drawerOpen.value = true }
function handleAction(act: string) { ElMessage.success(`已操作: ${act}`) }
function feedback(v: 'up' | 'down') { ElMessage.success(v === 'up' ? '感谢反馈' : 'AI 会持续优化') }
function adoptAll() { ElMessage.success('已采纳全部建议') }

onMounted(() => {
  // 监听 ESC 关闭
  const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') closeDrawer() }
  window.addEventListener('keydown', handleEsc)
  onUnmounted(() => window.removeEventListener('keydown', handleEsc))
})
</script>

<template>
  <div class="page-container">
    <!-- 背景：合同详情页（蒙层 dimmed 状态） -->
    <div :class="['bg-page', { dimmed: drawerOpen }]">
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

      <div class="info-cards">
        <div class="info-card">
          <h4>📋 合同基本信息</h4>
          <div class="info-grid">
            <div class="item"><div class="l">合同编号</div><div class="v">HT-2026-031</div></div>
            <div class="item"><div class="l">合同类型</div><div class="v">销售合同</div></div>
            <div class="item"><div class="l">业务分类</div><div class="v">SaaS 服务</div></div>
            <div class="item"><div class="l">客户名称</div><div class="v">万象科技有限公司</div></div>
            <div class="item"><div class="l">签约日期</div><div class="v">2026-06-11</div></div>
            <div class="item"><div class="l">有效期</div><div class="v">2026-06-11 ~ 2027-06-10</div></div>
            <div class="item"><div class="l">合同金额</div><div class="v mono">¥ 86,500.00</div></div>
            <div class="item"><div class="l">币种</div><div class="v">人民币</div></div>
            <div class="item"><div class="l">我方签约人</div><div class="v">张明</div></div>
            <div class="item"><div class="l">客户签约人</div><div class="v">王磊</div></div>
            <div class="item"><div class="l">所属项目</div><div class="v">万象科技二期</div></div>
            <div class="item"><div class="l">关联销售</div><div class="v">王芳</div></div>
          </div>
        </div>

        <div class="info-card">
          <h4>📌 备注信息</h4>
          <p class="remark">
            客户为续约客户，去年同期签订 HT-2025-118（金额 9.2 万，付款周期 45 天，状态：已履约完成）。
            本次续约由销售王芳跟进，付款条件有所调整。
          </p>
        </div>

        <div class="trigger-area">
          <button class="btn-trigger" @click="openDrawer">
            ✦ 触发 AI 体检
          </button>
        </div>
      </div>
    </div>

    <!-- 抽屉蒙层 + 抽屉主体 -->
    <div v-if="drawerOpen" class="drawer-mask" @click="closeDrawer"></div>
    <div v-if="drawerOpen" class="drawer">
      <div class="drawer-head">
        <div class="h">
          <div class="title"><span class="t-icon">✦</span><span>AI 合同体检</span></div>
          <button class="close" @click="closeDrawer">✕</button>
        </div>
        <div class="sub">HT-2026-031 · 万象科技 SaaS 服务合同 · 耗时 0.6s</div>
      </div>

      <div class="drawer-body">
        <!-- 综合评分 -->
        <div class="drawer-score">
          <div class="num">72</div>
          <div class="label">综合健康分</div>
          <div class="risk medium"><span class="dot"></span>中风险 · 建议补充 2 项条款</div>
        </div>

        <!-- 智能摘要 -->
        <div class="drawer-summary">
          AI 已识别 <strong>3 个风险点</strong>（2 高 1 中），<strong>2 个最关键</strong>：付款周期短于行业 33% + 缺少违约金条款。建议采纳下方 3 条 AI 建议。
        </div>

        <!-- 5 维 -->
        <div class="section-h">5 维评分</div>
        <div class="drawer-dim">
          <div v-for="d in dims" :key="d.name" class="d">
            <span class="n">{{ d.name }}</span>
            <div class="b"><div :class="['f', { warn: d.warn }]" :style="{ width: d.score + '%' }"></div></div>
            <span class="s">{{ d.score }}</span>
          </div>
        </div>

        <!-- 风险预警 -->
        <div class="section-h">⚠️ 风险预警 · 3 项</div>
        <div v-for="(r, i) in risks" :key="i" :class="['drawer-warn', r.level]">
          <div class="head">
            <div class="title">{{ r.title }}</div>
            <span :class="['ai-risk-chip', r.level]"><span class="dot"></span>{{ r.level === 'high' ? '高' : '中' }}</span>
          </div>
          <div class="desc">{{ r.desc }}</div>
          <div class="actions">
            <button v-for="(a, ai) in r.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '']" @click="handleAction(a)">{{ a }}</button>
          </div>
        </div>

        <!-- AI 建议 -->
        <div class="section-h">💡 AI 建议 · 3 条</div>
        <div v-for="s in suggestions" :key="s.idx" :class="['ai-suggestion', { warning: s.warning, success: s.success }]">
          <div class="ai-s-icon">{{ s.idx }}</div>
          <div class="ai-s-body">
            <div class="ai-s-title">{{ s.title }}</div>
            <div class="ai-s-desc">{{ s.desc }}</div>
            <div class="ai-s-actions">
              <button v-for="(a, ai) in s.actions" :key="ai" class="btn-s primary" @click="handleAction(a)">{{ a }}</button>
            </div>
          </div>
        </div>

        <!-- 相似合同 -->
        <div class="section-h">📊 相似合同</div>
        <div class="drawer-similar">
          <div v-for="(s, i) in similar" :key="i" :class="['sim-row', { current: s.current }]">
            <div class="name">{{ s.name }}</div>
            <div class="v">{{ s.pay }}</div>
            <div class="v">{{ s.breach }}</div>
            <div :class="['score', s.scoreClass]">{{ s.score }}</div>
          </div>
        </div>
        <div class="insight">💡 <strong>洞察：</strong>与去年同客户相比，付款周期缩短 15 天，违约金被删，AI 推测为销售冲业绩让步。</div>

        <!-- 反馈 -->
        <div class="feedback">
          这次 AI 体检对你有帮助吗？
          <div class="ai-feedback">
            <button class="up" title="有用" @click="feedback('up')">👍</button>
            <button title="没用" @click="feedback('down')">👎</button>
          </div>
        </div>
      </div>

      <div class="drawer-foot">
        <div class="meta">✦ 模型 risk-v2.3 · 成本 0.01 元</div>
        <button class="btn-s" @click="handleAction('完整报告')">📥 完整报告</button>
        <button class="btn-s primary" @click="adoptAll">✓ 采纳全部建议</button>
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

.page-container { position: relative; }

// 背景：合同详情页
.bg-page { transition: opacity 0.3s; &.dimmed { opacity: 0.4; pointer-events: none; } }

.contract-hero { background: $gradient-ai; border-radius: $radius-lg; padding: 24px 32px; margin-bottom: 16px; color: #fff; display: flex; justify-content: space-between; align-items: center; }
.ch-left { flex: 1; .ch-id { font-family: $font-family-mono; font-size: 12px; background: rgba(255, 255, 255, 0.2); display: inline-block; padding: 2px 10px; border-radius: 9999px; margin-bottom: 6px; } h2 { font-size: 22px; font-weight: 700; margin: 0 0 6px 0; } .ch-meta { font-size: 12.5px; color: rgba(255, 255, 255, 0.85); strong { color: #fff; } } }
.ch-right { text-align: right; .ch-amount-l { font-size: 11px; color: rgba(255, 255, 255, 0.7); } .ch-amount { font-size: 28px; font-weight: 700; font-family: $font-family-mono; } }

.info-cards { display: flex; flex-direction: column; gap: 16px; }
.info-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 18px 22px; h4 { font-size: 14px; font-weight: 600; margin: 0 0 12px 0; } .remark { font-size: 13px; line-height: 1.6; color: $color-text-secondary; margin: 0; } }
.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px 24px; }
.item { display: flex; gap: 12px; font-size: 12.5px; padding: 4px 0; .l { color: $color-text-tertiary; min-width: 80px; flex-shrink: 0; } .v { color: $color-text-primary; } .v.mono { font-family: $font-family-mono; font-weight: 600; } }

.trigger-area { text-align: center; padding: 20px 0; }
.btn-trigger { padding: 12px 24px; background: $gradient-ai; color: #fff; border: none; border-radius: $radius-md; font-size: 14px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3); transition: all 0.2s; &:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4); } }

// drawer-mask
.drawer-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.4); z-index: 100; animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

// drawer
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: 480px; max-width: 90vw; background: #fff; z-index: 101; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(15, 23, 42, 0.15); animation: slideIn 0.25s; }
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }

.drawer-head { padding: 16px 20px; border-bottom: 1px solid $color-border; background: $gradient-ai-soft; .h { display: flex; justify-content: space-between; align-items: center; } .title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; color: $color-text-primary; .t-icon { font-size: 20px; color: $color-ai; } } .close { width: 28px; height: 28px; border-radius: 50%; background: transparent; border: none; font-size: 18px; color: $color-text-tertiary; cursor: pointer; &:hover { background: $color-bg; color: $color-text-primary; } } .sub { font-size: 11.5px; color: $color-text-tertiary; margin-top: 4px; font-family: $font-family-mono; } }
.drawer-body { flex: 1; padding: 16px 20px; overflow-y: auto; }

.drawer-score { text-align: center; padding: 14px 0 18px 0; border-bottom: 1px dashed $color-border; margin-bottom: 12px; .num { font-size: 48px; font-weight: 700; color: $color-ai; line-height: 1; font-family: $font-family-mono; } .label { font-size: 12px; color: $color-text-secondary; margin: 4px 0 8px 0; } .risk { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; &.medium { background: rgba(245, 158, 11, 0.1); color: #B45309; } .dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; } } }
.drawer-summary { background: $color-ai-bg; border: 1px solid $color-ai-border; border-radius: $radius-md; padding: 10px 14px; font-size: 12.5px; line-height: 1.6; color: $color-text-secondary; margin-bottom: 14px; strong { color: $color-text-primary; } }

.section-h { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin: 12px 0 8px 0; }

// 5 维（drawer 内）
.drawer-dim { display: flex; flex-direction: column; gap: 8px; margin-bottom: 4px; }
.d { display: grid; grid-template-columns: 80px 1fr 32px; gap: 8px; align-items: center; .n { font-size: 11.5px; color: $color-text-primary; } .b { height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; .f { height: 100%; background: $gradient-ai; border-radius: 3px; &.warn { background: linear-gradient(135deg, #F59E0B, #EF4444); } } } .s { font-size: 11.5px; font-weight: 700; font-family: $font-family-mono; text-align: right; } }

// 风险
.drawer-warn { padding: 10px 12px; background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; margin-bottom: 8px; &.high { border-left-color: $color-danger; } &.medium { border-left-color: #F59E0B; } .head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px; } .title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; } .desc { font-size: 11.5px; line-height: 1.5; color: $color-text-secondary; margin-bottom: 6px; } .actions { display: flex; gap: 4px; } }
.ai-risk-chip { display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 9999px; font-size: 10.5px; font-weight: 600; &.high { background: $color-danger-bg; color: $color-danger; } &.medium { background: rgba(245, 158, 11, 0.1); color: #B45309; } .dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; } }
.btn-s { padding: 3px 10px; font-size: 11px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3); } } }

// 建议
.ai-suggestion { display: flex; gap: 10px; padding: 10px 12px; background: #fff; border: 1px solid $color-ai-border; border-left: 4px solid $color-ai; border-radius: $radius-md; margin-bottom: 8px; &.warning { border-left-color: #F59E0B; background: rgba(245, 158, 11, 0.04); } &.success { border-left-color: $color-success; background: rgba(16, 185, 129, 0.04); } .ai-s-icon { width: 24px; height: 24px; border-radius: 50%; background: $gradient-ai; color: #fff; display: grid; place-items: center; font-size: 11px; font-weight: 700; flex-shrink: 0; } }
.ai-suggestion.warning .ai-s-icon { background: linear-gradient(135deg, #F59E0B, #EF4444); }
.ai-suggestion.success .ai-s-icon { background: $color-success; }
.ai-s-body { flex: 1; min-width: 0; .ai-s-title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 2px; } .ai-s-desc { font-size: 11.5px; line-height: 1.5; color: $color-text-secondary; margin-bottom: 6px; } .ai-s-actions { display: flex; gap: 4px; } }

// 相似合同
.drawer-similar { display: flex; flex-direction: column; gap: 4px; }
.sim-row { display: grid; grid-template-columns: 1fr 50px 60px 40px; gap: 8px; align-items: center; padding: 8px 10px; border-radius: $radius-sm; font-size: 11.5px; &.current { background: $color-ai-bg; font-weight: 600; } .name { color: $color-text-primary; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .v { font-family: $font-family-mono; color: $color-text-secondary; text-align: center; } .score { font-family: $font-family-mono; font-weight: 700; text-align: right; &.good { color: $color-success; } &.warn { color: #F59E0B; } &.bad { color: $color-danger; } } }
.insight { font-size: 11px; color: $color-text-tertiary; margin-top: 6px; line-height: 1.5; strong { color: $color-text-primary; } }

.feedback { margin-top: 16px; text-align: center; font-size: 11.5px; color: $color-text-secondary; }
.ai-feedback { display: inline-flex; gap: 4px; margin-left: 6px; button { width: 28px; height: 28px; border-radius: 50%; background: #fff; border: 1px solid $color-border; font-size: 13px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; } &.up { background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); } } }

.drawer-foot { padding: 12px 20px; border-top: 1px solid $color-border; background: #FAFBFF; display: flex; align-items: center; gap: 8px; .meta { font-size: 11px; color: $color-text-tertiary; font-family: $font-family-mono; flex: 1; } }
</style>
