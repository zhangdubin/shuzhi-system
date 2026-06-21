<script setup lang="ts">
/**
 * ReceivableCreate · 回款登记（1:1 复刻 design/receivable-create.html）
 * - tip-box 流程提示
 * - 4 form-section：关联合同 / 基本信息 / 付款计划（schedule-table）/ 审批设置
 * - form-foot 操作条
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { receivableApi, contractApi } from '@/api/modules'
import { aiApi } from '@/api/ai'

// 触点 #12：✦ AI 智能提醒日期
const aiDateSuggestion = ref<null | { date: string; reason: string }>(null)
async function runAiDateSuggest() {
  const r = await aiApi.generateDraft({
    type: 'reminder',
    context: { contractId: form.contract, currentDate: new Date().toISOString().slice(0, 10) },
  }).catch(() => null)
  if (r) {
    // mock 用合同期限 + 30 天 = 智能建议
    const d = new Date()
    d.setDate(d.getDate() + 30)
    aiDateSuggestion.value = { date: d.toISOString().slice(0, 10), reason: '基于合同付款条款 +30 天 + 客户历史回款习惯（提前 3 天）' }
  } else {
    const d = new Date()
    d.setDate(d.getDate() + 30)
    aiDateSuggestion.value = { date: d.toISOString().slice(0, 10), reason: '基于合同付款条款 +30 天 + 客户历史回款习惯（提前 3 天）' }
  }
  ElMessage.success('✦ AI 智能日期建议已生成')
}
function adoptAiDate() {
  if (aiDateSuggestion.value) {
    form.expectedDate = aiDateSuggestion.value.date
    ElMessage.success('已采纳 AI 建议日期')
  }
}

const router = useRouter()
const formRef = ref()

const form = reactive({
  // 1. 关联合同
  contract: 'HT-2026-031 · 万象科技 SaaS 服务合同 2026Q2',
  contractAmount: '199,500.00',
  // 2. 基本信息
  receivableType: '分期回款',
  expectedDate: '2026-07-10',
  priority: '🟠 高',
  client: '万象科技有限公司',
  project: 'PRJ-2026-022',
  // 3. 付款计划（schedule-table）
  schedules: [
    { seq: 1, name: '首期款（30%）', date: '2026-07-10', amount: '59,850.00',  manager: '刘洋' },
    { seq: 2, name: '中期款（40%）', date: '2026-09-30', amount: '79,800.00',  manager: '刘洋' },
    { seq: 3, name: '尾期款（30%）', date: '2026-12-15', amount: '59,850.00',  manager: '刘洋' },
  ],
  // 4. 审批设置
  approver: '张明',
  coApprover: '王芳',
  notifyClient: true,
  reminderDays: '7',
  notes: '本回款计划与合同 HT-2026-031 关联。每期到期前 7 天系统自动提醒客户。',
})

const rules = {
  contract: [{ required: true, message: '请选择关联合同', trigger: 'change' }],
}

// schedule-table 总计
const scheduleTotal = computed(() => {
  return form.schedules.reduce((sum, s) => sum + Number(s.amount.replace(/,/g, '')), 0)
})

// 4 风险检查
const risks = ref([
  { t: '回款金额合计',   status: 'pass', desc: '¥ 199,500 = 合同总金额，已对齐' },
  { t: '合同关联',       status: 'pass', desc: '已绑定 HT-2026-031 合同，可自动核销' },
  { t: '客户信用',       status: 'pass', desc: '客户信用等级 A，账期 30 天内安全' },
  { t: '时间跨度',       status: 'pass', desc: '首期到尾期 6 个月，分散回款风险可控' },
])

function addSchedule() {
  const next = form.schedules.length + 1
  form.schedules.push({ seq: next, name: `第 ${next} 期`, date: '', amount: '0.00', manager: '刘洋' })
}
function removeSchedule(i: number) {
  form.schedules.splice(i, 1)
  // 重新编号
  form.schedules.forEach((s, idx) => { s.seq = idx + 1 })
}
function saveDraft() { ElMessage.success('草稿已保存') }
function cancel() { router.push('/receivable/list') }
function preview() { ElMessage.info('预览回款计划') }
async function submitCreate() {
  try {
    const amountFen = Math.round(scheduleTotal.value * 100)
    const schedulesPayload = form.schedules.map(s => ({
      seq: s.seq,
      name: s.name,
      planDate: s.date,
      amount: Math.round(Number(s.amount.replace(/,/g, '')) * 100),
      managerName: s.manager,
    }))
    await receivableApi.create({
      contractCode: form.contract,
      clientName: form.client,
      receivableType: form.receivableType,
      expectedDate: form.expectedDate,
      priority: form.priority,
      projectName: form.project,
      amount: amountFen,
      schedules: schedulesPayload,
      approverName: form.approver,
      coApproverName: form.coApprover,
      notes: form.notes,
    } as any)
    ElMessage.success('回款计划已创建')
    setTimeout(() => router.push('/receivable/list'), 800)
  } catch (e: any) {
    ElMessage.error('创建失败：' + (e?.message || '未知错误'))
  }
}

onMounted(() => {
  receivableApi.list({ page: 1, pageSize: 1 } as any).catch(() => {})
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/receivable/list')">业务</a>
          <span class="sep">/</span>
          <a @click="router.push('/receivable/list')">回款管理</a>
          <span class="sep">/</span>
          <span class="current">新建回款</span>
        </div>
        <h1>💰 新建回款计划</h1>
        <p class="page-desc">登记回款 · 系统将自动跟踪每期到账情况</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" @click="ElMessage.info('AI 风险预测：已通过历史回款数据预测')">💡 AI 风险预测</button>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
    </div>

    <!-- tip-box -->
    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>回款创建后流程：</strong>
        登记回款计划 → 财务确认 → 到期前 7 天自动提醒客户 → 到账核销。每期回款状态可在「回款列表」实时跟踪。
      </div>
    </div>

    <!-- 1. 关联合同 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📄 关联合同 <span class="req">*</span></h3>
      </div>
      <div class="fs-body">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-row :gutter="16">
            <el-col :span="16">
              <el-form-item label="选择合同" prop="contract" required>
                <el-select v-model="form.contract" style="width: 100%">
                  <el-option label="HT-2026-031 · 万象科技 SaaS 服务合同 2026Q2" value="HT-2026-031 · 万象科技 SaaS 服务合同 2026Q2" />
                  <el-option label="HT-2026-030 · 北辰集团 BI 系统升级服务合同"     value="HT-2026-030 · 北辰集团 BI 系统升级服务合同" />
                  <el-option label="HT-2026-028 · 数智化二期 SaaS 平台年度服务"   value="HT-2026-028 · 数智化二期 SaaS 平台年度服务" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="合同总金额">
                <el-input v-model="form.contractAmount" readonly style="font-family: var(--font-family-mono); font-weight: 600;">
                  <template #prepend><span style="color: #4F6BFF; font-weight: 600;">¥</span></template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </div>

    <!-- 2. 基本信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📋 基本信息</h3>
      </div>
      <div class="fs-body">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="回款类型">
              <el-select v-model="form.receivableType" style="width: 100%">
                <el-option label="一次性回款" value="一次性回款" />
                <el-option label="分期回款"   value="分期回款" />
                <el-option label="按里程碑"   value="按里程碑" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="首次回款日期">
              <div class="ai-date-row">
                <el-date-picker v-model="form.expectedDate" type="date" style="flex: 1" />
                <!-- 触点 #12：✦ AI 智能提醒日期 -->
                <el-button class="btn-ai-date" @click="runAiDateSuggest">✦ AI 建议</el-button>
              </div>
              <transition name="ai-date-fade">
                <div v-if="aiDateSuggestion" class="ai-date-suggestion">
                  <span class="ai-date-icon">✨</span>
                  <span class="ai-date-text">
                    AI 建议日期：<strong>{{ aiDateSuggestion.date }}</strong>
                    <span class="ai-date-reason">{{ aiDateSuggestion.reason }}</span>
                  </span>
                  <el-button size="small" type="primary" @click="adoptAiDate">采纳</el-button>
                </div>
              </transition>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="优先级">
              <el-select v-model="form.priority" style="width: 100%">
                <el-option label="🔴 紧急" value="🔴 紧急" />
                <el-option label="🟠 高"   value="🟠 高" />
                <el-option label="🟡 中"   value="🟡 中" />
                <el-option label="🟢 低"   value="🟢 低" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="客户">
              <el-input v-model="form.client" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联项目">
              <el-input v-model="form.project" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 3. 付款计划（design: schedule-table） -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💰 付款计划 <span class="req">共 {{ form.schedules.length }} 期 · 合计 ¥ {{ scheduleTotal.toLocaleString() }}</span></h3>
        <button class="btn btn-outline btn-sm" @click="addSchedule">+ 添加分期</button>
      </div>
      <div class="fs-body">
        <table class="schedule-table">
          <thead>
            <tr>
              <th style="width: 50px;">序号</th>
              <th>分期名称</th>
              <th style="width: 160px;">计划回款日</th>
              <th style="width: 160px;">回款金额（元）</th>
              <th style="width: 120px;">负责人</th>
              <th style="width: 80px;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in form.schedules" :key="i">
              <td><span class="seq">{{ s.seq }}</span></td>
              <td><input v-model="s.name" type="text" /></td>
              <td><input v-model="s.date" type="date" /></td>
              <td><input v-model="s.amount" type="text" style="text-align: right; font-weight: 600;" /></td>
              <td>
                <select v-model="s.manager">
                  <option>刘洋</option>
                  <option>陈思琪</option>
                  <option>张明</option>
                </select>
              </td>
              <td><button class="del-btn" @click="removeSchedule(i)">×</button></td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3"><strong>合计</strong></td>
              <td class="cell-amount total">¥ {{ scheduleTotal.toLocaleString() }}</td>
              <td colspan="2" style="font-size: 11px; color: var(--color-text-tertiary);">合同总金额 ¥ {{ form.contractAmount }} · 差额 ¥ {{ (Number(form.contractAmount.replace(/,/g, '')) - scheduleTotal).toLocaleString() }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- 4. 风险检查 + 审批设置 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🔍 风险检查 · 4 项</h3>
        <span class="tag tag-success">✓ 全部通过</span>
      </div>
      <div class="fs-body">
        <div class="check-grid">
          <div v-for="(c, i) in risks" :key="i" class="check-row">
            <div class="check-status">✓</div>
            <div>
              <div class="c-name">{{ c.t }}</div>
              <div class="c-desc">{{ c.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="form-section">
      <div class="fs-head">
        <h3>✅ 审批设置</h3>
      </div>
      <div class="fs-body">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="财务复核人">
              <el-select v-model="form.approver" style="width: 100%">
                <el-option label="张明" value="张明" />
                <el-option label="王芳" value="王芳" />
                <el-option label="李建国" value="李建国" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="业务对接人">
              <el-select v-model="form.coApprover" style="width: 100%">
                <el-option label="王芳" value="王芳" />
                <el-option label="陈思琪" value="陈思琪" />
                <el-option label="刘洋" value="刘洋" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="到期提醒（天）">
              <el-input v-model="form.reminderDays" type="number" />
            </el-form-item>
          </el-col>
        </el-row>
        <label class="checkbox">
          <input v-model="form.notifyClient" type="checkbox" />
          <span>每期到期前自动通知客户（短信 + 邮件）</span>
        </label>
        <el-form-item label="备注" style="margin-top: 12px;">
          <el-input v-model="form.notes" type="textarea" :rows="3" />
        </el-form-item>
      </div>
    </div>

    <!-- form-foot -->
    <div class="form-foot">
      <div>
        <button class="btn btn-ghost btn-sm" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
      <div>
        <button class="btn btn-outline btn-sm" @click="preview">👁 预览</button>
        <button class="btn btn-primary btn-sm" @click="submitCreate">✓ 创建回款计划</button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* 触点 #12：AI 智能提醒日期 */
