<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const stats = ref<any>({})
const kpiList = ref<any[]>([])
const trendChart = ref<any>({ labels: [], series: [] })
const todos = ref<any[]>([])
const teamMembers = ref<any[]>([])

// 静态团队/活动（design 风格）
const recentActivities = ref([
  { icon: '▤', color: '#E0E6FF', iconColor: '#4F6BFF', title: '王芳 上传了 <strong>3 张发票</strong>，OCR 自动识别完成', meta: '10 分钟前 · 发票识别', module: 'invoice' },
  { icon: '▦', color: '#FEF3C7', iconColor: '#B45309', title: '李明 创建了合同 <strong>HT-2026-031</strong>，待法务审批', meta: '32 分钟前 · 合同管理', module: 'contract' },
  { icon: '✓', color: '#D1FAE5', iconColor: '#047857', title: '系统自动回款到账 <strong>¥ 86,500.00</strong>', meta: '1 小时前 · 回款管理', module: 'receivable' },
  { icon: '▥', color: '#FAE8FF', iconColor: '#86198F', title: '项目 <strong>「数智化二期」</strong> 进度更新至 68%', meta: '2 小时前 · 项目管理', module: 'project' },
  { icon: '▣', color: '#CFFAFE', iconColor: '#0E7490', title: '张明 新建了 <strong>「差旅报销」</strong> 发票模板', meta: '3 小时前 · 发票模板', module: 'template' },
])
const staticTeam = [
  { name: '张明', role: '财务总监', avatar: 'https://i.pravatar.cc/64?img=15', online: true },
  { name: '王芳', role: '财务专员', avatar: 'https://i.pravatar.cc/64?img=23', online: true },
  { name: '李明', role: '法务主管', avatar: 'https://i.pravatar.cc/64?img=33', online: true },
  { name: '陈思琪', role: '项目经理', avatar: 'https://i.pravatar.cc/64?img=12', online: true },
  { name: '刘洋', role: '销售经理', avatar: 'https://i.pravatar.cc/64?img=45', online: false },
]

// 6 大模块入口
const moduleRoutes = ref<Array<{ name: string; path: string; icon: string; gradient: string; bg: string; color: string }>>([
  { name: '发票识别', path: '/invoice/ocr',     icon: '▤', gradient: 'linear-gradient(135deg,#4F6BFF,#7C3AED)', bg: 'rgba(79,107,255,0.10)', color: '#4F6BFF' },
  { name: '发票模板', path: '/invoice/template', icon: '▣', gradient: 'linear-gradient(135deg,#06B6D4,#0891B2)', bg: 'rgba(6,182,212,0.10)',  color: '#06B6D4' },
  { name: '销售费用', path: '/expense/list',    icon: '◈', gradient: 'linear-gradient(135deg,#10B981,#059669)', bg: 'rgba(16,185,129,0.10)', color: '#10B981' },
  { name: '项目管理', path: '/project/list',    icon: '▥', gradient: 'linear-gradient(135deg,#F59E0B,#D97706)', bg: 'rgba(245,158,11,0.10)', color: '#F59E0B' },
  { name: '合同管理', path: '/contract/list',   icon: '▦', gradient: 'linear-gradient(135deg,#EC4899,#BE185D)', bg: 'rgba(236,72,153,0.10)', color: '#EC4899' },
  { name: '回款管理', path: '/receivable/list', icon: '▩', gradient: 'linear-gradient(135deg,#8B5CF6,#6D28D9)', bg: 'rgba(139,92,246,0.10)', color: '#8B5CF6' },
])

