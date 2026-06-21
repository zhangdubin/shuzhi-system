<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi, type OcrResult } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const activeTab = ref('result')
const result = ref<OcrResult | null>(null)

// 顶部摘要信息（与 design/invoice-detail.html 1:1 对齐）
const summary = ref({
  invoiceNo: '25113300000012345678',
  invoiceCode: '011002600611',
  invoiceType: '增值税电子普通发票',
  totalAmount: 28000,
  sellerName: '上海数智信息技术有限公司',
  buyerName: '万象科技有限公司',
  buyerTaxNo: '91310000MA1FL01X9G',
  issueDate: '2026-06-08',
  confidence: 0.968,
  ocrStatus: '识别成功' as '识别成功' | '待复核' | '识别失败',
  verifyStatus: 'verified' as 'verified' | 'pending' | 'failed',
})

const previewUrl = ref<string>('')

// 识别字段（双列 info-grid 用）
const fields = ref({
  invoiceType: '增值税电子普通发票',
  invoiceCode: '011002600611',
  invoiceNo: '25113300000012345678',
  issueDate: '2026-06-08',
  checkCode: '5102 6583 1234 5678 9AB',
  sellerName: '上海数智信息技术有限公司',
  sellerTaxNo: '91310000MA1FL01X9G',
  sellerAccount: '招商银行上海分行 6225 **** 8888',
  buyerName: '万象科技有限公司',
  buyerTaxNo: '91310000MA1FL01X9G',
  buyerAccount: '工商银行上海分行 6222 **** 1234',
  amountExclTax: 26415.09,
  taxAmount: 1584.91,
  totalAmount: 28000,
  totalAmountCn: '贰万捌仟元整',
  remark: 'Q2 服务费尾款',
})

// 字段置信度（用于进度条与对比）
const fieldConfidences: Record<string, number> = {
  invoiceType: 0.99,
  invoiceCode: 0.97,
  invoiceNo: 0.99,
  issueDate: 0.87,
  checkCode: 0.92,
  sellerName: 0.98,
  sellerTaxNo: 0.95,
  sellerAccount: 0.88,
  buyerName: 0.98,
  buyerTaxNo: 0.96,
  buyerAccount: 0.85,
  amountExclTax: 0.93,
  taxAmount: 0.93,
  totalAmount: 0.82,
  totalAmountCn: 0.94,
  remark: 0.91,
}

// 商品明细
const items = ref([
  {
    name: '*软件服务*技术服务费',
    spec: '—',
    qty: 1,
    price: 26415.09,
    amount: 26415.09,
    taxRate: '6%',
    taxAmount: 1584.91,
  },
])

// 查验记录
const verifyRecords = ref([
  { at: '2026-06-12 09:24:11', result: '通过', source: '国税总局查验', reason: '—', elapsed: '1.2s' },
  { at: '2026-06-12 09:23:58', result: '通过', source: '本地 OCR + 规则', reason: '—', elapsed: '0.4s' },
])

// 报销记录
const expenseLinks = ref([
  { code: 'EXP-2026-0612-001', name: '软件服务费报销', applicant: '陈思琪', date: '2026-06-12', amount: 28000, status: '审批中' },
])

// 上传信息
const uploadInfo = ref({
  fileName: 'invoice_20260608_001.pdf',
  fileSize: '238 KB',
  fileType: 'PDF',
  pages: 1,
  uploader: '王芳',
  uploadedAt: '2026-06-12 09:23',
})

// 审批时间线
const timeline = ref([
  { t: '文件上传', m: '王芳 · 2026-06-12 09:23', done: true },
  { t: 'OCR 识别完成', m: '系统 · 2026-06-12 09:23 · 耗时 2.3s', done: true },
  { t: '人工核验', m: '待 张明 处理', done: false },
  { t: '提交入账', m: '未开始', done: false },
])

