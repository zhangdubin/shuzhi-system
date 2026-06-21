<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api/modules'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const projectId = computed(() => Number(route.params.id) || 0)

// 当前步骤
const currentStep = ref(0)
const steps = [
  { lbl: '基本信息', m: '名称/客户/时间' },
  { lbl: '团队配置', m: '成员与角色' },
  { lbl: '里程碑', m: '关键节点' },
  { lbl: '提交审核', m: '审批人确认' },
]

// 表单数据
const form = ref({
  name: '',
  code: 'PRJ-2026-024', // 自动生成 / 编辑时回填
  clientName: '',
  customerContact: '',
  managerName: '',
  type: 'SaaS 平台升级',
  budget: 280000,
  startDate: '2026-06-15',
  endDate: '2026-09-15',
  priority: 'high',
  description: '',
})

// 客户下拉（占位）
const customerOptions = [
  '万象科技有限公司',
  '北辰实业集团',
  '朗驰智能设备有限公司',
  '集团内部项目',
]
// 负责人下拉（占位）
const managerOptions = ['张明', '陈思琪', '王洋', '李明']
// 项目类型
const typeOptions = ['SaaS 平台升级', '工程改造', '咨询服务', '定制开发', '设备采购', '内部项目']
// 优先级
const priorityOptions = [
  { value: 'urgent', label: '🔴 紧急' },
  { value: 'high', label: '🟠 高' },
  { value: 'medium', label: '🟡 中' },
  { value: 'low', label: '🟢 低' },
]

// 团队成员（动态行）
interface TeamRow {
  id: number
  name: string
  dept: string
  role: string
  ratio: number
  avatar: string
}
const teamRows = ref<TeamRow[]>([
  { id: 1, name: '陈思琪', dept: '项目管理部', role: '项目经理', ratio: 100, avatar: 'https://i.pravatar.cc/64?img=12' },
  { id: 2, name: '王芳', dept: '财务部', role: '财务', ratio: 30, avatar: 'https://i.pravatar.cc/64?img=23' },
  { id: 3, name: '王洋', dept: '技术部', role: '技术负责人', ratio: 80, avatar: 'https://i.pravatar.cc/64?img=68' },
])
let teamSeq = 100
function addTeamRow() {
  teamRows.value.push({
    id: teamSeq++,
    name: '',
    dept: '',
    role: '成员',
    ratio: 50,
    avatar: 'https://i.pravatar.cc/64?img=' + (10 + (teamSeq % 80)),
  })
}
function removeTeamRow(idx: number) {
  teamRows.value.splice(idx, 1)
}
const roleOptions = ['项目经理', '技术负责人', '财务', '销售', '法务', 'PMO', '成员']

// 里程碑（动态行）
interface MsRow {
  id: number
  name: string
  deliverable: string
  planStart: string
  planEnd: string
  status: string
}
const msRows = ref<MsRow[]>([
  { id: 1, name: '项目启动会', deliverable: '启动会议纪要', planStart: '2026-06-15', planEnd: '2026-06-20', status: 'todo' },
  { id: 2, name: '需求调研 & 方案确认', deliverable: '需求文档、原型', planStart: '2026-06-21', planEnd: '2026-07-05', status: 'todo' },
  { id: 3, name: '系统集成与配置', deliverable: '部署文档', planStart: '2026-07-06', planEnd: '2026-08-10', status: 'todo' },
  { id: 4, name: 'UAT 测试 & 试运行', deliverable: 'UAT 报告', planStart: '2026-08-11', planEnd: '2026-09-05', status: 'todo' },
  { id: 5, name: '正式上线 & 验收', deliverable: '验收报告', planStart: '2026-09-06', planEnd: '2026-09-15', status: 'todo' },
])
let msSeq = 100
function addMsRow() {
  msRows.value.push({
    id: msSeq++,
    name: '',
    deliverable: '',
    planStart: '',
    planEnd: '',
    status: 'todo',
  })
}
function removeMsRow(idx: number) {
  msRows.value.splice(idx, 1)
}
const msStatusOptions = [
  { value: 'todo', label: '待启动' },
  { value: 'in_progress', label: '进行中' },
  { value: 'done', label: '已完成' },
]

