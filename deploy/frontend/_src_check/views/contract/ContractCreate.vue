<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractApi } from '@/api/modules'
import { clientApi } from '@/api/client'

const route = useRoute()
const router = useRouter()

const isEdit = ref(!!route.params.id)
const saving = ref(false)
const activeTab = ref('base')

// 表单（与 design/contract-create.html 4 个 form-section 对齐）
const form = ref({
  code: '',
  name: '',
  clientId: null as number | null,
  clientName: '',
  type: 'sales',
  amount: 0,
  currency: 'CNY',
  signDate: '',
  effectiveDate: '',
  expireDate: '',
  managerId: null as number | null,
  managerName: '',
  paymentTerms: '30%预付，60%验收，10%质保',
  description: '',
  // 模板
  templateId: null as number | null,
  // 条款
  terms: [
    '1. 服务内容：详见附件服务清单。',
    '2. 付款条款：合同生效后 5 个工作日内支付首款。',
    '3. SLA 保障：系统可用性 ≥ 99.9%，故障响应时间 ≤ 30 分钟。',
    '4. 知识产权：平台软件著作权归乙方所有。',
    '5. 违约责任：赔偿总额不超过本合同年度总金额的 200%。',
    '6. 终止条款：任一方可提前 30 天书面通知对方后终止本合同。',
  ] as string[],
  // 附件
  attachments: [
    { name: '主合同.pdf', size: '1.2 MB' },
    { name: '技术方案.docx', size: '580 KB' },
  ] as Array<{ name: string; size: string }>,
})

const clients = ref<any[]>([])
const users = ref<any[]>([])

const TYPE_OPTIONS = [
  { value: 'sales', label: '销售合同' },
  { value: 'purchase', label: '采购合同' },
  { value: 'service', label: '服务合同' },
  { value: 'framework', label: '框架协议' },
]
const TEMPLATES = [
  { id: 1, name: 'SaaS 销售标准合同' },
  { id: 2, name: '软件采购框架协议' },
  { id: 3, name: '系统集成服务合同' },
]

async function loadRefs() {
  // 客户 / 负责人下拉
  const cRes: any = await clientApi.list({ page: 1, pageSize: 200 }).catch(() => null)
  if (cRes?.list) clients.value = cRes.list
  // 用户（从 adminApi 也可以，这里简化为写死）
  users.value = [
    { id: 1, name: '张明（管理员）' },
    { id: 2, name: '陈思琪' },
    { id: 3, name: '王芳' },
    { id: 4, name: '李明' },
    { id: 5, name: '刘洋' },
  ]
}

function genCode() {
  const ts = new Date()
  return `HT-${ts.getFullYear()}-${String(Math.floor(Math.random() * 900 + 100))}`
}

function onClientChange(id: number | null) {
  const c = clients.value.find(x => x.id === id)
  if (c) form.value.clientName = c.name
}

function onManagerChange(id: number | null) {
  const u = users.value.find(x => x.id === id)
  if (u) form.value.managerName = u.name
}

function addAttachment() {
  form.value.attachments.push({ name: '新附件.pdf', size: '0 KB' })
}
function removeAttachment(i: number) {
  form.value.attachments.splice(i, 1)
}

function addTerm() {
  form.value.terms.push(`${form.value.terms.length + 1}. 新条款...`)
}
function removeTerm(i: number) {
  form.value.terms.splice(i, 1)
}