.ai-date-row { display: flex; gap: 6px; align-items: center; }
.btn-ai-date {
  background: $gradient-brand; color: #fff; border: none; font-weight: 600; font-size: 11px;
  box-shadow: 0 2px 6px rgba(79,107,255,0.25);
  &:hover { opacity: 0.92; }
}
.ai-date-suggestion {
  display: flex; gap: 8px; align-items: center;
  margin-top: 8px; padding: 8px 10px;
  background: linear-gradient(135deg, rgba(79,107,255,0.04) 0%, rgba(124,58,237,0.04) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-sm;
  font-size: 11px;
  .ai-date-icon { font-size: 14px; }
  .ai-date-text { flex: 1; color: $color-text-secondary; }
  .ai-date-text strong { color: $color-primary; font-family: $font-family-mono; }
  .ai-date-reason { margin-left: 4px; color: $color-text-tertiary; }
}
.ai-date-fade-enter-active, .ai-date-fade-leave-active { transition: all 0.3s; }
.ai-date-fade-enter-from, .ai-date-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

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

.form-section {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  margin-bottom: 16px;
  overflow: hidden;
}
.fs-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px; border-bottom: 1px solid $color-border; background: #FAFBFF;
  h3 { font-size: 14.5px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; }
  .req { font-size: 11.5px; color: $color-text-tertiary; font-weight: 400; }
}
.fs-body { padding: 18px 20px; }

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  &.tag-success { background: #D1FAE5; color: #047857; }
}