// 是否存在文件预览（用于 attach tab）
const hasPreview = computed(() => !!previewUrl.value)

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    if (id) {
      // 真实接口：拉识别记录列表后按 id 过滤；演示场景拿不到数据时退化到 mock
      const r = await invoiceOcrApi
        .records({ page: 1, pageSize: 50 })
        .then((r) => r.list.find((x) => x.id === id) || null)
        .catch(() => null)
      if (r) {
        result.value = r
        previewUrl.value = r.fileUrl || previewUrl.value
      }
    }
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/invoice/ocr')
}

function handleReOcr() {
  ElMessage.success('已重新发起 OCR 识别（演示）')
}

function handleAddExpense() {
  ElMessage.success('已加入报销单（演示）')
}

function handleAccept() {
  ElMessage.success('已采纳识别结果（演示）')
}

function handleVerify() {
  if (!result.value) return
  ElMessage.success('已发起发票查验（演示）')
}

function confClass(v: number) {
  if (v >= 0.9) return 'conf-high'
  if (v >= 0.7) return 'conf-mid'
  return 'conf-low'
}

function confLabel(v: number) {
  return `${(v * 100).toFixed(0)}%`
}

function fmtMoney(n: number) {
  return `¥ ${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// el-table 合计行（金额、税额两列汇总）
function itemsSummary({ columns }: { columns: Array<{ label: string; property: string }> }) {
  const totalAmount = items.value.reduce((a, b) => a + b.amount, 0)
  const totalTax = items.value.reduce((a, b) => a + b.taxAmount, 0)
  return columns.map((col) => {
    if (col.label === '商品名称') return '合计'
    if (col.label === '金额') return fmtMoney(totalAmount)
    if (col.label === '税额') return fmtMoney(totalTax)
    return ''
  })
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          财务 /
          <router-link to="/invoice/ocr" style="color: var(--color-text-tertiary)">发票识别</router-link>
          / {{ summary.invoiceNo }}
        </div>
        <h2 style="display: flex; align-items: center; gap: 8px">
          发票识别详情
          <span v-if="summary.ocrStatus === '识别成功'" class="tag tag-success">{{ summary.ocrStatus }}</span>
          <span v-else-if="summary.ocrStatus === '待复核'" class="tag tag-warning">{{ summary.ocrStatus }}</span>
          <span v-else class="tag tag-danger">{{ summary.ocrStatus }}</span>
          <span class="tag tag-info">置信度 {{ (summary.confidence * 100).toFixed(1) }}%</span>
        </h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="goBack">← 返回列表</el-button>
        <el-button @click="handleReOcr">⟲ 重新识别</el-button>
        <el-button type="primary" @click="handleAddExpense">✓ 加入报销</el-button>
      </div>
    </div>

    <!-- Hero（与 design/invoice-detail.html 1:1） -->
    <div class="detail-hero">
      <div class="dh-left">
        <div class="dh-id">发票号码 · {{ summary.invoiceNo }}</div>
        <h2>{{ summary.invoiceType }}</h2>
        <div class="dh-meta">
          销售方：<strong style="color: #fff">{{ summary.sellerName }}</strong>
          · 购买方：<strong style="color: #fff">{{ summary.buyerName }}</strong>
          · 开票日期 {{ summary.issueDate }}
        </div>
      </div>
      <div class="dh-right">
        <div class="dh-amount-l">价税合计</div>
        <div class="dh-amount" style="color: #FCA5A5">¥ {{ summary.totalAmount.toLocaleString() }}.00</div>
        <div class="dh-amount-l" style="margin-top: 4px; color: rgba(255,255,255,0.85)">{{ fields.totalAmountCn }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-tabs">
      <a :class="{ active: activeTab === 'result' }" @click="activeTab = 'result'">识别结果</a>
      <a :class="{ active: activeTab === 'items' }" @click="activeTab = 'items'">商品明细</a>
      <a :class="{ active: activeTab === 'verify' }" @click="activeTab = 'verify'">查验记录</a>
      <a :class="{ active: activeTab === 'expense' }" @click="activeTab = 'expense'">报销记录</a>
      <a :class="{ active: activeTab === 'attach' }" @click="activeTab = 'attach'">附件原图</a>
    </div>

    <!-- 识别结果 -->
    <div v-if="activeTab === 'result'" class="detail-section">
      <div class="detail-section-head">
        <h4>✨ 智能识别 · 字段核验</h4>
        <span class="tag tag-success">AI 置信度 {{ (summary.confidence * 100).toFixed(1) }}%</span>
      </div>
      <div class="detail-section-body">
        <div class="tip-box" style="margin-bottom: 14px">
          <span class="ico">💡</span>
          <span>AI 自动填入字段与最终入库值对比，置信度 &lt; 90% 的字段会标红提示复核。</span>
        </div>

        <!-- 字段对比（design/invoice-detail.html field-compare） -->
        <div class="field-compare">
          <span class="l">发票类型</span>
          <span class="ai">{{ fields.invoiceType }}</span>
          <span class="arrow">→</span>
          <span class="final">{{ fields.invoiceType }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.invoiceType)]">
            {{ confLabel(fieldConfidences.invoiceType) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">发票代码</span>
          <span class="ai mono">{{ fields.invoiceCode }}</span>
          <span class="arrow">→</span>
          <span class="final mono">{{ fields.invoiceCode }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.invoiceCode)]">
            {{ confLabel(fieldConfidences.invoiceCode) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">发票号码</span>
          <span class="ai mono">{{ fields.invoiceNo }}</span>
          <span class="arrow">→</span>
          <span class="final mono">{{ fields.invoiceNo }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.invoiceNo)]">
            {{ confLabel(fieldConfidences.invoiceNo) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">开票日期</span>
          <span :class="['ai', confClass(fieldConfidences.issueDate)]">
            {{ fields.issueDate }}
            <span v-if="fieldConfidences.issueDate < 0.9"> ⚠ {{ confLabel(fieldConfidences.issueDate) }}</span>
          </span>
          <span class="arrow">→</span>
          <span class="final">{{ fields.issueDate }}</span>
        </div>
        <div class="field-compare">
          <span class="l">销售方</span>
          <span class="ai">{{ fields.sellerName }}</span>
          <span class="arrow">→</span>
          <span class="final">{{ fields.sellerName }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.sellerName)]">
            {{ confLabel(fieldConfidences.sellerName) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">购买方</span>
          <span class="ai">{{ fields.buyerName }}</span>
          <span class="arrow">→</span>
          <span class="final">{{ fields.buyerName }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.buyerName)]">
            {{ confLabel(fieldConfidences.buyerName) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">纳税人识别号</span>
          <span class="ai mono">{{ fields.buyerTaxNo }}</span>
          <span class="arrow">→</span>
          <span class="final mono">{{ fields.buyerTaxNo }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.buyerTaxNo)]">
            {{ confLabel(fieldConfidences.buyerTaxNo) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">不含税金额</span>
          <span :class="['ai', confClass(fieldConfidences.amountExclTax)]">{{ fmtMoney(fields.amountExclTax) }}</span>
          <span class="arrow">→</span>
          <span class="final">{{ fmtMoney(fields.amountExclTax) }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.amountExclTax)]">
            {{ confLabel(fieldConfidences.amountExclTax) }}
          </span>
        </div>
        <div class="field-compare">
          <span class="l">税额</span>
          <span :class="['ai', confClass(fieldConfidences.taxAmount)]">{{ fmtMoney(fields.taxAmount) }}</span>
          <span class="arrow">→</span>
          <span class="final">{{ fmtMoney(fields.taxAmount) }}</span>
          <span :class="['conf-pill', confClass(fieldConfidences.taxAmount)]">
            {{ confLabel(fieldConfidences.taxAmount) }}
          </span>
        </div>
        <div class="field-compare" style="border-bottom: none">
          <span class="l">价税合计</span>
          <span :class="['ai', confClass(fieldConfidences.totalAmount)]">
            {{ fmtMoney(fields.totalAmount) }}
            <span v-if="fieldConfidences.totalAmount < 0.9"> ⚠ {{ confLabel(fieldConfidences.totalAmount) }}</span>
          </span>
          <span class="arrow">→</span>
          <span class="final" style="color: #B91C1C; font-weight: 700">{{ fmtMoney(fields.totalAmount) }}</span>
        </div>
      </div>
    </div>

    <!-- 详细字段（info-grid） -->
    <div v-if="activeTab === 'result'" class="detail-section">
      <div class="detail-section-head">
        <h4>📋 完整字段信息</h4>
      </div>
      <div class="detail-section-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">发票代码</span><span class="v mono">{{ fields.invoiceCode }}</span></div>
          <div class="info-row"><span class="l">发票号码</span><span class="v mono">{{ fields.invoiceNo }}</span></div>
          <div class="info-row"><span class="l">发票类型</span><span class="v">{{ fields.invoiceType }}</span></div>
          <div class="info-row"><span class="l">开票日期</span><span class="v">{{ fields.issueDate }}</span></div>
          <div class="info-row"><span class="l">校验码</span><span class="v mono">{{ fields.checkCode }}</span></div>
          <div class="info-row"><span class="l">销售方名称</span><span class="v">{{ fields.sellerName }}</span></div>
          <div class="info-row"><span class="l">销售方纳税人识别号</span><span class="v mono" style="font-size: 12.5px">{{ fields.sellerTaxNo }}</span></div>
          <div class="info-row"><span class="l">销售方账户</span><span class="v mono" style="font-size: 12.5px">{{ fields.sellerAccount }}</span></div>
          <div class="info-row"><span class="l">购买方名称</span><span class="v">{{ fields.buyerName }}</span></div>
          <div class="info-row"><span class="l">购买方纳税人识别号</span><span class="v mono" style="font-size: 12.5px">{{ fields.buyerTaxNo }}</span></div>
          <div class="info-row"><span class="l">购买方账户</span><span class="v mono" style="font-size: 12.5px">{{ fields.buyerAccount }}</span></div>
          <div class="info-row"><span class="l">不含税金额</span><span class="v">{{ fmtMoney(fields.amountExclTax) }}</span></div>
          <div class="info-row"><span class="l">税额</span><span class="v">{{ fmtMoney(fields.taxAmount) }}</span></div>
          <div class="info-row"><span class="l">价税合计</span><span class="v" style="color: #EF4444; font-weight: 700">{{ fmtMoney(fields.totalAmount) }}</span></div>
          <div class="info-row"><span class="l">大写金额</span><span class="v">{{ fields.totalAmountCn }}</span></div>
          <div class="info-row full">
            <span class="l">备注</span>
            <div class="term-block">
              <div class="d">{{ fields.remark }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 置信度概览 -->
    <div v-if="activeTab === 'result'" class="detail-section">
      <div class="detail-section-head"><h4>📊 各字段置信度</h4></div>
      <div class="detail-section-body">
        <div class="conf-grid">
          <div v-for="(v, k) in fieldConfidences" :key="k" class="conf-row">
            <div class="conf-key">{{ k }}</div>
            <div class="conf-bar">
              <div :class="['conf-fill', confClass(v)]" :style="{ width: `${v * 100}%` }" />
            </div>
            <div :class="['conf-val', confClass(v)]">{{ confLabel(v) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 商品明细 -->
    <div v-if="activeTab === 'items'" class="detail-section">
      <div class="detail-section-head">
        <h4>📋 商品明细</h4>
        <span class="tag">{{ items.length }} 项</span>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="items" size="small" show-summary :summary-method="itemsSummary">
          <el-table-column prop="name" label="商品名称" min-width="280" />
          <el-table-column prop="qty" label="数量" width="80" align="right" />
          <el-table-column label="单价" width="140" align="right">
            <template #default="{ row }">{{ fmtMoney(row.price) }}</template>
          </el-table-column>
          <el-table-column label="金额" width="140" align="right">
            <template #default="{ row }">
              <strong>{{ fmtMoney(row.amount) }}</strong>
            </template>
          </el-table-column>
          <el-table-column prop="taxRate" label="税率" width="80" align="center" />
          <el-table-column label="税额" width="140" align="right">
            <template #default="{ row }">{{ fmtMoney(row.taxAmount) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 查验记录 -->
    <div v-if="activeTab === 'verify'" class="detail-section">
      <div class="detail-section-head">
        <h4>🔍 查验记录</h4>
        <el-button size="small" @click="handleVerify">重新查验</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="verifyRecords" size="small">
          <el-table-column prop="at" label="查验时间" width="180" />
          <el-table-column label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="row.result === '通过' ? 'success' : 'danger'" size="small">
                {{ row.result === '通过' ? '✓ 通过' : '✗ 失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="数据源" width="160" />
          <el-table-column prop="reason" label="风险原因" />
          <el-table-column prop="elapsed" label="耗时" width="80" align="right" />
        </el-table>
      </div>
    </div>

    <!-- 报销记录 -->
    <div v-if="activeTab === 'expense'" class="detail-section">
      <div class="detail-section-head">
        <h4>💰 关联报销记录</h4>
        <el-button size="small" type="primary" @click="handleAddExpense">+ 新建报销</el-button>
      </div>
      <div class="detail-section-body" style="padding: 0">
        <el-table :data="expenseLinks" size="small">
          <el-table-column prop="code" label="报销单号" width="180" />
          <el-table-column prop="name" label="事项" min-width="200" />
          <el-table-column prop="applicant" label="报销人" width="100" />
          <el-table-column prop="date" label="报销日期" width="120" />
          <el-table-column label="金额" width="140" align="right">
            <template #default="{ row }">
              <span style="color: #EF4444; font-weight: 600">{{ fmtMoney(row.amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" type="warning">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 附件原图 -->
    <div v-if="activeTab === 'attach'" class="detail-section">
      <div class="detail-section-head">
        <h4>📎 附件原图</h4>
        <span class="tag tag-info">{{ uploadInfo.fileType }} · {{ uploadInfo.fileSize }} · {{ uploadInfo.pages }} 页</span>
      </div>
      <div class="detail-section-body">
        <div class="attach-preview">
          <div v-if="hasPreview" class="attach-img">
            <img :src="previewUrl" alt="发票原图" />
            <div class="attach-img-mask">
              <span>OCR 识别框</span>
            </div>
          </div>
          <div v-else class="attach-placeholder">
            <div class="ico">📄</div>
            <div class="t">{{ uploadInfo.fileName }}</div>
            <div class="m">{{ uploadInfo.fileSize }} · 上传人 {{ uploadInfo.uploader }} · {{ uploadInfo.uploadedAt }}</div>
            <el-button size="small" type="primary" style="margin-top: 12px" @click="handleAccept">查看完整文件</el-button>
          </div>
        </div>

        <!-- 上传信息 info-grid -->
        <div class="info-grid" style="margin-top: 18px">
          <div class="info-row"><span class="l">原文件名</span><span class="v mono" style="font-size: 12px">{{ uploadInfo.fileName }}</span></div>
          <div class="info-row"><span class="l">文件大小</span><span class="v">{{ uploadInfo.fileSize }}</span></div>
          <div class="info-row"><span class="l">文件类型</span><span class="v">{{ uploadInfo.fileType }}</span></div>
          <div class="info-row"><span class="l">页数</span><span class="v">{{ uploadInfo.pages }} 页</span></div>
          <div class="info-row"><span class="l">上传人</span><span class="v">{{ uploadInfo.uploader }}</span></div>
          <div class="info-row"><span class="l">上传时间</span><span class="v">{{ uploadInfo.uploadedAt }}</span></div>
        </div>
      </div>
    </div>

    <!-- 右侧状态卡（与 design/invoice-detail.html 1:1） -->
    <div class="detail-section">
      <div class="detail-section-head"><h4>📌 识别流程时间线</h4></div>
      <div class="detail-section-body">
        <div class="timeline-det">
          <div v-for="(s, i) in timeline" :key="i" :class="['timeline-det-item', s.done ? 'done' : '']">
            <div class="t">{{ s.t }}</div>
            <div class="m">{{ s.m }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

/* 字段对比（design/invoice-detail.html） */
.field-compare {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid $color-border;
  &:last-child { border-bottom: none; }
  .l {
    font-size: 12px;
    color: $color-text-tertiary;
    width: 110px;
    flex-shrink: 0;
  }
  .ai {
    flex: 1;
    font-family: $font-family-mono;
    font-size: 12.5px;
    padding: 5px 10px;
    background: $color-primary-bg;
    color: $color-primary;
    border-radius: 4px;
    &.conf-mid { background: rgba(245,158,11,0.12); color: #B45309; }
    &.conf-low { background: rgba(239,68,68,0.12); color: #B91C1C; }
  }
  .arrow { color: $color-text-tertiary; }
  .final {
    flex: 1;
    font-size: 12.5px;
    padding: 5px 10px;
    background: #F0FDF4;
    color: #047857;
    border-radius: 4px;
    font-weight: 500;
  }
  .conf-pill {
    flex-shrink: 0;
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

/* 置信度网格 */
.conf-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 24px;
}
.conf-row {
  display: grid;
  grid-template-columns: 140px 1fr 50px;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  .conf-key {
    font-size: 12px;
    color: $color-text-tertiary;
    font-family: $font-family-mono;
  }
  .conf-bar {
    height: 8px;
    background: #F1F5F9;
    border-radius: 999px;
    overflow: hidden;
  }
  .conf-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
    &.conf-high { background: linear-gradient(90deg, #10B981, #059669); }
    &.conf-mid { background: linear-gradient(90deg, #F59E0B, #D97706); }
    &.conf-low { background: linear-gradient(90deg, #EF4444, #DC2626); }
  }
  .conf-val {
    text-align: right;
    font-size: 12px;
    font-weight: 600;
    font-family: $font-family-mono;
    &.conf-high { color: #047857; }
    &.conf-mid { color: #B45309; }
    &.conf-low { color: #B91C1C; }
  }
}

/* 附件预览 */
.attach-preview {
  border: 1px solid $color-border;
  border-radius: $radius-md;
  background: #F8FAFC;
  min-height: 280px;
  display: grid;
  place-items: center;
  overflow: hidden;
}
.attach-img {
  position: relative;
  width: 100%;
  img { display: block; max-width: 100%; max-height: 480px; margin: 0 auto; }
}
.attach-img-mask {
  position: absolute;
  top: 12px; right: 12px;
  background: rgba(79,107,255,0.9);
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11.5px;
}
.attach-placeholder {
  text-align: center;
  padding: 48px 20px;
  color: $color-text-secondary;
  .ico { font-size: 56px; margin-bottom: 8px; }
  .t { font-size: 14px; font-weight: 500; color: $color-text-primary; font-family: $font-family-mono; }
  .m { font-size: 12px; color: $color-text-tertiary; margin-top: 4px; }
}

/* 状态时间线（与 design/invoice-detail.html 同款） */
.timeline-det {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  padding-left: 24px;
  &::before {
    content: '';
    position: absolute;
    left: 8px; top: 6px; bottom: 6px;
    width: 2px;
    background: $color-border;
  }
}
.timeline-det-item {
  position: relative;
  padding-left: 0;
  &::before {
    content: '';
    position: absolute;
    left: -20px; top: 4px;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid $color-border;
  }
  .t { font-size: 13px; font-weight: 500; color: $color-text-primary; }
  .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  &.done::before {
    background: $color-success;
    border-color: $color-success;
  }
}
</style>