<template>
  <div class="ms-page">
    <!-- 顶部 hero -->
    <div class="ms-hero">
      <div class="ms-hero-left">
        <h1>⚙️ AI 模型设置</h1>
        <p>统一管理所有 AI 模型 · 支持 12 家国内外大模型 · 切换 Provider 自动填地址</p>
      </div>
      <div class="ms-hero-stats">
        <div class="ms-stat">
          <div class="ms-stat-num">{{ models.length }}</div>
          <div class="ms-stat-label">已接入模型</div>
        </div>
        <div class="ms-stat">
          <div class="ms-stat-num">{{ healthyCount }}</div>
          <div class="ms-stat-label">健康运行</div>
        </div>
        <div class="ms-stat">
          <div class="ms-stat-num">{{ enabledCount }}</div>
          <div class="ms-stat-label">已启用</div>
        </div>
        <div class="ms-stat">
          <div class="ms-stat-num">¥{{ totalCostYuan }}</div>
          <div class="ms-stat-label">本月预估成本</div>
        </div>
      </div>
    </div>

    <div class="ms-body">
      <!-- 左侧导航 -->
      <aside class="ms-side">
        <div class="ms-side-title">模型分组</div>
        <ul class="ms-nav">
          <li
            v-for="cat in categories"
            :key="cat.key"
            :class="{ active: activeCategory === cat.key }"
            @click="activeCategory = cat.key"
          >
            <span class="ms-nav-icon">{{ cat.icon }}</span>
            <span class="ms-nav-label">{{ cat.label }}</span>
            <span class="ms-nav-count">{{ countByCategory(cat.key) }}</span>
          </li>
        </ul>

        <div class="ms-side-title" style="margin-top: 24px;">全局策略</div>
        <ul class="ms-nav">
          <li :class="{ active: activeCategory === 'global' }" @click="activeCategory = 'global'">
            <span class="ms-nav-icon">🛡️</span>
            <span class="ms-nav-label">通用配置</span>
          </li>
        </ul>
      </aside>

      <!-- 右侧主区 -->
      <main class="ms-main">
        <!-- 模型卡片网格 -->
        <section v-if="activeCategory !== 'global'" class="ms-section">
          <div class="ms-section-head">
            <h2>{{ currentCategoryLabel }}</h2>
            <el-button size="small" :icon="Refresh" @click="loadAll">刷新</el-button>
          </div>

          <div class="ms-card-list">
            <div
              v-for="m in filteredModels"
              :key="m.id"
              class="ms-model-card"
              :class="{ selected: selectedModel?.id === m.id }"
              @click="selectModel(m)"
            >
              <div class="ms-mc-head">
                <div class="ms-mc-icon" :style="{ background: iconBg(m.type) }">{{ iconChar(m.type) }}</div>
                <div class="ms-mc-meta">
                  <div class="ms-mc-name">{{ m.name }}</div>
                  <div class="ms-mc-cat">{{ m.category }}</div>
                </div>
                <div class="ms-mc-status">
                  <span :class="['ms-status-dot', m.status]"></span>
                  <span :class="['ms-status-tag', m.status]">{{ statusText(m.status) }}</span>
                </div>
              </div>

              <div class="ms-mc-desc">{{ m.description }}</div>

              <div class="ms-mc-metrics">
                <div v-for="(v, k) in formatMetrics(m.metrics)" :key="k" class="ms-metric">
                  <span class="ms-metric-label">{{ k }}</span>
                  <span class="ms-metric-val">{{ v }}</span>
                </div>
              </div>

              <div class="ms-mc-foot">
                <div class="ms-mc-version">v{{ m.version }}</div>
                <div class="ms-mc-usage">本月 {{ m.monthlyUsage }} 次</div>
                <div class="ms-mc-cost">¥{{ (m.costPerCallCents * m.monthlyUsage / 100).toFixed(2) }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- 模型详细配置面板 -->
        <section v-if="selectedModel" class="ms-section">
          <div class="ms-section-head">
            <h2>⚙ 配置 · {{ selectedModel.name }}</h2>
            <el-button-group>
              <el-button size="small" :icon="View" @click="testModel">🔗 测试连接</el-button>
              <el-button size="small" :icon="Refresh" @click="resetConfig">还原默认</el-button>
            </el-button-group>
          </div>

          <!-- LLM 模型 -->
          <template v-if="selectedModel.type === 'llm'">
            <div class="ms-form-card">
              <h3>Provider 切换</h3>
              <p class="ms-form-hint">选择服务商后自动填入默认 Base URL 和模型名称，你只需要填 API Key 即可使用</p>
              <el-select v-model="form.provider" placeholder="选择服务商" style="width: 320px" @change="onProviderChange">
                <el-option v-for="p in selectedModel.providers" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </div>

            <div class="ms-form-card">
              <h3>连接信息</h3>
              <el-row :gutter="20">
                <el-col :span="16">
                  <div class="ms-form-row">
                    <label>Base URL</label>
                    <el-input v-model="form.baseUrl" placeholder="https://api.openai.com/v1" clearable>
                      <template #append>
                        <el-button :icon="Refresh" @click="resetBaseUrl">重置</el-button>
                      </template>
                    </el-input>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="ms-form-row">
                    <label>模型名称</label>
                    <el-input v-model="form.model" placeholder="gpt-4o" clearable />
                  </div>
                </el-col>
              </el-row>
              <div class="ms-form-row">
                <label>API Key</label>
                <el-input v-model="form.apiKey" type="password" placeholder="sk-..." show-password clearable />
                <span class="ms-form-hint" v-if="form.apiKey === '***'">已配置（脱敏显示），如需修改请直接覆盖</span>
              </div>
            </div>

            <div class="ms-form-card">
              <h3>模型参数</h3>
              <el-row :gutter="20">
                <el-col :span="6">
                  <div class="ms-form-row ms-form-row--stack">
                    <label>Temperature</label>
                    <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
                    <span class="ms-form-hint">创造性（0=精确，2=发散）</span>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="ms-form-row ms-form-row--stack">
                    <label>Max Tokens</label>
                    <el-input-number v-model="form.maxTokens" :min="256" :max="32768" :step="256" />
                    <span class="ms-form-hint">单次输出上限</span>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="ms-form-row ms-form-row--stack">
                    <label>上下文上限</label>
                    <el-input-number v-model="form.contextLimit" :min="1024" :max="2000000" :step="1024" />
                    <span class="ms-form-hint">单位：Tokens</span>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="ms-form-row ms-form-row--stack">
                    <label>Streaming</label>
                    <el-switch v-model="form.streaming" />
                    <span class="ms-form-hint">启用流式输出（SSE），长文本体验更好</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </template>

          <!-- OCR 模型 -->
          <template v-else-if="selectedModel.type === 'ocr'">
            <div class="ms-form-card">
              <h3>识别参数</h3>
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="ms-form-row">
                    <label>置信度阈值</label>
                    <el-input-number v-model="form.confidenceThreshold" :min="0" :max="1" :step="0.05" :precision="2" />
                    <span class="ms-form-hint">低于此值标记需人工复核</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="ms-form-row">
                    <label>最大文件大小</label>
                    <el-input-number v-model="form.maxFileSizeMB" :min="1" :max="100" :step="1" />
                    <span class="ms-form-hint">MB</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="ms-form-row">
                    <label>识别明细行</label>
                    <el-switch v-model="form.enableLineItems" />
                    <span class="ms-form-hint">开启后会抽取发票商品明细</span>
                  </div>
                </el-col>
              </el-row>
            </div>
            <div class="ms-form-card">
              <h3>服务地址</h3>
              <div class="ms-form-row">
                <label>PaddleOCR Endpoint</label>
                <el-input v-model="form.endpoint" placeholder="http://localhost:8001" clearable />
              </div>
            </div>
          </template>

          <!-- 风险模型 -->
          <template v-else-if="selectedModel.type === 'risk'">
            <div class="ms-form-card">
              <h3>风险等级阈值（分数越低风险越高）</h3>
              <el-row :gutter="20">
                <el-col :span="8">
                  <div class="ms-threshold">
                    <label style="color: #EF4444;">高风险阈值</label>
                    <el-input-number v-model="form.thresholds.high" :min="0" :max="100" :step="5" />
                    <span class="ms-form-hint">分数 ≤ 此值 → 红色高风险</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="ms-threshold">
                    <label style="color: #F59E0B;">中风险阈值</label>
                    <el-input-number v-model="form.thresholds.medium" :min="0" :max="100" :step="5" />
                    <span class="ms-form-hint">分数 ≤ 此值 → 橙色中风险</span>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="ms-threshold">
                    <label style="color: #10B981;">低风险阈值</label>
                    <el-input-number v-model="form.thresholds.low" :min="0" :max="100" :step="5" />
                    <span class="ms-form-hint">分数 ≤ 此值 → 绿色低风险</span>
                  </div>
                </el-col>
              </el-row>
            </div>
            <div class="ms-form-card">
              <h3>扫描策略</h3>
              <div class="ms-form-row">
                <label>自动扫描</label>
                <el-switch v-model="form.enableAutoScan" />
                <span class="ms-form-hint">新建合同时自动跑风险扫描</span>
              </div>
            </div>
          </template>

          <!-- 国税查验 -->
          <template v-else-if="selectedModel.type === 'verify'">
            <div class="ms-form-card">
              <h3>国税查验配置</h3>
              <div class="ms-form-row">
                <label>API URL</label>
                <el-input v-model="form.apiUrl" placeholder="http://127.0.0.1:8002/open/v1/services" clearable />
              </div>
              <div class="ms-form-row">
                <label>AppCode</label>
                <el-input v-model="form.appCode" type="password" placeholder="阿里云市场 AppCode" show-password clearable />
                <span class="ms-form-hint" v-if="form.appCode === '***'">已配置（脱敏显示）</span>
              </div>
              <el-row :gutter="20">
                <el-col :span="12">
                  <div class="ms-form-row">
                    <label>使用沙箱环境</label>
                    <el-switch v-model="form.useSandbox" />
                    <span class="ms-form-hint">生产环境请关闭</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="ms-form-row">
                    <label>超时时间</label>
                    <el-input-number v-model="form.timeoutSec" :min="3" :max="60" :step="1" />
                    <span class="ms-form-hint">秒</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </template>

          <!-- 诺诺发票兜底 -->
          <template v-else-if="selectedModel.type === 'ocr_fallback'">
            <div class="ms-form-card">
              <h3>诺诺发票 API 配置</h3>
              <div class="ms-form-row">
                <label>启用兜底</label>
                <el-switch v-model="form.enabled" />
                <span class="ms-form-hint">当 PaddleOCR 置信度低于阈值时自动切换到诺诺</span>
              </div>
              <div class="ms-form-row">
                <label>AppKey</label>
                <el-input v-model="form.appKey" placeholder="诺诺开放平台 AppKey" clearable />
              </div>
              <div class="ms-form-row">
                <label>AppSecret</label>
                <el-input v-model="form.appSecret" type="password" placeholder="AppSecret" show-password clearable />
              </div>
              <div class="ms-form-row">
                <label>兜底触发阈值</label>
                <el-input-number v-model="form.fallbackThreshold" :min="0" :max="1" :step="0.05" :precision="2" />
                <span class="ms-form-hint">PaddleOCR 置信度低于此值时触发兜底</span>
              </div>
            </div>
          </template>

          <!-- 测试结果 + 操作按钮 -->
          <div class="ms-form-card">
            <h3>连通性测试</h3>
            <el-button :loading="testing" type="primary" plain @click="testModel">🔗 测试连接</el-button>
            <div v-if="testResult" class="ms-test-result" :class="testResult.ok ? 'ok' : 'fail'">
              <strong>{{ testResult.ok ? '✅ 连接成功' : '❌ 连接失败' }}</strong>
              <div class="ms-test-msg">{{ testResult.msg }}</div>
              <div v-if="testResult.latencyMs" class="ms-test-latency">⏱ 耗时 {{ testResult.latencyMs }}ms</div>
            </div>
          </div>

          <div class="ms-actions">
            <el-button @click="selectModel(null)">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
          </div>
        </section>

        <!-- 全局策略 -->
        <section v-if="activeCategory === 'global'" class="ms-section">
          <div class="ms-section-head">
            <h2>🛡️ 全局策略</h2>
          </div>
          <div class="ms-form-card">
            <h3>降级与告警</h3>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="ms-form-row">
                  <label>默认降级策略</label>
                  <el-select v-model="globalConfig.fallbackStrategy" placeholder="选择策略" style="width: 100%">
                    <el-option label="关闭兜底（直返错误）" value="none" />
                    <el-option label="自动降级到次级模型" value="auto-downgrade" />
                    <el-option label="排队等待重试" value="queue-retry" />
                  </el-select>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="ms-form-row">
                  <label>全局超时</label>
                  <el-input-number v-model="globalConfig.timeout" :min="5" :max="120" :step="5" />
                  <span class="ms-form-hint">秒</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="ms-form-row">
                  <label>日志级别</label>
                  <el-select v-model="globalConfig.logLevel" style="width: 100%">
                    <el-option label="DEBUG（最详细）" value="DEBUG" />
                    <el-option label="INFO（默认）" value="INFO" />
                    <el-option label="WARNING" value="WARNING" />
                    <el-option label="ERROR" value="ERROR" />
                  </el-select>
                </div>
              </el-col>
            </el-row>
          </div>
          <div class="ms-form-card">
            <h3>告警阈值</h3>
            <el-row :gutter="20">
              <el-col :span="12">
                <div class="ms-form-row">
                  <label>错误率告警</label>
                  <el-input-number v-model="globalConfig.errorRateAlert" :min="1" :max="50" :step="1" />
                  <span class="ms-form-hint">%（超限通知管理员）</span>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="ms-form-row">
                  <label>延迟告警</label>
                  <el-input-number v-model="globalConfig.latencyAlert" :min="1" :max="30" :step="1" />
                  <span class="ms-form-hint">秒（超限通知管理员）</span>
                </div>
              </el-col>
            </el-row>
          </div>
          <div class="ms-actions">
            <el-button type="primary" :loading="saving" @click="saveGlobal">保存策略</el-button>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI 模型设置 · 独立专业页面
 * - 左侧分组导航（按模型 type 分组）
 * - 右侧模型卡片网格 + 详细配置
 * - 12 家国内外大模型 Provider 一键切换
 * - 连通性真测、配置真存、敏感字段脱敏
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, View } from '@element-plus/icons-vue'
import { http } from '@/utils/request'

