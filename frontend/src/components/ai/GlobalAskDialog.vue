<script setup lang="ts">
/**
 * GlobalAskDialog · 全局命令面板 ⌘K（触点 #14）
 * - 暗色浮层（类似 Linear/Notion ⌘K 体验）
 * - AI 对话 + 推荐问题 + 快捷命令导航
 * - mock SSE 流式输出
 */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'

const router = useRouter()
const visible = defineModel<boolean>('visible', { default: false })

const query = ref('')
const messages = ref<Array<{ role: 'user' | 'ai'; content: string; streaming?: boolean }>>([])
const askInput = ref<HTMLTextAreaElement>()
const aiTyping = ref(false)
let streamTimer: number | null = null

// 快捷命令
const cmds = [
  { icon: '📄', label: '新建合同',         path: '/contract/create' },
  { icon: '📝', label: '新建销售费用',     path: '/expense/create' },
  { icon: '💰', label: '新建回款计划',     path: '/receivable/create' },
  { icon: '📷', label: '发票识别',         path: '/invoice/ocr' },
  { icon: '🤖', label: 'AI 智能中心',     path: '/ai/panel/contract' },
  { icon: '📊', label: 'Dashboard',       path: '/dashboard' },
  { icon: '📋', label: '合同列表',         path: '/contract/list' },
  { icon: '📦', label: '项目列表',         path: '/project/list' },
  { icon: '🏢', label: '客户列表',         path: '/client/list' },
  { icon: '💸', label: '回款列表',         path: '/receivable/list' },
]

// 推荐问题
const suggestedQuestions = [
  '本月签了多少合同？',
  '逾期回款有哪些？',
  '哪些项目存在风险？',
  '最近 30 天发票识别准确率如何？',
  '本季度销售费用支出多少？',
]

function open() { visible.value = true; nextTick(() => askInput.value?.focus()) }
function close() {
  visible.value = false
  if (streamTimer) { clearInterval(streamTimer); streamTimer = null }
}

function goCmd(path: string) {
  router.push(path)
  close()
}

const fullAnswer = ref('')
async function ask() {
  const q = query.value.trim()
  if (!q) return
  messages.value.push({ role: 'user', content: q })
  query.value = ''
  aiTyping.value = true
  // mock SSE 流式
  fullAnswer.value = ''
  const mockAnswer = '根据本月数据：\n- 新签合同 8 份，金额 ¥1,234,500（环比 +18%）\n- 销售费用 12 单，总额 ¥86,500（环比 -5%）\n- 逾期回款 3 笔，金额 ¥48,600（建议催办）\n- AI 风险项目 2 个（PRJ-2026-018 / PRJ-2026-022）\n\n详情请查看 Dashboard / 业务报表。'
  let idx = 0
  messages.value.push({ role: 'ai', content: '', streaming: true })
  streamTimer = window.setInterval(() => {
    if (idx >= mockAnswer.length) {
      if (streamTimer) clearInterval(streamTimer)
      const last = messages.value[messages.value.length - 1]
      if (last) last.streaming = false
      aiTyping.value = false
      return
    }
    fullAnswer.value += mockAnswer[idx]
    const last = messages.value[messages.value.length - 1]
    if (last) last.content = fullAnswer.value
    idx++
  }, 30)
}

function onKeydown(e: KeyboardEvent) {
  // ⌘K 或 Ctrl+K 唤起
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    open()
  } else if (e.key === 'Escape' && visible.value) {
    close()
  }
}

onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown); if (streamTimer) clearInterval(streamTimer) })

defineExpose({ open, close })
</script>