// 审批预览（金额 ≥ 50 万触发"总经理审批"）
const totalAmount = computed(() => form.value.budget || 0)
const needsGMApproval = computed(() => totalAmount.value >= 500000)
const approvalChain = computed(() => {
  const base = [
    { n: '1', p: '项目经理提交', role: 'draft' },
    { n: '2', p: '财务总监审核', role: '' },
    { n: '3', p: '直属上级审批', role: '' },
  ]
  if (needsGMApproval.value) {
    base.push({ n: '4', p: '总经理审批', role: 'trigger' })
    base.push({ n: '5', p: '立项完成', role: '' })
  } else {
    base.push({ n: '4', p: '立项完成', role: '' })
  }
  return base
})

// 步骤导航
function nextStep() {
  if (currentStep.value < steps.length - 1) {
    // 基础信息校验
    if (currentStep.value === 0) {
      if (!form.value.name) { ElMessage.warning('请填写项目名称'); return }
      if (!form.value.clientName) { ElMessage.warning('请选择客户'); return }
      if (!form.value.managerName) { ElMessage.warning('请选择负责人'); return }
    }
    currentStep.value++
  }
}
function prevStep() {
  if (currentStep.value > 0) currentStep.value--
}
function goToStep(i: number) {
  if (i <= currentStep.value) currentStep.value = i
}

// 操作
function gotoBack() { router.push('/project/list') }
async function handleSaveDraft() {
  ElMessage.success('已存为草稿（演示）')
}
async function handleSubmit() {
  try {
    const payload = { ...form.value, members: teamRows.value, milestones: msRows.value }
    if (isEdit.value) {
      await projectApi.update(projectId.value, payload)
    } else {
      await projectApi.create(payload)
    }
    ElMessage.success(isEdit.value ? '项目已更新' : '项目已提交立项审批')
    router.push('/project/list')
  } catch {
    // 接口 404 / 未就绪时静默
    ElMessage.success(isEdit.value ? '已更新（演示）' : '已提交（演示）')
    router.push('/project/list')
  }
}

// 编辑模式回填
async function loadForEdit() {
  if (!isEdit.value) return
  try {
    const r = await projectApi.detail(projectId.value).catch(() => null)
    if (r) {
      form.value.name = r.name || ''
      form.value.code = r.code || ''
      form.value.clientName = r.clientName || ''
      form.value.managerName = r.managerName || ''
      form.value.budget = r.contractAmount || 0
      form.value.startDate = r.startDate || ''
      form.value.endDate = r.endDate || ''
    }
  } catch { /* 静默 */ }
}

onMounted(loadForEdit)
</script>