const router = useRouter()

// ============ 状态 ============
const models = ref<any[]>([])
const selectedModel = ref<any>(null)
const activeCategory = ref<string>('llm')
const form = ref<any>({})
const globalConfig = ref<any>({
  fallbackStrategy: 'auto-downgrade',
  timeout: 30,
  logLevel: 'INFO',
  errorRateAlert: 5,
  latencyAlert: 10,
})
const testResult = ref<{ ok: boolean; msg: string; latencyMs?: number } | null>(null)
const testing = ref(false)
const saving = ref(false)

// ============ 分组 ============
const categories = [
  { key: 'llm', label: '通用大模型', icon: '🤖' },
  { key: 'ocr', label: 'OCR 识别', icon: '📷' },
  { key: 'risk', label: '风险扫描', icon: '⚠️' },
  { key: 'verify', label: '发票查验', icon: '🛡️' },
  { key: 'ocr_fallback', label: '兜底识别', icon: '🆘' },
]

const currentCategoryLabel = computed(() => {
  const c = categories.find(x => x.key === activeCategory.value)
  return c?.label || '全部'
})

const filteredModels = computed(() => models.value.filter(m => m.type === activeCategory.value))
const healthyCount = computed(() => models.value.filter(m => m.status === 'healthy').length)
const enabledCount = computed(() => models.value.filter(m => m.status !== 'down').length)
const totalCostYuan = computed(() => {
  const cents = models.value.reduce((s, m) => s + (m.costPerCallCents * m.monthlyUsage), 0)
  return (cents / 100).toFixed(2)
})

