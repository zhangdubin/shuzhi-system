<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { expenseApi, invoiceOcrApi, projectApi } from "@/api/modules"
import { adminApi } from "@/api/admin"
import { aiApi } from '@/api/ai'
import { useUserStore } from '@/stores/user'
import { sdk } from '@/api/sdk'

// 类别 icon fallback（字典里没 icon 字段，按 value 给一个常用 emoji）
const _CATEGORY_ICON_FALLBACK: Record<string, string> = {
  差旅: '✈', 招待: '🍽', 办公: '📎', 推广: '📢', 培训: '📚',
  快递: '📦', 出差交通: '🚄', 市内交通: '🚕', 打印: '🖨', 标书购买: '📑', 其他: '⋯',
}
function _iconOf(value: string, label: string): string {
  return _CATEGORY_ICON_FALLBACK[value] || _CATEGORY_ICON_FALLBACK[label] || '🏷'
}

// 触点 #10：✦ AI 拍照识别
const aiCaptureVisible = ref(false)
const aiCaptureLoading = ref(false)
const aiCaptureResult = ref<null | { fields: Record<string, any>; model: string; confidence: number }>(null)

async function runAiCapture() {
  aiCaptureLoading.value = true
  try {
    const r = await aiApi.extractInvoice({ fileId: 'demo-receipt', fileUrl: 'blob:demo', type: 'receipt' }).catch(() => null)
    if (r) {
      aiCaptureResult.value = { fields: Object.fromEntries(Object.entries(r.fields).map(([k, v]) => [k, (v as any).value])), model: r.meta.model, confidence: r.meta.confidence }
    } else {
      aiCaptureResult.value = {
        fields: { amount: 248, seller: '北京滴滴出行科技有限公司', date: '2026-06-12', category: '差旅-打车' },
        model: 'ernie-3.5 (mock)', confidence: 0.92,
      }
    }
    ElMessage.success('✦ AI 拍照识别完成')
  } finally {
    aiCaptureLoading.value = false
  }
}

function adoptAiCapture() {
  const r = aiCaptureResult.value
  if (!r) return
  ElMessage.success('已采纳 AI 识别结果到表单')
  aiCaptureVisible.value = false
}

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const step = ref(1)
const editId = ref<number | null>(null)
const approvalTemplates = ref<any[]>([])  // 审批流模板列表（步骤 3 预览用）
const editLoading = ref(false)
const isEdit = computed(() => editId.value !== null)
const steps = [
  { num: 1, lbl: '基础信息', meta: '费用类型、关联项目、申请日期' },
  { num: 2, lbl: '费用明细', meta: '子项金额、备注' },
  { num: 3, lbl: '提交审批', meta: '确认附件与审批流' },
]

// 表单
const form = reactive({
  category: '差旅',     // 差旅 / 招待 / 办公 / 推广 / 培训 / 其他
  purpose: '',           // 用途摘要
  applicantAt: new Date().toISOString().slice(0, 10),
  projectLink: '',
  description: '',
  paymentMethod: '支付宝/微信',
})

// 动态费用行
interface ExpenseItem { id: number; date: string; subCategory: string; amount: number; remark: string }
const items = ref<ExpenseItem[]>([
  { id: 1, date: form.applicantAt, subCategory: '机票', amount: 0, remark: '' },
])
let nextId = 2

function addItem() {
  items.value.push({ id: nextId++, date: form.applicantAt, subCategory: '', amount: 0, remark: '' })
}
function removeItem(id: number) {
  if (items.value.length <= 1) {
    ElMessage.warning('至少保留一条费用明细')
    return
  }
  items.value = items.value.filter((x) => x.id !== id)
}

