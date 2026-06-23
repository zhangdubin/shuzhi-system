<script setup lang="ts">
/**
 * AiAsk · AI 智能问答（真实接通版）
 * - 发送：POST /api/v1/ai/ask/ask（多轮续 conversationId）
 * - 推荐：POST /api/v1/ai/ask/suggestions
 * - 反馈：POST /api/v1/ai/ask/feedback
 * - 历史：从 ai_tasks 取本用户 ask 类历史 + localStorage 缓存
 * - 渲染：data.rows（动态表格） / chart（ECharts） / sources / meta
 */
import { ref, nextTick, onMounted, computed, h, defineComponent, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { aiApi } from '@/api/ai'
import dayjs from 'dayjs'

use([CanvasRenderer, BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const route = useRoute()
const router = useRouter()

// ============================================================
// 状态
// ============================================================
type Message = {
  id: string
  role: 'user' | 'ai'
  type: 'text' | 'data' | 'chart' | 'doc' | 'draft'
  text: string
  rows?: any[]
  chart?: any
  sources?: any[]
  meta?: { model: string; durationMs: number; tokensUsed: number; costCents: number }
  messageId?: string
  time: string
  pending?: boolean
  error?: boolean
}

type Session = {
  id: string                  // session 前端 id
  conversationId: string      // 后端会话 id（首问后才会有）
  title: string
  preview: string
  updatedAt: number
  messages: Message[]
}

const STORAGE_KEY = 'shuzhi_ai_ask_sessions_v2'
const ACTIVE_KEY = 'shuzhi_ai_ask_active_v2'

const sessions = ref<Session[]>([])
const activeId = ref<string>('')
const askText = ref('')
const chatBox = ref<HTMLElement | null>(null)
const isThinking = ref(false)

// 快捷问题（先用本地兜底，onMounted 用后端建议覆盖）
const quickQuestions = ref<string[]>([
  '💰 本月哪些回款逾期？',
  '📊 销售费用花了多少？',
  '📁 在建项目有哪些？',
  '📄 合同总数',
  '👥 客户列表',
])

// ============================================================
// 持久化
// ============================================================
function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) sessions.value = JSON.parse(raw) || []
  } catch {}
  if (!sessions.value.length) {
    createNewSession('新对话', false)
  }
  const savedActive = localStorage.getItem(ACTIVE_KEY) || ''
  const exists = sessions.value.find((s) => s.id === savedActive)
  activeId.value = exists ? savedActive : sessions.value[0].id
}
function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value))
    localStorage.setItem(ACTIVE_KEY, activeId.value)
  } catch {}
}
const currentSession = computed<Session | undefined>(() =>
  sessions.value.find((s) => s.id === activeId.value)
)

