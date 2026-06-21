<script setup lang="ts">
/**
 * AiPanelProject · AI 项目分析（1:1 复刻 design/ai-panel-project.html 511 行）
 * - 顶部 project-hero 蓝紫渐变
 * - 7 detail-tabs，AI 分析 active
 * - 1fr / 1.4fr 双栏：
 *   - 左：项目健康度（SVG 雷达图 5 维 + 5 维进度条）+ 3 风险预警
 *   - 右：智能摘要 + 3 AI 建议 + 相似项目对比 4 行 + AI 异常时间线 + 反馈条
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 5 维
const dims = ref([
  { name: '📈 进度', score: 90, color: 'success' },
  { name: '💰 成本', score: 75, color: 'warning' },
  { name: '⭐ 质量', score: 85, color: 'success' },
  { name: '⚠️ 风险', score: 65, color: 'danger' },
  { name: '🤝 客户', score: 95, color: 'success' },
])

// 3 风险预警
const risks = ref([
  { level: 'high',   icon: '🚨', title: '进度滞后 7%', desc: 'M4 里程碑延期 5 天，预计影响 M5 启动时间。建议：增派 1 名后端工程师 / 每日站会跟踪。', actions: ['采纳', '查看详情'] },
  { level: 'medium', icon: '💸', title: '预算超支风险', desc: '已消耗预算 62%，剩余 38% 需覆盖剩余 32% 工期，预计超支约 8.5 万（占总预算 8%）。', actions: ['采纳', '查看详情'] },
  { level: 'low',    icon: '🔍', title: '客户响应变慢', desc: '客户最近 7 天平均响应时间 26h（历史 8h），需主动跟进避免阻塞。', actions: ['采纳', '忽略'] },
])

// 3 AI 建议
const suggestions = ref([
  { idx: 1, warning: true, title: '本周三组织 M5 验收对齐会', desc: '基于历史项目数据，里程碑延期 5 天后再拖 1 周，延期概率将升至 65%。建议提前与客户对齐验收标准。', actions: ['📅 创建会议', '稍后'] },
  { idx: 2, success: true, title: '把"后端 API 模块"从李明一人改为王洋协助', desc: '相似项目数据：单人负责模块延期率 38%，双人协作 12%。王洋历史参与过该模块（贡献度 28%）。', actions: ['✓ 调整团队', '查看相似项目'] },
  { idx: 3, title: '向客户主动汇报当前进度', desc: '客户最近响应变慢，主动汇报能挽回信任。本项目客户历史偏好：邮件 + 简短周报。', actions: ['✍️ AI 起草邮件', '稍后'] },
])

// 相似项目
const similar = ref([
  { name: '📌 数智化二期 <span class="ai-badge-mini">本项目</span>', score: 82, scoreColor: 'warning', delay: '+5',  delayColor: 'warning', over: '8%',  overColor: 'warning', current: true },
  { name: '数智化一期',       score: 91, scoreColor: 'success', delay: '0',   delayColor: 'success', over: '-2%', overColor: 'success', current: false },
  { name: '客户A 业务中台',   score: 88, scoreColor: 'success', delay: '+3',  delayColor: 'warning', over: '5%',  overColor: 'success', current: false },
  { name: '客户B 数据治理',   score: 72, scoreColor: 'danger',  delay: '+18', delayColor: 'danger',  over: '15%', overColor: 'danger',  current: false },
])

// 异常时间线
const events = ref([
  { time: '2 小时前',   text: '⚠️ M4 里程碑延期 <strong>5 天</strong>，影响后续 3 个任务' },
  { time: '昨天 16:42', text: '📉 客户最近 3 次需求变更，平均响应 <strong>26h</strong>（历史 8h）' },
  { time: '3 天前',     text: '💸 预算消耗速度 <strong>+12%</strong>，触发黄色预警' },
  { time: '1 周前',     text: '👥 关键人员李明连续 5 天加班（健康度 -8）' },
  { time: '2 周前',     text: '✅ M3 里程碑按时完成（健康度 +5）' },
])

function handleTab(t: string) {
  if (t === 'AI') return
  router.push(`/project/1/${t === '基本信息' ? '' : t === '进度' ? 'progress' : t === '里程碑' ? 'milestones' : t === '任务' ? 'tasks' : t === '文件' ? 'files' : 'dynamics'}`)
}
function handleAction(act: string) { ElMessage.success(`已操作: ${act}`) }
function feedback(v: 'up' | 'down') { ElMessage.success(v === 'up' ? '感谢反馈' : 'AI 会持续优化') }
</script>

<template>
  <div class="page-container">
    <!-- project-hero 蓝紫渐变 -->
    <div class="project-hero">
      <div class="ph-left">
        <div class="ph-id">PRJ-2026-005</div>
        <h2>数智化二期 - 平台升级</h2>
        <div class="ph-meta">客户：<strong>万象科技</strong> · 实施中 · 进度 68% · 2026-04-01 ~ 2026-09-30</div>
      </div>
      <div class="ph-right">
        <div class="ph-stat">
          <div class="ph-stat-l">综合健康分</div>
          <div class="ph-stat-n">82</div>
          <div class="ph-stat-l">良好</div>
        </div>
      </div>
    </div>

    <!-- 7 detail-tabs，AI 分析 active -->
    <div class="detail-tabs">
      <div class="tab" @click="handleTab('基本信息')">📋 基本信息</div>
      <div class="tab" @click="handleTab('进度')">📈 进度</div>
      <div class="tab" @click="handleTab('里程碑')">🏁 里程碑</div>
      <div class="tab" @click="handleTab('任务')">📋 任务</div>
      <div class="tab" @click="handleTab('文件')">📁 文件</div>
      <div class="tab" @click="handleTab('动态')">💬 动态</div>
      <div class="tab active">✨ AI 分析 <span class="ai-badge">3</span></div>
    </div>

    <div class="ai-grid-pj">
      <!-- 左：健康度 + 风险预警 -->
      <div class="ai-left">
        <!-- 健康度 5 维雷达图 -->
        <div class="card">
          <div class="card-head">
            <h3>✦ 项目健康度</h3>
            <span class="muted">基于 5 维评估</span>
          </div>
          <div class="health-body">
            <div class="radar-wrap">
              <div class="overall">82</div>
              <div class="overall-label">综合分 · 良好</div>
              <!-- SVG 5 维雷达图（design 1:1） -->
              <svg viewBox="0 0 200 200" class="radar-svg">
                <polygon points="100,20 175,75 145,165 55,165 25,75" fill="none" stroke="#E2E8F0" stroke-width="1"/>
                <polygon points="100,40 158,82 137,150 63,150 42,82" fill="none" stroke="#E2E8F0" stroke-width="1"/>
                <polygon points="100,60 141,90 129,135 71,135 59,90" fill="none" stroke="#E2E8F0" stroke-width="1"/>
                <polygon points="100,80 124,98 121,120 79,120 76,98" fill="none" stroke="#E2E8F0" stroke-width="1"/>
                <line x1="100" y1="100" x2="100" y2="20" stroke="#CBD5E1" stroke-width="1"/>
                <line x1="100" y1="100" x2="175" y2="75" stroke="#CBD5E1" stroke-width="1"/>
                <line x1="100" y1="100" x2="145" y2="165" stroke="#CBD5E1" stroke-width="1"/>
                <line x1="100" y1="100" x2="55" y2="165" stroke="#CBD5E1" stroke-width="1"/>
                <line x1="100" y1="100" x2="25" y2="75" stroke="#CBD5E1" stroke-width="1"/>
                <polygon points="100,30 168,77 130,148 65,148 33,77" fill="rgba(124,58,237,0.25)" stroke="#7C3AED" stroke-width="2"/>
                <circle cx="100" cy="30" r="3" fill="#7C3AED"/>
                <circle cx="168" cy="77" r="3" fill="#7C3AED"/>
                <circle cx="130" cy="148" r="3" fill="#7C3AED"/>
                <circle cx="65" cy="148" r="3" fill="#7C3AED"/>
                <circle cx="33" cy="77" r="3" fill="#7C3AED"/>
                <text x="100" y="14" text-anchor="middle" font-size="10" fill="#475569">进度</text>
                <text x="183" y="73" text-anchor="start" font-size="10" fill="#475569">质量</text>
                <text x="148" y="180" text-anchor="middle" font-size="10" fill="#475569">客户</text>
                <text x="52" y="180" text-anchor="end" font-size="10" fill="#475569">成本</text>
                <text x="17" y="73" text-anchor="end" font-size="10" fill="#475569">风险</text>
              </svg>
            </div>
            <div class="dim-list">
              <div v-for="d in dims" :key="d.name" class="ai-dim">
                <span class="dim-name">{{ d.name }}</span>
                <div class="dim-bar"><div :class="['fill', d.color]" :style="{ width: d.score + '%' }"></div></div>
                <span class="dim-score">{{ d.score }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 风险预警 -->
        <div class="card">
          <div class="card-head">
            <h3>⚠️ 风险预警 <span class="ai-badge danger">3</span></h3>
          </div>
          <div class="card-body">
            <div v-for="(r, i) in risks" :key="i" :class="['ai-warn-card', r.level]">
              <div class="head">
                <div class="title">{{ r.icon }} {{ r.title }}</div>
                <span :class="['ai-risk-chip', r.level]"><span class="dot"></span>{{ r.level === 'high' ? '高' : r.level === 'medium' ? '中' : '低' }}</span>
              </div>
              <div class="desc">{{ r.desc }}</div>
              <div class="actions">
                <button v-for="(a, ai) in r.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '']" @click="handleAction(a)">{{ a }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：智能摘要 + 3 建议 + 相似 + 时间线 -->
      <div class="ai-right">
        <!-- 智能摘要 -->
        <div class="ai-summary-block">
          <strong>AI 摘要：</strong> 数智化二期项目 <strong>整体健康</strong>，但已进入 <strong>风险积累期</strong>。进度的 7% 滞后通过增资源可在 10 天内追回；成本的 8% 超支需客户理解或调整范围；客户满意度持续 95 分 <strong>为项目最大资产</strong>。建议<strong>本周三</strong>组织三方会议对齐 M5 验收标准。
        </div>

        <!-- 3 AI 建议 -->
        <div class="card elevated">
          <div class="card-head">
            <h4>💡 AI 给你的 3 条建议</h4>
            <span class="ai-confidence high">置信度 88%</span>
          </div>
          <div class="card-body">
            <div v-for="s in suggestions" :key="s.idx" :class="['ai-suggestion', { warning: s.warning, success: s.success }]">
              <div class="ai-s-icon">{{ s.idx }}</div>
              <div class="ai-s-body">
                <div class="ai-s-title">{{ s.title }}</div>
                <div class="ai-s-desc">{{ s.desc }}</div>
                <div class="ai-s-actions">
                  <button v-for="(a, ai) in s.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '']" @click="handleAction(a)">{{ a }}</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 相似项目 -->
        <div class="card">
          <div class="card-head">
            <h3>📊 相似项目参考</h3>
            <span class="muted">基于项目特征匹配 3 个</span>
          </div>
          <div class="similar-table">
            <div class="ai-similar-row head">
              <div>项目</div>
              <div style="text-align:right">健康度</div>
              <div style="text-align:right">延期天数</div>
              <div style="text-align:right">超支率</div>
            </div>
            <div v-for="(s, i) in similar" :key="i" :class="['ai-similar-row', { current: s.current }]">
              <div class="name" v-html="s.name"></div>
              <div :class="['v', s.scoreColor]" style="text-align:right">{{ s.score }}</div>
              <div :class="['v', s.delayColor]" style="text-align:right">{{ s.delay }}</div>
              <div :class="['v', s.overColor]" style="text-align:right">{{ s.over }}</div>
            </div>
          </div>
        </div>

        <!-- AI 异常时间线 -->
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
          <div class="ai-feedback-bar">
            <span>这次 AI 分析对你有帮助吗？</span>
            <div class="fb-actions">
              <div class="ai-feedback">
                <button class="up" title="有用" @click="feedback('up')">👍</button>
                <button title="没用" @click="feedback('down')">👎</button>
              </div>
              <a class="link-ai" @click="handleAction('查看完整报告')">查看完整报告 →</a>
            </div>
          </div>
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

// project-hero
.project-hero { background: $gradient-ai; border-radius: $radius-lg; padding: 24px 32px; margin-bottom: 16px; color: #fff; display: flex; justify-content: space-between; align-items: center; }
.ph-left { flex: 1; .ph-id { font-family: $font-family-mono; font-size: 12px; background: rgba(255, 255, 255, 0.2); display: inline-block; padding: 2px 10px; border-radius: 9999px; margin-bottom: 6px; } h2 { font-size: 22px; font-weight: 700; margin: 0 0 6px 0; } .ph-meta { font-size: 12.5px; color: rgba(255, 255, 255, 0.85); strong { color: #fff; } } }
.ph-right .ph-stat { text-align: right; .ph-stat-l { font-size: 11px; color: rgba(255, 255, 255, 0.7); } .ph-stat-n { font-size: 36px; font-weight: 700; font-family: $font-family-mono; line-height: 1; } }

// detail-tabs
.detail-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 8px 16px; border-radius: $radius-md; font-size: 13px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; &:hover { color: $color-text-primary; background: $color-bg; } &.active { background: $color-primary-bg; color: $color-primary; font-weight: 500; } }
.ai-badge { display: inline-block; padding: 1px 6px; background: $gradient-ai; color: #fff; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 4px; vertical-align: middle; &.danger { background: $color-danger; } }
.ai-badge-mini { font-size: 9px; padding: 1px 5px; background: $gradient-ai; color: #fff; border-radius: 9999px; }
.muted { color: $color-text-tertiary; font-size: 11px; }
.link-ai { font-size: 12px; color: $color-ai; cursor: pointer; &:hover { text-decoration: underline; } }

// 双栏
.ai-grid-pj { display: grid; grid-template-columns: 1fr 1.4fr; gap: 20px; @media (max-width: 1100px) { grid-template-columns: 1fr; } }
.ai-left, .ai-right { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

// card
.card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; &.elevated { box-shadow: 0 4px 16px rgba(124, 58, 237, 0.08); } }
.card-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 22px; border-bottom: 1px solid $color-border; h3 { font-size: 14px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 6px; } h4 { font-size: 14px; font-weight: 600; margin: 0; } }
.card-body { padding: 12px 22px 16px; }

// 健康度
.health-body { padding: 16px 22px; display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center; }
.radar-wrap { width: 180px; text-align: center; .overall { font-size: 36px; font-weight: 700; color: $color-ai; line-height: 1; font-family: $font-family-mono; } .overall-label { font-size: 11px; color: $color-text-tertiary; margin: 4px 0 8px 0; } .radar-svg { width: 160px; height: 160px; margin: 0 auto; display: block; } }
.dim-list { display: flex; flex-direction: column; gap: 10px; }
.ai-dim { display: grid; grid-template-columns: 80px 1fr 32px; gap: 10px; align-items: center; .dim-name { font-size: 12px; color: $color-text-primary; } .dim-bar { height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; .fill { height: 100%; background: $gradient-ai; border-radius: 3px; &.success { background: $color-success; } &.warning { background: #F59E0B; } &.danger { background: $color-danger; } } } .dim-score { font-size: 12px; font-weight: 700; color: $color-text-primary; font-family: $font-family-mono; text-align: right; } }

// 风险预警
.ai-warn-card { padding: 12px 14px; background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; margin-bottom: 10px; &:last-child { margin-bottom: 0; } &.danger { border-left-color: $color-danger; } &.high { border-left-color: $color-danger; } &.medium { border-left-color: #F59E0B; } &.low { border-left-color: $color-ai; } &.info { border-left-color: $color-ai; } }
.ai-warn-card .head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; .title { font-size: 13px; font-weight: 600; color: $color-text-primary; } .desc { font-size: 12px; line-height: 1.6; color: $color-text-secondary; margin-bottom: 8px; } .actions { display: flex; gap: 6px; } }
.ai-risk-chip { display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px; border-radius: 9999px; font-size: 10.5px; font-weight: 600; &.high { background: $color-danger-bg; color: $color-danger; } &.medium { background: rgba(245, 158, 11, 0.1); color: #B45309; } &.low { background: $color-ai-bg; color: $color-ai; } .dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; } }
.btn-s { padding: 4px 10px; font-size: 11.5px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } } }

// 智能摘要
.ai-summary-block { background: $gradient-ai-soft; border: 1px solid $color-ai-border; border-radius: $radius-md; padding: 14px 18px; font-size: 12.5px; line-height: 1.7; color: $color-text-secondary; strong { color: $color-text-primary; } }

// AI 建议
.ai-suggestion { display: flex; gap: 12px; padding: 12px 14px; background: #fff; border: 1px solid $color-ai-border; border-left: 4px solid $color-ai; border-radius: $radius-md; margin-bottom: 10px; &:last-child { margin-bottom: 0; } &.warning { border-left-color: #F59E0B; background: rgba(245, 158, 11, 0.04); } &.success { border-left-color: $color-success; background: rgba(16, 185, 129, 0.04); } .ai-s-icon { width: 28px; height: 28px; border-radius: 50%; background: $gradient-ai; color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; flex-shrink: 0; } }
.ai-suggestion.warning .ai-s-icon { background: linear-gradient(135deg, #F59E0B, #EF4444); }
.ai-suggestion.success .ai-s-icon { background: $color-success; }
.ai-s-body { flex: 1; min-width: 0; .ai-s-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; } .ai-s-desc { font-size: 12px; line-height: 1.6; color: $color-text-secondary; margin-bottom: 8px; strong { color: $color-primary; } } .ai-s-actions { display: flex; gap: 6px; } }
.ai-confidence { padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; &.high { background: rgba(16, 185, 129, 0.12); color: #047857; } }

// 相似项目
.similar-table { padding: 0; }
.ai-similar-row { display: grid; grid-template-columns: 1fr 80px 80px 80px; gap: 12px; align-items: center; padding: 12px 22px; border-bottom: 1px solid $color-border; font-size: 12.5px; &:last-child { border-bottom: none; } &.head { background: #FAFBFF; color: $color-text-tertiary; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; } &.current { background: $color-ai-bg; font-weight: 600; .name { color: $color-text-primary; } } .name { color: $color-text-primary; } .v { font-family: $font-family-mono; font-weight: 600; &.success { color: $color-success; } &.warning { color: #F59E0B; } &.danger { color: $color-danger; } } }

// AI 时间线
.ai-timeline { padding: 4px 0; }
.at-item { position: relative; padding: 8px 0 8px 16px; border-left: 2px dashed $color-border; margin-left: 4px; &:last-child { padding-bottom: 0; } .at-time { font-size: 11px; color: $color-text-tertiary; font-family: $font-family-mono; margin-bottom: 2px; } .at-text { font-size: 12.5px; line-height: 1.5; color: $color-text-primary; strong { color: $color-text-primary; } } }

// 反馈条
.ai-feedback-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #F8FAFC; border-top: 1px solid $color-border; font-size: 12.5px; color: $color-text-secondary; }
.fb-actions { display: flex; align-items: center; gap: 12px; }
.ai-feedback { display: flex; gap: 6px; button { width: 32px; height: 32px; border-radius: 50%; background: #fff; border: 1px solid $color-border; font-size: 14px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; } &.up { background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); } } }
</style>