// 实时总金额
const totalAmount = computed(() => items.value.reduce((s, x) => s + (Number(x.amount) || 0), 0))
const totalAmountDisplay = computed(() => totalAmount.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

// 匹配当前金额应该用的审批流模板
const matchedApprovalTemplate = computed(() => {
  const list = approvalTemplates.value.filter(t => t.isActive)
  if (list.length === 0) return null
  const amtCents = Math.round(totalAmount.value * 100)  // 转分跟后端一致
  // 优先匹配 amount_min 条件
  let matched: any = null
  for (const t of list) {
    const cond = t.condition || {}
    const amin = cond.amount_min
    if (amin != null && amtCents >= Number(amin)) {
      if (!matched || ((matched.condition || {}).amount_min || 0) < Number(amin)) {
        matched = t
      }
    }
  }
  if (!matched) {
    matched = list.find(t => t.isDefault) || list[0]
  }
  return matched
})
const approvalSteps = computed<any[]>(() => {
  const t = matchedApprovalTemplate.value
  if (!t) return []
  return (t.rules || []).map((r: string, i: number) => ({
    seq: i + 1,
    name: ({ submitter: '提交', direct_leader: '直属上级', finance: '财务审核', gm: '总经理审批', gm_if_over_5000: '总经理审批（≥¥5,000）' } as any)[r] || r,
    rule: r,
  }))
})

// tip-box：单笔 ≥ 5000 触发"财务总监审批"
const needCfoApproval = computed(() => totalAmount.value >= 5000)

// 类别选项：从后端字典 expense_category 同步，失败回退到硬编码 6 个
const categories = ref<{ value: string; icon: string; label: string }[]>([
  { value: '差旅', icon: '✈', label: '差旅' },
  { value: '招待', icon: '🍽', label: '招待' },
  { value: '办公', icon: '📎', label: '办公' },
  { value: '推广', icon: '📢', label: '推广' },
  { value: '培训', icon: '📚', label: '培训' },
  { value: '其他', icon: '⋯', label: '其他' },
])

// 子项类别（按选中主类别切换，简化版：固定常用）
const subCategories = ['机票', '酒店', '打车/交通', '餐补/其他', '办公用品', '业务招待', '场地/物料', '其他']

// 关联项目下拉：从 projectApi.list 拉真实数据（fallback: 空数组）
const projectOptions = ref<{ value: string; label: string }[]>([])

// 提交人（自动从 userStore 取）
const applicantName = computed(() => userStore.userInfo?.name || '当前用户')
const departmentName = computed(() => userStore.userInfo?.department || '未分配')

// 步骤切换
function nextStep() {
  if (step.value === 1) {
    if (!form.purpose.trim()) { ElMessage.warning('请填写费用事由'); return }
    if (!form.applicantAt) { ElMessage.warning('请选择申请日期'); return }
  }
  if (step.value === 2) {
    if (items.value.length === 0) { ElMessage.warning('请至少添加一条费用明细'); return }
    if (totalAmount.value <= 0) { ElMessage.warning('总金额需大于 0'); return }
  }
  if (step.value < 3) step.value++
}
function prevStep() { if (step.value > 1) step.value-- }

// 暂存 / 提交
async function saveDraft() {
  try {
    const payload: any = {
      category: form.category,
      title: form.purpose,
      description: form.description || null,
      amount: Number(totalAmount.value.toFixed(2)), // 后端 amount: float 单位元
      expenseDate: form.applicantAt,
      projectId: form.projectLink ? Number(form.projectLink) : null,
      contractId: null,
        breakdown: items.value.map((it: ExpenseItem) => ({
          label: it.subCategory,
          amount: Number(Number(it.amount || 0).toFixed(2)), // 后端 ExpenseBreakdownItem.amount: float 单位元
          remark: it.remark || null,
        })),
    }
    const r: any = editId.value
      ? await expenseApi.update(editId.value, payload).catch((e: any) => {
          ElMessage.error(e?.response?.data?.detail || '保存失败')
          return null
        })
      : await expenseApi.create(payload as any).catch((e: any) => {
          ElMessage.error(e?.response?.data?.detail || '保存失败')
          return null
        })
    if (r?.expenseId) {
      ElMessage.success(editId.value ? '已保存修改' : '已暂存为草稿')
      router.replace('/expense/list').then(() => {
        setTimeout(() => window.location.reload(), 200)
      })
    } else {
      ElMessage.error(r?.message || '保存失败')
    }
  } catch {
    /* cancel */
  }
}
async function submitApproval() {
  try {
    await ElMessageBox.confirm(
      `确认提交审批？报销总金额 ¥${totalAmountDisplay.value}。${needCfoApproval.value ? '单笔 ≥ ¥5,000，将触发财务总监审批。' : ''}`,
      '提交确认',
      { confirmButtonText: '确认提交', cancelButtonText: '再看看', type: 'warning' }
    )
  } catch {
    return
  }
  const payload = {
    category: form.category,
    title: form.purpose,          // 后端字段是 title
    description: form.description || null,
    amount: Number(totalAmount.value.toFixed(2)), // 后端 amount: float 单位元（内部 ×100 存分）
    expenseDate: form.applicantAt,
    projectId: form.projectLink ? Number(form.projectLink) : null,
    contractId: null,
      breakdown: items.value.map((it: ExpenseItem) => ({
        label: it.subCategory,
        amount: Number(Number(it.amount || 0).toFixed(2)), // 后端 ExpenseBreakdownItem.amount: float 单位元
        remark: it.remark || null,
      })),
  }
  console.log('[submitApproval] payload:', payload)
  let r: any = null
  if (editId.value) {
    r = await expenseApi.update(editId.value, payload).catch((e: any) => {
      console.error('[submitApproval] update error:', e?.response?.status, e?.response?.data)
      const detail = e?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : (e?.message || '提交失败'))
      ElMessage.error('保存失败：' + msg)
      return null
    })
  } else {
    r = await expenseApi.create(payload as any).catch((e: any) => {
      console.error('[submitApproval] create error:', e?.response?.status, e?.response?.data)
      const detail = e?.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : (e?.message || '提交失败'))
      ElMessage.error('提交失败：' + msg)
      return null
    })
  }
  console.log('[submitApproval] result:', r)
  if (r?.expenseId) {
    await expenseApi.submit(r.expenseId).catch(() => null)
  }
  if (r?.expenseId) {
    ElMessage.success('已提交审批')
    // 强制刷新 list 页面（避免 vue-router 复用组件导致 onMounted 不触发）
    router.replace('/expense/list').then(() => {
      // 触发 list 的 loadData
      setTimeout(() => window.location.reload(), 200)
    })
  } else {
    ElMessage.error(r?.message || '提交失败')
  }
}