// ============================================================
// 会话操作
// ============================================================
function newId() {
  return 's_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}
function nowStr() {
  return dayjs().format('HH:mm')
}
function shortTime(ts: number) {
  const d = dayjs(ts)
  const now = dayjs()
  if (d.isSame(now, 'day')) return d.format('HH:mm')
  if (d.isSame(now.subtract(1, 'day'), 'day')) return '昨天'
  if (d.isSame(now, 'year')) return d.format('M/D')
  return d.format('YYYY/M/D')
}

function createNewSession(title = '新对话', switchTo = true) {
  const s: Session = {
    id: newId(),
    conversationId: '',
    title,
    preview: '',
    updatedAt: Date.now(),
    messages: [
      {
        id: newId(),
        role: 'ai',
        type: 'text',
        text: '你好，我是 AI 助手 ✦\n\n可以问我：\n- 本月哪些回款逾期？\n- 销售费用花了多少？\n- 在建项目有哪些？\n\nAI 回答仅供参考，请人工核对关键数据。',
        time: nowStr(),
      },
    ],
  }
  sessions.value.unshift(s)
  if (switchTo) {
    activeId.value = s.id
    ElMessage.success('已新建会话')
  }
  persist()
  return s
}

function switchSession(id: string) {
  if (id === activeId.value) return
  activeId.value = id
  persist()
}

function deleteSession(id: string, evt?: Event) {
  evt?.stopPropagation()
  if (!confirm('删除该会话？')) return
  const idx = sessions.value.findIndex((s) => s.id === id)
  if (idx < 0) return
  sessions.value.splice(idx, 1)
  if (!sessions.value.length) {
    createNewSession('新对话', false)
  }
  if (activeId.value === id) {
    activeId.value = sessions.value[0].id
  }
  persist()
}

function clearAll() {
  if (!confirm('清空所有历史会话？')) return
  localStorage.removeItem(STORAGE_KEY)
  sessions.value = []
  createNewSession('新对话', false)
  activeId.value = sessions.value[0].id
  persist()
  ElMessage.success('已清空历史会话')
}

// ============================================================
// 发送
// ============================================================
async function send(text?: string) {
  const content = (text ?? askText.value).trim()
  if (!content || isThinking.value) return
  const s = currentSession.value || createNewSession('新对话', true)

  // 1. 入栈用户消息
  const userMsg: Message = {
    id: newId(),
    role: 'user',
    type: 'text',
    text: content,
    time: nowStr(),
  }
  s.messages.push(userMsg)
  s.preview = content.length > 30 ? content.slice(0, 30) + '…' : content
  // 首问设标题
  const userMsgCount = s.messages.filter((m) => m.role === 'user').length
  if (userMsgCount === 1) s.title = content.length > 18 ? content.slice(0, 18) + '…' : content
  s.updatedAt = Date.now()

  // 2. AI 思考占位
  const aiMsg: Message = {
    id: newId(),
    role: 'ai',
    type: 'text',
    text: '正在分析中…',
    time: nowStr(),
    pending: true,
  }
  s.messages.push(aiMsg)
  askText.value = ''
  isThinking.value = true
  await scroll()

  // 3. 真实请求
  try {
    const resp = await aiApi.ask({
      question: content,
      context: {
        currentPage: route.fullPath,
        conversationId: s.conversationId || undefined,
      },
      options: { stream: false, returnChart: true, maxSources: 5 },
    })
    // 续上 conversationId
    s.conversationId = resp.conversationId || s.conversationId
    // 回填 AI 消息
    Object.assign(aiMsg, {
      type: resp.answerType || 'text',
      text: resp.answer || '',
      rows: resp.data?.rows,
      chart: resp.chart,
      sources: resp.sources,
      meta: resp.meta,
      messageId: resp.messageId,
      pending: false,
    })
  } catch (e: any) {
    aiMsg.text = `❌ 调用失败：${e?.message || '未知错误'}`
    aiMsg.error = true
    aiMsg.pending = false
    ElMessage.error(aiMsg.text)
  } finally {
    s.updatedAt = Date.now()
    isThinking.value = false
    persist()
    await scroll()
  }
}

async function loadSuggestions() {
  try {
    const resp = await aiApi.askSuggestions({ page: 'dashboard', limit: 7 })
    if (resp?.suggestions?.length) {
      quickQuestions.value = resp.suggestions.map((s) => `${s.icon || '✨'} ${s.text}`)
    }
  } catch {
    /* 静默 */
  }
}

async function feedback(m: Message, rating: 'up' | 'down') {
  if (!m?.messageId) {
    ElMessage.warning('该消息没有可反馈的 ID')
    return
  }
  try {
    const { http } = await import('@/utils/request')
    await http.post('/ai/ask/feedback', { messageId: m.messageId, rating })
    ElMessage.success(rating === 'up' ? '👍 已记录：有用' : '👎 已记录：不满意')
  } catch (e: any) {
    ElMessage.error(e?.message || '反馈失败')
  }
}

async function regenerate(prevUserMsg: Message | undefined) {
  if (!prevUserMsg || isThinking.value) return
  // 直接用上一次问题重发（不重复入栈 user）
  const content = prevUserMsg.text
  const s = currentSession.value
  if (!s) return
  // 找到当前最后一条 ai 消息（pending 或已完成的）并标记 pending
  const last = s.messages[s.messages.length - 1]
  if (last?.role !== 'ai') return
  last.pending = true
  last.text = '正在重新生成…'
  isThinking.value = true
  await scroll()
  try {
    const resp = await aiApi.ask({
      question: content,
      context: { currentPage: route.fullPath, conversationId: s.conversationId || undefined },
      options: { stream: false, returnChart: true, maxSources: 5 },
    })
    s.conversationId = resp.conversationId || s.conversationId
    Object.assign(last, {
      type: resp.answerType || 'text',
      text: resp.answer || '',
      rows: resp.data?.rows,
      chart: resp.chart,
      sources: resp.sources,
      meta: resp.meta,
      messageId: resp.messageId,
      pending: false,
    })
  } catch (e: any) {
    last.text = `❌ 重新生成失败：${e?.message || '未知错误'}`
    last.error = true
    last.pending = false
    ElMessage.error(last.text)
  } finally {
    isThinking.value = false
    persist()
    await scroll()
  }
}

async function scroll() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

// ============================================================
// 子渲染器（4 个）
// ============================================================
const Markdown = defineComponent({
  name: 'Markdown',
  props: { source: { type: String, default: '' } },
  setup(props) {
    return () => {
      const lines = (props.source || '').split('\n')
      const nodes: any[] = []
      lines.forEach((line, idx) => {
        const parts: any[] = []
        const regex = /\*\*(.+?)\*\*/g
        let last = 0
        let m
        while ((m = regex.exec(line)) !== null) {
          if (m.index > last) parts.push(line.slice(last, m.index))
          parts.push(h('strong', null, m[1]))
          last = m.index + m[0].length
        }
        if (last < line.length) parts.push(line.slice(last))
        nodes.push(h('div', { key: idx, style: { minHeight: '1.2em' } }, parts.length ? parts : ['\u00a0']))
      })
      return h('div', { class: 'md' }, nodes)
    }
  },
})

const DynamicTable = defineComponent({
  name: 'DynamicTable',
  props: { rows: { type: Array, default: () => [] } },
  setup(props: any) {
    const rows = computed(() => (props.rows || []) as any[])
    const columns = computed(() => {
      if (!rows.value.length) return [] as string[]
      const set = new Set<string>()
      rows.value.forEach((r) => Object.keys(r || {}).forEach((k) => set.add(k)))
      return Array.from(set)
    })
    const fmtVal = (v: any) => {
      if (v === null || v === undefined) return '—'
      if (typeof v === 'number') return v.toLocaleString()
      if (typeof v === 'boolean') return v ? '是' : '否'
      return String(v)
    }
    return () => {
      if (!rows.value.length) {
        return h('div', { class: 'msg-data empty' }, '📊 暂无数据')
      }
      return h('div', { class: 'msg-data' }, [
        h('div', { class: 'md-head' }, `📊 ${rows.value.length} 条数据`),
        h('table', null, [
          h('thead', null, [h('tr', null, columns.value.map((c) => h('th', null, c)))]),
          h(
            'tbody',
            null,
            rows.value.map((r, i) =>
              h('tr', { key: i }, columns.value.map((c) => h('td', null, fmtVal(r[c]))))
            )
          ),
        ]),
      ])
    }
  },
})

const ChartView = defineComponent({
  name: 'ChartView',
  props: { chart: { type: Object, default: null } },
  setup(props: any) {
    const option = computed(() => {
      const c = props.chart
      if (!c) return null
      if (c.config) return c.config
      return c
    })
    return () =>
      option.value
        ? h(VChart, { option: option.value, style: 'height: 240px; width: 100%;', autoresize: true })
        : null
  },
})

const Sources = defineComponent({
  name: 'Sources',
  props: { sources: { type: Array, default: () => [] } },
  setup(props: any) {
    return () =>
      h(
        'div',
        { class: 'msg-sources' },
        (props.sources || []).map((s: any, i: number) =>
          h(
            'a',
            {
              key: i,
              class: 'src-pill',
              href: s.url || '#',
              target: '_blank',
              rel: 'noopener',
              title: s.snippet || s.title,
            },
            `🔗 ${s.title || s.id || '来源'}`
          )
        )
      )
  },
})

const MarkdownC = Markdown
const DynamicTableC = DynamicTable
const ChartViewC = ChartView
const SourcesC = Sources

// ============================================================
// 工具
// ============================================================
function copyText(m: Message) {
  navigator.clipboard.writeText(m.text || '').then(
    () => ElMessage.success('已复制'),
    () => ElMessage.error('复制失败')
  )
}

// 监听路由 ?q=
watch(
  () => route.query.q,
  (q) => {
    if (typeof q === 'string' && q.trim()) {
      setTimeout(() => send(q), 200)
    }
  }
)

onMounted(() => {
  loadFromStorage()
  loadSuggestions()
})
</script>

<template>
  <div class="page ai-ask">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/dashboard')">首页</a>
          <span class="sep">/</span>
          <a @click="router.push('/ai/center')">数智（AI）</a>
          <span class="sep">/</span>
          <span class="current">智能问答</span>
        </div>
        <h1 class="ai-ask-title">💬 智能问答</h1>
        <p class="page-desc">自然语言问数据，让 AI 帮你查、答、想</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/ai/center')">← 返回</button>
        <button class="btn btn-primary btn-sm" data-test="new-session-top" @click="createNewSession()">+ 新建会话</button>
      </div>
    </div>

    <div class="ask-layout">
      <!-- 左：会话列表（来自 localStorage 真实历史） -->
      <div class="session-list">
        <div class="sl-head">
          <h4>历史会话 <span class="sl-count">{{ sessions.length }}</span></h4>
          <button class="btn-new-session" data-test="new-session" title="新建会话" @click="createNewSession()">
            <span class="bns-icon">+</span>
            <span class="bns-text">新建会话</span>
          </button>
        </div>
        <div class="sl-body">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['sl-item', { active: s.id === activeId }]"
            @click="switchSession(s.id)"
          >
            <div class="sli-icon">💬</div>
            <div class="sli-body">
              <div class="sli-title">{{ s.title || '新对话' }}</div>
              <div class="sli-preview">{{ s.preview || '（暂无内容）' }}</div>
              <div class="sli-time">{{ shortTime(s.updatedAt) }}</div>
            </div>
            <button class="sli-del" title="删除" @click="deleteSession(s.id, $event)">×</button>
          </div>
          <div v-if="!sessions.length" class="sl-empty">暂无历史会话</div>
          <button v-else class="sl-clear-all" @click="clearAll">清空历史会话</button>
        </div>
      </div>

      <!-- 右：聊天区 -->
      <div class="chat-area">
        <div class="chat-box" ref="chatBox">
          <template v-for="(m, i) in currentSession?.messages" :key="m.id">
            <div :class="['msg', m.role]">
              <div class="msg-avatar">{{ m.role === 'user' ? '我' : '✦' }}</div>
              <div class="msg-body">
                <div class="msg-meta">
                  <span class="msg-name">{{ m.role === 'user' ? '我' : 'AI 助手' }}</span>
                  <span class="msg-time">{{ m.time }}</span>
                  <span v-if="m.meta?.model" class="msg-tag">· {{ m.meta.model }} · {{ m.meta.durationMs }}ms</span>
                </div>

                <div v-if="m.pending" class="msg-text">
                  <span class="dots"><span></span><span></span><span></span></span>
                  {{ m.text }}
                </div>
                <template v-else>
                  <component v-if="m.type === 'text' || m.text" :is="MarkdownC" class="msg-text" :source="m.text" />
                  <component
                    v-if="m.type === 'data' && m.rows && m.rows.length"
                    :is="DynamicTableC"
                    :rows="m.rows"
                  />
                  <component v-if="m.chart" :is="ChartViewC" :chart="m.chart" />
                  <component v-if="m.sources && m.sources.length" :is="SourcesC" :sources="m.sources" />
                </template>

                <div v-if="m.role === 'ai' && !m.pending && m.messageId" class="msg-actions">
                  <button @click="copyText(m)">📋 复制</button>
                  <button @click="feedback(m, 'up')">👍 有用</button>
                  <button @click="feedback(m, 'down')">👎 不准</button>
                  <button @click="regenerate(currentSession?.messages[i - 1])">🔄 重新生成</button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <div class="ask-input-box">
          <div class="quick-q ai-ask-suggestions">
            <span
              v-for="(q, i) in quickQuestions"
              :key="i"
              class="qq suggestion"
              @click="send(q)"
            >{{ q }}</span>
          </div>
          <div class="input-row ai-ask-input">
            <span class="icon">✦</span>
            <textarea
              v-model="askText"
              rows="1"
              placeholder="试试：'本月哪些项目回款逾期了？'（回车发送，Shift+回车换行）"
              :disabled="isThinking"
              @keydown.enter.exact.prevent="send()"
            ></textarea>
            <button class="btn-send" :disabled="isThinking || !askText.trim()" @click="send()">
              {{ isThinking ? '思考中…' : '发送' }}
            </button>
          </div>
          <div class="input-hint">AI 回答仅供参考，请人工核对关键数据后再做决策</div>
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
$color-ai-bg: rgba(124, 58, 237, 0.08);
$color-ai-border: rgba(124, 58, 237, 0.25);

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-actions { display: flex; gap: 8px; }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-ai; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } }
.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-ai-bg; color: $color-ai; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// 双栏
.ask-layout { display: grid; grid-template-columns: 260px 1fr; gap: 16px; min-height: calc(100vh - 200px); @media (max-width: 900px) { grid-template-columns: 1fr; } }

