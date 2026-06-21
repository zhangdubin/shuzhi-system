<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'

const fileInput = ref<HTMLInputElement>()
const fileName = ref('')
const previewUrl = ref<string>('')
const submitting = ref(false)
const taskId = ref('')
const progress = ref(0)
const status = ref('idle')
const result = ref<Record<string, unknown> | null>(null)

const steps = ['文件上传', 'OCR 识别', '字段抽取', '结果生成']

// 字段抽取结果（design/ai-extract-demo.html 风格的字段卡 + 置信度）
interface ExtractedField {
  key: string
  label: string
  value: string
  confidence: number
  group?: string
  required?: boolean
  warning?: string
}

const fields = ref<ExtractedField[]>([])

// 抽取完成后的统计
const summary = ref({
  total: 0,
  high: 0,
  mid: 0,
  low: 0,
  cost: 0.002,
  model: 'PaddleOCR-v3',
  elapsed: '1.8s',
})

const overallScore = computed(() => {
  if (!fields.value.length) return 0
  const sum = fields.value.reduce((a, b) => a + b.confidence, 0)
  return Math.round((sum / fields.value.length) * 100)
})

function confClass(v: number) {
  if (v >= 0.9) return 'conf-high'
  if (v >= 0.7) return 'conf-mid'
  return 'conf-low'
}

function confLabel(v: number) {
  return `${Math.round(v * 100)}%`
}

function handleFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  fileName.value = f.name
  previewUrl.value = URL.createObjectURL(f)
}