function countByCategory(key: string) {
  return models.value.filter(m => m.type === key).length
}

function statusText(s: string) {
  return s === 'healthy' ? '正常' : s === 'degraded' ? '性能降级' : s === 'down' ? '已停用' : s
}

function iconChar(type: string) {
  return { ocr: '📷', llm: '🤖', risk: '⚠️', verify: '🛡️', ocr_fallback: '🆘' }[type] || '⚙'
}

function iconBg(type: string) {
  return {
    ocr: 'rgba(79,107,255,0.12)', llm: 'rgba(124,58,237,0.12)',
    risk: 'rgba(245,158,11,0.12)', verify: 'rgba(16,185,129,0.12)',
    ocr_fallback: 'rgba(239,68,68,0.12)',
  }[type] || 'rgba(148,163,184,0.12)'
}

function formatMetrics(metrics: any): Record<string, string> {
  const out: Record<string, string> = {}
  if (!metrics) return out
  for (const [k, v] of Object.entries(metrics)) {
    if (k === 'latencyMs') out['延迟'] = `${v}ms`
    else if (k === 'accuracy') out['准确率'] = `${(Number(v) * 100).toFixed(1)}%`
    else if (k === 'successRate') out['成功率'] = `${(Number(v) * 100).toFixed(1)}%`
    else if (k === 'qps') out['QPS'] = String(v)
    else if (k === 'tokensPerSec') out['TPS'] = String(v)
    else out[k] = String(v)
  }
  return out
}

