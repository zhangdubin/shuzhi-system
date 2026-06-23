<script setup lang="ts">
/**
 * AiCenter · AI 中心（1:1 复刻 design/ai-center.html）
 * - 顶部 ai-hero 蓝紫渐变（radial-gradient ::before + 巨大 ✦ ::after）
 * - 6 大 AI 能力入口 cap-grid（4 列）
 * - 主体 2:1 双栏：左问数+任务 / 右提醒+模型状态+快捷入口
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const askText = ref('')

// 模型设置抽屉
const modelSettingsVisible = ref(false)
const selectedModel = ref<any>(null)
function openModelSettings(model?: any) {
  selectedModel.value = model || null
  modelSettingsVisible.value = true
}
function saveModelSettings() {
  ElMessage.success(`已保存「${selectedModel.value?.name}」配置`)
  modelSettingsVisible.value = false
}

function onProviderChange(provider: string) {
  const presets: Record<string, { url: string; model: string; ctx: number }> = {
    openai: { url: 'https://api.openai.com/v1', model: 'gpt-4o', ctx: 128000 },
    qwen: { url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-max', ctx: 131072 },
    deepseek: { url: 'https://api.deepseek.com/v1', model: 'deepseek-chat', ctx: 64000 },
    minimax: { url: 'https://api.minimax.chat/v1', model: 'MiniMax-Text-01', ctx: 1000000 },
    zhipu: { url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4', ctx: 128000 },
    baidu: { url: 'https://qianfan.baidubce.com/v2', model: 'ernie-4.0-8k', ctx: 8192 },
    tencent: { url: 'https://hunyuan.cloud.tencent.com', model: 'hunyuan-pro', ctx: 128000 },
    custom: { url: '', model: '', ctx: 4096 },
  }
  const p = presets[provider]
  if (p) ElMessage.info(`已切换至 ${provider}，请补充 API Key 并确认模型名称`)
}

function testLLMConnection() {
  ElMessage.info('正在测试连接...')
  setTimeout(() => ElMessage.success('✅ 连接成功，模型响应正常'), 1200)
}

// 6 大 AI 能力
const caps = ref([
  { icon: '📷', name: '智能字段抽取',     badge: 'NEW', desc: '上传发票/合同/名片，2 秒自动填好表单', stat: '2,840',  link: '/invoice/ocr' },
  { icon: '⚠️', name: '风险智能识别',     badge: '',    desc: '合同/项目/凭证异常实时标红 + 建议',     stat: '23',     link: '/ai/risk' },
  { icon: '🔗', name: '银行流水智能匹配', badge: '',    desc: '自动匹配回款到合同/发票',               stat: '91%',    link: '/receivable' },
  { icon: '💬', name: '自然语言问数',     badge: '',    desc: '"本月哪些项目回款逾期了？" 一问即答', stat: '186',    link: '/ai/ask' },
  { icon: '📝', name: '智能起草/生成',     badge: '',    desc: '合同初稿/汇报/通知 AI 起草',           stat: '68%',    link: '/ai/extract' },
  { icon: '🤖', name: 'Agent 自动化',     badge: '',    desc: '定时任务 + 触发器 + 后台自动跑',        stat: '8',      link: '/ai/tasks' },
])

// 实时任务（5 条）
const tasks = ref([
  { icon: '📷', name: '批量发票识别 - 差旅报销 5月',  meta: ['处理中 · 23/58', '预计 12 秒'], status: 'running' },
  { icon: '📄', name: '合同风险扫描 - 数智化二期',     meta: ['分析中', '预计 8 秒'],         status: 'running' },
  { icon: '🔗', name: '银行流水匹配 - 6月第2周',       meta: ['匹配中', '预计 5 秒'],         status: 'running' },
  { icon: '✓',  name: '日报生成 - 6 月 12 日',          meta: ['已完成 · 2 分钟前'],           status: 'done' },
  { icon: '⚠',  name: '回款逾期分析',                  meta: ['失败 · 模型超时', '重试'],    status: 'failed' },
])

// 今日 AI 提醒（3 条）
const alerts = ref([
  { level: 'danger',  icon: '!', title: '合同 C-2024-123 已逾期 3 天未签字',     desc: '金额 158 万，建议立即催办客户法务',     actions: ['立即处理', '稍后提醒'] },
  { level: 'warning', icon: '⚠', title: '发票 OCR 抽取异常',                    desc: '3 张增值税专用发票税率识别有误，建议人工复核', actions: ['去复核', '忽略'] },
  { level: 'success', icon: '✓', title: '本周回款匹配完成 124 笔',               desc: '匹配率 91%，另有 11 笔需人工确认',     actions: ['查看报告'] },
])

// 模型状态（5 个）
const models = ref([
  { name: 'PaddleOCR 发票识别',  meta: '延迟 0.4s',  status: 'normal' },
  { name: '风险识别 v2.3',       meta: '准确 94.2%', status: 'normal' },
  { name: 'LLM 起草 Qwen2.5',    meta: '延迟 2.8s',  status: 'degraded' },
  { name: '国税查验接口',         meta: '正常',       status: 'normal' },
  { name: '诺诺发票兜底',         meta: '未启用',     status: 'down' },
])

// 快捷入口（6 个）
const quickEntries = ref([
  { icon: '📷', name: '字段抽取演示', link: '/invoice/ocr' },
  { icon: '💬', name: '智能问答',     link: '/ai/ask' },
  { icon: '⚡', name: '任务中心',     link: '/ai/tasks' },
  { icon: '⚙', name: '模型管理',     link: '/ai/center' },
  { icon: '📊', name: 'AI 数据报表',  link: '/ai/center' },
  { icon: '📖', name: '使用文档',     link: '/ai/center' },
])

// 快捷问题
const quickQuestions = ref([
  '💰 本月开票金额', '⚠️ 风险项目', '📊 上周销售费用', '🔄 待回款客户', '📅 本月合同到期',
])

function askAI() {
  if (!askText.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  router.push({ path: '/ai/ask', query: { q: askText.value } })
}
function useQuickQ(q: string) { askText.value = q.replace(/^[^ ]+ /, ''); askAI() }
function handleAction(name: string) { ElMessage.success(`已操作: ${name}`) }
function configureModel(m: any) { openModelSettings(m) }
function goCap(c: any) { router.push(c.link) }
function goQuick(e: any) { router.push(e.link) }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/dashboard')">首页</a>
          <span class="sep">/</span>
          <span class="current">数智（AI）</span>
          <span class="sep">/</span>
          <span class="current">AI 中心</span>
        </div>
        <h1>AI 中心 <span class="ai-badge phase">Phase 1</span></h1>
        <p class="page-desc">让 AI 处理重复劳动，让你专注决策</p>
      </div>
    </div>

    <!-- ai-hero 蓝紫渐变 -->
    <div class="ai-hero">
      <div class="ai-hero-body">
        <h1>✦ 数智化工作台</h1>
        <p>让 AI 处理重复劳动，让你专注决策。本月 AI 已为你节省 <strong>87.5 小时</strong>，字段抽取准确率 <strong>94.2%</strong>，风险预警命中 <strong>23 次</strong>。</p>
        <div class="ai-hero-actions">
          <button class="btn-ghost">📖 使用指南</button>
          <button class="btn-white" @click="openModelSettings()">⚙️ 模型设置</button>
        </div>
      </div>
    </div>

    <!-- 6 大 AI 能力入口 -->
    <div class="cap-card">
      <div class="cap-head">
        <h3>AI 能力 <span class="text-tertiary">点击使用，对应原业务页面会同步出现 AI 能力入口</span></h3>
        <a class="link-ai">查看全部 →</a>
      </div>
      <div class="ai-cap-grid">
        <div v-for="(c, i) in caps" :key="i" class="ai-cap" @click="goCap(c)">
          <div class="ac-icon">{{ c.icon }}</div>
          <div class="ac-name">{{ c.name }} <span v-if="c.badge" class="ai-badge outline">{{ c.badge }}</span></div>
          <div class="ac-desc">{{ c.desc }}</div>
          <div class="ac-stat">
            <span>已抽取 <span class="num">{{ c.stat }}</span></span>
            <a class="link-ai">体验 →</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 主体 2:1 双栏 -->
    <div class="ai-main">
      <!-- 左：问数 + 任务 -->
      <div class="ai-left">
        <!-- 问数输入框 -->
        <div class="ai-ask-box">
          <h4>✦ 问问 AI 助手</h4>
          <div class="ask-input">
            <span class="ask-icon">✦</span>
            <input v-model="askText" type="text" placeholder="试试：'本月哪些项目回款逾期了？'" @keyup.enter="askAI" />
            <button @click="askAI">提问</button>
          </div>
          <div class="ask-suggest">
            <span v-for="(q, i) in quickQuestions" :key="i" @click="useQuickQ(q)">{{ q }}</span>
          </div>
        </div>

        <!-- 实时任务 -->
        <div class="card">
          <div class="card-head">
            <h3>实时任务 <span class="ai-loading">3 个进行中</span></h3>
            <a class="link-ai" @click="router.push('/ai/tasks')">任务中心 →</a>
          </div>
          <div class="card-body">
            <div v-for="(t, i) in tasks" :key="i" class="ai-task">
              <div class="at-icon">{{ t.icon }}</div>
              <div class="at-body">
                <div class="at-name">{{ t.name }}</div>
                <div class="at-meta">
                  <span v-for="(m, mi) in t.meta" :key="mi">
                    <template v-if="mi > 0">· </template>{{ m }}
                  </span>
                </div>
              </div>
              <span :class="['at-status', t.status]">
                <span v-if="t.status === 'running'" class="ai-thinking-dots">
                  <span></span><span></span><span></span>
                </span>
                <template v-else-if="t.status === 'done'">已完成</template>
                <template v-else>失败</template>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：今日提醒 + 模型状态 + 快捷入口 -->
      <div class="ai-right">
        <!-- 今日 AI 提醒 -->
        <div class="card">
          <div class="card-head">
            <h3>今日 AI 提醒</h3>
            <span class="ai-badge">{{ alerts.length }}</span>
          </div>
          <div class="card-body">
            <div v-for="(a, i) in alerts" :key="i" :class="['ai-suggestion', a.level]">
              <div class="ai-s-icon">{{ a.icon }}</div>
              <div class="ai-s-body">
                <div class="ai-s-title">{{ a.title }}</div>
                <div class="ai-s-desc">{{ a.desc }}</div>
                <div class="ai-s-actions">
                  <button v-for="(act, ai) in a.actions" :key="ai" :class="['btn-s', ai === 0 ? 'primary' : '']" @click="handleAction(act)">{{ act }}</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 模型状态 -->
        <div class="card">
          <div class="card-head">
            <h3>模型状态</h3>
            <a class="link-ai">管理 →</a>
          </div>
          <div class="card-body">
            <div v-for="(m, i) in models" :key="i" class="ai-model-row">
              <div :class="['mr-status', m.status]"></div>
              <div class="mr-name">{{ m.name }}</div>
              <div class="mr-meta">{{ m.meta }}</div>
              <div class="mr-actions">
                <button :title="m.status === 'down' ? '启用' : '配置'" @click="configureModel(m)">
                  {{ m.status === 'down' ? '▶' : '⚙' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 快捷入口 -->
        <div class="card">
          <div class="card-head">
            <h3>快速入口</h3>
          </div>
          <div class="card-body">
            <div class="ai-quick">
              <a v-for="(e, i) in quickEntries" :key="i" @click="goQuick(e)">
                <span class="icon">{{ e.icon }}</span>{{ e.name }}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 模型设置抽屉 -->
  <el-drawer
    v-model="modelSettingsVisible"
    :title="selectedModel ? `⚙ 配置 · ${selectedModel.name}` : '⚙ 全局模型设置'"
    direction="rtl"
    size="440px"
  >
    <template v-if="selectedModel">
      <!-- 单个模型配置 -->
      <div class="ms-section">
        <div class="ms-model-info">
          <span :class="['ms-status-dot', selectedModel.status]"></span>
          <span class="ms-model-name">{{ selectedModel.name }}</span>
          <span :class="['ms-status-tag', selectedModel.status]">
            {{ selectedModel.status === 'normal' ? '正常' : selectedModel.status === 'degraded' ? '性能降级' : '已停用' }}
          </span>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-section-title">基础参数</div>
        <div class="ms-row">
          <label>启用状态</label>
          <el-switch />
        </div>
        <div class="ms-row">
          <label>超时时间</label>
          <el-input-number :min="1" :max="60" :step="1" /> <span class="ms-unit">秒</span>
        </div>
        <div class="ms-row">
          <label>最大重试</label>
          <el-input-number :min="0" :max="5" :step="1" /> <span class="ms-unit">次</span>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-section-title">模型参数</div>
        <div class="ms-row">
          <label>Temperature</label>
          <el-input-number :min="0" :max="2" :step="0.1" :precision="1" /> <span class="ms-unit">（创造性）</span>
        </div>
        <div class="ms-row">
          <label>Max Tokens</label>
          <el-input-number :min="256" :max="8192" :step="256" /> <span class="ms-unit">（输出上限）</span>
        </div>
        <div class="ms-row">
          <label>Fallback 模型</label>
          <el-select placeholder="无降级" style="width:160px">
            <el-option label="无降级" value="" />
            <el-option label="qwen2.5-7b" value="qwen2.5-7b" />
            <el-option label="gpt-4o-mini" value="gpt-4o-mini" />
          </el-select>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-section-title">通用大模型对接</div>
        <div class="ms-row">
          <label>Provider</label>
          <el-select placeholder="选择服务商" style="width:180px" @change="onProviderChange">
            <el-option label="OpenAI 兼容" value="openai" />
            <el-option label="阿里通义 (Qwen)" value="qwen" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="MiniMax" value="minimax" />
            <el-option label="智谱 (GLM)" value="zhipu" />
            <el-option label="百度 (ERNIE)" value="baidu" />
            <el-option label="腾讯 (Hunyuan)" value="tencent" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </div>
        <div class="ms-row ms-row-col">
          <label>Base URL</label>
          <el-input placeholder="https://api.openai.com/v1" style="flex:1" />
        </div>
        <div class="ms-row ms-row-col">
          <label>API Key</label>
          <el-input type="password" placeholder="sk-..." show-password style="flex:1" />
        </div>
        <div class="ms-row ms-row-col">
          <label>模型名称</label>
          <el-input placeholder="gpt-4o / qwen-max / deepseek-chat" style="flex:1" />
        </div>
        <div class="ms-row">
          <label>上下文上限</label>
          <el-input-number :min="1024" :max="200000" :step="1024" /> <span class="ms-unit">Tokens</span>
        </div>
        <div class="ms-row">
          <label>Streaming</label>
          <el-switch /> <span class="ms-unit">启用流式输出（SSE）</span>
        </div>
        <div class="ms-test-row">
          <el-button size="small" @click="testLLMConnection">🔗 测试连接</el-button>
          <span class="ms-test-hint">验证 API Key 和网络连通性</span>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-section-title">告警阈值</div>
        <div class="ms-row">
          <label>错误率告警</label>
          <el-input-number :min="1" :max="50" :step="1" /> <span class="ms-unit">%（超限提醒）</span>
        </div>
        <div class="ms-row">
          <label>延迟告警</label>
          <el-input-number :min="1" :max="30" :step="1" /> <span class="ms-unit">秒（超限提醒）</span>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- 全局设置 -->
      <div class="ms-section">
        <div class="ms-section-title">全局策略</div>
        <div class="ms-row">
          <label>默认降级策略</label>
          <el-select placeholder="选择策略" style="width:180px">
            <el-option label="自动切换备用模型" value="auto" />
            <el-option label="返回错误" value="error" />
            <el-option label="使用缓存结果" value="cache" />
          </el-select>
        </div>
        <div class="ms-row">
          <label>全局超时</label>
          <el-input-number :min="5" :max="120" :step="5" :model-value="30" /> <span class="ms-unit">秒</span>
        </div>
        <div class="ms-row">
          <label>日志级别</label>
          <el-select placeholder="日志级别" style="width:180px">
            <el-option label="debug" value="debug" />
            <el-option label="info" value="info" />
            <el-option label="warn" value="warn" />
            <el-option label="error" value="error" />
          </el-select>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-section-title">全部模型</div>
        <div v-for="(m, i) in models" :key="i" class="ms-model-row">
          <span :class="['ms-status-dot', m.status]"></span>
          <div class="ms-model-info">
            <div class="ms-model-name">{{ m.name }}</div>
            <div class="ms-model-meta">{{ m.meta }}</div>
          </div>
          <el-button size="small" @click="openModelSettings(m)">配置</el-button>
        </div>
      </div>
    </template>

    <div class="ms-footer">
      <el-button @click="modelSettingsVisible = false">取消</el-button>
      <el-button type="primary" @click="saveModelSettings">保存配置</el-button>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

// AI 主题色（design 1:1）
$color-ai: #7C3AED;
$color-ai-2: #4F6BFF;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-border: rgba(124, 58, 237, 0.25);
$color-ai-bg: rgba(124, 58, 237, 0.08);
$gradient-ai-soft: linear-gradient(135deg, rgba(79, 107, 255, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%);
$shadow-ai: 0 4px 16px rgba(124, 58, 237, 0.15);

.page-header h1 { @include page-title-h1; margin: 0; display: flex; align-items: center; gap: 8px; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.text-tertiary { color: $color-text-tertiary; font-size: 12px; font-weight: normal; }
.link-ai { font-size: 12px; color: $color-ai; cursor: pointer; &:hover { text-decoration: underline; } }

// ai-badge
.ai-badge { font-size: 10px; padding: 1px 6px; background: $gradient-ai; color: #fff; border-radius: 9999px; font-weight: 600; letter-spacing: 0.3px; }
.ai-badge.outline { background: transparent; color: $color-ai; border: 1px solid $color-ai-border; }
.ai-badge.phase { background: rgba(79, 107, 255, 0.1); color: #4F6BFF; font-weight: 500; font-size: 11px; padding: 1px 8px; }
.ai-loading { font-size: 11px; padding: 2px 8px; background: $color-ai-bg; color: $color-ai; border-radius: 9999px; font-weight: 500; }

// ai-hero
.ai-hero {
  position: relative;
  background: $gradient-ai;
  border-radius: $radius-lg;
  padding: 28px 32px;
  color: #fff;
  margin-bottom: 24px;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    right: -60px; top: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.15), transparent 70%);
    border-radius: 50%;
  }
  &::after {
    content: '✦';
    position: absolute;
    right: 32px; bottom: -20px;
    font-size: 160px;
    color: rgba(255, 255, 255, 0.08);
    font-weight: 700;
  }
}
.ai-hero-body { position: relative; z-index: 1; }
.ai-hero h1 { font-size: 24px; font-weight: 700; margin: 0 0 8px 0; display: flex; align-items: center; gap: 12px; }
.ai-hero p { font-size: 13.5px; color: rgba(255, 255, 255, 0.85); max-width: 580px; line-height: 1.6; margin: 0; }
.ai-hero p strong { color: #fff; font-weight: 600; }
.ai-hero-actions { display: flex; gap: 12px; margin-top: 18px; }
.btn-ghost, .btn-white {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.25);
  padding: 7px 14px;
  border-radius: $radius-md;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  &:hover { background: rgba(255, 255, 255, 0.28); }
}
.btn-white { background: #fff; color: $color-ai; font-weight: 600; &:hover { background: rgba(255, 255, 255, 0.92); } }

// cap card
.cap-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; margin-bottom: 24px; }
.cap-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 22px; border-bottom: 1px solid $color-border; h3 { font-size: 15px; font-weight: 600; margin: 0; } }
.ai-cap-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 20px 22px; @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); } @media (max-width: 600px) { grid-template-columns: 1fr; } }
.ai-cap {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  &:hover { transform: translateY(-3px); box-shadow: $shadow-ai; border-color: $color-ai-border; }
  .ac-icon { width: 44px; height: 44px; background: $color-ai-bg; color: $color-ai; border-radius: $radius-md; display: grid; place-items: center; font-size: 20px; margin-bottom: 10px; }
  .ac-name { font-size: 14.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
  .ac-desc { font-size: 12px; color: $color-text-tertiary; line-height: 1.5; min-height: 36px; }
  .ac-stat { margin-top: 12px; padding-top: 12px; border-top: 1px solid $color-border; display: flex; justify-content: space-between; font-size: 11.5px; color: $color-text-tertiary; .num { color: $color-ai; font-weight: 600; } }
}

// 主体 2:1
.ai-main { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; @media (max-width: 1100px) { grid-template-columns: 1fr; } }
.ai-left, .ai-right { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

// card
.card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; }
.card-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 22px; border-bottom: 1px solid $color-border; h3 { font-size: 14px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; } }
.card-body { padding: 4px 22px 16px; }

// ai-ask-box
.ai-ask-box {
  background: $gradient-ai-soft;
  border: 1px solid $color-ai-border;
  border-radius: $radius-lg;
  padding: 20px;
  margin-bottom: 16px;
  h4 { font-size: 14px; font-weight: 600; color: $color-text-primary; margin: 0 0 12px 0; display: flex; align-items: center; gap: 8px; }
  .ask-input {
    background: #fff;
    border: 1.5px solid $color-ai-border;
    border-radius: $radius-md;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.2s;
    &:focus-within { border-color: $color-ai; box-shadow: 0 0 0 3px $color-ai-bg; }
    .ask-icon { font-size: 16px; color: $color-ai; }
    input { flex: 1; border: none; outline: none; font-size: 13.5px; background: transparent; font-family: inherit; color: $color-text-primary; }
    input::placeholder { color: $color-text-tertiary; }
    button { background: $gradient-ai; color: #fff; border: none; border-radius: $radius-sm; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; }
  }
  .ask-suggest { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
  .ask-suggest span { font-size: 11.5px; color: $color-text-secondary; padding: 3px 10px; background: #fff; border: 1px solid $color-border; border-radius: 9999px; cursor: pointer; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }
}

// ai-task
.ai-task { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid $color-border; &:last-child { border-bottom: none; } }
.at-icon { width: 32px; height: 32px; background: $color-ai-bg; color: $color-ai; border-radius: $radius-sm; display: grid; place-items: center; font-size: 14px; flex-shrink: 0; }
.at-body { flex: 1; min-width: 0; .at-name { font-size: 13px; font-weight: 500; color: $color-text-primary; margin-bottom: 2px; } .at-meta { font-size: 11.5px; color: $color-text-tertiary; display: flex; gap: 6px; flex-wrap: wrap; } }
.at-status { font-size: 11px; padding: 2px 8px; border-radius: 9999px; flex-shrink: 0; }
.at-status.running { color: $color-ai; background: $color-ai-bg; }
.at-status.done { color: $color-success; background: $color-success-bg; }
.at-status.failed { color: $color-danger; background: $color-danger-bg; }

.ai-thinking-dots { display: inline-flex; gap: 3px; }
.ai-thinking-dots span { width: 5px; height: 5px; background: $color-ai; border-radius: 50%; animation: ai-bounce 1.4s infinite; }
.ai-thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.ai-thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes ai-bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

// ai-suggestion
.ai-suggestion { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid $color-border; &:last-child { border-bottom: none; } .ai-s-icon { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; font-size: 14px; font-weight: 700; flex-shrink: 0; } }
.ai-suggestion.danger .ai-s-icon { background: $color-danger-bg; color: $color-danger; }
.ai-suggestion.warning .ai-s-icon { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.ai-suggestion.success .ai-s-icon { background: $color-success-bg; color: $color-success; }
.ai-s-body { flex: 1; min-width: 0; .ai-s-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; } .ai-s-desc { font-size: 12px; color: $color-text-secondary; line-height: 1.5; margin-bottom: 8px; } }
.ai-s-actions { display: flex; gap: 6px; }
.btn-s { padding: 4px 10px; font-size: 12px; border: 1px solid $color-border; background: #fff; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: $shadow-ai; } } }

// ai-model-row
.ai-model-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid $color-border; &:last-child { border-bottom: none; } }
.mr-status { width: 8px; height: 8px; border-radius: 50%; background: $color-success; flex-shrink: 0; }
.mr-status.degraded { background: #F59E0B; }
.mr-status.down { background: $color-danger; }
.mr-name { font-size: 13px; font-weight: 500; color: $color-text-primary; flex: 1; }
.mr-meta { font-size: 11.5px; color: $color-text-tertiary; }
.mr-actions button { background: transparent; border: 1px solid $color-border; border-radius: $radius-sm; width: 24px; height: 24px; cursor: pointer; font-size: 11px; color: $color-text-secondary; &:hover { border-color: $color-ai; color: $color-ai; } }

// ai-quick
.ai-quick { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.ai-quick a { padding: 10px 12px; background: $color-ai-bg; border: 1px solid $color-ai-border; border-radius: $radius-md; font-size: 12.5px; color: $color-text-primary; display: flex; align-items: center; gap: 8px; cursor: pointer; transition: all 0.2s; .icon { width: 22px; height: 22px; background: #fff; border-radius: $radius-sm; display: grid; place-items: center; font-size: 12px; color: $color-ai; } &:hover { background: $gradient-ai; color: #fff; border-color: transparent; } &:hover .icon { background: rgba(255, 255, 255, 0.2); color: #fff; } }

// 模型设置抽屉
.ms-section { margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid $color-border; &:last-of-type { border-bottom: none; } }
.ms-section-title { font-size: 12px; font-weight: 600; color: $color-text-secondary; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }
.ms-model-info { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.ms-model-name { font-size: 15px; font-weight: 600; color: $color-text-primary; }
.ms-model-meta { font-size: 12px; color: $color-text-tertiary; }
.ms-status-dot { width: 8px; height: 8px; border-radius: 50%; background: $color-success; flex-shrink: 0; }
.ms-status-dot.degraded { background: #F59E0B; }
.ms-status-dot.down { background: $color-danger; }
.ms-status-tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: rgba(16,185,129,0.1); color: $color-success; &.degraded { background: rgba(245,158,11,0.1); color: #F59E0B; } &.down { background: rgba(239,68,68,0.1); color: $color-danger; } }
.ms-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; label { font-size: 13px; color: $color-text-primary; min-width: 90px; } }
.ms-unit { font-size: 12px; color: $color-text-tertiary; white-space: nowrap; }
.ms-model-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid $color-border; &:last-child { border-bottom: none; } }
.ms-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 20px; border-top: 1px solid $color-border; }
.ms-row-col { flex-wrap: wrap; gap: 8px; label { min-width: 70px; } input { flex: 1; min-width: 0; } }
.ms-test-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.ms-test-hint { font-size: 12px; color: $color-text-tertiary; }
</style>