async function handleExtract() {
  if (!fileName.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  submitting.value = true
  status.value = 'uploading'
  progress.value = 0
  result.value = null
  fields.value = []
  summary.value = { total: 0, high: 0, mid: 0, low: 0, cost: 0, model: '', elapsed: '' }

  try {
    // 同步接口：直接返回 fields（不再轮询 taskDetail）
    const r = await aiApi.extractInvoice({
      fileId: 'demo-' + Date.now(),
      fileUrl: previewUrl.value || `https://placeholder/${fileName.value}`,
      type: 'invoice',
    })
    taskId.value = r.taskId || r.meta?.traceId || ''
    status.value = 'done'
    progress.value = 100

    // 把后端 fields 转成 ExtractedField[] 渲染
    if (r.fields) {
      const ext: ExtractedField[] = []
      const groupMap: Record<string, string> = {
        invoiceCode: '基础', invoiceNo: '基础', issueDate: '基础', invoiceType: '基础',
        buyerName: '购销方', buyerTaxId: '购销方', sellerName: '购销方',
        amount: '金额', taxAmount: '金额', totalAmount: '金额', totalAmountCn: '金额', taxRate: '金额',
        remark: '其他',
      }
      const labelMap: Record<string, string> = {
        invoiceCode: '发票代码', invoiceNo: '发票号码', issueDate: '开票日期', invoiceType: '发票类型',
        buyerName: '购方名称', buyerTaxId: '统一社会信用代码', sellerName: '销方名称',
        amount: '金额（不含税）', taxAmount: '税额', totalAmount: '价税合计（小写）', totalAmountCn: '价税合计（大写）',
        taxRate: '税率', remark: '备注',
      }
      for (const [key, info] of Object.entries(r.fields)) {
        ext.push({
          key,
          label: labelMap[key] || key,
          value: String(info.value),
          confidence: info.confidence,
          group: groupMap[key] || '其他',
          required: ['invoiceCode', 'invoiceNo', 'issueDate', 'buyerName', 'totalAmountCn'].includes(key),
        })
      }
      result.value = r
      fields.value = ext
      summary.value = {
        total: ext.length,
        high: ext.filter((f) => f.confidence >= 90).length,
        mid: ext.filter((f) => f.confidence >= 70 && f.confidence < 90).length,
        low: ext.filter((f) => f.confidence < 70).length,
        cost: r.meta.costCents,
        model: r.meta.model,
        elapsed: `${r.meta.durationMs}ms`,
      }
      ElMessage.success(`AI 抽取完成 · 耗时 ${r.meta.durationMs}ms`)
    } else {
      // 兜底用 demo 数据
      fillDemoFields()
    }
  } catch (e: any) {
    console.error(e)
    ElMessage.error('AI 抽取失败：' + (e?.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

function fillDemoFields() {
  // 与 design/ai-extract-demo.html 1:1 对齐的字段集合
  const demo: ExtractedField[] = [
    { key: 'invoiceCode', label: '发票代码', value: '011002000000', confidence: 0.99, group: '基础', required: true },
    { key: 'invoiceNo', label: '发票号码', value: '12345678', confidence: 0.99, group: '基础', required: true },
    { key: 'issueDate', label: '开票日期', value: '2024-05-21', confidence: 0.98, group: '基础', required: true },
    { key: 'invoiceType', label: '发票类型', value: '增值税电子专用发票', confidence: 0.96, group: '基础' },
    { key: 'buyerName', label: '购方名称', value: '示例客户有限公司', confidence: 0.97, group: '购销方', required: true },
    { key: 'buyerTaxNo', label: '统一社会信用代码', value: '91110000XXXXXXXX', confidence: 0.92, group: '购销方' },
    { key: 'sellerName', label: '销方名称', value: '数智科技服务（北京）有限公司', confidence: 0.99, group: '购销方' },
    { key: 'amountExclTax', label: '金额（不含税）', value: '95,000.00', confidence: 0.96, group: '金额', required: true },
    { key: 'taxAmount', label: '税额', value: '5,700.00', confidence: 0.96, group: '金额' },
    { key: 'totalAmountCn', label: '价税合计（大写）', value: '壹拾万零柒佰元整', confidence: 0.98, group: '金额', required: true },
    { key: 'totalAmount', label: '价税合计（小写）', value: '100,700.00', confidence: 0.99, group: '金额' },
    { key: 'taxRate', label: '税率', value: '6%', confidence: 0.72, group: '金额', warning: '中置信度，建议复核' },
    { key: 'remark', label: '备注', value: '合同号 C-2024-123（AI 自动识别并关联）', confidence: 0.95, group: '其他' },
  ]
  fields.value = demo
  summary.value = {
    total: demo.length,
    high: demo.filter((d) => d.confidence >= 0.9).length,
    mid: demo.filter((d) => d.confidence >= 0.7 && d.confidence < 0.9).length,
    low: demo.filter((d) => d.confidence < 0.7).length,
    cost: 0.002,
    model: 'PaddleOCR-v3',
    elapsed: '1.8s',
  }
}

function handleAccept() {
  ElMessage.success('已采纳 AI 抽取结果')
}

function handleReject() {
  ElMessage.info('已转人工复核')
}

function handleReExtract() {
  handleExtract()
}

async function handleExportJson() {
  if (!fields.value.length) {
    ElMessage.warning('暂无抽取结果')
    return
  }
  const obj = fields.value.reduce((a, b) => {
    a[b.key] = b.value
    return a
  }, {} as Record<string, string>)
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ai-extract-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出 JSON')
}

async function handleCopy() {
  if (!fields.value.length) {
    ElMessage.warning('暂无抽取结果')
    return
  }
  const text = fields.value.map((f) => `${f.label}: ${f.value}`).join('\n')
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    // fallback：选中文本
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制到剪贴板')
  }
}

// 字段按 group 分组
const groupedFields = computed(() => {
  const map = new Map<string, ExtractedField[]>()
  for (const f of fields.value) {
    const g = f.group || '其他'
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(f)
  }
  return Array.from(map.entries())
})

const hasResult = computed(() => fields.value.length > 0)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>📷 AI 智能字段抽取</h2>
        <p class="page-desc">上传发票/合同图片，AI 自动抽取关键字段并结构化展示</p>
      </div>
    </div>

    <!-- AI 演示横幅（design/ai-extract-demo.html demo-banner 同款） -->
    <div class="demo-banner">
      <div class="ico">✦</div>
      <div>
        <strong>AI 字段抽取演示</strong> — 左侧为原始材料，右侧为 AI 抽取结果（带
        <span class="ai-badge">AI</span> 角标）。本月本能力已节省录入时间 <strong>52 小时</strong>。
      </div>
    </div>

    <!-- 步骤条（保留原有 4 步骤）-->
    <el-steps :active="Math.floor(progress / 25)" finish-status="success" align-center style="margin-bottom: 20px">
      <el-step v-for="s in steps" :key="s" :title="s" />
    </el-steps>

    <el-row :gutter="20">
      <!-- 左侧：原图（design/ai-extract-demo.html demo-source）-->
      <el-col :span="10">
        <div class="demo-card">
          <div class="demo-card-head">
            <h3>📄 原始材料 <span class="text-tertiary" style="font-size: 11px; font-weight: normal">{{ fileName || '尚未选择文件' }}</span></h3>
            <span v-if="previewUrl" class="text-tertiary" style="font-size: 11px">{{ status }}</span>
          </div>
          <div class="demo-card-body">
            <input ref="fileInput" type="file" hidden accept="image/*,.pdf" @change="handleFile" />
            <div v-if="!previewUrl" class="upload-zone" @click="fileInput?.click()">
              <div style="text-align: center; color: #94A3B8">
                <div style="font-size: 48px">📄</div>
                <p>点击选择文件</p>
                <p class="text-tertiary" style="font-size: 12px">支持 JPG / PNG / PDF · 单张最大 10MB</p>
              </div>
            </div>
            <div v-else class="source-preview">
              <img v-if="previewUrl.startsWith('blob:') || previewUrl.startsWith('data:') || previewUrl.startsWith('http')" :src="previewUrl" alt="原始材料" />
              <div v-else class="fake-invoice">
                <div class="fi-title">增值税电子专用发票</div>
                <div class="fi-row"><span class="fi-label">发票代码：</span><span class="fi-value">011002000000</span></div>
                <div class="fi-row"><span class="fi-label">发票号码：</span><span class="fi-value">12345678</span></div>
                <div class="fi-row"><span class="fi-label">开票日期：</span><span class="fi-value">2024年05月21日</span></div>
                <div class="fi-row"><span class="fi-label">购方名称：</span><span class="fi-value">示例客户有限公司</span></div>
                <div class="fi-row"><span class="fi-label">销方名称：</span><span class="fi-value">数智科技服务（北京）有限公司</span></div>
                <div class="fi-row" style="font-weight: 600; margin-top: 6px">
                  <span class="fi-label">价税合计：</span>
                  <span class="fi-value">壹拾万零柒佰元整（¥100,700.00）</span>
                </div>
              </div>

              <!-- AI 抽取框（叠加在原图上）-->
              <div v-if="hasResult" class="extract-box" style="top: 18%; left: 30%; width: 45%; height: 6%" data-label="购方名称" />
              <div v-if="hasResult" class="extract-box" style="top: 22%; left: 42%; width: 50%; height: 6%" data-label="统一社会信用代码" />
              <div v-if="hasResult" class="extract-box" style="top: 60%; left: 30%; width: 60%; height: 6%" data-label="价税合计" />
            </div>
          </div>
          <div class="demo-card-foot">
            <el-button v-if="!previewUrl" type="primary" style="width: 100%" @click="fileInput?.click()">📁 选择文件</el-button>
            <el-button v-else style="width: 100%" @click="fileInput?.click()">↻ 重新选择</el-button>
            <el-button type="primary" :loading="submitting" style="width: 100%; margin-top: 8px" @click="handleExtract">
              ✨ 开始 AI 抽取
            </el-button>
          </div>
        </div>
      </el-col>

      <!-- 右侧：抽取结果（design/ai-extract-demo.html demo-result）-->
      <el-col :span="14">
        <div class="demo-card">
          <div class="demo-card-head">
            <h3>✦ AI 抽取结果 <span class="ai-badge" style="font-size: 10.5px">自动填入</span></h3>
            <span v-if="hasResult" class="text-tertiary" style="font-size: 11.5px">用时 {{ summary.elapsed }}</span>
          </div>
          <div class="demo-card-body">
            <!-- 抽取中：进度条 -->
            <div v-if="submitting || (status !== 'idle' && !hasResult)" class="demo-progress">
              <div class="stage">
                <span class="label">
                  <span class="ai-loading">抽取中</span>
                  <span>正在抽取字段...</span>
                </span>
                <span class="pct">{{ Math.round(progress) }}%</span>
              </div>
              <div class="bar"><div class="fill" :style="{ width: `${progress}%` }" /></div>
              <div v-if="taskId" style="margin-top: 8px; font-size: 11.5px; color: #94A3B8">
                任务 ID：{{ taskId }} · 状态 {{ status }}
              </div>
            </div>

            <!-- 暂无结果占位 -->
            <el-empty v-if="!hasResult && !submitting" description="上传文件后查看抽取结果" />

            <!-- 抽取完成：总览评分 + 置信度图例 + 字段块 -->
            <template v-if="hasResult">
              <!-- 总览评分卡 -->
              <div class="ai-summary-card">
                <div class="score">{{ overallScore }}</div>
                <div class="info">
                  <strong>整体置信度 {{ overallScore }} 分（{{ overallScore >= 90 ? '优秀' : overallScore >= 70 ? '良好' : '需复核' }}）</strong>
                  <br />
                  共抽取 {{ summary.total }} 个字段 · {{ summary.high }} 个高置信度
                  <span v-if="summary.mid"> · {{ summary.mid }} 个需复核</span>
                </div>
              </div>

              <!-- 置信度图例 -->
              <div class="confidence-legend">
                <div class="item"><span class="dot" style="background: #10B981" />高 ≥ 90%</div>
                <div class="item"><span class="dot" style="background: #F59E0B" />中 70-90%</div>
                <div class="item"><span class="dot" style="background: #EF4444" />低 &lt; 70%</div>
                <div class="item" style="margin-left: auto; color: var(--color-primary)">查看抽取历史趋势 →</div>
              </div>

              <!-- 字段块（按 group 分组，每条 term-block）-->
              <div v-for="[group, list] in groupedFields" :key="group" class="field-group">
                <h4 class="group-title">{{ group }}</h4>
                <div
                  v-for="f in list"
                  :key="f.key"
                  :class="['term-block', 'field-block', confClass(f.confidence), { 'field-required': f.required, 'field-warning': f.warning }]"
                >
                  <div class="field-label-row">
                    <span class="field-label">
                      {{ f.label }}
                      <span v-if="f.required" class="req">*</span>
                      <span class="ai-badge">AI</span>
                    </span>
                    <span :class="['conf-pill', confClass(f.confidence)]">{{ confLabel(f.confidence) }}</span>
                  </div>
                  <div class="field-value">{{ f.value }}</div>
                  <div v-if="f.warning" class="field-warning">⚠ {{ f.warning }}</div>
                </div>
              </div>

              <!-- 智能关联建议 -->
              <div class="ai-suggestion">
                <div class="ai-s-icon">🔗</div>
                <div class="ai-s-body">
                  <div class="ai-s-title">智能关联建议</div>
                  <div class="ai-s-desc">
                    AI 检测到备注中包含合同号 <strong>C-2024-123</strong>，建议自动关联到
                    <strong>「数智化二期」项目</strong>，并匹配 <strong>客户：示例客户有限公司</strong>。
                  </div>
                  <div class="ai-s-actions">
                    <el-button size="small" type="success" @click="handleAccept">✓ 采纳关联</el-button>
                    <el-button size="small">手动选择</el-button>
                  </div>
                </div>
              </div>
            </template>
          </div>

          <!-- 底部操作栏（design 同款 result-actions）-->
          <div v-if="hasResult" class="result-actions">
            <div class="meta">
              ✦ 抽取消耗时 <strong>{{ summary.elapsed }}</strong> · 模型 <strong>{{ summary.model }}</strong> · 成本 <strong>{{ summary.cost.toFixed(3) }} 元</strong>
            </div>
            <div style="display: flex; gap: 8px">
              <el-button size="small" @click="handleCopy">📋 复制</el-button>
              <el-button size="small" @click="handleExportJson">📥 导出 JSON</el-button>
              <el-button size="small" @click="handleReExtract">🔄 重新抽取</el-button>
              <el-button size="small" type="success" @click="handleAccept">✓ 采纳结果</el-button>
              <el-button size="small" @click="handleReject">✗ 转人工</el-button>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
/* 演示横幅 */
.demo-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(124,58,237,0.04) 0%, rgba(79,107,255,0.04) 100%);
  border: 1px solid rgba(124,58,237,0.18);
  border-radius: $radius-lg;
  margin-bottom: 16px;
  font-size: 13px;
  color: $color-text-secondary;
  .ico {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #7C3AED, #4F6BFF);
    border-radius: $radius-md;
    color: #fff;
    display: grid; place-items: center;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
  }
  strong { color: $color-text-primary; }
}

/* AI badge */
.ai-badge {
  display: inline-block;
  padding: 1px 6px;
  background: linear-gradient(135deg, #7C3AED, #4F6BFF);
  color: #fff;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 600;
  margin-left: 4px;
  vertical-align: middle;
}
.ai-loading {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, #7C3AED, #4F6BFF);
  color: #fff;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
  animation: ai-pulse 1.5s infinite;
}
@keyframes ai-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 左右分栏卡片 */
.demo-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  overflow: hidden;
  margin-bottom: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.demo-card-head {
  padding: 14px 18px;
  border-bottom: 1px solid $color-border;
  display: flex;
  justify-content: space-between;
  align-items: center;
  h3 {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
    display: flex; align-items: center; gap: 6px;
  }
}
.demo-card-body {
  padding: 18px;
  background: #F8FAFC;
  flex: 1;
}
.demo-card-foot {
  padding: 12px 18px;
  border-top: 1px solid $color-border;
  background: #fff;
}

/* 上传区 */
.upload-zone {
  border: 2px dashed $color-border-strong;
  border-radius: $radius-md;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fff;
  transition: all 0.2s;
  &:hover { border-color: $color-primary; background: rgba(79,107,255,0.04); }
}

/* 左侧原图预览 */
.source-preview {
  position: relative;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  overflow: hidden;
  img {
    display: block;
    max-width: 100%;
    max-height: 540px;
    margin: 0 auto;
  }
}
.fake-invoice {
  padding: 18px 22px;
  font-size: 12px;
  color: #1E293B;
  .fi-title {
    text-align: center;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 14px;
    color: #0F172A;
  }
  .fi-row {
    display: flex;
    margin-bottom: 6px;
    .fi-label { color: #64748B; min-width: 88px; }
    .fi-value { color: #0F172A; font-weight: 500; }
  }
}

/* AI 抽取框高亮 */
.extract-box {
  position: absolute;
  border: 2px solid #7C3AED;
  background: rgba(124, 58, 237, 0.08);
  border-radius: 3px;
  pointer-events: none;
  animation: extract-pulse 1.5s infinite;
  &::after {
    content: attr(data-label);
    position: absolute;
    bottom: 100%;
    left: 0;
    background: linear-gradient(135deg, #7C3AED, #4F6BFF);
    color: #fff;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 3px 3px 0 0;
    font-weight: 600;
    white-space: nowrap;
  }
}
@keyframes extract-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.3); }
  50% { box-shadow: 0 0 0 6px rgba(124, 58, 237, 0); }
}

/* 进度条 */
.demo-progress {
  background: rgba(124, 58, 237, 0.05);
  border: 1px solid rgba(124, 58, 237, 0.18);
  border-radius: $radius-md;
  padding: 14px 18px;
  .stage {
    font-size: 12.5px;
    color: $color-text-secondary;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    .label { display: flex; align-items: center; gap: 8px; }
    .pct { color: #7C3AED; font-weight: 600; }
  }
  .bar {
    height: 6px;
    background: #fff;
    border-radius: 999px;
    overflow: hidden;
    .fill {
      height: 100%;
      background: linear-gradient(90deg, #7C3AED, #4F6BFF);
      border-radius: 999px;
      transition: width 0.3s ease;
    }
  }
}

/* 总览评分 */
.ai-summary-card {
  background: rgba(124, 58, 237, 0.05);
  border: 1px solid rgba(124, 58, 237, 0.18);
  border-radius: $radius-md;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  .score {
    font-size: 28px;
    font-weight: 700;
    color: #7C3AED;
    font-family: $font-family-mono;
  }
  .info { flex: 1; font-size: 12.5px; color: $color-text-secondary; line-height: 1.5; }
  .info strong { color: $color-text-primary; }
}

/* 置信度图例 */
.confidence-legend {
  display: flex;
  gap: 14px;
  padding: 10px 14px;
  background: #F8FAFC;
  border-radius: $radius-sm;
  margin-bottom: 16px;
  font-size: 12px;
  color: $color-text-secondary;
  .item { display: flex; align-items: center; gap: 5px; }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
  }
}

/* 字段分组 */
.field-group {
  margin-bottom: 16px;
  .group-title {
    font-size: 12.5px;
    font-weight: 600;
    color: $color-text-secondary;
    margin: 0 0 8px 0;
    padding-left: 4px;
  }
}

/* term-block 字段块（用 detail.scss 的 term-block 风格 + AI 高亮） */
.field-block {
  position: relative;
  margin-bottom: 8px;
  padding: 12px 14px;
  background: linear-gradient(90deg, #F5F3FF 0%, #FAFBFF 100%);
  border-left: 3px solid #7C3AED;
  &.conf-high { border-left-color: #10B981; background: linear-gradient(90deg, #ECFDF5 0%, #FAFBFF 100%); }
  &.conf-mid { border-left-color: #F59E0B; background: linear-gradient(90deg, #FFFBEB 0%, #FAFBFF 100%); }
  &.conf-low { border-left-color: #EF4444; background: linear-gradient(90deg, #FEF2F2 0%, #FAFBFF 100%); }
  &.field-required {
    .field-label::before {
      content: '★';
      color: #7C3AED;
      margin-right: 3px;
      font-size: 11px;
    }
  }
  &.field-warning {
    border-left-width: 4px;
  }
  .field-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .field-label {
    font-size: 12.5px;
    font-weight: 500;
    color: $color-text-primary;
    display: flex;
    align-items: center;
    .req { color: $color-danger; margin: 0 3px; }
  }
  .field-value {
    font-size: 13.5px;
    color: $color-text-primary;
    font-weight: 500;
    word-break: break-all;
  }
  .field-warning {
    font-size: 11.5px;
    color: #B45309;
    margin-top: 4px;
  }
  .conf-pill {
    min-width: 42px;
    text-align: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    &.conf-high { background: rgba(16,185,129,0.12); color: #047857; }
    &.conf-mid { background: rgba(245,158,11,0.12); color: #B45309; }
    &.conf-low { background: rgba(239,68,68,0.12); color: #B91C1C; }
  }
}

/* 智能关联建议 */
.ai-suggestion {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: linear-gradient(135deg, rgba(124,58,237,0.06), rgba(79,107,255,0.06));
  border: 1px solid rgba(124,58,237,0.2);
  border-radius: $radius-md;
  margin-top: 16px;
  .ai-s-icon { font-size: 20px; flex-shrink: 0; }
  .ai-s-body { flex: 1; }
  .ai-s-title {
    font-size: 13px;
    font-weight: 600;
    color: $color-text-primary;
    margin-bottom: 4px;
  }
  .ai-s-desc {
    font-size: 12.5px;
    color: $color-text-secondary;
    line-height: 1.6;
    margin-bottom: 8px;
    strong { color: $color-primary; }
  }
}

/* 底部操作栏 */
.result-actions {
  display: flex;
  gap: 10px;
  padding: 12px 18px;
  background: #F8FAFC;
  border-top: 1px solid $color-border;
  justify-content: space-between;
  align-items: center;
  .meta { font-size: 12px; color: $color-text-tertiary; }
}
</style>