// 左：会话列表
.session-list { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; display: flex; flex-direction: column; max-height: calc(100vh - 200px); }

// 头部：左边标题 + 计数 chip，右边两个圆形 icon 按钮
.sl-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 14px 12px; border-bottom: 1px dashed $color-border; background: #fff; h4 { font-size: 13px; font-weight: 600; margin: 0; color: $color-text-primary; display: flex; align-items: center; gap: 6px; } }
.sl-head h4::before { content: ''; width: 3px; height: 12px; background: $gradient-ai; border-radius: 2px; }
.sl-count { color: #fff; background: $gradient-ai; font-weight: 500; font-size: 10.5px; padding: 1px 7px; border-radius: 9999px; }
.btn-new-session { display: inline-flex; align-items: center; gap: 4px; height: 28px; padding: 0 10px; border-radius: 9999px; background: $gradient-ai; color: #fff; border: none; font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit; transition: all 0.15s; box-shadow: 0 1px 2px rgba(124, 58, 237, 0.15); &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35); transform: translateY(-1px); } &:active { transform: translateY(0); } .bns-icon { font-size: 14px; font-weight: 600; line-height: 1; } }

// 列表
.sl-body { padding: 8px; overflow-y: auto; flex: 1; }
.sl-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 10px 10px 12px; border-radius: 10px; cursor: pointer; transition: all 0.15s; margin-bottom: 4px; position: relative; border: 1px solid transparent; &:hover { background: #F8F9FF; border-color: rgba(124, 58, 237, 0.15); } &.active { background: linear-gradient(135deg, rgba(79, 107, 255, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%); border-color: rgba(124, 58, 237, 0.25); } &.active .sli-icon { background: $gradient-ai; color: #fff; } &:hover .sli-del { opacity: 1; } }
.sli-icon { width: 24px; height: 24px; border-radius: 7px; background: $color-ai-bg; color: $color-ai; font-size: 12px; flex-shrink: 0; display: grid; place-items: center; margin-top: 2px; transition: all 0.15s; }
.sli-body { flex: 1; min-width: 0; padding-right: 18px; .sli-title { font-size: 12.5px; color: $color-text-primary; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.4; } .sli-preview { font-size: 11.5px; color: $color-text-tertiary; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.4; } .sli-time { font-size: 10.5px; color: $color-text-tertiary; margin-top: 4px; display: inline-flex; align-items: center; gap: 3px; } .sli-time::before { content: ''; width: 4px; height: 4px; border-radius: 50%; background: $color-text-tertiary; opacity: 0.6; } }
.sli-del { position: absolute; right: 6px; top: 8px; width: 18px; height: 18px; border-radius: 50%; background: transparent; border: none; color: $color-text-tertiary; font-size: 14px; line-height: 1; cursor: pointer; opacity: 0; transition: all 0.15s; display: grid; place-items: center; &:hover { background: $color-danger; color: #fff; opacity: 1; } }
.sl-empty { text-align: center; font-size: 12px; color: $color-text-tertiary; padding: 24px 0; }
.sl-clear-all { display: block; width: calc(100% - 16px); margin: 6px 8px 4px; padding: 6px 0; background: transparent; border: none; font-size: 11.5px; color: $color-text-tertiary; cursor: pointer; border-radius: 6px; font-family: inherit; &:hover { color: $color-danger; background: $color-danger-bg; } }

// 右：聊天区
.chat-area { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; display: flex; flex-direction: column; min-width: 0; }
.chat-box { flex: 1; padding: 20px 24px; overflow-y: auto; max-height: calc(100vh - 320px); min-height: 400px; }
.msg { display: flex; gap: 12px; margin-bottom: 18px; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.msg.user .msg-avatar { background: $color-primary-bg; color: $color-primary; }
.msg.ai .msg-avatar { background: $gradient-ai; color: #fff; font-size: 14px; }
.msg-body { max-width: 80%; min-width: 0; }
.msg.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
.msg-meta { display: flex; gap: 8px; font-size: 11px; color: $color-text-tertiary; margin-bottom: 4px; align-items: center; flex-wrap: wrap; .msg-name { font-weight: 500; color: $color-text-secondary; } .msg-time { font-family: $font-family-mono; } .msg-tag { background: $color-ai-bg; color: $color-ai; padding: 1px 6px; border-radius: 9999px; font-size: 10.5px; } }
.msg-text { display: block; background: $color-bg; padding: 10px 14px; border-radius: $radius-md; font-size: 13px; line-height: 1.7; color: $color-text-primary; white-space: pre-wrap; word-break: break-word; }
.msg.user .msg-text { background: $gradient-ai; color: #fff; }
.msg-text :deep(strong) { color: $color-ai; font-weight: 600; }
.msg.user .msg-text :deep(strong) { color: #FFE082; }
.msg-text .dots { display: inline-flex; gap: 3px; margin-right: 6px; }
.msg-text .dots span { width: 5px; height: 5px; background: $color-ai; border-radius: 50%; animation: bounce 1.4s infinite; }
.msg-text .dots span:nth-child(2) { animation-delay: 0.2s; }
.msg-text .dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

.msg-data { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 10px 12px; margin-top: 6px; }
.msg-data.empty { color: $color-text-tertiary; font-size: 12px; text-align: center; }
.md-head { font-size: 12px; color: $color-text-tertiary; margin-bottom: 6px; font-weight: 500; }
.msg-data table { width: 100%; border-collapse: collapse; font-size: 12px; }
.msg-data th { text-align: left; padding: 6px 8px; background: $color-bg; color: $color-text-tertiary; font-weight: 500; }
.msg-data td { padding: 6px 8px; border-bottom: 1px solid $color-border; }
.msg-data .mono { font-family: $font-family-mono; color: $color-text-secondary; }
.tag { font-size: 10.5px; padding: 1px 6px; border-radius: 9999px; }
.tag.danger { background: $color-danger-bg; color: $color-danger; }
.tag.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.tag.info { background: rgba(148, 163, 184, 0.15); color: #64748B; }

.msg-sources { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.src-pill { font-size: 11.5px; padding: 2px 8px; background: $color-ai-bg; color: $color-ai; border-radius: 9999px; text-decoration: none; &:hover { background: $color-ai; color: #fff; } }

.msg-actions { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.msg-actions button { font-size: 11px; padding: 3px 8px; background: transparent; border: 1px solid $color-border; color: $color-text-tertiary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }

// ask input
.ask-input-box { border-top: 1px solid $color-border; padding: 14px 20px; background: #FAFBFF; }
.quick-q { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.qq { font-size: 11.5px; color: $color-text-secondary; padding: 3px 10px; background: #fff; border: 1px solid $color-border; border-radius: 9999px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }
.input-row { display: flex; align-items: center; gap: 10px; background: #fff; border: 1.5px solid $color-ai-border; border-radius: $radius-md; padding: 8px 12px; transition: all 0.2s; &:focus-within { border-color: $color-ai; box-shadow: 0 0 0 3px $color-ai-bg; } .icon { font-size: 16px; color: $color-ai; } input, textarea { flex: 1; border: none; outline: none; font-size: 13.5px; background: transparent; font-family: inherit; resize: none; line-height: 1.5; max-height: 100px; } input::placeholder, textarea::placeholder { color: $color-text-tertiary; } }
.btn-send { background: $gradient-ai; color: #fff; border: none; border-radius: $radius-sm; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit; &:disabled { opacity: 0.5; cursor: not-allowed; } }
.input-hint { font-size: 11px; color: $color-text-tertiary; margin-top: 6px; text-align: center; }
</style>
