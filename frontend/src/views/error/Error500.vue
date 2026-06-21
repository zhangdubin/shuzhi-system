<script setup lang="ts">
/**
 * Error500 · 服务器错误（1:1 复刻 design/error-500.html + 触点 #21 AI 助手）
 */
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'

const router = useRouter()
const traceId = 'TRC-' + Date.now().toString(36).toUpperCase()

async function askAi() {
  ElMessage.info('AI 助手正在分析（mock）...')
  const r = await aiApi.feedbackSubmit({
    targetType: 'risk',
    targetId: traceId,
    rating: 'down',
    comment: `[Error500] 自动诊断报告：traceId=${traceId}, 错误类型=后端服务异常`,
    category: 'error-diagnosis',
  }).catch(() => null)
  ElMessage.success(`✨ AI 助手已记录问题（traceId: ${traceId}）\n我们会自动分析并通知您修复进度。`)
}
</script>

<template>
  <div class="err-page">
    <div class="err-content">
      <div class="err-icon">⚙️</div>
      <div class="err-code">500</div>
      <h1>服务器打了个盹</h1>
      <p class="err-sub">
        服务暂时出了点问题，我们正在紧急修复。<br/>
        请稍后再试，或联系管理员查看服务状态。
      </p>
      <div class="ai-diagnose">
        <span class="ai-diagnose-icon">🤖</span>
        <span class="ai-diagnose-text">AI 助手已自动记录此次异常（traceId: <code>{{ traceId }}</code>），我们将分析根因并通知修复进度</span>
        <button class="btn-ai-diagnose" @click="askAi">立即诊断</button>
      </div>
      <div class="err-actions">
        <a class="btn btn-primary btn-lg" @click.prevent="router.push('/dashboard')">🏠 返回首页</a>
        <a class="btn btn-outline btn-lg" @click.prevent="router.back()">← 返回上页</a>
        <a class="btn btn-ghost" @click.prevent="router.push('/index')">📑 页面总览</a>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.err-page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
  padding: 40px 20px;
}
.err-content { text-align: center; max-width: 560px; }
.err-icon { font-size: 80px; margin-bottom: 16px; }
.err-code {
  font-size: 96px; font-weight: 900; line-height: 1;
  background: $gradient-brand;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  font-family: $font-family-mono;
  margin-bottom: 12px;
}
.err-content h1 { font-size: 24px; font-weight: 700; color: $color-text-primary; margin-bottom: 8px; }
.err-sub { font-size: 14px; color: $color-text-secondary; line-height: 1.7; margin-bottom: 24px; }
.ai-diagnose {
  display: flex; gap: 10px; align-items: center; padding: 12px 16px;
  background: linear-gradient(135deg, rgba(79,107,255,0.05) 0%, rgba(124,58,237,0.05) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-md; margin-bottom: 20px;
  text-align: left;
  .ai-diagnose-icon { font-size: 22px; flex-shrink: 0; }
  .ai-diagnose-text { flex: 1; font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
  code { background: rgba(124,58,237,0.1); color: #7C3AED; padding: 1px 5px; border-radius: 3px; font-family: $font-family-mono; font-size: 11px; }
}
.btn-ai-diagnose {
  flex-shrink: 0; padding: 6px 12px; font-size: 12px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none; border-radius: $radius-sm; cursor: pointer;
  &:hover { opacity: 0.92; }
}
.err-actions { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
</style>