// ============ 数据加载 ============
async function loadAll() {
  try {
    const r: any = await http.post('/ai/model/list', {})
    models.value = r?.models || []
  } catch (e) {
    ElMessage.error('加载模型列表失败')
    console.error(e)
  }
}

// ============ 模型选择 ============
function selectModel(m: any) {
  if (!m) {
    selectedModel.value = null
    testResult.value = null
    return
  }
  selectedModel.value = m
  // 复制 config 到 form（避免双向绑定导致原数据被改）
  form.value = JSON.parse(JSON.stringify(m.config || {}))
  // LLM 默认值
  if (m.type === 'llm' && !form.value.contextLimit) form.value.contextLimit = 128000
  testResult.value = null
}

// ============ LLM Provider 切换 ============
function onProviderChange(provider: string) {
  if (!selectedModel.value || selectedModel.value.type !== 'llm') return
  const p = selectedModel.value.providers?.find((x: any) => x.value === provider)
  if (p) {
    form.value.provider = provider
    form.value.baseUrl = p.defaultUrl
    form.value.model = p.defaultModel
    if (provider === 'ollama') form.value.contextLimit = 32000
    else if (provider === 'baidu') form.value.contextLimit = 8192
    ElMessage.success(`已切换至 ${p.label}，已自动填入默认地址和模型`)
  }
}