<template>
  <transition name="cmdk-fade">
    <div v-if="visible" class="cmdk-mask" @click.self="close">
      <div class="cmdk-panel">
        <!-- 顶栏：输入框 + ⌘K 提示 -->
        <div class="cmdk-input-row">
          <span class="cmdk-prefix">✨</span>
          <input
            ref="askInput"
            v-model="query"
            class="cmdk-input"
            placeholder="问 AI、搜索命令、跳页面..."
            @keydown.enter="ask"
          />
          <kbd class="cmdk-kbd">esc</kbd>
        </div>

        <!-- 主体：左命令 + 右对话 -->
        <div class="cmdk-body">
          <!-- 左：快捷命令 -->
          <div class="cmdk-commands">
            <h4>⚡ 快捷命令</h4>
            <div
              v-for="c in cmds"
              :key="c.path"
              class="cmdk-cmd-item"
              @click="goCmd(c.path)"
            >
              <span class="cmd-icon">{{ c.icon }}</span>
              <span>{{ c.label }}</span>
            </div>
          </div>

          <!-- 右：AI 对话 -->
          <div class="cmdk-ai">
            <h4>💬 AI 问答</h4>
            <div v-if="!messages.length" class="cmdk-suggested">
              <p>试试这些问题：</p>
              <div
                v-for="q in suggestedQuestions"
                :key="q"
                class="cmdk-suggest-item"
                @click="query = q; ask()"
              >
                ✦ {{ q }}
              </div>
            </div>
            <div v-else class="cmdk-messages">
              <div
                v-for="(m, i) in messages"
                :key="i"
                :class="['cmdk-msg', `cmdk-msg-${m.role}`]"
              >
                <div class="cmdk-msg-avatar">{{ m.role === 'user' ? '🧑' : '✨' }}</div>
                <div class="cmdk-msg-content">
                  <pre>{{ m.content }}<span v-if="m.streaming" class="cmdk-cursor">▍</span></pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底栏：状态 -->
        <div class="cmdk-foot">
          <span>⏎ 提问</span>
          <span>⌘K 唤起 / esc 关闭</span>
          <span>由 ernie-3.5 驱动</span>
        </div>
      </div>
    </div>
  </transition>
</template>

<style lang="scss" scoped>
.cmdk-mask {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(11, 18, 32, 0.6);
  backdrop-filter: blur(8px);
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: 12vh;
}
.cmdk-panel {
  width: 760px; max-width: 92vw; max-height: 70vh;
  background: linear-gradient(180deg, #1A1F2E 0%, #0F1320 100%);
  border: 1px solid rgba(124, 58, 237, 0.4);
  border-radius: 14px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(79,107,255,0.2);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.cmdk-input-row {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  .cmdk-prefix { font-size: 20px; }
  .cmdk-input {
    flex: 1; background: transparent; border: none; outline: none;
    color: #fff; font-size: 15px; font-family: inherit;
    &::placeholder { color: rgba(255,255,255,0.4); }
  }
  .cmdk-kbd {
    font-size: 10px; padding: 2px 6px;
    background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6);
    border-radius: 4px;
  }
}
.cmdk-body { display: grid; grid-template-columns: 1fr 1.4fr; flex: 1; overflow: hidden; }
.cmdk-commands, .cmdk-ai {
  padding: 14px 16px; overflow-y: auto;
  h4 { font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.5); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
}
.cmdk-commands { border-right: 1px solid rgba(255,255,255,0.06); }
.cmdk-cmd-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 6px;
  font-size: 13px; color: rgba(255,255,255,0.8);
  cursor: pointer; transition: all 0.1s;
  &:hover { background: rgba(124,58,237,0.2); color: #fff; }
  .cmd-icon { font-size: 14px; }
}
.cmdk-suggested p { font-size: 11px; color: rgba(255,255,255,0.5); margin-bottom: 8px; }
.cmdk-suggest-item {
  padding: 8px 12px; margin-bottom: 4px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: 6px; font-size: 12.5px;
  color: rgba(255,255,255,0.85); cursor: pointer;
  &:hover { border-color: #7C3AED; color: #fff; }
}
.cmdk-messages { display: flex; flex-direction: column; gap: 12px; }
.cmdk-msg { display: flex; gap: 8px; }
.cmdk-msg-avatar { font-size: 18px; flex-shrink: 0; }
.cmdk-msg-content {
  flex: 1; min-width: 0;
  pre { margin: 0; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 6px; font-family: inherit; font-size: 12.5px; color: rgba(255,255,255,0.9); line-height: 1.6; white-space: pre-wrap; }
}
.cmdk-msg-user .cmdk-msg-content pre { background: rgba(79,107,255,0.15); }
.cmdk-cursor { animation: blink 0.8s infinite; color: #7C3AED; }
@keyframes blink { 50% { opacity: 0; } }
.cmdk-foot {
  display: flex; gap: 16px;
  padding: 8px 20px;
  background: rgba(0,0,0,0.3);
  font-size: 10px; color: rgba(255,255,255,0.4);
  border-top: 1px solid rgba(255,255,255,0.06);
}
.cmdk-fade-enter-active, .cmdk-fade-leave-active { transition: all 0.2s; }
.cmdk-fade-enter-from, .cmdk-fade-leave-to { opacity: 0; }
</style>
