<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { expenseApi } from '@/api/modules'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const step = ref(1)
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
  paymentMethod: '对公转账',
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

// tip-box：单笔 ≥ 5000 触发"财务总监审批"
const needCfoApproval = computed(() => totalAmount.value >= 5000)

// 类别选项（与设计稿 type-card 6 个一致 + 简化为 4 个核心 + 其他）
const categories = [
  { value: '差旅', icon: '✈' },
  { value: '招待', icon: '🍽' },
  { value: '办公', icon: '📎' },
  { value: '推广', icon: '📢' },
  { value: '培训', icon: '📚' },
  { value: '其他', icon: '⋯' },
]

// 子项类别（按选中主类别切换，简化版：固定常用）
const subCategories = ['机票', '酒店', '打车/交通', '餐补/其他', '办公用品', '业务招待', '场地/物料', '其他']

// 项目下拉（演示用）
const projectOptions = [
  { value: 'PRJ-2026-022', label: 'PRJ-2026-022 · 万象科技 SaaS 部署' },
  { value: 'PRJ-2026-018', label: 'PRJ-2026-018 · 数智化二期' },
  { value: 'PRJ-2026-015', label: 'PRJ-2026-015 · 朗驰智能改造' },
  { value: '', label: '暂不关联' },
]

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
    const r: any = await expenseApi.create({
      ...form,
      applicant: applicantName.value,
      status: 'draft',
      amount: totalAmount.value,
    } as any).catch(() => null)
    if (r?.id || r?.code === 0) {
      ElMessage.success('已暂存为草稿')
      router.push('/expense/list')
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
  const r: any = await expenseApi.create({
    ...form,
    applicant: applicantName.value,
    amount: totalAmount.value,
    status: 'draft',
  } as any).catch(() => null)
  if (r?.id) {
    await expenseApi.submit(r.id).catch(() => null)
  }
  if (r?.id || r?.code === 0) {
    ElMessage.success('已提交审批')
    router.push('/expense/list')
  } else {
    ElMessage.error(r?.message || '提交失败')
  }
  router.push('/expense/list')
}

function cancel() { router.push('/expense/list') }

onMounted(() => {
  // 自动填一个常用事由（演示用）
  if (!form.purpose) form.purpose = ''
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/expense/list" style="color: var(--color-text-tertiary)">销售费用</router-link> / 新建
        </div>
        <h2>新建销售费用</h2>
        <p class="page-desc">单号自动生成 · 提交后将进入审批流</p>
      </div>
      <div style="display: flex; gap: 8px">
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
          <div class="ap-step done"><span class="n">1</span><span class="p">提交人 · {{ applicantName }}</span></div>
          <span class="ap-arrow">→</span>
          <div class="ap-step"><span class="n">2</span><span class="p">部门经理</span></div>
          <span class="ap-arrow">→</span>
          <div class="ap-step"><span class="n">3</span><span class="p">财务审核</span></div>
          <span class="ap-arrow">→</span>
          <div :class="['ap-step', needCfoApproval ? 'trigger' : '']">
            <span class="n">{{ needCfoApproval ? '4' : '4*' }}</span>
            <span class="p">出纳支付{{ needCfoApproval ? '（含财务总监）' : '' }}</span>
          </div>
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
        <el-button @click="saveDraft">存为草稿</el-button>
        <el-button v-if="step < 3" type="primary" @click="nextStep">下一步 →</el-button>
        <el-button v-else type="primary" @click="submitApproval">✓ 提交审批</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }
.page-container { padding-bottom: 80px; }
</style>