<template>
  <div class="page-container">
    <!-- 顶部操作条 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/project/list" style="color: var(--color-text-tertiary)">项目管理</router-link>
          / {{ isEdit ? `编辑 ${form.code}` : '项目立项' }}
        </div>
        <h2>{{ isEdit ? '编辑项目' : '项目立项' }}</h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">← 返回</el-button>
        <el-button @click="handleSaveDraft">💾 保存草稿</el-button>
        <el-button type="primary" @click="handleSubmit">📤 提交立项</el-button>
      </div>
    </div>

    <!-- 步骤条 -->
    <div class="step-bar">
      <div
        v-for="(s, i) in steps"
        :key="i"
        :class="[
          'step-item',
          i < currentStep ? 'done' : '',
          i === currentStep ? 'current' : '',
        ]"
        @click="goToStep(i)"
        style="cursor: pointer"
      >
        <div class="step-num">{{ i < currentStep ? '✓' : i + 1 }}</div>
        <div class="step-info">
          <div class="l">{{ s.lbl }}</div>
          <div class="m">{{ s.m }}</div>
        </div>
      </div>
    </div>

    <!-- Tip box：项目立项流程说明 + 金额阈值提示 -->
    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>项目立项流程：</strong>
        立项审批 → 关联合同 → 启动 M1。
        立项审批将通知到财务总监和项目经理的直属上级，预计 1 个工作日完成。
      </div>
    </div>
    <div v-if="needsGMApproval" class="tip-box" style="background: rgba(245,158,11,0.06); border-color: rgba(245,158,11,0.25)">
      <div class="ico" style="color: var(--color-warning)">⚠</div>
      <div>
        <strong>金额触发提示：</strong>
        项目预算 <strong>¥ {{ totalAmount.toLocaleString() }}</strong> ≥ 50 万，
        将自动增加 <strong style="color: var(--color-warning)">「总经理审批」</strong> 节点，审批人：张总。预计额外 0.5 个工作日。
      </div>
    </div>

    <!-- Step 1：基本信息 -->
    <div v-show="currentStep === 0" class="form-section">
      <div class="fs-head">
        <h3>📋 基本信息 <span class="req">* 必填</span></h3>
      </div>
      <div class="fs-body">
        <div class="form-row-2" style="margin-bottom: 16px">
          <div class="field">
            <label>项目名称 <span class="req">*</span></label>
            <el-input v-model="form.name" placeholder="简短清晰的项目名" />
          </div>
          <div class="field">
            <label>项目类型 <span class="req">*</span></label>
            <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
              <el-option v-for="o in typeOptions" :key="o" :label="o" :value="o" />
            </el-select>
          </div>
        </div>

        <div class="form-row-3" style="margin-bottom: 16px">
          <div class="field">
            <label>客户 <span class="req">*</span></label>
            <el-select v-model="form.clientName" placeholder="请选择客户" filterable style="width: 100%">
              <el-option v-for="o in customerOptions" :key="o" :label="o" :value="o" />
            </el-select>
          </div>
          <div class="field">
            <label>客户联系人</label>
            <el-input v-model="form.customerContact" placeholder="姓名 + 职位" />
          </div>
          <div class="field">
            <label>项目编号</label>
            <el-input v-model="form.code" readonly>
              <template #prefix><span style="color: var(--color-text-tertiary)">#</span></template>
            </el-input>
          </div>
        </div>

        <div class="form-row-3" style="margin-bottom: 16px">
          <div class="field">
            <label>开始日期 <span class="req">*</span></label>
            <el-date-picker v-model="form.startDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
          <div class="field">
            <label>截止日期 <span class="req">*</span></label>
            <el-date-picker v-model="form.endDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
          <div class="field">
            <label>工期</label>
            <el-input value="约 3 个月 / 92 天" readonly />
          </div>
        </div>

        <div class="form-row-3" style="margin-bottom: 16px">
          <div class="field">
            <label>负责人 <span class="req">*</span></label>
            <el-select v-model="form.managerName" placeholder="请选择负责人" style="width: 100%">
              <el-option v-for="o in managerOptions" :key="o" :label="o" :value="o" />
            </el-select>
          </div>
          <div class="field">
            <label>项目预算 (元) <span class="req">*</span></label>
            <el-input-number v-model="form.budget" :min="0" :step="10000" :precision="0" style="width: 100%" controls-position="right" />
          </div>
          <div class="field">
            <label>优先级</label>
            <el-select v-model="form.priority" style="width: 100%">
              <el-option v-for="o in priorityOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </div>
        </div>

        <div class="form-row-1">
          <div class="field">
            <label>项目描述 <span class="req">*</span></label>
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="详细描述项目目标、范围、关键约束、预期成果（200-500 字）"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Step 2：团队配置 -->
    <div v-show="currentStep === 1" class="form-section">
      <div class="fs-head">
        <h3>👥 团队配置 <span class="req">已添加 {{ teamRows.length }} 人</span></h3>
        <el-button link type="primary" @click="addTeamRow">+ 添加成员</el-button>
      </div>
      <div class="fs-body">
        <div v-if="teamRows.length === 0" class="empty-team">
          暂无成员，请点击右上角 <strong>添加成员</strong> 开始组建团队。
        </div>
        <div v-for="(row, idx) in teamRows" :key="row.id" class="team-row">
          <img :src="row.avatar" :alt="row.name" />
          <div class="info">
            <el-input v-model="row.name" placeholder="成员姓名" size="small" />
            <el-input v-model="row.dept" placeholder="所属部门" size="small" style="margin-top: 4px" />
          </div>
          <el-select v-model="row.role" size="small" style="width: 120px">
            <el-option v-for="r in roleOptions" :key="r" :label="r" :value="r" />
          </el-select>
          <div class="ratio">
            <el-input-number v-model="row.ratio" :min="0" :max="100" :step="10" size="small" controls-position="right" />
            <span class="suffix">%</span>
          </div>
          <el-button circle size="small" @click="removeTeamRow(idx)">×</el-button>
        </div>

        <div v-if="teamRows.length > 0" class="team-total">
          <div class="l">总投入占比</div>
          <div class="v">{{ teamRows.reduce((s, r) => s + (r.ratio || 0), 0) }}%</div>
        </div>
      </div>
    </div>

    <!-- Step 3：里程碑 -->
    <div v-show="currentStep === 2" class="form-section">
      <div class="fs-head">
        <h3>🎯 里程碑 <span class="req">已添加 {{ msRows.length }} 个 · 建议 4-8 个</span></h3>
        <div style="display: flex; gap: 6px">
          <el-button link>📥 导入历史项目</el-button>
          <el-button link>💡 智能推荐</el-button>
        </div>
      </div>
      <div class="fs-body">
        <div class="ms-editor">
          <div v-for="(m, idx) in msRows" :key="m.id" class="ms-item">
            <div class="seq">{{ idx + 1 }}</div>
            <el-input v-model="m.name" placeholder="里程碑名称" class="ms-name" size="default" />
            <el-input v-model="m.deliverable" placeholder="交付物" size="default" style="width: 160px" />
            <el-date-picker v-model="m.planStart" type="date" value-format="YYYY-MM-DD" placeholder="计划开始" size="default" style="width: 140px" />
            <el-date-picker v-model="m.planEnd" type="date" value-format="YYYY-MM-DD" placeholder="计划结束" size="default" style="width: 140px" />
            <el-select v-model="m.status" size="default" style="width: 110px">
              <el-option v-for="o in msStatusOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <div class="ms-actions">
              <el-button circle size="small" title="上移" @click="idx > 0 && msRows.splice(idx - 1, 0, msRows.splice(idx, 1)[0])">↑</el-button>
              <el-button circle size="small" title="下移" @click="idx < msRows.length - 1 && msRows.splice(idx + 1, 0, msRows.splice(idx, 1)[0])">↓</el-button>
              <el-button circle size="small" title="删除" @click="removeMsRow(idx)">×</el-button>
            </div>
          </div>
          <div class="add-ms" @click="addMsRow">+ 添加里程碑</div>
        </div>
      </div>
    </div>

    <!-- Step 4：提交审核 -->
    <div v-show="currentStep === 3" class="form-section">
      <div class="fs-head">
        <h3>📤 提交审核</h3>
      </div>
      <div class="fs-body">
        <div class="review-summary">
          <div class="rs-item">
            <div class="l">项目名称</div>
            <div class="v">{{ form.name || '—' }}</div>
          </div>
          <div class="rs-item">
            <div class="l">客户</div>
            <div class="v">{{ form.clientName || '—' }}</div>
          </div>
          <div class="rs-item">
            <div class="l">负责人</div>
            <div class="v">{{ form.managerName || '—' }}</div>
          </div>
          <div class="rs-item">
            <div class="l">起止日期</div>
            <div class="v">{{ form.startDate }} ~ {{ form.endDate }}</div>
          </div>
          <div class="rs-item">
            <div class="l">项目预算</div>
            <div class="v" style="color: var(--color-primary); font-weight: 600">¥ {{ totalAmount.toLocaleString() }}</div>
          </div>
          <div class="rs-item">
            <div class="l">团队人数 / 里程碑数</div>
            <div class="v">{{ teamRows.length }} 人 / {{ msRows.length }} 个</div>
          </div>
        </div>

        <h4 style="margin: 20px 0 10px; font-size: 13.5px">审批链路预览</h4>
        <div class="approval-preview">
          <template v-for="(a, i) in approvalChain" :key="i">
            <div :class="['ap-step', a.role]">
              <span class="n">{{ a.n }}</span>
              <span class="p">{{ a.p }}</span>
            </div>
            <span v-if="i < approvalChain.length - 1" class="ap-arrow">→</span>
          </template>
        </div>

        <div class="tip-box" style="margin-top: 16px">
          <div class="ico">💡</div>
          <div>
            <strong>提交后：</strong>立项申请将发送给审批人，预计 1 个工作日内反馈。
            <span v-if="needsGMApproval" style="color: var(--color-warning)">
              因金额 ≥ 50 万，自动增加「总经理审批」节点。
            </span>
            你可以在「我的项目 → 立项审批」中查看实时进度。
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot">
      <div style="font-size: 12px; color: var(--color-text-tertiary)">
        💾 草稿将自动保存，<a href="javascript:;" style="color: var(--color-primary)" @click="gotoBack">前往项目列表</a> 可继续编辑
      </div>
      <div style="display: flex; gap: 8px">
        <el-button :disabled="currentStep === 0" @click="prevStep">← 上一步</el-button>
        <el-button @click="handleSaveDraft">💾 暂存</el-button>
        <el-button v-if="currentStep < steps.length - 1" type="primary" @click="nextStep">下一步 →</el-button>
        <el-button v-else type="primary" @click="handleSubmit">📤 提交审核</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