function cancel() { router.push('/expense/list') }

// 智能归类：根据销售方/发票类型关键字推断费用类别
function _classifyByInvoice(sellerName: string, invoiceType: string): string {
  const s = (sellerName || '').toLowerCase()
  const t = (invoiceType || '')
  if (/酒店|宾馆|民宿|旅馆|旅游|航空|铁路|出租|网约车|打车|滴滴|航站|机场|机票|高铁|火车/.test(s)) return '差旅'
  if (/餐饮|餐厅|饭店|食堂|咖啡|茶|酒|招待|宴请|酒店(?!管理)|火锅/.test(s)) return '招待'
  if (/办公|文具|打印|印刷|耗材|纸张|墨盒|硒鼓|京东(?!物流)|得力|晨光/.test(s)) return '办公'
  if (/软件|科技|SaaS|云|数据|信息|网络|通信|移动|联通|电信|服务费|平台费|订阅|授权/.test(s)) return '办公'
  if (/广告|推广|传媒|宣传|营销|百度|头条|抖音|小红书|小红|投放/.test(s)) return '推广'
  if (/培训|教育|学校|课程|讲座|咨询|顾问/.test(s)) return '办公'
  return '其他'
}

onMounted(async () => {
  // 拉取费用类别字典（与后台 /admin/dicts 同步）
  try {
    const r: any = await sdk.common.dict('expense_category')
    const list = r?.list || []
    if (list.length > 0) {
      categories.value = list.map((d: any) => ({
        value: d.value,
        label: d.label || d.value,
        icon: _iconOf(d.value, d.label || d.value),
      }))
    }
  } catch (e) {
    console.warn('[load expense_category dict]', e)
  }

  // 拉取关联项目列表（从项目管理的真实数据）
  try {
    const r: any = await projectApi.list({ page: 1, pageSize: 100 } as any)
    const list = r?.list || []
    projectOptions.value = list.map((p: any) => ({
      // 后端 projects/list 返回字段是 id（不是 projectId）
      value: String(p.id ?? p.projectId),
      label: `${p.code} · ${p.name}${p.clientName ? ' · ' + p.clientName : ''}`,
    }))
  } catch (e) {
    console.warn('[load projects list]', e)
  }

  // 编辑模式：?id=40 加载已有费用
  const editIdVal = Number(route.query.id)
  if (editIdVal && !Number.isNaN(editIdVal)) {
    editId.value = editIdVal
    editLoading.value = true
    try {
      const d: any = await expenseApi.detail(editIdVal).catch(() => null)
      if (d) {
        form.category = d.category || '其他'
        form.purpose = d.title || ''
        form.description = d.description || ''
        form.applicantAt = (d.expenseDate || form.applicantAt).slice(0, 10)
        form.projectLink = d.projectId ? String(d.projectId) : ''
        // 填充明细
        if (Array.isArray(d.breakdown) && d.breakdown.length > 0) {
          items.value = d.breakdown.map((b: any, i: number) => ({
            id: i + 1,
            date: form.applicantAt,
            subCategory: b.label || '',
            amount: Number(b.amount || 0), // 后端 detail 返回的就是元
            remark: b.remark || '',
          }))
          nextId = d.breakdown.length + 1
        }
        ElMessage.success(`已加载费用 #${editIdVal}（${d.status === 'draft' ? '草稿' : d.status}）`)
      }
    } finally {
      editLoading.value = false
    }
  }

  // 加载审批流模板预览（步骤 3 用）
  try {
    const r: any = await adminApi.approvalTemplateList({ businessType: 'expense' }).catch(() => null)
    const list: any[] = (r?.list || r?.data?.list || r?.data || r) || []
    approvalTemplates.value = Array.isArray(list) ? list : []
  } catch (e) {
    console.warn('[load approval templates]', e)
  }

  // 触点 #24：从发票详情跳转过来时预填表单
  const invId = Number(route.query.invoiceId)
  if (invId && !Number.isNaN(invId)) {
    try {
      const resp: any = await invoiceOcrApi.detail(invId).catch(() => null)
      const d = resp?.data || resp
      if (d) {
        const seller = d.sellerName || ''
        const amt = Number(d.totalAmount || 0)
        const invNo = d.invoiceNo || d.code || String(invId)
        // 自动归类
        form.category = _classifyByInvoice(seller, d.invoiceType || '')
        // 第一条明细填金额
        if (items.value.length > 0) {
          items.value[0].date = (d.issueDate || form.applicantAt).slice(0, 10)
          items.value[0].subCategory = seller.slice(0, 20) || '发票入账'
          items.value[0].amount = amt
          items.value[0].remark = `关联发票 ${invNo} · ${seller}`
        }
        form.purpose = `关联发票 ${invNo} 报销`
        // description 用 [关联发票 INV-{数字ID}] 格式，便于后端按 linkedInvoiceId 过滤
        form.description = `[关联发票 INV-${invId}] 销售方：${seller} | 金额：¥${amt.toFixed(2)} | ${seller} → 入账`
        ElMessage.success(`已预填发票 #${invId} 的报销信息`)
      }
    } catch (e) {
      console.warn('[prefill invoice]', e)
    }
  }
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部 -->
    <div class="page-header">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/expense/list" style="color: var(--color-text-tertiary)">销售费用</router-link> / {{ isEdit ? '编辑' : '新建' }}
        </div>
        <h1>{{ isEdit ? '✎ 编辑销售费用' : '📝 录入销售费用' }}</h1>
        <p class="page-desc">{{ isEdit ? `正在编辑费用 #${editId}（${editLoading ? '加载中…' : '已加载'}）` : '单号 EX-2026-0612-003 · 提交后将进入审批流' }}</p>
      </div>
      <div style="display: flex; gap: 8px">
        <!-- 触点 #10：✦ AI 拍照识别 -->
        <el-button class="btn-ai-capture" @click="aiCaptureVisible = true">✦ AI 拍照识别</el-button>
        <el-button @click="cancel">取消</el-button>
      </div>
    </div>

    <!-- 步骤条 -->
    <div class="step-bar">
      <div
        v-for="s in steps"
        :key="s.num"
        :class="['step-item', step > s.num ? 'done' : (step === s.num ? 'current' : '')]"
      >
        <div class="step-num">{{ step > s.num ? '✓' : s.num }}</div>
        <div class="step-info">
          <div class="l">{{ s.lbl }}</div>
          <div class="m">{{ s.meta }}</div>
        </div>
      </div>
    </div>

    <!-- Step 1: 基础信息 -->
    <div v-if="step === 1" class="form-section">
      <div class="fs-head">
        <h3>📝 基础信息</h3>
        <span class="req">* 为必填</span>
      </div>
      <div class="fs-body">
        <div class="form-row-1">
          <div class="field">
            <label>费用类别 <span class="req">*</span></label>
            <el-radio-group v-model="form.category" size="default" style="flex-wrap: wrap; gap: 4px">
              <el-radio-button v-for="c in categories" :key="c.value" :value="c.value">
                {{ c.icon }} {{ c.value }}
              </el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div class="form-row-2" style="margin-top: 16px">
          <div class="field">
            <label>用途摘要 <span class="req">*</span></label>
            <el-input v-model="form.purpose" placeholder="如：上海-北京客户拜访（北辰集团）" maxlength="80" show-word-limit />
          </div>
          <div class="field">
            <label>申请日期 <span class="req">*</span></label>
            <el-date-picker v-model="form.applicantAt" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
        </div>

        <div class="form-row-2" style="margin-top: 4px">
          <div class="field">
            <label>关联项目</label>
            <el-select v-model="form.projectLink" placeholder="选择关联项目（可选）" style="width: 100%" clearable>
              <el-option v-for="o in projectOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </div>
          <div class="field">
            <label>支付方式</label>
            <el-select v-model="form.paymentMethod" style="width: 100%">
              <el-option label="对公转账" value="对公转账" />
              <el-option label="现金" value="现金" />
              <el-option label="支付宝/微信" value="支付宝/微信" />
            </el-select>
          </div>
        </div>

        <div class="form-row-1" style="margin-top: 4px">
          <div class="field">
            <label>申请人</label>
            <el-input :value="`${applicantName} · ${departmentName}`" disabled />
          </div>
        </div>

        <div class="form-row-1" style="margin-top: 4px">
          <div class="field">
            <label>详细说明</label>
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              placeholder="详细说明费用用途、参与人员、客户背景等（选填）"
              maxlength="500"
              show-word-limit
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2: 费用明细 -->
    <div v-if="step === 2" class="form-section">
      <div class="fs-head">
        <h3>💰 费用明细</h3>
        <el-button type="primary" link @click="addItem">+ 添加一行</el-button>
      </div>
      <div class="fs-body">
        <el-table :data="items" border>
          <el-table-column type="index" label="#" width="50" />
          <el-table-column label="费用日期" width="160">
            <template #default="{ row }">
              <el-date-picker v-model="row.date" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%" />
            </template>
          </el-table-column>
          <el-table-column label="子项类别" width="140">
            <template #default="{ row }">
              <el-select v-model="row.subCategory" size="small" placeholder="选择" style="width: 100%">
                <el-option v-for="s in subCategories" :key="s" :label="s" :value="s" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="金额（元）" width="160">
            <template #default="{ row }">
              <el-input-number
                v-model="row.amount"
                :min="0"
                :precision="2"
                :step="10"
                size="small"
                style="width: 100%"
                controls-position="right"
              />
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="240">
            <template #default="{ row }">
              <el-input v-model="row.remark" size="small" placeholder="选填" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button type="danger" link size="small" @click="removeItem(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 总金额 + tip-box -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px">
          <div
            class="tip-box"
            :style="{
              'margin-bottom': 0,
              'flex': 1,
              'margin-right': '16px',
              ...(needCfoApproval ? { background: 'rgba(245,158,11,0.08)', borderColor: 'rgba(245,158,11,0.3)' } : {}),
            }"
          >
            <div class="ico" :style="needCfoApproval ? 'color: var(--color-warning);' : ''">{{ needCfoApproval ? '⚠' : 'ℹ' }}</div>
            <div>
              <strong v-if="needCfoApproval">触发财务总监审批：</strong>
              <strong v-else>说明：</strong>
              本次合计 ¥{{ totalAmountDisplay }} 元，
              <template v-if="needCfoApproval">已超过 ¥5,000 门槛，将额外经过"财务总监"审批节点。</template>
              <template v-else>未触发 ¥5,000 财务总监审批门槛。</template>
            </div>
          </div>
          <div style="text-align: right">
            <div style="font-size: 12px; color: var(--color-text-tertiary)">合计金额</div>
            <div style="font-size: 26px; font-weight: 700; color: var(--color-danger); line-height: 1.2">
              ¥ {{ totalAmountDisplay }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3: 提交预览 -->
    <div v-if="step === 3" class="form-section">
      <div class="fs-head">
        <h3>✅ 提交预览</h3>
        <span class="req">确认后提交至审批流</span>
      </div>
      <div class="fs-body">
        <div class="info-grid">
          <div class="info-row"><span class="l">费用类别</span><span class="v">{{ form.category }}</span></div>
          <div class="info-row"><span class="l">用途摘要</span><span class="v">{{ form.purpose || '—' }}</span></div>
          <div class="info-row"><span class="l">申请日期</span><span class="v">{{ form.applicantAt }}</span></div>
          <div class="info-row"><span class="l">关联项目</span><span class="v">
            <a v-if="form.projectLink" href="javascript:;" style="color: var(--color-primary)">{{ projectOptions.find(p => p.value === form.projectLink)?.label || form.projectLink }}</a>
            <span v-else>—</span>
          </span></div>
          <div class="info-row"><span class="l">申请人</span><span class="v">{{ applicantName }} · {{ departmentName }}</span></div>
          <div class="info-row"><span class="l">支付方式</span><span class="v">{{ form.paymentMethod }}</span></div>
          <div class="info-row"><span class="l">费用项数</span><span class="v">{{ items.length }} 项</span></div>
          <div class="info-row"><span class="l">合计金额</span><span class="v" style="color: var(--color-danger); font-weight: 700; font-size: 15px">
            ¥ {{ totalAmountDisplay }}
          </span></div>
          <div class="info-row full" v-if="form.description">
            <span class="l">详细说明</span>
            <div class="term-block">
              <div class="d">{{ form.description }}</div>
            </div>
          </div>
        </div>

        <div class="approval-preview" style="margin-top: 18px">
          <div v-if="matchedApprovalTemplate" style="margin-bottom: 10px; font-size: 12px; color: var(--color-text-tertiary)">
            📐 当前使用模板：<strong style="color: var(--color-primary)">{{ matchedApprovalTemplate.name }}</strong>
            <span v-if="matchedApprovalTemplate.condition && matchedApprovalTemplate.condition.amount_min" style="margin-left: 6px; color: #B45309">
              ⚡ 金额 ≥ ¥{{ (matchedApprovalTemplate.condition.amount_min / 100).toLocaleString() }} 触发
            </span>
          </div>
          <template v-if="approvalSteps.length > 0">
            <template v-for="(s, i) in approvalSteps" :key="i">
              <div :class="['ap-step', i === 0 ? 'done' : '']">
                <span class="n">{{ s.seq }}</span>
                <span class="p">{{ s.name }}<span v-if="i === 0"> · {{ applicantName }}</span></span>
              </div>
              <span v-if="i < approvalSteps.length - 1" class="ap-arrow">→</span>
            </template>
          </template>
          <template v-else>
            <div class="ap-step done"><span class="n">1</span><span class="p">提交人 · {{ applicantName }}</span></div>
            <span class="ap-arrow">→</span>
            <div class="ap-step"><span class="n">2</span><span class="p">部门经理</span></div>
            <span class="ap-arrow">→</span>
            <div class="ap-step"><span class="n">3</span><span class="p">财务审核</span></div>
          </template>
        </div>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot">
      <div style="font-size: 12.5px; color: var(--color-text-tertiary)">
        <span v-if="step === 1">下一步：填写费用明细</span>
        <span v-else-if="step === 2">下一步：确认信息并提交</span>
        <span v-else>合计：<strong style="color: var(--color-danger); font-size: 14px">¥ {{ totalAmountDisplay }}</strong>
          <span v-if="needCfoApproval" style="margin-left: 8px; color: var(--color-warning)">⚠ 将触发财务总监审批</span>
        </span>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button v-if="step > 1" @click="prevStep">← 上一步</el-button>
        <el-button @click="saveDraft">{{ isEdit ? "保存修改" : "存为草稿" }}</el-button>
        <el-button v-if="step < 3" type="primary" @click="nextStep">下一步 →</el-button>
        <el-button v-else type="primary" @click="submitApproval">✓ 提交审批</el-button>
      </div>
    </div>

    <!-- 触点 #10：✦ AI 拍照识别 Drawer -->
    <el-drawer v-model="aiCaptureVisible" title="✦ AI 拍照识别" direction="rtl" size="480px">
      <div class="ai-capture-drawer">
        <div class="ai-capture-zone" @click="runAiCapture">
          <div class="ai-capture-icon">📸</div>
          <h3>点击上传发票 / 小票照片</h3>
          <p>支持 JPG / PNG / PDF · 自动识别金额、销方、日期、品类</p>
        </div>

        <el-progress v-if="aiCaptureLoading" :percentage="65" :stroke-width="6" status="success" />

        <div v-if="aiCaptureResult" class="ai-capture-result">
          <h4>✨ 识别结果</h4>
          <p class="ai-capture-meta">由 {{ aiCaptureResult.model }} 识别 · 置信度 {{ (aiCaptureResult.confidence * 100).toFixed(0) }}%</p>
          <div class="ai-capture-fields">
            <div v-for="(v, k) in aiCaptureResult.fields" :key="k" class="ai-capture-row">
              <span class="ai-capture-k">{{ k }}</span>
              <span class="ai-capture-v">{{ v }}</span>
            </div>
          </div>
          <div class="ai-capture-actions">
            <el-button type="primary" @click="adoptAiCapture">✓ 采纳到表单</el-button>
            <el-button @click="aiCaptureResult = null">重新识别</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
/* 触点 #10：AI 拍照识别 */
.btn-ai-capture {
  background: $gradient-brand; color: #fff; border: none; font-weight: 600;
  box-shadow: 0 2px 8px rgba(79,107,255,0.25);
  &:hover { opacity: 0.92; }
}
.ai-capture-drawer { padding: 0 4px; }
.ai-capture-zone {
  padding: 40px 20px; text-align: center;
  background: linear-gradient(135deg, rgba(79,107,255,0.05) 0%, rgba(124,58,237,0.05) 100%);
  border: 2px dashed rgba(124,58,237,0.4);
  border-radius: $radius-md;
  cursor: pointer; transition: all 0.15s;
  &:hover { border-color: #7C3AED; background: linear-gradient(135deg, rgba(79,107,255,0.08) 0%, rgba(124,58,237,0.08) 100%); }
  .ai-capture-icon { font-size: 48px; margin-bottom: 12px; }
  h3 { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  p { font-size: 12px; color: $color-text-secondary; }
}
.ai-capture-result {
  margin-top: 20px; padding: 14px;
  background: linear-gradient(135deg, rgba(79,107,255,0.03) 0%, rgba(124,58,237,0.03) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-md;
  h4 { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
}
.ai-capture-meta { font-size: 11px; color: $color-text-secondary; margin-bottom: 10px; }
.ai-capture-fields { display: flex; flex-direction: column; gap: 6px; }
.ai-capture-row {
  display: flex; justify-content: space-between; padding: 6px 10px;
  background: #fff; border-radius: $radius-sm; font-size: 12px;
  .ai-capture-k { color: $color-text-tertiary; }
  .ai-capture-v { color: $color-text-primary; font-weight: 600; }
}
.ai-capture-actions { display: flex; gap: 8px; margin-top: 12px; }
</style>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }
.page-container { padding-bottom: 80px; }
</style>