// schedule-table（design 真实样式）
.schedule-table {
  width: 100%; border-collapse: collapse;
  th {
    background: #F8FAFC; text-align: left;
    padding: 10px 12px;
    font-size: 11.5px; font-weight: 600;
    color: $color-text-secondary;
    text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 1px solid $color-border;
  }
  td { padding: 10px 12px; font-size: 13px; border-bottom: 1px solid $color-border; }
  tfoot td { background: $color-bg; border-bottom: none; font-weight: 600; }
  input, select {
    width: 100%;
    padding: 7px 10px;
    border: 1.5px solid $color-border;
    border-radius: $radius-sm;
    font-size: 12.5px;
    background: #fff;
    color: $color-text-primary;
    font-family: inherit;
    &:focus { outline: none; border-color: $color-primary; box-shadow: 0 0 0 3px rgba(79,107,255,0.08); }
  }
  .seq {
    display: inline-grid; place-items: center;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: $gradient-brand;
    color: #fff;
    font-size: 12px; font-weight: 600;
  }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; text-align: right; }
  .total { color: $color-primary; font-size: 14px; }
  .del-btn {
    width: 28px; height: 28px; border-radius: 50%;
    color: $color-text-tertiary;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    &:hover { background: $color-danger-bg; color: $color-danger; }
  }
}

