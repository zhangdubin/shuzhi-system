<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/reimbursement/list')">报销中心</a>
          <span class="sep">/</span>
          <span class="current">{{ form?.formNo || '详情' }}</span>
        </div>
        <h1>🧾 {{ form?.formNo }} <span :class="['tag', statusClass(form?.status)]">{{ form?.statusLabel }}</span></h1>
        <p class="page-desc">{{ form?.title }}</p>
      </div>
      <div class="page-actions">
        <el-button @click="router.push('/reimbursement/list')">← 返回</el-button>
        <el-button @click="onPrint">🖨 打印 / 导出 PDF</el-button>
        <!-- UDPE 统一单据打印引擎（M2 阶段 5 第三个迁移点） -->
        <PrintByTemplateButton
          template-code="reimbursement_v1"
          :business-id="form?.formId || Number(route.params.id)"
          source-module="reimbursement"
          label="按模板打印"
          icon="🧾"
          el-type="default"
          @click="printDialogVisible = true"
        />
        <el-button v-if="form && form.status !== 'done'" type="primary" @click="fillbackVisible = true">💰 录入实际报销</el-button>
      </div>
    </div>

    <!-- 关键信息 -->
    <div v-if="form" class="info-grid">
      <div class="info-card">
        <div class="lbl">报销人</div>
        <div class="val">{{ form.applicant?.name || '—' }}</div>
      </div>
      <div class="info-card">
        <div class="lbl">部门</div>
        <div class="val">{{ form.department?.name || '—' }}</div>
      </div>
      <div class="info-card">
        <div class="lbl">费用日期</div>
        <div class="val">{{ form.expenseDate || '—' }}</div>
      </div>
      <div class="info-card">
        <div class="lbl">支付日期</div>
        <div class="val">{{ form.paymentDate || '—' }}</div>
      </div>
      <div class="info-card">
        <div class="lbl">凭证号</div>
        <div class="val">{{ form.voucherNo || '—' }}</div>
      </div>
      <div class="info-card">
        <div class="lbl">模板</div>
        <div class="val">{{ templateName(form.templateType) }}</div>
      </div>
      <div class="info-card highlight">
        <div class="lbl">申请金额</div>
        <div class="val">¥{{ fmtMoney(form.totalAmount) }}</div>
      </div>
      <div class="info-card highlight" v-if="form.actualAmount > 0">
        <div class="lbl">实报金额</div>
        <div class="val">¥{{ fmtMoney(form.actualAmount) }}</div>
      </div>
    </div>

    <!-- 费用明细 -->
    <div class="page-card">
      <div class="card-head"><h3>📋 费用明细（关联 {{ form?.details?.length || 0 }} 笔销售费用）</h3></div>
      <el-table :data="form?.details || []" stripe>
        <el-table-column label="#" width="50" type="index" />
        <el-table-column label="日期" width="100">
          <template #default="{ row }">{{ row.expenseDate || '—' }}</template>
        </el-table-column>
        <el-table-column label="费用单号" width="150">
          <template #default="{ row }"><span class="mono">{{ row.expenseCode }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="80">
          <template #default="{ row }">{{ row.expenseType }}</template>
        </el-table-column>
        <el-table-column prop="title" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column label="客户/供应商" width="140">
          <template #default="{ row }">{{ row.clientName || row.projectName || '—' }}</template>
        </el-table-column>
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }"><span class="money">¥{{ fmtMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="已报销" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.reimbursedAmount >= row.amount ? 'text-success' : 'text-warning'">¥{{ fmtMoney(row.reimbursedAmount) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- AI 说明 -->
    <div v-if="form?.aiDescription" class="page-card">
      <div class="card-head"><h3>✨ AI 生成的报销说明</h3></div>
      <div class="ai-text">{{ form.aiDescription }}</div>
    </div>

    <!-- 备注 -->
    <div v-if="form?.remark" class="page-card">
      <div class="card-head"><h3>📝 备注</h3></div>
      <div class="remark">{{ form.remark }}</div>
    </div>

    <!-- 回填 Dialog（R18 重设计） -->
    <el-dialog v-model="fillbackVisible" width="640px" :close-on-click-modal="false" align-center custom-class="fillback-dialog">
      <template #header>
        <div class="fb-head">
          <div class="fb-head-icon">💰</div>
          <div class="fb-head-text">
            <div class="fb-title">录入实际报销结果</div>
            <div class="fb-sub">确认实际打款金额并分摊到每笔费用，提交后自动回写销售费用</div>
          </div>
        </div>
      </template>

      <div class="fb-banner">
        <div class="fb-banner-l">
          <div class="fb-banner-lbl">本次申请总额</div>
          <div class="fb-banner-val">¥{{ fmtMoney(form?.totalAmount || 0) }}</div>
        </div>
        <div class="fb-banner-arrow">→</div>
        <div class="fb-banner-r">
          <div class="fb-banner-lbl">实际报销总额</div>
          <div class="fb-banner-input">
            <span class="fb-cur">¥</span>
            <input
              v-model.number="fillbackForm.actualAmountYuan"
              type="number"
              min="0"
              step="0.01"
              class="fb-amount-input"
              placeholder="0.00"
            />
          </div>
          <div class="fb-banner-hint">
            <span v-if="fillbackDiff === 0" class="hint-ok">✓ 与申请金额一致</span>
            <span v-else-if="fillbackDiff > 0" class="hint-up">▲ 比申请多 ¥{{ fillbackDiff.toFixed(2) }}</span>
            <span v-else class="hint-down">▼ 比申请少 ¥{{ Math.abs(fillbackDiff).toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <div class="fb-section">
        <div class="fb-section-title">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          财务信息
        </div>
        <div class="fb-grid">
          <div class="fb-field">
            <label>支付日期</label>
            <el-date-picker v-model="fillbackForm.paymentDate" type="date" value-format="YYYY-MM-DD" class="fb-date" />
          </div>
          <div class="fb-field">
            <label>凭证号 <span class="fb-opt">（可选）</span></label>
            <input v-model="fillbackForm.voucherNo" class="fb-input" placeholder="如 VCH-2026-001" maxlength="32" />
          </div>
        </div>
        <div class="fb-field full">
          <label>备注</label>
          <textarea v-model="fillbackForm.remark" class="fb-textarea" :rows="2" maxlength="200" placeholder="可填写打款渠道、调整原因等" />
          <div class="fb-char-count">{{ (fillbackForm.remark || '').length }} / 200</div>
        </div>
      </div>

      <div class="fb-section">
        <div class="fb-section-title">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
          分摊到每笔费用
          <span class="fb-section-hint">默认按申请金额，可单独调整</span>
        </div>
        <div class="fb-list">
          <div v-for="d in form?.details" :key="d.expenseId" class="fb-list-row">
            <div class="fb-list-l">
              <div class="fb-list-code">{{ d.expenseCode }}</div>
              <div class="fb-list-title">{{ d.title || '—' }}</div>
            </div>
            <div class="fb-list-amt">
              <span class="fb-list-lbl">申请</span>
              <span class="fb-list-val">¥{{ fmtMoney(d.amount) }}</span>
            </div>
            <div class="fb-list-arrow">→</div>
            <div class="fb-list-input">
              <span class="fb-cur-sm">¥</span>
              <input
                v-model.number="detailAmountsYuan[d.expenseId]"
                type="number"
                min="0"
                step="0.01"
                class="fb-input-num"
                placeholder="0.00"
              />
            </div>
          </div>
          <div v-if="!form?.details || form.details.length === 0" class="fb-list-empty">
            暂无关联费用
          </div>
        </div>
        <div class="fb-sum">
          <span>分摊合计</span>
          <b>¥{{ detailSumYuan.toFixed(2) }}</b>
          <span v-if="Math.abs(detailSumYuan - (fillbackForm.actualAmountYuan || 0)) > 0.01" class="fb-sum-warn">
            ⚠ 与实报金额差 ¥{{ Math.abs(detailSumYuan - (fillbackForm.actualAmountYuan || 0)).toFixed(2) }}
          </span>
        </div>
      </div>

      <template #footer>
        <div class="fb-foot">
          <el-button class="fb-btn-cancel" @click="fillbackVisible = false">取消</el-button>
          <el-button class="fb-btn-save" type="primary" :loading="submitting" @click="onFillback">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;vertical-align:-2px;"><polyline points="20 6 9 17 4 12"></polyline></svg>
            确认并回写费用
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 打印 Dialog（A4 风格） -->
    <el-dialog v-model="printVisible" title="🖨 报销单打印预览" width="900px" :close-on-click-modal="false">
      <div class="print-actions">
        <el-button @click="onDownloadPDF" :loading="pdfBusy">⇩ 下载 PDF</el-button>
        <el-button type="primary" @click="onNativePrint">🖨 浏览器打印</el-button>
        <span class="print-hint">提示：A4 纸打印，关闭页眉页脚</span>
      </div>
      <div id="print-area" class="print-area">
        <div class="print-company">{{ templateData?.schema?.header?.company || '数智化管理系统' }}</div>
        <h1 class="print-title">{{ templateData?.schema?.header?.title || '费用报销单' }}</h1>
        <div class="print-subtitle">{{ templateData?.schema?.header?.subtitle || '' }}</div>

        <table class="print-meta">
          <tr>
            <td class="lbl">报销人</td><td>{{ form?.applicant?.name }}</td>
            <td class="lbl">部门</td><td>{{ form?.department?.name || '—' }}</td>
          </tr>
          <tr>
            <td class="lbl">单据编号</td><td>{{ form?.formNo }}</td>
            <td class="lbl">报销日期</td><td>{{ form?.expenseDate }}</td>
          </tr>
        </table>

        <table class="print-detail">
          <thead>
            <tr>
              <th v-for="c in templateData?.schema?.details?.columns || []" :key="c.key" :style="{ textAlign: c.align || 'left' }">{{ c.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(d, i) in form?.details || []" :key="d.id">
              <td v-for="c in templateData?.schema?.details?.columns || []" :key="c.key" :style="{ textAlign: c.align || 'left' }">
                <template v-if="c.key === 'seq'">{{ i + 1 }}</template>
                <template v-else-if="c.key === 'amount'">¥{{ fmtMoney(d.amount) }}</template>
                <template v-else>{{ d[c.key === 'expenseDate' ? 'expenseDate' : c.key === 'expenseCode' ? 'expenseCode' : c.key === 'expenseType' ? 'expenseType' : c.key === 'clientName' ? 'clientName' : c.key === 'title' ? 'title' : ''] }}</template>
              </td>
            </tr>
            <tr class="sum-row">
              <td :colspan="(templateData?.schema?.details?.columns?.length || 1) - 1" style="text-align:right">合计</td>
              <td style="text-align:right"><b>¥{{ fmtMoney(form?.totalAmount) }}</b></td>
            </tr>
          </tbody>
        </table>

        <table class="print-cap">
          <tr>
            <td class="lbl">金额大写</td>
            <td class="val"><b>{{ toChineseAmount(((form?.actualAmount || form?.totalAmount) || 0) / 100) }}</b></td>
          </tr>
        </table>

        <table class="print-summary">
          <tr>
            <td class="lbl">申请金额</td><td><b class="money">¥{{ fmtMoney(form?.totalAmount) }}</b></td>
            <td class="lbl">实报金额</td><td><b class="money">¥{{ fmtMoney(form?.actualAmount) }}</b></td>
            <td class="lbl">凭证号</td><td>{{ form?.voucherNo || '—' }}</td>
          </tr>
        </table>

        <div v-if="form?.aiDescription" class="print-ai">
          <h4>报销说明（AI 生成）</h4>
          <p>{{ form.aiDescription }}</p>
        </div>

        <div v-if="form?.remark" class="print-ai">
          <h4>备注</h4>
          <p>{{ form.remark }}</p>
        </div>

        <div class="print-sign">
          <div v-for="s in templateData?.schema?.footer?.signatures || []" :key="s.key" class="sign-col">
            <div class="sign-label">{{ s.label }}</div>
            <div class="sign-line"></div>
          </div>
        </div>

        <div class="print-note">{{ templateData?.schema?.footer?.note || '' }}</div>
      </div>
    </el-dialog>
  </div>


    <!-- UDPE 通用预览弹窗（M2 阶段 6） -->
    <PrintPreviewDialog
      v-model="printDialogVisible"
      template-code="reimbursement_v1"
      :data="{ _resolver: form?.formId || Number(route.params.id) }"
      source-module="reimbursement"
      :source-id="form?.formId || Number(route.params.id)"
      title="报销单打印预览"
    />
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reimburseApi } from '@/api/modules'
import { PrintByTemplateButton, PrintPreviewDialog } from '@/components/common/print'
import { printApi } from '@/api/print'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const form = ref<any>(null)
const templateData = ref<any>(null)
const templates = ref<any[]>([])

const fillbackVisible = ref(false)
const printDialogVisible = ref(false)
const fillbackForm = reactive({
  actualAmountYuan: 0,             // 元（前端交互用）
  paymentDate: new Date().toISOString().substring(0, 10),
  voucherNo: '',
  remark: '',
})
// 提交给后端时转分；保留旧字段名 detailAmounts（key=expenseId，value=分）以兼容 service
const detailAmounts = reactive<Record<number, number>>({})
// 前端展示用：元
const detailAmountsYuan = reactive<Record<number, number>>({})

// 与申请金额的差（元）
const fillbackDiff = computed(() => {
  const applied = (form.value?.totalAmount || 0) / 100
  return Number((Number(fillbackForm.actualAmountYuan || 0) - applied).toFixed(2))
})
// 分摊合计（元）
const detailSumYuan = computed(() => {
  return Object.values(detailAmountsYuan).reduce((s: number, v: any) => s + (Number(v) || 0), 0)
})

const printVisible = ref(false)
const pdfBusy = ref(false)

function fmtMoney(v: number) { return ((v || 0) / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function toChineseAmount(num: number | string): string {
  const n = Number(num || 0)
  if (!isFinite(n) || n === 0) return '零元整'
  const upper = ['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']
  const unit  = ['', '拾', '佰', '仟']
  const big   = ['', '万', '亿', '兆']
  const s = Math.abs(n).toFixed(2)
  const [intPart, decPart] = s.split('.')
  let intStr = ''
  if (intPart === '0') {
    intStr = ''
  } else {
    const groups: string[] = []
    let p = intPart
    while (p.length > 0) {
      const g = p.slice(-4)
      p = p.slice(0, -4)
      groups.unshift(g)
    }
    const groupStrs = groups.map((chunk) => {
      if (/^0+$/.test(chunk)) return ''
      let s = ''
      for (let i = 0; i < chunk.length; i++) {
        const d = Number(chunk[i])
        if (d !== 0) {
          if (i > 0 && s.length > 0 && s[s.length-1] !== '零' && Number(chunk[i-1]) === 0) s += '零'
          s += upper[d] + unit[chunk.length - 1 - i]
        }
      }
      return s
    })
    for (let gi = 0; gi < groupStrs.length; gi++) {
      const gs = groupStrs[gi]
      if (gs === '') {
        if (gi < groupStrs.length - 1 && groupStrs.slice(gi+1).some(g => g !== '')) intStr += '零'
        continue
      }
      if (gi > 0 && intStr.length > 0 && ['万','亿','兆'].includes(intStr[intStr.length-1]) && !intStr.endsWith('零')) {
        const curChunk = groups[gi]
        if (curChunk[0] === '0') intStr += '零'
      }
      intStr += gs + big[groupStrs.length - 1 - gi]
    }
    intStr = intStr.replace(/零+/g, '零').replace(/零+$/g, '')
  }
  const jiao = Number(decPart[0])
  const fen  = Number(decPart[1])
  let decStr = ''
  if (jiao === 0 && fen === 0) {
    decStr = '整'
    if (intStr === '') intStr = '零'
  } else {
    if (jiao !== 0) decStr += upper[jiao] + '角'
    else decStr += '零'
    if (fen !== 0) decStr += upper[fen] + '分'
    if (intStr === '') intStr = '零'
  }
  return (n < 0 ? '负' : '') + intStr + '元' + decStr
}
function templateName(code: string) { return templates.value.find(t => t.code === code)?.name || code }
function statusClass(s: string) {
  return { draft: 'tag-info', printed: 'tag-warning', reimbursed: 'tag-primary', done: 'tag-success', cancelled: 'tag-danger' }[s] || 'tag-info'
}

async function loadData() {
  loading.value = true
  try {
    const formId = Number(route.params.id)
    const r: any = await reimburseApi.detail(formId)
    form.value = r || r?.data
    // 同步填默认值
    if (form.value) {
      fillbackForm.actualAmountYuan = (form.value.totalAmount || 0) / 100
      fillbackForm.remark = form.value.remark || ''
      // 默认每笔 = 申请金额
      form.value.details?.forEach((d: any) => {
        const yuan = (d.amount || 0) / 100
        detailAmountsYuan[d.expenseId] = yuan
        detailAmounts[d.expenseId] = d.amount
      })
    }
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const r: any = await reimburseApi.templates()
    templates.value = r || r?.data || []
  } catch (e) { console.warn(e) }
}

function findTemplate() {
  if (!form.value) return
  const tpl = form.value.templateSnapshot
  if (tpl) { templateData.value = tpl; return }
  const t = templates.value.find(x => x.code === form.value.templateType) || templates.value[0]
  templateData.value = t
}

async function onPrint() {
  await loadTemplates()
  findTemplate()
  printVisible.value = true
}

async function onDownloadPDF() {
  pdfBusy.value = true
  const loading = ElMessage({ message: '正在生成 PDF…', type: 'info', duration: 0 })
  try {
    const blob = await printApi.pdfBlob({
      templateCode: 'reimbursement_v1',
      data: { _resolver: form.value?.formId || Number(route.params.id) },
      options: { sourceModule: 'reimbursement', sourceId: String(form.value?.formId || route.params.id) },
    })
    loading.close()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${form.value?.formNo || '报销单'}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('PDF 已下载')
  } catch (e: any) {
    loading.close()
    ElMessage.error('PDF 生成失败: ' + (e?.message || '') + '，回退到浏览器打印')
    onNativePrint()
  } finally {
    pdfBusy.value = false
  }
}

async function onNativePrint() {
  const printContents = document.getElementById('print-area')?.innerHTML || ''
  const win = window.open('', '_blank')
  if (!win) { ElMessage.warning('请允许弹窗以使用打印功能'); return }
  win.document.write(`<!DOCTYPE html><html><head><title>${form.value?.formNo}</title>
<style>
  body { font-family: -apple-system, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif; padding: 20mm 18mm; color: #1F2937; }
  .print-company { text-align: center; color: #4F6BFF; font-size: 12px; margin-bottom: 4px; }
  .print-title { text-align: center; font-size: 22px; margin: 4px 0; }
  .print-subtitle { text-align: center; color: #6B7280; font-size: 10px; margin-bottom: 18px; }
  .print-meta, .print-detail, .print-summary { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
  .print-meta td, .print-summary td { padding: 6px 10px; font-size: 12px; border: 1px solid #E5E7EB; }
  .print-meta .lbl, .print-summary .lbl { color: #6B7280; background: #F9FAFB; width: 80px; }
  .print-detail th, .print-detail td { padding: 8px 10px; font-size: 11.5px; border: 1px solid #E5E7EB; }
  .print-detail th { background: #4F6BFF; color: #fff; font-weight: 600; }
  .print-detail .sum-row td { background: #EEF2FF; font-weight: 600; }
  .money { color: #DC2626; }
  .print-ai { margin-top: 14px; padding: 10px 12px; background: #F9FAFB; border-radius: 4px; }
  .print-ai h4 { font-size: 12px; margin: 0 0 6px; color: #374151; }
  .print-ai p { font-size: 11.5px; color: #4B5563; line-height: 1.6; margin: 0; }
  .print-sign { display: flex; gap: 24px; margin-top: 30px; }
  .sign-col { flex: 1; }
  .sign-label { font-size: 11px; color: #6B7280; margin-bottom: 4px; }
  .sign-line { border-bottom: 1px solid #1F2937; height: 30px; }
  .print-note { text-align: center; font-size: 10px; color: #9CA3AF; margin-top: 16px; }
  @page { size: A4; margin: 18mm; }
  @media print { .no-print { display: none !important; } }
</style>
</head><body>${printContents}</body></html>`)
  win.document.close()
  setTimeout(() => { win.print(); win.close() }, 300)

  // 标记为已打印
  try {
    if (form.value && form.value.status === 'draft') {
      await reimburseApi.markPrinted(form.value.formId)
      form.value.status = 'printed'
      form.value.statusLabel = '已打印'
    }
  } catch (e) { /* ignore */ }
}

async function onFillback() {
  submitting.value = true
  try {
    // 提交时元 → 分（同步填到 detailAmounts，给后端用）
    const detailAmountsStr: Record<string, number> = {}
    Object.entries(detailAmountsYuan).forEach(([k, v]) => {
      const cents = Math.round((Number(v) || 0) * 100)
      detailAmountsStr[k] = cents
      detailAmounts[Number(k)] = cents
    })
    const actualAmountCents = Math.round((Number(fillbackForm.actualAmountYuan) || 0) * 100)
    const r: any = await reimburseApi.fillback({
      formId: form.value.formId,
      actualAmount: actualAmountCents,
      paymentDate: fillbackForm.paymentDate,
      voucherNo: fillbackForm.voucherNo,
      remark: fillbackForm.remark,
      detailAmounts: detailAmountsStr,
    } as any)
    ElMessage.success('已回填实际报销，并自动同步销售费用状态')
    fillbackVisible.value = false
    loadData()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : (e?.message || '失败'))
    ElMessage.error('回填失败：' + msg)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadTemplates()
  loadData()
})


</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

.info-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.info-card {
  background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 12px 16px;
  .lbl { font-size: 11px; color: $color-text-tertiary; }
  .val { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-top: 2px; }
  &.highlight { background: linear-gradient(135deg, #4F6BFF08, #7C3AED08); border-color: rgba(79,107,255,0.2); }
  &.highlight .val { color: #DC2626; font-size: 18px; }
}

.page-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 16px; margin-bottom: 12px; }
.card-head h3 { font-size: 14px; font-weight: 600; margin: 0 0 12px 0; }

.ai-text, .remark { padding: 12px 16px; background: $color-bg; border-radius: $radius-md; color: $color-text-secondary; font-size: 13px; line-height: 1.7; }

.mono { font-family: $font-family-mono; font-size: 11.5px; color: $color-text-secondary; }
.money { color: #DC2626; font-weight: 600; }
.text-success { color: #10B981; }
.text-warning { color: #F59E0B; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px; }
.tag-success { background: rgba(16,185,129,0.1); color: #10B981; }
.tag-warning { background: rgba(245,158,11,0.1); color: #F59E0B; }
.tag-primary { background: rgba(79,107,255,0.1); color: #4F6BFF; }
.tag-info    { background: rgba(148,163,184,0.15); color: #64748B; }
.tag-danger  { background: rgba(239,68,68,0.1);  color: #EF4444; }

.per-detail h4 { font-size: 12px; margin: 0 0 8px; }
.per-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 12.5px; }
.hint { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

.print-actions { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; padding: 10px 12px; background: #F8FAFC; border-radius: $radius-md; }
.print-hint { font-size: 11px; color: $color-text-tertiary; margin-left: 8px; }

.print-area .print-cap { width:100%; border-collapse:collapse; margin-bottom:6px; }
.print-area .print-cap td { padding:6px 10px; border:1px solid #D1D5DB; font-size:13px; }
.print-area .print-cap .lbl { background:#F3F4F6; color:#4B5563; width:90px; font-weight:500; white-space:nowrap; }
.print-area .print-cap .val { font-weight:600; letter-spacing: 0.5px; color:#1F2937; }
.print-area {
  background: #fff; padding: 24px; border: 1px solid $color-border; border-radius: $radius-md;
  font-size: 12px;
  .print-company { text-align: center; color: #4F6BFF; font-size: 12px; margin-bottom: 4px; }
  .print-title { text-align: center; font-size: 22px; margin: 4px 0; }
  .print-subtitle { text-align: center; color: #6B7280; font-size: 10px; margin-bottom: 18px; }
  .print-meta, .print-detail, .print-summary { width: 100%; border-collapse: collapse; margin-bottom: 14px; }
  .print-meta td, .print-summary td { padding: 6px 10px; font-size: 12px; border: 1px solid #E5E7EB; }
  .print-meta .lbl, .print-summary .lbl { color: #6B7280; background: #F9FAFB; width: 80px; }
  .print-detail th, .print-detail td { padding: 8px 10px; font-size: 11.5px; border: 1px solid #E5E7EB; }
  .print-detail th { background: #4F6BFF; color: #fff; font-weight: 600; }
  .print-detail .sum-row td { background: #EEF2FF; font-weight: 600; }
  .money { color: #DC2626; }
  .print-ai { margin-top: 14px; padding: 10px 12px; background: #F9FAFB; border-radius: 4px; }
  .print-ai h4 { font-size: 12px; margin: 0 0 6px; }
  .print-ai p { font-size: 11.5px; color: #4B5563; line-height: 1.6; margin: 0; }
  .print-sign { display: flex; gap: 24px; margin-top: 30px; }
  .sign-col { flex: 1; }
  .sign-label { font-size: 11px; color: #6B7280; margin-bottom: 4px; }
  .sign-line { border-bottom: 1px solid #1F2937; height: 30px; }
  .print-note { text-align: center; font-size: 10px; color: #9CA3AF; margin-top: 16px; }
}

/* ============ R18 「录入实际报销」弹窗重设计 ============ */
.fillback-dialog {
  border-radius: 14px !important;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15, 23, 42, 0.04) !important;
}
.fillback-dialog .el-dialog__header {
  padding: 22px 28px 18px !important;
  border-bottom: 1px solid #F1F5F9;
  margin-right: 0 !important;
  background: linear-gradient(180deg, #FAFBFF 0%, #FFFFFF 100%);
}
.fillback-dialog .el-dialog__headerbtn {
  top: 22px !important; right: 22px !important;
  width: 28px; height: 28px; border-radius: 6px;
  background: #F1F5F9; transition: all 0.15s;
}
.fillback-dialog .el-dialog__headerbtn:hover { background: #E2E8F0; }
.fillback-dialog .el-dialog__body {
  padding: 22px 28px 4px !important; background: #FFFFFF;
}
.fillback-dialog .el-dialog__footer {
  padding: 14px 28px 22px !important;
  background: #FAFBFF; border-top: 1px solid #F1F5F9;
}

/* header */
.fb-head { display: flex; align-items: center; gap: 14px; }
.fb-head-icon {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 6px rgba(79, 107, 255, 0.15);
}
.fb-head-text { line-height: 1.4; }
.fb-title { font-size: 16px; font-weight: 600; color: #0F172A; letter-spacing: 0.2px; }
.fb-sub { font-size: 12px; color: #64748B; margin-top: 2px; }

/* banner: 申请额 → 实报额 */
.fb-banner {
  display: grid; grid-template-columns: 1fr 32px 1.4fr;
  align-items: center; gap: 12px;
  padding: 18px 20px;
  background: linear-gradient(135deg, #F8FAFF 0%, #EEF2FF 100%);
  border: 1px solid #E0E7FF;
  border-radius: 12px;
  margin-bottom: 18px;
}
.fb-banner-lbl { font-size: 12px; color: #64748B; font-weight: 500; }
.fb-banner-val { font-size: 22px; font-weight: 700; color: #475569; font-family: 'SF Mono', Menlo, monospace; line-height: 1.2; margin-top: 4px; }
.fb-banner-arrow { font-size: 22px; color: #94A3B8; text-align: center; }
.fb-banner-r { display: flex; flex-direction: column; gap: 4px; }
.fb-banner-input {
  display: flex; align-items: baseline; gap: 4px;
  background: #FFFFFF;
  border: 1.5px solid #4F6BFF;
  border-radius: 8px;
  padding: 6px 12px;
  box-shadow: 0 0 0 3px rgba(79, 107, 255, 0.1);
  transition: all 0.15s;
}
.fb-banner-input:focus-within { box-shadow: 0 0 0 4px rgba(79, 107, 255, 0.18); }
.fb-cur { font-size: 18px; color: #4F6BFF; font-weight: 600; font-family: 'SF Mono', Menlo, monospace; }
.fb-amount-input {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 22px; font-weight: 700; color: #4F6BFF;
  font-family: 'SF Mono', Menlo, monospace;
  width: 100%; padding: 0;
}
.fb-amount-input::placeholder { color: #CBD5E1; }
.fb-banner-hint { font-size: 12px; }
.hint-ok { color: #047857; }
.hint-up { color: #B45309; }
.hint-down { color: #2563EB; }

/* sections */
.fb-section { margin-bottom: 18px; }
.fb-section-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: #0F172A;
  margin-bottom: 10px;
}
.fb-section-title svg { color: #4F6BFF; }
.fb-section-hint { font-size: 11px; color: #94A3B8; font-weight: 400; margin-left: auto; }
.fb-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.fb-field { display: flex; flex-direction: column; gap: 6px; position: relative; }
.fb-field.full { width: 100%; }
.fb-field label { font-size: 12px; color: #475569; font-weight: 500; }
.fb-opt { color: #94A3B8; font-weight: 400; font-size: 11px; }
.fb-input, .fb-textarea {
  width: 100%;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  color: #0F172A;
  font-family: inherit;
  transition: all 0.15s;
}
.fb-input:hover { border-color: #CBD5E1; background: #FFFFFF; }
.fb-input:focus, .fb-textarea:focus {
  outline: none; border-color: #4F6BFF; background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(79, 107, 255, 0.12);
}
.fb-input::placeholder, .fb-textarea::placeholder { color: #94A3B8; }
.fb-textarea { resize: vertical; min-height: 56px; }
.fb-date { width: 100%; }
.fb-char-count { position: absolute; right: 8px; bottom: 6px; font-size: 10px; color: #94A3B8; pointer-events: none; }

/* list */
.fb-list { display: flex; flex-direction: column; gap: 6px; }
.fb-list-row {
  display: grid; grid-template-columns: 1fr 110px 16px 130px;
  align-items: center; gap: 10px;
  padding: 10px 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  transition: all 0.15s;
}
.fb-list-row:hover { background: #FFFFFF; border-color: #4F6BFF; box-shadow: 0 2px 8px rgba(79, 107, 255, 0.08); }
.fb-list-l { min-width: 0; }
.fb-list-code { font-family: 'SF Mono', Menlo, monospace; font-size: 11px; color: #4F6BFF; font-weight: 500; }
.fb-list-title { font-size: 12.5px; color: #0F172A; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fb-list-amt { text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
.fb-list-lbl { font-size: 10px; color: #94A3B8; }
.fb-list-val { font-size: 13px; color: #475569; font-family: 'SF Mono', Menlo, monospace; font-weight: 500; }
.fb-list-arrow { color: #CBD5E1; text-align: center; font-size: 14px; }
.fb-list-input { display: flex; align-items: center; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px 8px; }
.fb-list-input:focus-within { border-color: #4F6BFF; box-shadow: 0 0 0 3px rgba(79, 107, 255, 0.12); }
.fb-cur-sm { font-size: 11px; color: #94A3B8; font-family: 'SF Mono', monospace; }
.fb-input-num {
  flex: 1; border: none; outline: none; background: transparent;
  font-size: 13px; color: #0F172A; text-align: right;
  font-family: 'SF Mono', Menlo, monospace;
  width: 100%; padding: 0;
}
.fb-input-num::placeholder { color: #CBD5E1; }
.fb-list-empty { padding: 24px; text-align: center; color: #94A3B8; font-size: 12px; }

.fb-sum {
  display: flex; justify-content: flex-end; align-items: baseline; gap: 8px;
  margin-top: 10px; padding: 10px 12px;
  font-size: 12px; color: #64748B;
}
.fb-sum b {
  font-size: 16px; color: #4F6BFF; font-weight: 700;
  font-family: 'SF Mono', Menlo, monospace;
}
.fb-sum-warn { color: #B45309; font-size: 11px; margin-left: 4px; }

/* footer buttons */
.fb-foot { display: flex; justify-content: flex-end; gap: 10px; }
.fb-btn-cancel { border-radius: 8px !important; padding: 9px 20px !important; font-weight: 500 !important; }
.fb-btn-save {
  border-radius: 8px !important;
  padding: 9px 22px !important;
  font-weight: 500 !important;
  background: linear-gradient(135deg, #4F6BFF 0%, #3D5BE0 100%) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(79, 107, 255, 0.3) !important;
}
.fb-btn-save:hover {
  box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4) !important;
  transform: translateY(-1px);
}
.fb-btn-save:active { transform: translateY(0); }

</style>
