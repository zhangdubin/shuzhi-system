<script setup lang="ts">
/**
 * AiAsk · AI 智能问答（无 design，按 ai-center ask-box + 聊天界面 pattern 自造）
 * - 左侧会话列表（4 个历史会话）
 * - 右侧聊天区：用户问 + AI 答（带 SQL 解释 / 数据可视化 / 引用）
 * - 底部 ask-input + 快捷问题
 */
import { ref, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const askText = ref('')
const messages = ref<any[]>([])
const chatBox = ref<HTMLElement | null>(null)
const isThinking = ref(false)

// 4 个历史会话
const sessions = ref([
  { id: 's1', title: '本月回款逾期分析', time: '14:23', active: true },
  { id: 's2', title: 'Q2 销售费用汇总',   time: '昨天',  active: false },
  { id: 's3', title: '项目 PRJ-018 健康度', time: '昨天',  active: false },
  { id: 's4', title: '本月合同到期清单',   time: '6/12',  active: false },
])

// 7 个示例问题
const quickQuestions = ref([
  '💰 本月开票金额',
  '⚠️ 风险项目',
  '📊 上周销售费用',
  '🔄 待回款客户',
  '📅 本月合同到期',
  '📈 Q2 营收趋势',
  '👥 客户分布',
])

// 初始化默认消息
const initMessages = () => {
  messages.value = [
    { role: 'user',  text: '本月哪些项目回款逾期了？',  time: '14:23' },
    { role: 'ai',    text: '已为您查询，本月共有 **3 个项目** 回款逾期，总金额 **¥ 286,500**：', time: '14:23' },
    { role: 'ai', type: 'data', items: [
      { project: 'PRJ-2026-018', client: '万象科技', amount: 128000, overdue: 5, status: '高' },
      { project: 'PRJ-2026-022', client: '云汇信息', amount: 96500,  overdue: 3, status: '中' },
      { project: 'PRJ-2026-031', client: '数智未来', amount: 62000,  overdue: 1, status: '低' },
    ]},
    { role: 'ai', type: 'sql', sql: 'SELECT project_code, client_name, amount, overdue_days\nFROM receivable_overdue\nWHERE status = \'overdue\'\nORDER BY overdue_days DESC' },
    { role: 'ai',    text: '建议：优先催办 PRJ-2026-018（逾期 5 天，金额最大）。我可以帮您起草催收通知吗？', time: '14:23' },
    { role: 'user',  text: '好的，起草催收通知',                  time: '14:25' },
    { role: 'ai',    text: '已为您生成催收通知草稿 ✨\n\n---\n\n**主题**：关于 PRJ-2026-018 项目尾款催收\n\n尊敬的万象科技有限公司：\n\n贵司与我司签订的 PRJ-2026-018《数智化平台开发合同》尾款 ¥128,000 已逾期 5 天。请贵司在 3 个工作日内完成支付。\n\n如有疑问请联系：财务部 张明 010-12345678', time: '14:25' },
  ]
}

async function send(text?: string) {
  const content = (text ?? askText.value).trim()
  if (!content) return
  messages.value.push({ role: 'user', text: content, time: now() })
  askText.value = ''
  isThinking.value = true
  await scroll()
  setTimeout(async () => {
    isThinking.value = false
    messages.value.push({ role: 'ai', text: aiAnswer(content), time: now() })
    await scroll()
  }, 1200)
}

function aiAnswer(q: string): string {
  if (q.includes('开票') || q.includes('金额')) {
    return '本月（截至 6/14）共开票 **¥ 1,248,500**，环比上月 +12.4%。其中 6 月第 2 周最高（¥ 412K）。'
  }
  if (q.includes('风险')) {
    return '当前识别到 **5 个高风险事项**：\n- 合同逾期 3 项（金额合计 ¥286.5K）\n- 发票税率异常 1 项\n- 项目超期 1 项\n\n建议优先处理合同催收。'
  }
  if (q.includes('回款') || q.includes('逾期')) {
    return '本月待回款客户共 **12 家**，已收 ¥1.42M，剩余 ¥0.95M。其中 3 家有逾期（合计 ¥286.5K），详见回款管理。'
  }
  if (q.includes('合同')) {
    return '本月合同到期 4 份：\n- HT-2026-028（6/30 到期，金额 ¥86K）\n- HT-2026-031（7/15 到期，金额 ¥42K）\n- HT-2026-019（7/20 到期，金额 ¥128K）\n- HT-2026-022（7/28 到期，金额 ¥65K）\n\n建议提前 30 天启动续签。'
  }
  return '已记录您的问题。AI 助手正在分析中...（demo 模式：可点击下方快捷问题体验）'
}

function now() {
  const d = new Date()
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

async function scroll() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

function selectSession(s: any) {
  sessions.value.forEach(x => x.active = x.id === s.id)
  initMessages()
  ElMessage.success(`切换到会话: ${s.title}`)
}

function newSession() { ElMessage.info('新建会话') }
function copyAnswer(m: any) { navigator.clipboard.writeText(m.text || ''); ElMessage.success('已复制') }
function useful(m: any) { ElMessage.success('已反馈：有用') }
function regenerate() { ElMessage.info('重新生成') }

onMounted(() => {
  // 接受路由 query ?q=
  const q = route.query.q as string
  if (q) { askText.value = q; send(q) } else { initMessages() }
  scroll()
})
</script>

<template>
  <div class="page-container">
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
        <button class="btn btn-primary btn-sm" @click="newSession">+ 新建会话</button>
      </div>
    </div>

    <div class="ask-layout">
      <!-- 左：会话列表 -->
      <div class="session-list">
        <div class="sl-head">
          <h4>历史会话</h4>
          <button class="btn-new" @click="newSession">+</button>
        </div>
        <div class="sl-body">
          <div v-for="s in sessions" :key="s.id" :class="['sl-item', { active: s.active }]" @click="selectSession(s)">
            <div class="sli-icon">💬</div>
            <div class="sli-body">
              <div class="sli-title">{{ s.title }}</div>
              <div class="sli-time">{{ s.time }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：聊天区 -->
      <div class="chat-area">
        <div class="chat-box" ref="chatBox">
          <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role, m.role === 'ai' ? 'assistant' : '']">
            <div class="msg-avatar">{{ m.role === 'user' ? '我' : '✦' }}</div>
            <div class="msg-body">
              <div class="msg-meta">
                <span class="msg-name">{{ m.role === 'user' ? '我' : 'AI 助手' }}</span>
                <span class="msg-time">{{ m.time }}</span>
              </div>
              <!-- 普通文本 -->
              <div v-if="!m.type" class="msg-text msg-content">{{ m.text }}</div>
              <!-- 数据表格 -->
              <div v-else-if="m.type === 'data'" class="msg-data">
                <div class="md-head">📊 3 条数据</div>
                <table>
                  <thead>
                    <tr><th>项目</th><th>客户</th><th>金额</th><th>逾期</th><th>风险</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(r, ri) in m.items" :key="ri">
                      <td><span class="mono">{{ r.project }}</span></td>
                      <td>{{ r.client }}</td>
                      <td><b class="amount">¥ {{ r.amount.toLocaleString() }}</b></td>
                      <td>{{ r.overdue }} 天</td>
                      <td><span :class="['tag', r.status === '高' ? 'danger' : r.status === '中' ? 'warning' : 'info']">{{ r.status }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <!-- SQL -->
              <div v-else-if="m.type === 'sql'" class="msg-sql">
                <div class="ms-head">🔍 生成的 SQL</div>
                <pre>{{ m.sql }}</pre>
              </div>
              <div v-if="m.role === 'ai'" class="msg-actions">
                <button @click="copyAnswer(m)">📋 复制</button>
                <button @click="useful(m)">👍 有用</button>
                <button @click="regenerate">🔄 重新生成</button>
              </div>
            </div>
          </div>
          <div v-if="isThinking" class="msg ai thinking">
            <div class="msg-avatar">✦</div>
            <div class="msg-body">
              <div class="msg-meta"><span class="msg-name">AI 助手</span><span class="msg-time">{{ now() }}</span></div>
              <div class="msg-text">
                <span class="dots"><span></span><span></span><span></span></span>
                正在分析中...
              </div>
            </div>
          </div>
        </div>

        <div class="ask-input-box">
          <div class="quick-q ai-ask-suggestions">
            <span v-for="(q, i) in quickQuestions" :key="i" class="qq suggestion" @click="send(q)">{{ q }}</span>
          </div>
          <div class="input-row ai-ask-input">
            <span class="icon">✦</span>
            <textarea v-model="askText" rows="1" placeholder="试试：'本月哪些项目回款逾期了？'" @keydown.enter.exact.prevent="send()"></textarea>
            <button class="btn-send" @click="send()">发送</button>
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
$gradient-ai-soft: linear-gradient(135deg, rgba(79, 107, 255, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%);

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-actions { display: flex; gap: 8px; }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-ai; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } }
.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-ai-bg; color: $color-ai; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// 双栏布局
.ask-layout { display: grid; grid-template-columns: 240px 1fr; gap: 16px; min-height: calc(100vh - 200px); @media (max-width: 900px) { grid-template-columns: 1fr; } }

// 左：会话列表
.session-list { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.sl-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF; h4 { font-size: 13px; font-weight: 600; margin: 0; } }
.btn-new { width: 24px; height: 24px; border-radius: 50%; background: $gradient-ai; color: #fff; border: none; font-size: 14px; cursor: pointer; }
.sl-body { padding: 8px; max-height: 600px; overflow-y: auto; }
.sl-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: $radius-md; cursor: pointer; transition: all 0.15s; margin-bottom: 2px; &:hover { background: $color-ai-bg; } &.active { background: $color-ai-bg; border-left: 3px solid $color-ai; padding-left: 9px; } }
.sli-icon { font-size: 16px; color: $color-ai; flex-shrink: 0; }
.sli-body { flex: 1; min-width: 0; .sli-title { font-size: 12.5px; color: $color-text-primary; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .sli-time { font-size: 10.5px; color: $color-text-tertiary; margin-top: 2px; } }

// 右：聊天区
.chat-area { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; display: flex; flex-direction: column; min-width: 0; }
.chat-box { flex: 1; padding: 20px 24px; overflow-y: auto; max-height: calc(100vh - 320px); }
.msg { display: flex; gap: 12px; margin-bottom: 18px; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.msg.user .msg-avatar { background: $color-primary-bg; color: $color-primary; }
.msg.ai .msg-avatar { background: $gradient-ai; color: #fff; font-size: 14px; }
.msg-body { max-width: 70%; min-width: 0; }
.msg.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
.msg-meta { display: flex; gap: 8px; font-size: 11px; color: $color-text-tertiary; margin-bottom: 4px; .msg-name { font-weight: 500; color: $color-text-secondary; } .msg-time { font-family: $font-family-mono; } }
.msg-text { background: $color-bg; padding: 10px 14px; border-radius: $radius-md; font-size: 13px; line-height: 1.7; color: $color-text-primary; white-space: pre-wrap; word-break: break-word; }
.msg.user .msg-text { background: $gradient-ai; color: #fff; }
.msg-text strong { color: $color-ai; font-weight: 600; }
.msg.user .msg-text strong { color: #FFE082; }
.msg-text .dots { display: inline-flex; gap: 3px; margin-right: 6px; }
.msg-text .dots span { width: 5px; height: 5px; background: $color-ai; border-radius: 50%; animation: bounce 1.4s infinite; }
.msg-text .dots span:nth-child(2) { animation-delay: 0.2s; }
.msg-text .dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

// msg-data（数据表格）
.msg-data { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 10px 12px; margin-top: 6px; }
.md-head { font-size: 12px; color: $color-text-tertiary; margin-bottom: 6px; font-weight: 500; }
.msg-data table { width: 100%; border-collapse: collapse; font-size: 12px; }
.msg-data th { text-align: left; padding: 6px 8px; background: $color-bg; color: $color-text-tertiary; font-weight: 500; }
.msg-data td { padding: 6px 8px; border-bottom: 1px solid $color-border; }
.msg-data .mono { font-family: $font-family-mono; color: $color-text-secondary; }
.msg-data .amount { color: $color-ai; font-weight: 600; font-family: $font-family-mono; }
.tag { font-size: 10.5px; padding: 1px 6px; border-radius: 9999px; }
.tag.danger { background: $color-danger-bg; color: $color-danger; }
.tag.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.tag.info { background: rgba(148, 163, 184, 0.15); color: #64748B; }

// msg-sql
.msg-sql { background: #1F2937; color: #E5E7EB; border-radius: $radius-md; padding: 10px 12px; margin-top: 6px; }
.ms-head { font-size: 11.5px; color: #94A3B8; margin-bottom: 6px; }
.msg-sql pre { font-family: $font-family-mono; font-size: 11.5px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; margin: 0; }

.msg-actions { display: flex; gap: 6px; margin-top: 6px; }
.msg-actions button { font-size: 11px; padding: 3px 8px; background: transparent; border: 1px solid $color-border; color: $color-text-tertiary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }

// ask input
.ask-input-box { border-top: 1px solid $color-border; padding: 14px 20px; background: #FAFBFF; }
.quick-q { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.qq { font-size: 11.5px; color: $color-text-secondary; padding: 3px 10px; background: #fff; border: 1px solid $color-border; border-radius: 9999px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }
.input-row { display: flex; align-items: center; gap: 10px; background: #fff; border: 1.5px solid $color-ai-border; border-radius: $radius-md; padding: 8px 12px; transition: all 0.2s; &:focus-within { border-color: $color-ai; box-shadow: 0 0 0 3px $color-ai-bg; } .icon { font-size: 16px; color: $color-ai; }     input, textarea { flex: 1; border: none; outline: none; font-size: 13.5px; background: transparent; font-family: inherit; resize: none; line-height: 1.5; max-height: 100px; } input::placeholder { color: $color-text-tertiary; } }
.btn-send { background: $gradient-ai; color: #fff; border: none; border-radius: $radius-sm; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit; }
.input-hint { font-size: 11px; color: $color-text-tertiary; margin-top: 6px; text-align: center; }
</style>