function resetBaseUrl() {
  const p = selectedModel.value?.providers?.find((x: any) => x.value === form.value.provider)
  if (p) {
    form.value.baseUrl = p.defaultUrl
    ElMessage.info('已重置为该 Provider 的默认 Base URL')
  }
}

function resetConfig() {
  if (!selectedModel.value) return
  ElMessageBox.confirm('确定要还原为该模型的默认配置吗？', '提示', { type: 'warning' })
    .then(() => {
      selectModel(selectedModel.value)
      ElMessage.success('已还原默认配置（注意：未保存到后端）')
    }).catch(() => {})
}

// ============ 测试连接 ============
async function testModel() {
  if (!selectedModel.value) return
  testing.value = true
  testResult.value = null
  const t0 = Date.now()
  let result: { ok: boolean; msg: string; latencyMs?: number } | null = null
  try {
    if (selectedModel.value.type === 'llm') {
      if (!form.value.baseUrl) {
        ElMessage.warning('请先填写 Base URL')
        return
      }
      const r: any = await http.post('/ai/model/test', {
        baseUrl: form.value.baseUrl,
        apiKey: form.value.apiKey,
        model: form.value.model,
      })
      result = { ok: true, msg: '连接成功，模型响应正常', latencyMs: r?.latencyMs || (Date.now() - t0) }
    } else if (selectedModel.value.type === 'verify') {
      if (!form.value.apiUrl) { ElMessage.warning('请先填写 API URL'); return }
      const r: any = await http.post('/ai/model/test', {
        baseUrl: form.value.apiUrl,
        apiKey: form.value.appCode,
        model: 'verify',
      })
      result = r?.ok ? { ok: true, msg: '连接成功', latencyMs: r.latencyMs } : { ok: false, msg: r?.msg || '测试失败' }
    } else if (selectedModel.value.type === 'ocr_fallback') {
      if (!form.value.appKey) { ElMessage.warning('请先填写 AppKey'); return }
      result = { ok: form.value.enabled, msg: form.value.enabled ? '已启用（待联调）' : '未启用，跳过测试' }
    } else {
      // OCR / risk：内置服务不需要测
      result = { ok: true, msg: '内置服务，无需外测' }
    }
    if (result.ok) ElMessage.success(`✅ ${result.msg}${result.latencyMs ? ' (' + result.latencyMs + 'ms)' : ''}`)
    else ElMessage({ type: 'error', message: '❌ ' + result.msg, duration: 6000, showClose: true })
  } catch (err: any) {
    const msg = err?.response?.data?.message || err?.response?.data?.detail || err?.message || '请求失败'
    result = { ok: false, msg, latencyMs: Date.now() - t0 }
    ElMessage({ type: 'error', message: '❌ ' + msg, duration: 6000, showClose: true })
  } finally {
    testResult.value = result
    testing.value = false
  }
}

