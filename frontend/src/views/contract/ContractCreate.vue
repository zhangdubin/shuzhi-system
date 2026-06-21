<script setup lang="ts">
/**
 * ContractCreate · 合同创建（1:1 复刻 design/contract-create.html）
 * - 顶部 step-bar（4 步：基本信息 / 条款 / 付款 / 提交）
 * - tip-box 流程提示
 * - 5 form-section：合同模板 / 基本信息 / 合同条款 / 付款计划 / 附件
 * - approval-preview 审批流预览
 * - 底部 form-foot 操作条（保存草稿/取消/预览/提交审批）
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractApi } from '@/api/modules'
import { aiApi } from '@/api/ai'

// 触点 #6：✦ AI 一键起草 Drawer
const aiDrawerVisible = ref(false)
const aiDraftType = ref('销售合同')
const aiDraftClient = ref('')
const aiDraftAmount = ref<number>(50000)
const aiDraftHint = ref('')
const aiDrafting = ref(false)
const aiDraftProgress = ref(0)
const aiDraftResult = ref<null | Awaited<ReturnType<typeof aiApi.generateDraft>>>(null)
let aiDraftTimer: number | null = null

async function runAiDraft() {
  aiDrafting.value = true
  aiDraftProgress.value = 0
  aiDraftResult.value = null
  // 模拟进度
  aiDraftTimer = window.setInterval(() => {
    if (aiDraftProgress.value >= 95) { if (aiDraftTimer) clearInterval(aiDraftTimer); return }
    aiDraftProgress.value = Math.min(95, aiDraftProgress.value + 8 + Math.random() * 5)
  }, 250)
  try {
    const r = await aiApi.generateDraft({
      type: 'contract',
      context: { contractType: aiDraftType.value, client: aiDraftClient.value, amount: aiDraftAmount.value, hint: aiDraftHint.value },
    }).catch(() => null)
    if (r) {
      aiDraftResult.value = r
      ElMessage.success('✦ AI 起草完成')
    } else {
      // mock 回退
      aiDraftResult.value = {
        taskId: 'task-mock-001',
        type: 'contract',
        draft: {
          title: `${aiDraftClient.value} ${aiDraftType.value}（AI 起草）`,
          content: '本合同...',
          sections: [
            { heading: '合同标的', body: `甲方向乙方提供 ${aiDraftType.value} 服务，金额 ¥ ${aiDraftAmount.value.toLocaleString()}。` },
            { heading: '服务期限', body: '本合同有效期 12 个月，自双方签字盖章之日起生效。' },
            { heading: '付款方式', body: `合同总金额 ¥ ${aiDraftAmount.value.toLocaleString()}，分 4 期支付，每季度 25%。` },
            { heading: '双方权利义务', body: '甲方应按时支付服务费用；乙方应按 SLA 99.9% 提供服务。' },
            { heading: '保密条款', body: '双方对在合作中获取的对方商业秘密承担保密义务。' },
            { heading: '违约责任', body: '任一方违约应承担合同金额 30% 的违约金，并赔偿对方损失。' },
            { heading: '争议解决', body: '本合同适用中华人民共和国法律，争议提交上海仲裁委员会仲裁。' },
            { heading: '其他', body: '本合同一式两份，双方各执一份，具同等法律效力。' },
          ],
          fields: { amount: aiDraftAmount.value, period: 12, payMethod: '分期付款' },
          confidence: 0.88,
          model: 'ernie-3.5 (mock)',
          durationMs: 1845,
        },
      }
      ElMessage.success('✦ AI 起草完成（mock）')
    }
    aiDraftProgress.value = 100
  } catch (e) {
    ElMessage.error('AI 起草失败：' + (e as any)?.message)
  } finally {
    aiDrafting.value = false
    if (aiDraftTimer) clearInterval(aiDraftTimer)
  }
}

function adoptAiDraft() {
  const r = aiDraftResult.value
  if (!r) return
  form.name = r.draft.title
  form.summary = r.draft.sections.map(s => `${s.heading}：${s.body}`).join('\n')
  form.amount = r.draft.fields.amount?.toLocaleString() || form.amount
  aiDrawerVisible.value = false
  ElMessage.success('已采纳 AI 起草内容到表单')
}

const router = useRouter()
const route = useRoute()
const formRef = ref()
const activeStep = ref(0)

const form = reactive({
  template: '标准销售合同 v2.1',
  name: '万象科技 SaaS 服务合同 2026Q2',
  type: '销售合同',
  client: '万象科技有限公司',
  contact: '李建国（CTO）',
  taxNo: '91310000MA1FL01X9G',
  amount: '86,500.00',
  currency: '人民币 (CNY)',
  period: '12 个月',
  signDate: '2026-06-12',
  startDate: '2026-06-15',
  endDate: '2027-06-10',
  payMethod: '分期付款',
  payTerm: '30 天',
  project: 'PRJ-2026-022 · 万象科技 SaaS 部署',
  manager: '陈思琪（项目经理）',
  summary: '万象科技 2026 年 Q2 SaaS 平台服务合同，涵盖发票识别、模板管理、报表分析等核心模块。包含季度版本升级、技术支持 SLA、专属客户经理等增值服务。分 4 期支付，每季度 ¥ 21,625。',
})

const rules = {
  name: [{ required: true, message: '请输入合同名称', trigger: 'blur' }],
  amount: [{ required: true, message: '请输入合同金额', trigger: 'blur' }],
  signDate: [{ required: true, message: '请选择签订日期', trigger: 'change' }],
}

// 3 个模板（design 真实示例）
const templates = ref([
  { name: '标准销售合同 v2.1', desc: '适用于一次性销售，含服务内容、付款、保密等 8 项标准条款', meta: '8 条款 · 已用 86 次', active: true },
  { name: 'SaaS 服务合同',     desc: '按订阅周期付费，含 SLA、数据安全、续费条款',           meta: '12 条款 · 已用 28 次', active: false },
  { name: '采购框架协议',     desc: '长期采购框架，含价格机制、订货流程、年度回顾',       meta: '15 条款 · 已用 4 次',  active: false },
])

// 8 条合同条款（design 真实示例）
const terms = ref([
  { t: '1. 服务内容', d: 'SaaS 平台标准版 30 个用户账号，含发票识别、模板管理、报表分析、API 对接等核心功能。' },
  { t: '2. 付款条款', d: '合同总金额 ¥ 86,500，分 4 期支付，每季度 ¥ 21,625。每期发票在付款前 5 个工作日开具。' },
  { t: '3. 服务期限', d: '本合同服务期为 12 个月，自 2026-06-15 起至 2027-06-14 止。期满前 30 日双方协商续约。' },
  { t: '4. SLA 保障', d: '系统可用性 99.9%，月度故障时长 < 43 分钟。超时按服务费 1%/小时补偿。' },
  { t: '5. 数据安全', d: '乙方数据加密存储于阿里云华东节点，3 副本异地灾备，符合等保三级。' },
  { t: '6. 知识产权', d: 'SaaS 平台知识产权归乙方所有。甲方数据归甲方所有，乙方不得用于服务以外任何目的。' },
  { t: '7. 保密条款', d: '双方对合作过程中知悉的对方商业秘密承担保密义务，期限至本合同终止后 3 年。' },
  { t: '8. 争议解决', d: '因本合同引起的争议，双方协商解决；协商不成的，提交上海仲裁委员会仲裁。' },
])

// 4 期付款计划（design 自动算出）
const payPlans = ref([
  { period: '第 1 期', amount: '21,625.00', date: '2026-06-15', invoice: '待开票', status: 'pending' },
  { period: '第 2 期', amount: '21,625.00', date: '2026-09-15', invoice: '—',      status: 'pending' },
  { period: '第 3 期', amount: '21,625.00', date: '2026-12-15', invoice: '—',      status: 'pending' },
  { period: '第 4 期', amount: '21,625.00', date: '2027-03-15', invoice: '—',      status: 'pending' },
])

// 4 步 step
const steps = [
  { num: 1, l: '基本信息', m: '模板 + 字段' },
  { num: 2, l: '合同条款', m: '模板带入，可编辑' },
  { num: 3, l: '付款计划', m: '分期自动生成' },
  { num: 4, l: '提交审批', m: '预览并发起' },
]

// 审批流预览
const approvalSteps = ref([
  { n: '1', p: '起草人' },
  { n: '2', p: '法务' },
  { n: '3', p: '财务' },
  { n: '≥5万', p: '总经理', trigger: true },
  { n: '4', p: '电子签' },
  { n: '5', p: '归档' },
])

function selectTpl(name: string) {
  templates.value.forEach(t => t.active = t.name === name)
  form.template = name
  ElMessage.info(`已选模板: ${name}`)
}
function addTerm() { ElMessage.info('添加条款') }
function importTerms() { ElMessage.info('导入条款') }
function resetTerms() { ElMessage.info('已重置为模板') }
function attachFiles() { ElMessage.info('选择附件') }
function saveDraft() { ElMessage.success('草稿已保存') }
function previewContract() { ElMessage.info('预览合同') }
async function submitApproval() {
  try {
    const amountNum = parseFloat(String(form.amount).replace(/,/g, '')) || 0
    await contractApi.create({
      title: form.name,
      description: form.summary,
      contractType: form.type,
      clientName: form.client,
      contactPerson: form.contact,
      taxNumber: form.taxNo,
      amount: amountNum,
      currency: form.currency,
      period: form.period,
      signDate: form.signDate,
      startDate: form.startDate,
      endDate: form.endDate,
      paymentMethod: form.payMethod,
      paymentTerm: form.payTerm,
      projectName: form.project,
      managerName: form.manager,
    } as any)
    ElMessage.success('合同已提交审批')
    setTimeout(() => router.push('/contract/list'), 800)
  } catch (e: any) {
    ElMessage.error('提交失败：' + (e?.message || '未知错误'))
  }
}

onMounted(async () => {
  // 触点 #24：从发票详情跳转过来 - 自动预填并标注关联
  const linkInvoiceId = Number(route.query.linkInvoiceId) || 0
  if (linkInvoiceId) {
    try {
      const { invoiceOcrApi } = await import('@/api/modules')
      const resp: any = await invoiceOcrApi.detail(linkInvoiceId).catch(() => null)
      const d = resp?.data || resp
      if (d) {
        const seller = d.sellerName || ''
        const amt = Number(d.totalAmount || 0)
        const invNo = d.invoiceNo || d.code || String(linkInvoiceId)
        const issueDate = (d.issueDate || '').slice(0, 10)
        form.client = seller || form.client
        form.amount = amt > 0 ? amt.toFixed(2) : form.amount
        form.name = `${seller} 关联合同（来自发票 ${invNo}）`
        form.summary = `本合同与发票 ${invNo}（开票日期 ${issueDate}，金额 ¥${amt.toFixed(2)}，销售方 ${seller}）关联。\n` + (form.summary || '')
        ElMessage.success(`已预填发票 #${linkInvoiceId} 的合同基础信息`)
      }
    } catch (e) {
      console.warn('[prefill invoice for contract]', e)
    }
  }
  contractApi.list({ page: 1, pageSize: 1 } as any).catch(() => {})
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部标题（design: h1 + breadcrumb） -->
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/contract/list')">业务</a>
          <span class="sep">/</span>
          <a @click="router.push('/contract/list')">合同管理</a>
          <span class="sep">/</span>
          <span class="current">新建合同</span>
        </div>
        <h1>新建合同</h1>
        <p class="page-desc">按 4 步完成合同起草，提交后将进入审批流</p>
      </div>
      <div class="page-actions">
        <!-- 触点 #6：✦ AI 一键起草 -->
        <button class="btn-ai-draft" @click="aiDrawerVisible = true">
          <span class="ai-draft-icon">✦</span>
          <span>AI 一键起草</span>
        </button>
        <button class="btn btn-outline btn-sm" @click="router.push('/contract/list')">取消</button>
      </div>
    </div>

    <!-- step-bar（design: 4 步） -->
    <div class="page-card">
      <div class="step-bar">
        <div v-for="(s, i) in steps" :key="i" :class="['step-item', { active: activeStep === i, done: activeStep > i }]">
          <div class="step-num">{{ activeStep > i ? '✓' : s.num }}</div>
          <div class="step-info">
            <div class="l">{{ s.l }}</div>
            <div class="m">{{ s.m }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 流程提示（design: tip-box） -->
    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>提交后流程：</strong>
        起草 → 法务审核 → 财务审核 → 总经理审批（≥ 5 万）→ 电子签 → 归档。
        预计 <strong>1-3 个工作日</strong>完成全部审批。
      </div>
    </div>

    <!-- 1. 合同模板 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📑 合同模板 <span class="req">已选 1 个</span></h3>
        <a class="link-primary">查看全部模板 →</a>
      </div>
      <div class="fs-body">
        <div class="tpl-grid">
          <div v-for="t in templates" :key="t.name" :class="['tpl-card', { active: t.active }]" @click="selectTpl(t.name)">
            <div class="name">{{ t.name }}</div>
            <div class="desc">{{ t.desc }}</div>
            <div class="meta">{{ t.meta }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 基本信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📋 基本信息 <span class="req">* 必填</span></h3>
      </div>
      <div class="fs-body">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="合同名称" prop="name" required>
                <el-input v-model="form.name" placeholder="例如：XX 公司 SaaS 服务合同 2026Q2" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="合同类型" required>
                <el-select v-model="form.type" style="width: 100%">
                  <el-option label="销售合同" value="销售合同" />
                  <el-option label="采购合同" value="采购合同" />
                  <el-option label="服务合同" value="服务合同" />
                  <el-option label="框架协议" value="框架协议" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="客户" required>
                <el-select v-model="form.client" style="width: 100%">
                  <el-option label="万象科技有限公司" value="万象科技有限公司" />
                  <el-option label="北辰实业集团" value="北辰实业集团" />
                  <el-option label="朗驰智能设备有限公司" value="朗驰智能设备有限公司" />
                  <el-option label="+ 新建客户" value="__new__" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="客户联系人">
                <el-input v-model="form.contact" placeholder="选填，自动带出" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="客户纳税人识别号">
                <el-input v-model="form.taxNo" style="font-family: var(--font-family-mono); font-size: 12.5px;" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="合同金额（元）" prop="amount" required>
                <el-input v-model="form.amount" style="font-weight: 600;">
                  <template #prepend><span style="color: #4F6BFF; font-weight: 600;">¥</span></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="币种">
                <el-select v-model="form.currency" style="width: 100%">
                  <el-option label="人民币 (CNY)" value="人民币 (CNY)" />
                  <el-option label="美元 (USD)" value="美元 (USD)" />
                  <el-option label="欧元 (EUR)" value="欧元 (EUR)" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="合同期限">
                <el-input v-model="form.period" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="签订日期" prop="signDate" required>
                <el-date-picker v-model="form.signDate" type="date" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="生效日期" required>
                <el-date-picker v-model="form.startDate" type="date" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="到期日期" required>
                <el-date-picker v-model="form.endDate" type="date" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="付款方式" required>
                <el-select v-model="form.payMethod" style="width: 100%">
                  <el-option label="一次性付清" value="一次性付清" />
                  <el-option label="分期付款" value="分期付款" />
                  <el-option label="按里程碑付款" value="按里程碑付款" />
                  <el-option label="按使用量付款" value="按使用量付款" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="付款账期">
                <el-select v-model="form.payTerm" style="width: 100%">
                  <el-option label="款到发货" value="款到发货" />
                  <el-option label="30 天" value="30 天" />
                  <el-option label="60 天" value="60 天" />
                  <el-option label="90 天" value="90 天" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="关联项目" required>
                <el-select v-model="form.project" style="width: 100%">
                  <el-option label="PRJ-2026-022 · 万象科技 SaaS 部署" value="PRJ-2026-022 · 万象科技 SaaS 部署" />
                  <el-option label="PRJ-2026-018 · 数智化二期" value="PRJ-2026-018 · 数智化二期" />
                  <el-option label="暂不关联" value="__none__" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="负责人" required>
                <el-select v-model="form.manager" style="width: 100%">
                  <el-option label="张明（财务总监）" value="张明（财务总监）" />
                  <el-option label="陈思琪（项目经理）" value="陈思琪（项目经理）" />
                  <el-option label="刘洋（销售经理）" value="刘洋（销售经理）" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="合同摘要" required>
            <el-input v-model="form.summary" type="textarea" :rows="3"
                      placeholder="简要描述本合同的目的、主要内容、生效条件等（200 字以内）" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 3. 合同条款 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📜 合同条款 <span class="req">来自模板 · 可编辑</span></h3>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-ghost btn-sm" @click="resetTerms">↻ 重置为模板</button>
          <button class="btn btn-outline btn-sm" @click="importTerms">📥 导入条款</button>
        </div>
      </div>
      <div class="fs-body">
        <div class="term-list">
          <div v-for="(t, i) in terms" :key="i" class="term-item">
            <div class="drag">⋮⋮</div>
            <div class="body">
              <div class="t">{{ t.t }}</div>
              <div class="d">{{ t.d }}</div>
            </div>
            <div class="actions">
              <button title="编辑">✎</button>
              <button title="删除">⊗</button>
            </div>
          </div>
        </div>
        <div class="add-term" @click="addTerm">+ 添加新条款</div>
      </div>
    </div>

    <!-- 4. 付款计划（design 自动算） -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💰 付款计划 <span class="req">分期 4 期 · 自动生成</span></h3>
        <a class="link-primary">⚙ 自定义付款计划</a>
      </div>
      <div class="fs-body">
        <table class="pay-table">
          <thead>
            <tr><th>期次</th><th>金额</th><th>计划日期</th><th>开票</th><th>状态</th></tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in payPlans" :key="i">
              <td><strong>{{ p.period }}</strong></td>
              <td class="cell-amount">¥ {{ p.amount }}</td>
              <td>{{ p.date }}</td>
              <td>{{ p.invoice }}</td>
              <td><span class="tag tag-info">待支付</span></td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td><strong>合计</strong></td>
              <td class="cell-amount total">¥ 86,500.00</td>
              <td colspan="3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- 5. 附件 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📎 附件 <span class="opt">（可选）</span></h3>
      </div>
      <div class="fs-body">
        <div class="att-area" @click="attachFiles">
          <div class="ico">📂</div>
          <div class="t">点击或拖拽上传合同相关文件</div>
          <div class="m">支持 PDF / Word / Excel / 图片 · 单文件 ≤ 20MB · 最多 10 个</div>
        </div>
      </div>
    </div>

    <!-- 审批流预览（design: approval-preview） -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🔄 审批流预览 <span class="req">已配置 6 步</span></h3>
      </div>
      <div class="fs-body">
        <div class="approval-preview">
          <template v-for="(s, i) in approvalSteps" :key="i">
            <div :class="['ap-step', { trigger: s.trigger }]">
              <span class="n">{{ s.n }}</span>
              <span class="p">{{ s.p }}</span>
            </div>
            <span v-if="i < approvalSteps.length - 1" class="ap-arrow">→</span>
          </template>
        </div>
      </div>
    </div>

    <!-- 底部操作条（design: form-foot sticky） -->
    <div class="form-foot">
      <div>
        <button class="btn btn-ghost btn-sm" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-outline btn-sm" @click="router.push('/contract/list')">取消</button>
      </div>
      <div>
        <button class="btn btn-outline btn-sm" @click="previewContract">👁 预览合同</button>
        <button class="btn btn-primary btn-sm" @click="submitApproval">✓ 提交审批</button>
      </div>
    </div>

    <!-- 触点 #6：✦ AI 一键起草 Drawer -->
    <el-drawer v-model="aiDrawerVisible" title="✦ AI 一键起草合同" direction="rtl" size="540px">
      <div class="ai-draft-drawer">
        <div class="ai-draft-intro">
          <div class="ai-draft-icon-big">✦</div>
          <h3>让 AI 帮您起草合同初稿</h3>
          <p>基于合同类型、客户、金额等关键信息，AI 30 秒内生成完整合同初稿（含 8 项标准条款）。</p>
        </div>

        <el-form label-position="top" size="default">
          <el-form-item label="合同类型">
            <el-select v-model="aiDraftType" placeholder="选择合同类型">
              <el-option label="销售合同" value="销售合同" />
              <el-option label="采购合同" value="采购合同" />
              <el-option label="SaaS 服务合同" value="SaaS 服务合同" />
              <el-option label="技术开发合同" value="技术开发合同" />
            </el-select>
          </el-form-item>
          <el-form-item label="客户名称">
            <el-input v-model="aiDraftClient" placeholder="例：万象科技有限公司" />
          </el-form-item>
          <el-form-item label="合同金额（元）">
            <el-input-number v-model="aiDraftAmount" :min="0" :step="1000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="关键需求（可选）">
            <el-input v-model="aiDraftHint" type="textarea" :rows="3" placeholder="例：分 4 期付款，含 SLA 99.9% 保障" />
          </el-form-item>
          <el-button
            class="ai-draft-submit"
            :loading="aiDrafting"
            :disabled="!aiDraftType || !aiDraftClient"
            @click="runAiDraft"
          >
            <span v-if="!aiDrafting">✦ 开始 AI 起草</span>
            <span v-else>AI 起草中... {{ aiDraftProgress }}%</span>
          </el-button>
        </el-form>

        <el-progress v-if="aiDrafting" :percentage="aiDraftProgress" :stroke-width="6" status="success" />

        <!-- AI 起草结果 -->
        <div v-if="aiDraftResult" class="ai-draft-result">
          <div class="ai-draft-result-head">
            <span class="ai-draft-result-icon">✨</span>
            <div class="ai-draft-result-meta">
              <h4>{{ aiDraftResult.draft.title }}</h4>
              <p>由 {{ aiDraftResult.draft.model }} 起草 · 置信度 {{ (aiDraftResult.draft.confidence * 100).toFixed(0) }}% · 用时 {{ aiDraftResult.draft.durationMs }}ms</p>
            </div>
          </div>
          <div class="ai-draft-sections">
            <div v-for="(s, i) in aiDraftResult.draft.sections" :key="i" class="ai-draft-section">
              <h5>{{ i + 1 }}. {{ s.heading }}</h5>
              <p>{{ s.body }}</p>
            </div>
          </div>
          <div class="ai-draft-actions">
            <el-button type="primary" @click="adoptAiDraft">✓ 采纳并填入表单</el-button>
            <el-button @click="aiDraftResult = null">重新起草</el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

// step-bar（design: 4 步）
.step-bar {
  display: flex;
  gap: 0;
  padding: 8px 0;
  position: relative;
}
.step-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  position: relative;
  &::after {
    content: '';
    position: absolute;
    right: -10px; top: 50%;
    transform: translateY(-50%);
    width: 0; height: 0;
    border-left: 12px solid $color-border;
    border-top: 22px solid transparent;
    border-bottom: 22px solid transparent;
    z-index: 1;
  }
  &:last-child::after { display: none; }
  &.active {
    .step-num { background: $gradient-brand; color: #fff; border-color: transparent; }
    .step-info .l { color: $color-text-primary; font-weight: 600; }
  }
  &.done {
    .step-num { background: $color-success; color: #fff; border-color: transparent; }
  }
  .step-num {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: $color-bg;
    color: $color-text-tertiary;
    display: grid; place-items: center;
    font-size: 14px; font-weight: 600;
    border: 2px solid $color-border-strong;
    flex-shrink: 0;
    z-index: 2;
  }
  .step-info .l { font-size: 13.5px; font-weight: 500; color: $color-text-secondary; }
  .step-info .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
}

// tip-box（design）
.tip-box {
  display: flex; gap: 10px;
  padding: 12px 14px;
  background: rgba(79,107,255,0.05);
  border: 1px solid rgba(79,107,255,0.2);
  border-radius: $radius-md;
  font-size: 12.5px;
  color: $color-text-secondary;
  line-height: 1.6;
  margin-bottom: 16px;
  .ico { color: $color-primary; font-size: 16px; flex-shrink: 0; }
  strong { color: $color-text-primary; }
}

// form-section（design 5 大区共用）
.form-section {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  margin-bottom: 16px;
  overflow: hidden;
}
.fs-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid $color-border;
  background: #FAFBFF;
  h3 { font-size: 14.5px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; }
  .req { font-size: 11.5px; color: $color-text-tertiary; font-weight: 400; }
  .opt { font-size: 11.5px; color: $color-text-tertiary; font-weight: 400; }
}
.fs-body { padding: 18px 20px; }
.link-primary { font-size: 12px; color: $color-primary; cursor: pointer; }

// tpl-grid 3 列（合同模板）
.tpl-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  @media (max-width: 900px) { grid-template-columns: 1fr; }
}
.tpl-card {
  border: 1.5px solid $color-border;
  border-radius: $radius-md;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
  &:hover { border-color: $color-primary; background: $color-primary-bg; }
  &.active {
    border-color: $color-primary;
    background: $color-primary-bg;
    box-shadow: 0 0 0 2px rgba(79,107,255,0.15);
  }
  .name { font-size: 13.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  .desc { font-size: 12px; color: $color-text-secondary; line-height: 1.5; margin-bottom: 6px; min-height: 36px; }
  .meta { font-size: 11.5px; color: $color-text-tertiary; }
}

// term-list（design 8 条款）
.term-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.term-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  .drag { color: $color-text-tertiary; cursor: grab; font-size: 14px; padding-top: 2px; }
  .body { flex: 1; min-width: 0; }
  .body .t { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  .body .d { font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
  .actions { display: flex; gap: 4px; }
  .actions button {
    color: $color-text-tertiary;
    font-size: 12px;
    padding: 4px 8px;
    border-radius: $radius-sm;
    background: transparent;
    border: none;
    cursor: pointer;
    &:hover { background: $color-primary-bg; color: $color-primary; }
  }
}
.add-term {
  border: 1.5px dashed $color-border;
  border-radius: $radius-md;
  padding: 12px;
  text-align: center;
  color: $color-text-tertiary;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover { border-color: $color-primary; color: $color-primary; background: $color-primary-bg; }
}

// pay-table（design 付款计划）
.pay-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  th {
    background: $color-bg;
    text-align: left;
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 600;
    color: $color-text-tertiary;
    border-bottom: 1px solid $color-border;
  }
  td {
    padding: 12px 14px;
    border-bottom: 1px solid $color-border;
  }
  tfoot td { background: $color-bg; border-bottom: none; font-weight: 600; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; color: $color-text-primary; }
  .total { color: $color-primary; font-size: 14px; }
}

// att-area
.att-area {
  border: 1.5px dashed $color-border;
  border-radius: $radius-md;
  padding: 24px;
  text-align: center;
  background: #FAFBFF;
  cursor: pointer;
  transition: all 0.15s;
  &:hover { border-color: $color-primary; background: $color-primary-bg; }
  .ico { font-size: 32px; color: $color-primary; margin-bottom: 6px; }
  .t { font-size: 13.5px; font-weight: 500; color: $color-text-primary; }
  .m { font-size: 11.5px; color: $color-text-tertiary; margin-top: 4px; }
}

// approval-preview
.approval-preview {
  background: linear-gradient(135deg, #FAFBFF 0%, #fff 100%);
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 16px 20px;
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.ap-step {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: 9999px;
  font-size: 12.5px;
  .n { color: $color-text-secondary; }
  .p { color: $color-text-primary; font-weight: 500; }
  &.trigger { background: $color-warning-bg; border-color: rgba(245,158,11,0.3); }
}
.ap-arrow { color: $color-text-tertiary; }

// form-foot（design 底部 sticky）
.form-foot {
  position: sticky;
  bottom: 0;
  background: #fff;
  border-top: 1px solid $color-border;
  padding: 14px 0;
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
  box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.04);
}

// btn
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px;
  font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
}

// Element Plus form-item override
:deep(.el-form-item__label) { font-weight: 500; color: $color-text-secondary; font-size: 12.5px; }

/* 触点 #6：✦ AI 一键起草按钮 + Drawer */
.btn-ai-draft {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: $radius-sm; font-size: 12px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none; cursor: pointer;
  box-shadow: 0 2px 8px rgba(79,107,255,0.25);
  transition: all 0.15s;
  &:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,107,255,0.35); }
  .ai-draft-icon {
    font-size: 14px; font-weight: 700;
    background: linear-gradient(135deg, #FFD700, #FF6B6B);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
}
.ai-draft-drawer { padding: 0 8px; }
.ai-draft-intro {
  text-align: center; padding: 16px 0 24px;
  border-bottom: 1px solid $color-border; margin-bottom: 20px;
  .ai-draft-icon-big { font-size: 36px; line-height: 1; margin-bottom: 8px; }
  h3 { font-size: 16px; font-weight: 600; color: $color-text-primary; margin-bottom: 6px; }
  p { font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
}
.ai-draft-submit {
  width: 100%; height: 40px; font-size: 14px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none;
  margin-top: 8px;
  &:hover { opacity: 0.92; }
}
.ai-draft-result {
  margin-top: 20px; padding: 14px;
  background: linear-gradient(135deg, rgba(79,107,255,0.03) 0%, rgba(124,58,237,0.03) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-md;
}
.ai-draft-result-head { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 12px; }
.ai-draft-result-icon { font-size: 22px; }
.ai-draft-result-meta h4 { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
.ai-draft-result-meta p { font-size: 11px; color: $color-text-secondary; }
.ai-draft-section {
  padding: 10px 12px; margin-bottom: 8px;
  background: #fff; border-radius: $radius-sm; border: 1px solid $color-border;
  h5 { font-size: 12px; font-weight: 600; color: $color-primary; margin-bottom: 4px; }
  p { font-size: 12px; color: $color-text-secondary; line-height: 1.5; }
}
.ai-draft-actions { display: flex; gap: 8px; margin-top: 12px; }
:deep(.el-form-item.is-required .el-form-item__label::before) { content: '*'; color: $color-danger; margin-right: 4px; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner), :deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px $color-border inset !important;
  border-radius: $radius-md !important;
  &:hover { box-shadow: 0 0 0 1px $color-primary inset !important; }
  &.is-focus { box-shadow: 0 0 0 1px $color-primary inset, 0 0 0 4px rgba(79,107,255,0.08) !important; }
}
</style>