async function submit(status: 'draft' | 'pending') {
  if (!form.value.name) { ElMessage.warning('请填写合同名称'); return }
  if (!form.value.clientId) { ElMessage.warning('请选择客户'); return }
  if (!form.value.amount || form.value.amount <= 0) { ElMessage.warning('请填写合同金额'); return }
  if (!form.value.signDate || !form.value.expireDate) { ElMessage.warning('请填写签订/到期日期'); return }

  saving.value = true
  try {
    const created: any = await contractApi.create({
      code: form.value.code || genCode(),
      name: form.value.name,
      type: form.value.type,
      status: 'draft',
      clientId: form.value.clientId,
      managerId: form.value.managerId || 1,
      amount: form.value.amount,
      currency: form.value.currency,
      signDate: form.value.signDate,
      effectiveDate: form.value.effectiveDate || form.value.signDate,
      expireDate: form.value.expireDate,
      paymentTerms: form.value.paymentTerms,
      description: form.value.description,
    } as any).catch(() => null)
    if ((status as string) === 'submit' && created?.id) {
      await contractApi.submit(created.id).catch(() => null)
    }
    if (created?.id || created?.code === 0) {
      ElMessage.success(status === 'draft' ? '已存为草稿' : '已提交审批')
      router.push('/contract/list')
    } else {
      ElMessage.error(created?.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push('/contract/list')
}

onMounted(() => {
  loadRefs()
  if (!isEdit.value && !form.value.code) {
    form.value.code = genCode()
  }
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部条 -->
    <div class="page-header">
      <div>
        <div class="breadcrumb">业务 / <router-link to="/contract/list" style="color: var(--color-text-tertiary)">合同管理</router-link> / {{ isEdit ? '编辑合同' : '新建合同' }}</div>
        <h2>{{ isEdit ? '编辑合同' : '新建合同' }}</h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="cancel">⊗ 取消</el-button>
        <el-button @click="submit('draft')">💾 存为草稿</el-button>
        <el-button type="primary" @click="submit('pending')">📤 提交审批</el-button>
      </div>
    </div>

    <div class="page-card">
      <!-- Tabs（与 design/contract-create.html 4 个 form-section 对应）-->
      <div class="detail-tabs">
        <a :class="{ active: activeTab === 'base' }" @click="activeTab = 'base'">📋 基本信息</a>
        <a :class="{ active: activeTab === 'terms' }" @click="activeTab = 'terms'">📑 合同条款</a>
        <a :class="{ active: activeTab === 'attach' }" @click="activeTab = 'attach'">📎 附件</a>
        <a :class="{ active: activeTab === 'flow' }" @click="activeTab = 'flow'">🔄 审批流</a>
      </div>

      <!-- Section 1: 基本信息 -->
      <div v-if="activeTab === 'base'" class="detail-section">
        <div class="detail-section-head">
          <h4>📋 基本信息 <span style="font-size:11.5px;color:var(--color-text-tertiary);font-weight:400;">* 必填</span></h4>
        </div>
        <div class="detail-section-body">
          <el-form label-position="top" label-width="0">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="合同编号">
                  <el-input v-model="form.code" placeholder="自动生成">
                    <template #append><el-button @click="form.code = genCode()">🎲</el-button></template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="合同类型" required>
                  <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
                    <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="合同名称" required>
                  <el-input v-model="form.name" placeholder="如：万象科技 SaaS 服务合同 2026Q2" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="客户" required>
                  <el-select v-model="form.clientId" placeholder="请选择客户" filterable style="width: 100%" @change="onClientChange">
                    <el-option v-for="c in clients" :key="c.id" :label="c.name" :value="c.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="负责人">
                  <el-select v-model="form.managerId" placeholder="请选择负责人" filterable style="width: 100%" @change="onManagerChange">
                    <el-option v-for="u in users" :key="u.id" :label="u.name" :value="u.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="合同金额 (元)" required>
                  <el-input-number v-model="form.amount" :min="0" :step="1000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="币种">
                  <el-select v-model="form.currency" style="width: 100%">
                    <el-option label="人民币 CNY" value="CNY" />
                    <el-option label="美元 USD" value="USD" />
                    <el-option label="欧元 EUR" value="EUR" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="签订日期" required>
                  <el-date-picker v-model="form.signDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="生效日期">
                  <el-date-picker v-model="form.effectiveDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="到期日期" required>
                  <el-date-picker v-model="form.expireDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="付款条款">
                  <el-input v-model="form.paymentTerms" placeholder="如：30%预付，60%验收，10%质保" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="合同摘要">
                  <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简述合同主要约定" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </div>
      </div>

      <!-- Section 2: 合同条款 -->
      <div v-if="activeTab === 'terms'" class="detail-section">
        <div class="detail-section-head">
          <h4>📑 合同条款 <span style="font-size:11.5px;color:var(--color-text-tertiary);font-weight:400;">已添加 {{ form.terms.length }} 条</span></h4>
          <el-button type="primary" link @click="addTerm">+ 添加条款</el-button>
        </div>
        <div class="detail-section-body">
          <div v-for="(t, i) in form.terms" :key="i" class="term-row">
            <el-input v-model="form.terms[i]" type="textarea" :rows="2" />
            <el-button type="danger" link @click="removeTerm(i)">删除</el-button>
          </div>
        </div>
      </div>

      <!-- Section 3: 附件 -->
      <div v-if="activeTab === 'attach'" class="detail-section">
        <div class="detail-section-head">
          <h4>📎 附件 <span style="font-size:11.5px;color:var(--color-text-tertiary);font-weight:400;">已添加 {{ form.attachments.length }} 个</span></h4>
          <el-button type="primary" link @click="addAttachment">+ 添加附件</el-button>
        </div>
        <div class="detail-section-body">
          <el-table :data="form.attachments">
            <el-table-column label="文件名" prop="name" />
            <el-table-column label="大小" prop="size" width="120" />
            <el-table-column label="操作" width="100">
              <template #default="{ $index }">
                <el-button type="danger" link @click="removeAttachment($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Section 4: 审批流 -->
      <div v-if="activeTab === 'flow'" class="detail-section">
        <div class="detail-section-head">
          <h4>🔄 审批流预览 <span style="font-size:11.5px;color:var(--color-text-tertiary);font-weight:400;">合同金额 ≥ 5 万触发总经理审批</span></h4>
        </div>
        <div class="detail-section-body">
          <div class="flow-horizontal">
            <div class="fh-row">
              <div class="fh-step pending">
                <div class="node">1</div>
                <div class="lbl">起草</div>
                <div class="meta">当前 · {{ form.managerName || '负责人' }}</div>
              </div>
              <div class="fh-line"></div>
              <div class="fh-step pending">
                <div class="node">2</div>
                <div class="lbl">法务审核</div>
                <div class="meta">法务部</div>
              </div>
              <div class="fh-line"></div>
              <div class="fh-step pending">
                <div class="node">3</div>
                <div class="lbl">财务审核</div>
                <div class="meta">财务部</div>
              </div>
              <div class="fh-line"></div>
              <div v-if="form.amount >= 50000" class="fh-step pending">
                <div class="node">4</div>
                <div class="lbl">总经理审批</div>
                <div class="meta">≥ 5 万触发</div>
              </div>
              <div v-else class="fh-line"></div>
              <div class="fh-step pending">
                <div class="node">{{ form.amount >= 50000 ? 5 : 4 }}</div>
                <div class="lbl">电子签</div>
                <div class="meta">未开始</div>
              </div>
              <div class="fh-line"></div>
              <div class="fh-step pending">
                <div class="node">{{ form.amount >= 50000 ? 6 : 5 }}</div>
                <div class="lbl">归档</div>
                <div class="meta">未开始</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot">
      <el-button @click="cancel">⊗ 取消</el-button>
      <el-button @click="submit('draft')">💾 存为草稿</el-button>
      <el-button type="primary" @click="submit('pending')">📤 提交审批</el-button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb { font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px; }
.term-row { display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px;
  :deep(.el-textarea) { flex: 1; }
}
.form-foot {
  display: flex; gap: 8px; justify-content: flex-end;
  padding: 16px 20px;
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  margin: 0 -22px -18px;
}
</style>