// 欢迎条
const greetingText = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const todayStr = computed(() => {
  const d = new Date()
  const w = ['日','一','二','三','四','五','六'][d.getDay()]
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日，星期${w}`
})

// 趋势图 tab
const trendTab = ref<'7d' | '30d' | 'qtr' | 'yr'>('7d')

async function loadStats() {
  const data: any = await dashboardApi.stats().catch(() => ({}))
  stats.value = data
  kpiList.value = data.kpi || []
  // 后端返 {name, color, data: number[]}，前端需要 points/dots（SVG 字符串）
  const tc = data.trendChart || { labels: [], series: [] }
  const labels = tc.labels || []
  if (labels.length && tc.series?.length) {
    const w = 740
    const h = 180
    const allVals = tc.series.flatMap((s: any) => s.data || [])
    const maxV = Math.max(...allVals, 1) * 1.1
    const minV = 0
    const stepX = labels.length > 1 ? w / (labels.length - 1) : 0
    tc.series = tc.series.map((s: any) => {
      const data = s.data || []
      const dots = data.map((v: number, i: number) => ({
        x: 40 + i * stepX,
        y: 20 + h - ((v - minV) / (maxV - minV)) * h,
      }))
      const points = dots.map((d: any) => `${d.x},${d.y}`).join(' ')
      return { ...s, points, dots }
    })
  }
  trendChart.value = tc
  todos.value = data.todos || []
  teamMembers.value = data.teamMembers || []
}

function fmtKpi(v: number, unit: string) {
  if (unit === '元') {
    if (v >= 10000) return (v / 10000).toFixed(1) + ' 万'
    return v.toLocaleString()
  }
  return v.toLocaleString() + ' ' + (unit || '')
}

function deltaTypeColor(t?: string) {
  if (t === 'up') return 'var(--color-success)'
  if (t === 'down') return 'var(--color-danger)'
  return 'var(--color-text-tertiary)'
}

function gotoModule(p: string) { router.push(p) }
function gotoActivity(mod: string) {
  const map: any = { invoice: '/invoice/ocr', contract: '/contract/list', receivable: '/receivable/list', project: '/project/list', template: '/invoice/template' }
  if (map[mod]) router.push(map[mod])
}

onMounted(loadStats)
</script>

<template>
  <div class="dashboard">
    <!-- 欢迎条 -->
    <div class="welcome fade-up">
      <div class="welcome-text">
        <h2>{{ greetingText }}，{{ userStore.userInfo?.name || '管理员' }} 👋</h2>
        <p>今天是 {{ todayStr }}，距离本季度结算还有 <strong>{{ stats.quarterRemainingDays || 19 }} 天</strong>。</p>
      </div>
      <div class="welcome-actions">
        <button class="welcome-btn">📅 今日待办</button>
        <button class="welcome-btn primary">+ 快速新建</button>
      </div>
    </div>

    <!-- 6 大模块入口（design 风格） -->
    <div class="modules-grid fade-up">
      <div
        v-for="m in moduleRoutes"
        :key="m.path"
        class="module-card"
        @click="gotoModule(m.path)"
      >
        <div class="m-icon" :style="{ background: m.gradient }">{{ m.icon }}</div>
        <div class="m-name">{{ m.name }}</div>
        <div class="m-stat" v-if="stats.moduleStats">
          <span class="num" v-for="(s, i) in [stats.moduleStats.find((x: any) => x.name === m.name)]" :key="i">
            <template v-if="s">
              {{ s.value }}<span style="font-size:11px;color:#94A3B8;margin-left:2px;">{{ s.unit }}</span>
            </template>
            <template v-else>—</template>
          </span>
        </div>
      </div>
    </div>

    <!-- 4 KPI 卡 -->
    <div class="stats-grid fade-up">
      <div v-for="k in kpiList" :key="k.key" class="stat-card">
        <div class="stat-label">
          {{ k.label }}
          <span class="stat-icon" :style="{
            background: k.key === 'monthRevenue' ? 'rgba(16,185,129,0.12)' :
                         k.key === 'pendingReceivable' ? 'rgba(245,158,11,0.12)' :
                         k.key === 'activeProjects' ? 'rgba(79,107,255,0.12)' :
                         'rgba(239,68,68,0.12)',
            color: k.key === 'monthRevenue' ? '#10B981' :
                   k.key === 'pendingReceivable' ? '#F59E0B' :
                   k.key === 'activeProjects' ? '#4F6BFF' :
                   '#EF4444'
          }">
            {{ k.key === 'monthRevenue' ? '¥' : k.key === 'pendingReceivable' ? '⏱' : k.key === 'activeProjects' ? '▥' : '!' }}
          </span>
        </div>
        <div class="stat-value">
          <span v-if="k.key === 'monthRevenue' || k.key === 'pendingReceivable'">¥ </span>{{ fmtKpi(k.value, k.unit) }}
        </div>
        <div class="stat-delta" v-if="k.delta != null || k.extra">
          <template v-if="k.delta != null">
            较上月
            <span :style="{ color: deltaTypeColor(k.deltaType), fontWeight: 600 }">
              {{ k.deltaType === 'up' ? '↑' : k.deltaType === 'down' ? '↓' : '→' }} {{ Math.abs(k.delta) }}{{ k.key === 'activeProjects' || k.key === 'invoicePending' ? '' : '%' }}
            </span>
          </template>
          <template v-else>{{ k.extra }}</template>
        </div>
      </div>
    </div>

    <!-- 双栏：趋势图 + 待办 -->
    <div class="main-grid">
      <div class="page-card">
        <div class="card-head">
          <h3>收支趋势</h3>
          <div class="chart-tabs">
            <a :class="{ active: trendTab === '7d' }" @click="trendTab = '7d'">7 天</a>
            <a :class="{ active: trendTab === '30d' }" @click="trendTab = '30d'">30 天</a>
            <a :class="{ active: trendTab === 'qtr' }" @click="trendTab = 'qtr'">本季度</a>
            <a :class="{ active: trendTab === 'yr' }" @click="trendTab = 'yr'">本年度</a>
          </div>
        </div>
        <div style="padding: 16px 22px 22px;">
          <svg viewBox="0 0 800 220" class="trend-svg" v-if="trendChart.labels && trendChart.labels.length">
            <line v-for="(y, i) in [200, 150, 100, 50]" :key="i" x1="40" :y1="y" x2="780" :y2="y" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="3 3" />
            <polyline
              v-for="(s, i) in trendChart.series" :key="`l-${i}`"
              :points="s.points" fill="none" :stroke="s.color" stroke-width="2.5"
            />
            <template v-for="(s, si) in trendChart.series" :key="`s-${si}`">
              <circle
                v-for="(p, pi) in s.dots" :key="`d-${si}-${pi}`"
                :cx="p.x" :cy="p.y" r="3.5" :fill="s.color" stroke="#fff" stroke-width="1.5"
              />
            </template>
            <text v-for="(l, i) in trendChart.labels" :key="'x'+i"
                  :x="40 + i * (740 / (trendChart.labels.length - 1))"
                  y="215" text-anchor="middle" font-size="11" fill="#94A3B8">
              {{ l }}
            </text>
          </svg>
          <el-empty v-else description="暂无趋势数据" :image-size="80" />
          <div class="trend-legend" v-if="trendChart.series && trendChart.series.length">
            <span v-for="(s, i) in trendChart.series" :key="'lg'+i" class="legend-item">
              <span class="dot" :style="{ background: s.color }"></span>
              {{ s.name }}
            </span>
          </div>
        </div>
      </div>

      <div class="page-card">
        <div class="card-head">
          <h3>待办事项</h3>
          <a href="javascript:;" class="link-all">查看全部 →</a>
        </div>
        <div style="padding: 8px 22px 18px;">
          <div v-for="(t, i) in todos" :key="i" :class="['todo-item', t.type]">
            <span :class="['todo-dot', t.type]"></span>
            <div class="todo-body">
              <div class="t">{{ t.title }}</div>
              <div class="m">{{ t.meta }}</div>
            </div>
          </div>
          <el-empty v-if="!todos.length" description="暂无待办" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- 双栏：最近活动 + 团队成员 -->
    <div class="main-grid">
      <div class="page-card">
        <div class="card-head">
          <h3>最近活动</h3>
          <a href="javascript:;" class="link-all">全部 →</a>
        </div>
        <div style="padding: 4px 22px 16px;">
          <div
            v-for="(a, i) in recentActivities"
            :key="i"
            class="timeline-item"
            @click="gotoActivity(a.module)"
          >
            <div class="timeline-dot" :style="{ background: a.color, color: a.iconColor }">{{ a.icon }}</div>
            <div class="timeline-body">
              <div class="t" v-html="a.title"></div>
              <div class="m">{{ a.meta }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="page-card">
        <div class="card-head">
          <h3>团队成员</h3>
          <span style="font-size:12px;color:var(--color-text-tertiary);">在线 {{ staticTeam.filter(t => t.online).length }} / 共 {{ staticTeam.length }}</span>
        </div>
        <div style="padding: 8px 22px 16px;">
          <div v-for="(m, i) in staticTeam" :key="i" class="team-item">
            <el-avatar :size="36" :src="m.avatar">{{ m.name.charAt(0) }}</el-avatar>
            <div class="t-info">
              <div class="name">{{ m.name }}</div>
              <div class="role">{{ m.role }}</div>
            </div>
            <div :class="['t-status', { offline: !m.online }]" :title="m.online ? '在线' : '离线'"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷入口（4 个）-->
    <div class="page-card fade-up">
      <h3 class="panel-title">快捷入口</h3>
      <div class="quick-grid">
        <router-link to="/invoice/ocr" class="quick-tile">
          <div class="quick-icon" style="background: linear-gradient(135deg, #4F6BFF, #7C3AED)">📷</div>
          <div class="quick-name">发票识别</div>
          <div class="quick-desc">上传发票图片，AI 智能识别字段</div>
        </router-link>
        <router-link to="/invoice/verify" class="quick-tile">
          <div class="quick-icon" style="background: linear-gradient(135deg, #10B981, #06B6D4)">✓</div>
          <div class="quick-name">发票查验</div>
          <div class="quick-desc">实时对接国税总局查验平台</div>
        </router-link>
        <router-link to="/ai/extract" class="quick-tile">
          <div class="quick-icon" style="background: linear-gradient(135deg, #F59E0B, #EF4444)">✨</div>
          <div class="quick-name">AI 抽取</div>
          <div class="quick-desc">从合同/邮件抽取关键数据</div>
        </router-link>
        <router-link to="/ai/panel/contract" class="quick-tile">
          <div class="quick-icon" style="background: linear-gradient(135deg, #8B5CF6, #EC4899)">🛡️</div>
          <div class="quick-name">AI 风控</div>
          <div class="quick-desc">合同/项目风险体检</div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }

// 欢迎条
.welcome {
  background: $gradient-brand;
  color: #fff;
  border-radius: $radius-lg;
  padding: 24px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 4px 12px rgba(79, 107, 255, 0.18);
  position: relative;
  overflow: hidden;
  &::after {
    content: '';
    position: absolute;
    right: -50px; top: -50px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }
  h2 { margin: 0 0 4px; font-size: 22px; font-weight: 600; }
  p { margin: 0; font-size: 13px; opacity: 0.85; }
  strong { color: #FDE68A; font-size: 16px; }
  &-actions { display: flex; gap: 8px; position: relative; z-index: 1; }
  &-btn {
    padding: 8px 16px;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    &:hover { background: rgba(255, 255, 255, 0.25); }
    &.primary {
      background: #fff;
      color: $color-primary;
      border-color: #fff;
      font-weight: 600;
      &:hover { background: #F8FAFC; }
    }
  }
}

// 6 大模块入口
.modules-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
  @media (max-width: 1280px) { grid-template-columns: repeat(3, 1fr); }
}
.module-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 20px 18px;
  cursor: pointer;
  transition: all 0.18s;
  position: relative;
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.06);
  }
  .m-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    color: #fff;
    display: grid; place-items: center;
    font-size: 20px;
    margin-bottom: 12px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
  .m-name { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  .m-stat { font-size: 12px; color: $color-text-tertiary; }
}

// 4 KPI
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  .stat-label {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; color: $color-text-tertiary; margin-bottom: 8px;
    .stat-icon {
      width: 28px; height: 28px; border-radius: 8px;
      display: grid; place-items: center; font-size: 13px; font-weight: 700;
    }
  }
  .stat-value {
    font-size: 24px; font-weight: 700; color: $color-text-primary;
    margin-bottom: 4px; font-family: $font-family-mono;
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; }
}

// 双栏
.main-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 14px;
  @media (max-width: 1024px) { grid-template-columns: 1fr; }
}

.page-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 22px;
}
.card-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
  h3 { margin: 0; font-size: 15px; font-weight: 600; color: $color-text-primary; }
  .link-all { font-size: 12px; color: $color-primary; cursor: pointer; }
}
.panel-title { margin: 0 0 14px; font-size: 15px; font-weight: 600; color: $color-text-primary; }

// 趋势图
.chart-tabs { display: flex; gap: 4px;
  a {
    padding: 4px 10px; font-size: 12px;
    color: $color-text-tertiary; border-radius: 4px;
    cursor: pointer; transition: all 0.15s;
    &:hover { background: $color-bg; }
    &.active { background: $color-primary-bg; color: $color-primary; font-weight: 500; }
  }
}
.trend-svg { width: 100%; height: 220px; display: block; }
.trend-legend { display: flex; gap: 16px; padding-top: 8px; font-size: 12px; color: $color-text-tertiary; }
.legend-item { display: flex; align-items: center; gap: 6px;
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
}

// 待办
.todo-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 0; border-bottom: 1px dashed $color-border;
  &:last-child { border-bottom: none; }
  .todo-dot {
    width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
    background: $color-primary;
    &.warning { background: $color-warning; }
    &.danger { background: $color-danger; }
  }
  .t { font-size: 13px; color: $color-text-primary; font-weight: 500; }
  .m { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; }
}

// 时间线
.timeline-item {
  display: flex; gap: 12px; padding: 10px 0;
  border-bottom: 1px dashed $color-border; cursor: pointer;
  &:last-child { border-bottom: none; }
  &:hover { background: $color-bg; margin: 0 -8px; padding: 10px 8px; border-radius: 6px; border-bottom-color: transparent; }
  .timeline-dot {
    width: 28px; height: 28px; border-radius: 8px;
    display: grid; place-items: center; font-size: 14px;
    flex-shrink: 0;
  }
  .t { font-size: 13px; color: $color-text-primary; }
  .m { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; }
}

// 团队
.team-item {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 0; border-bottom: 1px dashed $color-border;
  &:last-child { border-bottom: none; }
  .t-info { flex: 1; line-height: 1.3; .name { font-size: 13px; color: $color-text-primary; font-weight: 500; } .role { font-size: 11px; color: $color-text-tertiary; } }
  .t-status {
    width: 8px; height: 8px; border-radius: 50%; background: var(--color-success);
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
    &.offline { background: var(--color-text-tertiary); box-shadow: none; }
  }
}

// 快捷入口
.quick-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.quick-tile {
  display: flex; flex-direction: column; align-items: center;
  padding: 20px 16px;
  background: $color-bg;
  border-radius: $radius-md;
  text-decoration: none;
  transition: all 0.18s;
  &:hover { background: $color-primary-bg; transform: translateY(-2px); }
  .quick-icon {
    width: 44px; height: 44px; border-radius: 12px;
    color: #fff; display: grid; place-items: center;
    font-size: 20px; margin-bottom: 8px;
  }
  .quick-name { font-size: 13px; font-weight: 600; color: $color-text-primary; }
  .quick-desc { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; text-align: center; }
}

// 动画
.fade-up { animation: fadeUp 0.3s ease-out; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>