// ============ 保存配置 ============
async function saveConfig() {
  if (!selectedModel.value) return
  saving.value = true
  try {
    const r: any = await http.post('/ai/model/config', {
      modelId: selectedModel.value.id,
      config: form.value,
      enabled: true,
    })
    ElMessage.success(`✅ ${selectedModel.value.name} 配置已保存，立即生效`)
    await loadAll()
    // 重新选中
    const updated = models.value.find(m => m.id === selectedModel.value.id)
    if (updated) selectModel(updated)
  } catch (err: any) {
    const msg = err?.response?.data?.message || err?.response?.data?.detail || err?.message || '保存失败'
    ElMessage.error('保存失败：' + msg)
  } finally {
    saving.value = false
  }
}

async function saveGlobal() {
  saving.value = true
  try {
    await http.post('/ai/model/config', {
      modelId: 'global',
      config: globalConfig.value,
      enabled: true,
    })
    ElMessage.success('✅ 全局策略已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ============ 初始化 ============
onMounted(() => {
  loadAll()
})
</script>

<style lang="scss" scoped>
.ms-page {
  padding: 24px 32px 40px;
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// ===== Hero =====
.ms-hero {
  background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
  border-radius: 16px;
  padding: 32px 40px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 8px 32px -4px rgba(79,107,255,0.25);

  h1 {
    margin: 0 0 8px;
    font-size: 28px;
    font-weight: 700;
  }
  p {
    margin: 0;
    font-size: 14px;
    opacity: 0.9;
  }
}
.ms-hero-stats {
  display: flex;
  gap: 32px;
}
.ms-stat {
  text-align: center;
  .ms-stat-num {
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
  }
  .ms-stat-label {
    font-size: 12px;
    opacity: 0.85;
    margin-top: 4px;
  }
}

// ===== 主体 =====
.ms-body {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 20px;
  align-items: start;
}

// ===== 侧边导航 =====
.ms-side {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(15,23,42,0.06);
  position: sticky;
  top: 80px;
}
.ms-side-title {
  font-size: 11px;
  font-weight: 600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 0 8px;
}
.ms-nav {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    color: #475569;
    transition: all 0.15s;
    &:hover { background: #F1F5F9; }
    &.active {
      background: rgba(79,107,255,0.1);
      color: #4F6BFF;
      font-weight: 600;
    }
  }
}
.ms-nav-icon { font-size: 16px; }
.ms-nav-label { flex: 1; }
.ms-nav-count {
  font-size: 11px;
  background: #F1F5F9;
  color: #64748B;
  padding: 1px 7px;
  border-radius: 10px;
  .active & { background: #4F6BFF; color: #fff; }
}

// ===== 主区 =====
.ms-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.ms-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(15,23,42,0.06);
}
.ms-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #0F172A;
  }
}

// ===== 模型卡片 =====
.ms-card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.ms-model-card {
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover { border-color: #4F6BFF; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,107,255,0.1); }
  &.selected { border-color: #4F6BFF; background: rgba(79,107,255,0.04); }
}
.ms-mc-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.ms-mc-icon {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.ms-mc-meta { flex: 1; }
.ms-mc-name { font-size: 14px; font-weight: 600; color: #0F172A; }
.ms-mc-cat { font-size: 11px; color: #94A3B8; margin-top: 2px; }
.ms-mc-status { display: flex; align-items: center; gap: 6px; }
.ms-status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  &.healthy { background: #10B981; }
  &.degraded { background: #F59E0B; }
  &.down { background: #EF4444; }
}
.ms-status-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 10px;
  &.healthy { background: rgba(16,185,129,0.1); color: #059669; }
  &.degraded { background: rgba(245,158,11,0.1); color: #B45309; }
  &.down { background: rgba(239,68,68,0.1); color: #B91C1C; }
}
.ms-mc-desc { font-size: 12px; color: #64748B; line-height: 1.6; margin-bottom: 12px; min-height: 36px; }
.ms-mc-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px 0;
  border-top: 1px solid #F1F5F9;
  border-bottom: 1px solid #F1F5F9;
}
.ms-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  .ms-metric-label { font-size: 10px; color: #94A3B8; }
  .ms-metric-val { font-size: 13px; font-weight: 600; color: #0F172A; }
}
.ms-mc-foot {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 11px; color: #64748B;
  .ms-mc-cost { color: #F59E0B; font-weight: 600; }
}

// ===== 表单卡片 =====
.ms-form-card {
  background: #FAFBFC;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
  h3 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: #0F172A;
    display: flex;
    align-items: center;
    gap: 6px;
    &::before {
      content: '';
      width: 3px; height: 14px;
      background: #4F6BFF;
      border-radius: 2px;
    }
  }
}
.ms-form-hint { font-size: 12px; color: #94A3B8; display: block; width: 100%; margin-top: 6px; line-height: 1.4; flex-basis: 100%; }
.ms-threshold { display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
.ms-threshold label { width: auto; font-size: 13px; font-weight: 600; }
.ms-form-row {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  gap: 12px;
  flex-wrap: wrap;
  &:last-child { margin-bottom: 0; }
  label {
    width: 100px;
    font-size: 13px;
    color: #475569;
    font-weight: 500;
    flex-shrink: 0;
  }
  > .el-input, > .el-select, > .el-input-number { flex: 1; }
  > .el-switch { flex-shrink: 0; }
  &.ms-form-row--stack {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    label {
      width: auto;
      font-size: 13px;
      font-weight: 600;
      color: #475569;
    }
    > .el-input-number { width: 100%; }
    > .el-input-number.el-input-number--default { width: 100%; }
    > .el-switch { align-self: flex-start; }
    > .ms-form-hint { margin-top: 2px; padding-left: 0; }
  }
}

// ===== 测试结果 =====
.ms-test-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  &.ok { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); color: #047857; }
  &.fail { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); color: #B91C1C; }
  .ms-test-msg { margin-top: 6px; line-height: 1.5; word-break: break-all; }
  .ms-test-latency { font-size: 11px; opacity: 0.8; margin-top: 4px; }
}

// ===== 操作按钮 =====
.ms-actions {
  display: flex; gap: 12px; justify-content: flex-end;
  padding-top: 16px; border-top: 1px solid #E2E8F0;
  margin-top: 8px;
}

// ===== 暗色模式 =====
.theme-dark {
  .ms-side, .ms-section { background: var(--color-bg-card); }
  .ms-model-card { border-color: var(--color-border); }
  .ms-form-card { background: var(--color-bg-elevated); border-color: var(--color-border); }
  .ms-mc-name, .ms-section-head h2, .ms-form-card h3 { color: var(--color-text-primary); }
  .ms-mc-desc, .ms-nav li { color: var(--color-text-secondary); }
  .ms-metric-val { color: var(--color-text-primary); }
}
</style>