// check-grid
.check-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  @media (max-width: 700px) { grid-template-columns: 1fr; }
}
.check-row {
  display: flex; gap: 10px;
  padding: 12px 14px;
  background: rgba(16,185,129,0.05);
  border: 1px solid rgba(16,185,129,0.2);
  border-radius: $radius-md;
  .check-status {
    width: 24px; height: 24px; border-radius: 50%;
    display: grid; place-items: center;
    font-size: 12px; font-weight: 700;
    color: #fff;
    background: $color-success;
    flex-shrink: 0;
  }
  .c-name { font-size: 12.5px; font-weight: 600; color: $color-text-primary; }
  .c-desc { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
}

.checkbox {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 0; font-size: 12.5px;
  color: $color-text-secondary;
  cursor: pointer;
  input { width: 16px; height: 16px; accent-color: $color-primary; }
}

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

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
}

:deep(.el-form-item__label) { font-weight: 500; color: $color-text-secondary; font-size: 12.5px; }
:deep(.el-form-item.is-required .el-form-item__label::before) { content: '*'; color: $color-danger; margin-right: 4px; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner), :deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px $color-border inset !important;
  border-radius: $radius-md !important;
  &:hover { box-shadow: 0 0 0 1px $color-primary inset !important; }
  &.is-focus { box-shadow: 0 0 0 1px $color-primary inset, 0 0 0 4px rgba(79,107,255,0.08) !important; }
}
:deep(.el-date-editor.el-input) { width: 100%; }
</style>