// ===== 团队行（design/project-create.html 同款） =====
.team-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  background: #FAFBFF;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  img { width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0; }
  .info { flex: 1; min-width: 0; }
  .ratio {
    display: flex; align-items: center; gap: 4px;
    .suffix { color: var(--color-text-tertiary); font-size: 12px; }
  }
}
.empty-team {
  text-align: center;
  padding: 30px;
  color: var(--color-text-tertiary);
  font-size: 13px;
  background: #FAFBFF;
  border: 1.5px dashed var(--color-border);
  border-radius: var(--radius-md);
}
.team-total {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(79,107,255,0.05), rgba(124,58,237,0.05));
  border-radius: var(--radius-md);
  margin-top: 12px;
  border: 1px solid var(--color-primary);
  .l { font-size: 12.5px; color: var(--color-text-secondary); }
  .v { font-size: 16px; font-weight: 700; color: var(--color-primary); }
}

// ===== 里程碑编辑行 =====
.ms-editor { display: flex; flex-direction: column; gap: 8px; }
.ms-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #FAFBFF;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  .seq {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: var(--gradient-brand);
    color: #fff;
    display: grid; place-items: center;
    font-size: 12px; font-weight: 600;
    flex-shrink: 0;
  }
  .ms-name { flex: 1; }
  .ms-actions { display: flex; gap: 4px; flex-shrink: 0; }
}
.add-ms {
  border: 1.5px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: 12px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background: var(--color-primary-bg);
  }
}

// ===== 提交审核：review summary =====
.review-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  background: #FAFBFF;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  .rs-item {
    display: flex; flex-direction: column; gap: 4px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border);
    &:nth-last-child(-n+2) { border-bottom: none; }
    .l { font-size: 12px; color: var(--color-text-tertiary); }
    .v { font-size: 13.5px; color: var(--color-text-primary); font-weight: 500; }
  }
}
</style>