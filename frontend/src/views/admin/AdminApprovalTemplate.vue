<script setup lang="ts">
/**
 * AdminApprovalTemplate · 审批流模板配置（仅超管）
 * - 列表：所有模板（按 business_type 分组）
 * - 弹窗编辑：name / rules（步骤数组，支持上下移/删/增）/ condition / isDefault / isActive
 * - 一键种子默认模板
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

// 步骤规则的可选项（与后端 _resolve_approver 保持一致）
const RULE_OPTIONS = [
  { value: 'submitter', label: '提交', desc: '申请人本人（自动）' },
  { value: 'direct_leader', label: '直属上级', desc: '申请人所在部门负责人' },
  { value: 'finance', label: '财务审核', desc: '任意财务总监角色用户' },
  { value: 'gm', label: '总经理审批', desc: '任意总经理角色用户' },
  { value: 'gm_if_over_5000', label: '总经理审批（金额≥5000）', desc: '金额触发型' },
]

const templates = ref<any[]>([])
const loading = ref(false)

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editing = reactive({
  id: 0,
  name: '',
  businessType: 'expense',
  rules: [] as string[],
  conditionAmountMin: null as number | null,
  isDefault: false,
  isActive: true,
  remark: '',
})

const kpis = computed(() => {
  const all = templates.value
  return [
    { label: '模板总数', num: all.length, color: 'primary', icon: '📋' },
    { label: '启用中', num: all.filter(t => t.isActive).length, color: 'success', icon: '✓' },
    { label: '默认模板', num: all.filter(t => t.isDefault).length, color: 'warning', icon: '⭐' },
    { label: '业务类型', num: new Set(all.map(t => t.businessType)).size, color: 'info', icon: '🏷' },
  ]
})

async function loadList() {
  loading.value = true
  try {
    const res: any = await adminApi.approvalTemplateList().catch(() => null)
    const rows: any[] = (res?.list || res?.data?.list || res?.data || res) || []
    templates.value = Array.isArray(rows) ? rows : []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(editing, {
    id: 0, name: '', businessType: 'expense', rules: ['submitter', 'direct_leader', 'finance'],
    conditionAmountMin: null, isDefault: false, isActive: true, remark: '',
  })
  dialogVisible.value = true
}

function openEdit(t: any) {
  dialogMode.value = 'edit'
  Object.assign(editing, {
    id: t.id, name: t.name, businessType: t.businessType,
    rules: Array.isArray(t.rules) ? [...t.rules] : [],
    conditionAmountMin: (t.condition && t.condition.amount_min) || null,
    isDefault: !!t.isDefault, isActive: !!t.isActive, remark: t.remark || '',
  })
  dialogVisible.value = true
}

function ruleLabel(r: string) {
  return RULE_OPTIONS.find(o => o.value === r)?.label || r
}
function ruleDesc(r: string) {
  return RULE_OPTIONS.find(o => o.value === r)?.desc || ''
}

function addRule() {
  // 默认追加一个"财务审核"步骤
  editing.rules.push('finance')
}
function removeRule(i: number) {
  if (editing.rules.length <= 1) {
    ElMessage.warning('至少保留 1 个步骤')
    return
  }
  editing.rules.splice(i, 1)
}
function moveRule(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= editing.rules.length) return
  const tmp = editing.rules[i]
  editing.rules[i] = editing.rules[j]
  editing.rules[j] = tmp
}

async function saveTemplate() {
  if (!editing.name.trim()) { ElMessage.warning('请填写模板名称'); return }
  if (editing.rules.length === 0) { ElMessage.warning('至少添加 1 个步骤'); return }
  const payload: any = {
    name: editing.name.trim(),
    businessType: editing.businessType,
    rules: editing.rules,
    isDefault: editing.isDefault,
    isActive: editing.isActive,
    remark: editing.remark || null,
  }
  if (editing.conditionAmountMin != null && editing.conditionAmountMin !== ('' as any)) {
    payload.condition = { amount_min: Number(editing.conditionAmountMin) }
  } else {
    payload.condition = null
  }
  try {
    if (dialogMode.value === 'create') {
      await adminApi.approvalTemplateCreate(payload)
      ElMessage.success('已创建')
    } else {
      await adminApi.approvalTemplateUpdate(editing.id, payload)
      ElMessage.success('已保存')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  }
}

async function deleteTemplate(t: any) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${t.name}」？此操作不可恢复。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await adminApi.approvalTemplateDelete(t.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function seedDefaults() {
  try {
    const r: any = await adminApi.approvalTemplateSeedDefaults().catch(() => null)
    if (r?.data?.inserted?.length) {
      ElMessage.success(`已初始化：${r.data.inserted.join('、')}`)
    } else {
      ElMessage.info('默认模板已存在，无需重复初始化')
    }
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '初始化失败')
  }
}

function formatRule(r: string, idx: number) {
  return { name: ruleLabel(r), desc: ruleDesc(r) }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <!-- 顶部 header -->
    <div class="page-header">
      <div>
        <div class="breadcrumb">系统 / 管理后台 / 审批流模板</div>
        <h1>📐 审批流模板配置</h1>
        <p class="page-desc">为各业务类型（如销售费用）配置多套审批流，提交时按业务类型 + 金额自动匹配</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="seedDefaults">🌱 初始化默认模板</el-button>
        <el-button type="primary" @click="openCreate">＋ 新建模板</el-button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', `kpi-${k.color}`]">
        <div class="kpi-icon">{{ k.icon }}</div>
        <div class="kpi-body">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-num">{{ k.num }}</div>
        </div>
      </div>
    </div>

    <!-- 模板列表 -->
    <div class="card">
      <div class="card-head">
        <h3>📋 模板列表</h3>
        <span class="hint">已按 businessType + sortOrder 排序</span>
      </div>

      <div v-if="loading" class="empty-tip">加载中…</div>
      <div v-else-if="templates.length === 0" class="empty-tip">
        还没有审批流模板。点击右上「初始化默认模板」或「新建模板」开始。
      </div>

      <div v-else class="tpl-list">
        <div v-for="t in templates" :key="t.id" :class="['tpl-card', { 'tpl-inactive': !t.isActive, 'tpl-default': t.isDefault }]">
          <div class="tpl-head">
            <div class="tpl-title">
              <span class="tpl-name">{{ t.name }}</span>
              <span v-if="t.isDefault" class="tpl-badge tpl-badge-default">默认</span>
              <span v-if="!t.isActive" class="tpl-badge tpl-badge-off">已停用</span>
              <span class="tpl-biz">{{ t.businessType }}</span>
            </div>
            <div class="tpl-actions">
              <button class="link-btn" @click="openEdit(t)">✎ 编辑</button>
              <button class="link-btn link-danger" @click="deleteTemplate(t)">🗑 删除</button>
            </div>
          </div>

          <div class="tpl-flow">
            <div class="flow-line">
              <div v-for="(r, i) in t.rules" :key="i" class="flow-step">
                <div class="flow-num">{{ i + 1 }}</div>
                <div class="flow-name">{{ ruleLabel(r) }}</div>
                <div v-if="i < t.rules.length - 1" class="flow-arrow">→</div>
              </div>
            </div>
            <div v-if="t.condition && t.condition.amount_min" class="tpl-cond">
              ⚡ 触发条件：金额 ≥ ¥{{ (t.condition.amount_min / 100).toLocaleString() }}
            </div>
            <div v-if="t.remark" class="tpl-remark">{{ t.remark }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建审批流模板' : '编辑审批流模板'"
      width="720px"
      :close-on-click-modal="false"
    >
      <div class="form">
        <div class="form-row">
          <div class="form-field">
            <label>模板名称 <span class="required">*</span></label>
            <input v-model="editing.name" class="text-input" placeholder="如：差旅-标准、招待-大额" maxlength="32" />
          </div>
          <div class="form-field">
            <label>业务类型</label>
            <input v-model="editing.businessType" class="text-input" placeholder="expense / contract / ..." maxlength="32" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-field">
            <label>触发条件（可选）</label>
            <div class="amount-input">
              <span class="prefix">金额 ≥</span>
              <input v-model.number="editing.conditionAmountMin" type="number" min="0" class="text-input" placeholder="5000" />
              <span class="suffix">元</span>
              <span class="hint-tip">不填表示无金额限制</span>
            </div>
          </div>
          <div class="form-field">
            <label>选项</label>
            <div class="checkbox-row">
              <label class="cb"><input type="checkbox" v-model="editing.isDefault" /> 设为默认模板</label>
              <label class="cb"><input type="checkbox" v-model="editing.isActive" /> 启用</label>
            </div>
          </div>
        </div>

        <div class="form-field full">
          <label>审批步骤 <span class="required">*</span>（按顺序执行）</label>
          <div class="steps">
            <div v-for="(r, i) in editing.rules" :key="i" class="step-row">
              <div class="step-num">{{ i + 1 }}</div>
              <select v-model="editing.rules[i]" class="text-input">
                <option v-for="opt in RULE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }} — {{ opt.desc }}</option>
              </select>
              <div class="step-btns">
                <button class="step-btn" :disabled="i === 0" @click="moveRule(i, -1)" title="上移">↑</button>
                <button class="step-btn" :disabled="i === editing.rules.length - 1" @click="moveRule(i, 1)" title="下移">↓</button>
                <button class="step-btn step-del" @click="removeRule(i)" title="删除">×</button>
              </div>
            </div>
            <button class="add-step-btn" @click="addRule">＋ 添加步骤</button>
          </div>
        </div>

        <div class="form-field full">
          <label>备注</label>
          <input v-model="editing.remark" class="text-input" placeholder="可选" maxlength="200" />
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page-container { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: flex-end; padding: 0 0 18px; }
.breadcrumb { font-size: 12px; color: var(--color-text-tertiary, #94A3B8); margin-bottom: 6px; }
.page-header h1 { font-size: 22px; font-weight: 600; margin: 4px 0 6px; color: #0F172A; }
.page-desc { color: #64748B; font-size: 13px; margin: 0; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border-radius: 12px; padding: 16px 18px; display: flex; align-items: center; gap: 12px; border: 1px solid #E2E8F0; }
.kpi-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; background: #F1F5F9; }
.kpi-primary .kpi-icon { background: #EEF2FF; color: #4F6BFF; }
.kpi-success .kpi-icon { background: #ECFDF5; color: #047857; }
.kpi-warning .kpi-icon { background: #FFFBEB; color: #B45309; }
.kpi-info .kpi-icon { background: #EFF6FF; color: #1D4ED8; }
.kpi-label { font-size: 12px; color: #64748B; }
.kpi-num { font-size: 22px; font-weight: 700; color: #0F172A; line-height: 1.1; margin-top: 2px; font-family: 'SF Mono', Menlo, monospace; }

/* 卡片 */
.card { background: #fff; border-radius: 12px; border: 1px solid #E2E8F0; padding: 18px 20px; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.card-head h3 { font-size: 15px; font-weight: 600; color: #0F172A; margin: 0; }
.card-head .hint { font-size: 12px; color: #94A3B8; }
.empty-tip { padding: 40px 20px; text-align: center; color: #94A3B8; font-size: 13px; }

/* 模板列表 */
.tpl-list { display: flex; flex-direction: column; gap: 12px; }
.tpl-card { border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 16px; transition: all 0.15s; background: #FFFFFF; }
.tpl-card:hover { border-color: #4F6BFF; box-shadow: 0 4px 12px rgba(79, 107, 255, 0.08); }
.tpl-card.tpl-inactive { opacity: 0.55; }
.tpl-card.tpl-default { border-left: 3px solid #4F6BFF; }
.tpl-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.tpl-title { display: flex; align-items: center; gap: 8px; }
.tpl-name { font-size: 15px; font-weight: 600; color: #0F172A; }
.tpl-biz { font-family: 'SF Mono', monospace; font-size: 11px; color: #64748B; background: #F1F5F9; padding: 2px 8px; border-radius: 4px; }
.tpl-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
.tpl-badge-default { background: #EEF2FF; color: #4F6BFF; }
.tpl-badge-off { background: #F1F5F9; color: #94A3B8; }
.tpl-actions { display: flex; gap: 6px; }
.link-btn { background: none; border: none; padding: 4px 8px; font-size: 12px; color: #4F6BFF; cursor: pointer; border-radius: 4px; font-family: inherit; }
.link-btn:hover { background: #EEF2FF; }
.link-btn.link-danger { color: #DC2626; }
.link-btn.link-danger:hover { background: #FEE2E2; }

.tpl-flow { display: flex; flex-direction: column; gap: 6px; }
.flow-line { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.flow-step { display: flex; align-items: center; gap: 6px; }
.flow-num { width: 22px; height: 22px; border-radius: 50%; background: #EEF2FF; color: #4F6BFF; font-size: 11px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.flow-name { font-size: 13px; color: #334155; background: #F8FAFC; padding: 4px 10px; border-radius: 6px; border: 1px solid #E2E8F0; }
.flow-arrow { color: #CBD5E1; font-size: 14px; margin: 0 2px; }
.tpl-cond { font-size: 12px; color: #B45309; background: #FFFBEB; padding: 4px 10px; border-radius: 6px; border: 1px solid #FDE68A; align-self: flex-start; }
.tpl-remark { font-size: 12px; color: #64748B; margin-top: 4px; }

/* 表单 */
.form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-field label { font-size: 12px; color: #475569; font-weight: 500; }
.form-field .required { color: #DC2626; }
.form-field.full { width: 100%; }
.text-input { width: 100%; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 10px; font-size: 13px; background: #fff; font-family: inherit; color: #0F172A; }
.text-input:focus { outline: none; border-color: #4F6BFF; box-shadow: 0 0 0 3px rgba(79, 107, 255, 0.12); }
.amount-input { display: flex; align-items: center; gap: 6px; }
.amount-input .prefix, .amount-input .suffix { font-size: 12px; color: #64748B; white-space: nowrap; }
.amount-input .text-input { flex: 1; }
.hint-tip { font-size: 11px; color: #94A3B8; white-space: nowrap; }
.checkbox-row { display: flex; gap: 16px; align-items: center; height: 38px; }
.cb { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: #334155; cursor: pointer; }

.steps { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #F8FAFC; border-radius: 8px; }
.step-row { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 8px; }
.step-num { width: 26px; height: 26px; border-radius: 50%; background: #4F6BFF; color: #fff; font-size: 12px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.step-btns { display: flex; gap: 2px; }
.step-btn { width: 26px; height: 26px; border: 1px solid #E2E8F0; background: #fff; color: #475569; border-radius: 4px; cursor: pointer; font-size: 14px; line-height: 1; }
.step-btn:hover:not(:disabled) { background: #EEF2FF; color: #4F6BFF; border-color: #4F6BFF; }
.step-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.step-btn.step-del:hover { background: #FEE2E2; color: #DC2626; border-color: #DC2626; }
.add-step-btn { margin-top: 4px; padding: 8px; background: #fff; border: 1px dashed #CBD5E1; border-radius: 6px; color: #4F6BFF; cursor: pointer; font-size: 13px; font-family: inherit; }
.add-step-btn:hover { border-color: #4F6BFF; background: #EEF2FF; border-style: solid; }
</style>
