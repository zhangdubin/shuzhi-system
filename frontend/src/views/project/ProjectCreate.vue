<script setup lang="ts">
/**
 * ProjectCreate · 项目立项（1:1 复刻 design/project-create.html）
 * - step-bar 4 步（基本信息 / 团队 / 里程碑 / 预算）
 * - tip-box 流程提示
 * - 4 form-section：基本信息 / 团队组建 / 里程碑 / 预算
 * - form-foot 操作条
 */
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi } from '@/api/modules'
import { clientApi } from '@/api/client'

const router = useRouter()
const formRef = ref()

// 工期：默认按 startDate / endDate 自动算，用户手动改过后不再覆盖
const periodManuallyEdited = ref(false)
function autoCalcPeriod() {
  if (!form.startDate || !form.endDate) return
  const s = new Date(form.startDate as any)
  const e = new Date(form.endDate as any)
  if (isNaN(s.getTime()) || isNaN(e.getTime()) || e < s) return
  const days = Math.round((e.getTime() - s.getTime()) / 86400000) + 1
  const months = Math.max(1, Math.round(days / 30))
  form.period = `约 ${months} 个月 / ${days} 天`
}
watch(() => [form.startDate, form.endDate], () => {
  if (!periodManuallyEdited.value) autoCalcPeriod()
}, { immediate: true })

// 客户下拉（从客户管理拉真实数据）
const clientOptions = ref<Array<{ id: number; name: string; contactName?: string | null; code: string; shortName?: string | null }>>([])
async function loadClients() {
  try {
    // 后端 pageSize 限 100，分页拉全部
    const all: any[] = []
    const pageSize = 100
    for (let p = 1; p <= 50; p++) {
      const res: any = await clientApi.list({ page: p, pageSize, includeInactive: false } as any)
      const list = res?.list || []
      all.push(...list)
      const total = res?.total || 0
      if (list.length < pageSize || all.length >= total) break
    }
    clientOptions.value = all.map((c: any) => ({
      id: c.id, name: c.name, code: c.code,
      contactName: c.contactName, shortName: c.shortName,
    }))
  } catch (e) {
    console.warn('[ProjectCreate] 客户列表加载失败', e)
  }
}

/** 选客户后联级带出联系人/编号 */
function onClientChange(val: string) {
  const c = clientOptions.value.find(x => x.name === val)
  if (!c) return
  // 联系人有就带出，没有保持原值
  if (c.contactName) form.contact = c.contactName
  // 项目编号：项目自动生成（覆盖）
  form.code = `PRJ-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 9000) + 1000)}`
}

const form = reactive({
  // 1. 基本信息
  name: '万象科技 SaaS 部署',
  type: 'SaaS 平台升级',
  client: '万象科技有限公司',
  contact: '李建国（CTO）',
  code: 'PRJ-2026-024',
  startDate: '2026-06-15',
  endDate: '2026-09-15',
  period: '',
  manager: '陈思琪',
  priority: '🟠 高',
  description: '为万象科技部署 SaaS 平台标准版，包含发票识别、模板管理、报表分析等核心模块。30 个用户账号，需完成系统集成、数据迁移、培训上线。',
  // 2. 团队
  team: [
    { name: '陈思琪', role: '财务专员', avatar: 'https://i.pravatar.cc/64?img=12', teamRole: '项目经理' },
    { name: '王芳',   role: '财务专员', avatar: 'https://i.pravatar.cc/64?img=23', teamRole: '财务' },
    { name: '李明',   role: '法务主管', avatar: 'https://i.pravatar.cc/64?img=33', teamRole: '法务' },
    { name: '王洋',   role: '技术负责人', avatar: 'https://i.pravatar.cc/64?img=68', teamRole: '技术负责人' },
  ],
  // 3. 里程碑
  milestones: [
    { seq: 1, name: '项目启动会', date: '2026-06-15', status: 'done'    },
    { seq: 2, name: '需求调研',   date: '2026-06-25', status: 'current' },
    { seq: 3, name: '系统部署',   date: '2026-07-15', status: 'todo'    },
    { seq: 4, name: '数据迁移',   date: '2026-08-10', status: 'todo'    },
    { seq: 5, name: '项目验收',   date: '2026-09-10', status: 'todo'    },
  ],
  // 4. 预算
  budget: '286,000.00',
  budgets: [
    { item: '人力成本',  amount: '168,000', pct: 58.7 },
    { item: '软件采购',  amount: '60,000',  pct: 21.0 },
    { item: '差旅/会议', amount: '28,000',  pct: 9.8  },
    { item: '咨询/培训', amount: '20,000',  pct: 7.0  },
    { item: '预留缓冲',  amount: '10,000',  pct: 3.5  },
  ],
})

const rules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  startDate: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
}

function addTeam() { ElMessage.info('添加成员') }
function addMilestone() { ElMessage.info('添加里程碑') }
function importHistory() { ElMessage.info('导入历史项目') }

const aiDrawerVisible = ref(false)
const aiLoading = ref(false)
const aiSuggestions = ref<{icon: string; title: string; detail: string; level: string}[]>([])

function getAiSuggestions() {
  aiLoading.value = true
  aiDrawerVisible.value = true
  // 根据表单数据生成建议
  setTimeout(() => {
    const tips: {icon: string; title: string; detail: string; level: string}[] = []
    if (!form.client) tips.push({ icon: '🏢', title: '建议关联客户', detail: '项目未选择客户，关联客户后便于后续合同、回款、发票的自动关联。', level: 'warning' })
    if (!form.startDate || !form.endDate) tips.push({ icon: '📅', title: '建议设置项目周期', detail: '未设置起止日期，会影响里程碑自动生成和进度跟踪。', level: 'info' })
    if (!form.budget || parseFloat(form.budget.replace(/,/g, '')) === 0) tips.push({ icon: '💰', title: '建议填写预算', detail: '预算为空将无法进行费用审批和预算控制。', level: 'warning' })
    if (form.milestones.length < 3) tips.push({ icon: '🏁', title: '里程碑偏少', detail: '建议至少设置 3 个里程碑（启动/中期/验收），便于进度管控。', level: 'info' })
    if (form.team.length < 2) tips.push({ icon: '👥', title: '团队配置不足', detail: '建议至少配置项目经理和财务两个角色，确保职责分离。', level: 'info' })
    // 通用建议
    tips.push({ icon: '📋', title: '历史项目参考', detail: `系统中有类似类型的历史项目，建议参考「${form.type || '同类'}」项目的里程碑和预算分配。`, level: 'success' })
    tips.push({ icon: '⚠️', title: '风险提示', detail: '根据历史数据，SaaS 部署类项目平均延期 12%，建议预留 2 周缓冲期。', level: 'warning' })
    aiSuggestions.value = tips
    aiLoading.value = false
  }, 800)
}
// 里程碑模板：按项目类型给一套标准节点
const MILESTONE_TEMPLATES: Record<string, string[]> = {
  'SaaS 平台升级': ['项目启动会', '需求调研', '环境准备与部署', '系统集成', '数据迁移', '培训上线', '项目验收'],
  '工程改造':     ['项目启动', '现场勘察', '方案设计', '施工实施', '中期检查', '竣工验收'],
  '咨询服务':     ['项目启动', '调研访谈', '诊断分析', '方案设计', '汇报评审', '交付结项'],
  '定制开发':     ['项目启动', '需求调研', '原型设计', '开发实施', '内部测试', 'UAT 验收', '上线部署'],
  '设备采购':     ['需求确认', '供应商询比', '合同签订', '到货验收', '安装调试', '投入使用'],
  '内部项目':     ['项目启动', '方案设计', '执行实施', '阶段复盘', '完成交付'],
}
function smartRecommend() {
  const tpl = MILESTONE_TEMPLATES[form.type] || MILESTONE_TEMPLATES['内部项目']
  // 起止日期决定里程碑的日期分布
  const start = form.startDate ? new Date(form.startDate as any) : null
  const end = form.endDate ? new Date(form.endDate as any) : null
  let dates: string[] = []
  if (start && end && !isNaN(start.getTime()) && !isNaN(end.getTime()) && end >= start) {
    const totalDays = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86400000))
    tpl.forEach((_, i) => {
      const offset = tpl.length === 1 ? 0 : Math.round((totalDays * i) / (tpl.length - 1))
      const d = new Date(start.getTime() + offset * 86400000)
      dates.push(d.toISOString().slice(0, 10))
    })
  } else {
    // 没有起止日期则用今天的 N 天
    const today = new Date()
    tpl.forEach((_, i) => {
      const d = new Date(today.getTime() + i * 14 * 86400000)
      dates.push(d.toISOString().slice(0, 10))
    })
  }
  form.milestones = tpl.map((name, i) => ({
    seq: i + 1,
    name,
    date: dates[i],
    status: 'todo',
  }))
  ElMessage.success(`已按「${form.type}」生成 ${tpl.length} 个里程碑`)
}
function saveDraft() { ElMessage.success('草稿已保存') }
function cancel() { router.push('/project/list') }
async function submitApproval() {
  try {
    const budgetFen = Math.round(parseFloat(String(form.budget).replace(/,/g, '')) * 100) || 0
    await projectApi.create({
      name: form.name,
      type: form.type,
      clientName: form.client,
      contactPerson: form.contact,
      code: form.code,
      startDate: form.startDate || null,
      endDate: form.endDate || null,
      period: form.period,
      managerName: form.manager,
      priority: form.priority,
      description: form.description,
      teamMembers: form.team.map(t => ({ name: t.name, role: t.teamRole })),
      milestones: form.milestones.map(m => ({ seq: m.seq, name: m.name, date: m.date })),
      budget: budgetFen,
    } as any)
    ElMessage.success('项目已提交审批')
    setTimeout(() => router.push('/project/list'), 800)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d: any) => `${d.loc?.slice(-1)[0] || ''}: ${d.msg || ''}`).join('；')
      : (detail || e?.message || '未知错误')
    ElMessage.error('提交失败：' + msg)
  }
}

onMounted(() => {
  loadClients()
  projectApi.list({ page: 1, pageSize: 1 } as any).catch(() => {})
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/project/list')">业务</a>
          <span class="sep">/</span>
          <a @click="router.push('/project/list')">项目管理</a>
          <span class="sep">/</span>
          <span class="current">新建项目</span>
        </div>
        <h1>新建项目</h1>
        <p class="page-desc">项目立项 · 团队组建 · 里程碑 · 预算</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="getAiSuggestions">💡 AI 立项建议</button>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
    </div>

    <!-- step-bar 4 步 -->
    <div class="page-card">
      <div class="step-bar">
        <div class="step-item">
          <div class="step-num">1</div>
          <div class="step-info"><div class="l">基本信息</div><div class="m">项目 + 客户</div></div>
        </div>
        <div class="step-item">
          <div class="step-num">2</div>
          <div class="step-info"><div class="l">团队组建</div><div class="m">成员 + 角色</div></div>
        </div>
        <div class="step-item">
          <div class="step-num">3</div>
          <div class="step-info"><div class="l">里程碑</div><div class="m">关键节点</div></div>
        </div>
        <div class="step-item">
          <div class="step-num">4</div>
          <div class="step-info"><div class="l">预算</div><div class="m">成本拆分</div></div>
        </div>
      </div>
    </div>

    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>项目立项后流程：</strong>
        立项审批 → 关联合同 → 启动 M1。立项审批将通知到财务总监和项目经理的直属上级，预计 <strong>1 个工作日</strong>。
      </div>
    </div>

    <!-- 1. 基本信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📋 基本信息 <span class="req">* 必填</span></h3>
      </div>
      <div class="fs-body">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="项目名称" prop="name" required>
                <el-input v-model="form.name" placeholder="简短清晰的项目名" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="项目类型" required>
                <el-select v-model="form.type" style="width: 100%">
                  <el-option label="SaaS 平台升级" value="SaaS 平台升级" />
                  <el-option label="工程改造" value="工程改造" />
                  <el-option label="咨询服务" value="咨询服务" />
                  <el-option label="定制开发" value="定制开发" />
                  <el-option label="设备采购" value="设备采购" />
                  <el-option label="内部项目" value="内部项目" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="客户" required>
                <el-select
                  v-model="form.client"
                  placeholder="请选择客户（从客户管理加载）"
                  filterable
                  style="width: 100%"
                  @change="onClientChange"
                >
                  <el-option
                    v-for="c in clientOptions"
                    :key="c.id"
                    :label="c.shortName ? `${c.name}（${c.shortName}）` : c.name"
                    :value="c.name"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="客户联系人">
                <el-input v-model="form.contact" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="项目编号">
                <el-input v-model="form.code" readonly style="font-family: var(--font-family-mono); font-size: 12.5px;" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="开始日期" prop="startDate" required>
                <el-date-picker v-model="form.startDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="截止日期" required>
                <el-date-picker v-model="form.endDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="工期">
                <el-input v-model="form.period" placeholder="留空将按开始/截止日期自动计算" @input="periodManuallyEdited = true" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="项目经理" required>
                <el-select v-model="form.manager" style="width: 100%">
                  <el-option label="张明" value="张明" />
                  <el-option label="陈思琪" value="陈思琪" />
                  <el-option label="王洋" value="王洋" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="优先级">
                <el-select v-model="form.priority" style="width: 100%">
                  <el-option label="🔴 紧急" value="🔴 紧急" />
                  <el-option label="🟠 高" value="🟠 高" />
                  <el-option label="🟡 中" value="🟡 中" />
                  <el-option label="🟢 低" value="🟢 低" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="项目描述" required>
            <el-input v-model="form.description" type="textarea" :rows="4" placeholder="详细描述项目目标、范围、关键约束、预期成果（200-500 字）" />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 2. 团队组建 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>👥 团队组建 <span class="req">已添加 4 人</span></h3>
      </div>
      <div class="fs-body">
        <div class="team-search">
          <input class="search-input" placeholder="🔍 搜索员工姓名 / 部门..." style="flex: 1;" />
          <button class="btn btn-primary btn-sm" @click="addTeam">+ 添加成员</button>
        </div>

        <div class="team-grid">
          <div v-for="(m, i) in form.team" :key="i" class="team-row">
            <img :src="m.avatar" :alt="m.name" />
            <div class="info">
              <div class="n">{{ m.name }}</div>
              <div class="r">{{ m.role }}</div>
            </div>
            <select v-model="m.teamRole" class="role-sel">
              <option>项目经理</option>
              <option>技术负责人</option>
              <option>财务</option>
              <option>销售</option>
              <option>法务</option>
              <option>成员</option>
            </select>
            <button class="del" @click="form.team.splice(i, 1)">×</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 里程碑 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🎯 里程碑 <span class="req">已添加 5 个 · 建议 4-8 个</span></h3>
        <div style="display: flex; gap: 6px;">
          <button class="btn btn-ghost btn-sm" @click="importHistory">📥 导入历史项目</button>
          <button class="btn btn-outline btn-sm" @click="smartRecommend">💡 智能推荐</button>
        </div>
      </div>
      <div class="fs-body">
        <div class="ms-editor">
          <div v-for="(m, i) in form.milestones" :key="i" class="ms-item">
            <div class="seq">{{ m.seq }}</div>
            <input v-model="m.name" type="text" class="ms-name" />
            <el-date-picker v-model="m.date" type="date" value-format="YYYY-MM-DD" class="ms-date" />
            <select v-model="m.status" class="ms-status">
              <option value="todo">待启动</option>
              <option value="current">进行中</option>
              <option value="done">已完成</option>
            </select>
            <button class="del" @click="form.milestones.splice(i, 1)">×</button>
          </div>
        </div>
        <div class="add-ms" @click="addMilestone">+ 添加里程碑</div>
      </div>
    </div>

    <!-- 4. 预算 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💰 预算 <span class="req">成本拆分 · 5 项</span></h3>
        <span class="budget-total">合计：¥ {{ form.budget }}</span>
      </div>
      <div class="fs-body">
        <el-form label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="预算总额（元）">
                <el-input v-model="form.budget" style="font-weight: 600;">
                  <template #prepend><span style="color: #4F6BFF; font-weight: 600;">¥</span>  <!-- AI 建议抽屉 -->
  <el-drawer v-model="aiDrawerVisible" title="💡 AI 立项建议" size="480px" direction="rtl">
    <div v-if="aiLoading" style="text-align:center;padding:40px;color:#94A3B8;">
      <div style="font-size:24px;margin-bottom:8px;">✦</div>
      AI 正在分析项目信息…
    </div>
    <div v-else>
      <div v-if="aiSuggestions.length === 0" style="text-align:center;padding:40px;color:#94A3B8;">
        暂无建议，项目信息填写完整 👍
      </div>
      <div v-for="(s, i) in aiSuggestions" :key="i" style="display:flex;gap:12px;padding:14px 0;border-bottom:1px solid #F1F5F9;">
        <div style="font-size:20px;flex-shrink:0;">{{ s.icon }}</div>
        <div>
          <div style="font-weight:600;font-size:14px;color:#0F172A;">{{ s.title }}</div>
          <div style="font-size:13px;color:#64748B;margin-top:4px;line-height:1.6;">{{ s.detail }}</div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="aiDrawerVisible = false">关闭</el-button>
    </template>
  </el-drawer>
</template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="预算类型">
                <el-select style="width: 100%" placeholder="固定预算">
                  <el-option label="固定预算" value="固定" />
                  <el-option label="弹性预算 ± 20%" value="弹性" />
                  <el-option label="成本加成" value="成本加成" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <table class="budget-table">
            <thead>
              <tr><th>科目</th><th style="text-align: right;">金额（元）</th><th>占比</th><th>进度条</th></tr>
            </thead>
            <tbody>
              <tr v-for="(b, i) in form.budgets" :key="i">
                <td><strong>{{ b.item }}</strong></td>
                <td class="cell-amount">¥ {{ b.amount }}</td>
                <td>{{ b.pct }}%</td>
                <td>
                  <div class="budget-bar">
                    <div class="fill" :style="{ width: b.pct + '%' }"></div>
                  </div>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td><strong>合计</strong></td>
                <td class="cell-amount total">¥ {{ form.budget }}</td>
                <td>100%</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </el-form>
      </div>
    </div>

    <!-- form-foot -->
    <div class="form-foot">
      <div>
        <button class="btn btn-ghost btn-sm" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
      <div>
        <button class="btn btn-outline btn-sm">👁 预览</button>
        <button class="btn btn-primary btn-sm" @click="submitApproval">✓ 提交立项审批</button>
      </div>
    </div>
  </div>
  <!-- AI 建议抽屉 -->
  <el-drawer v-model="aiDrawerVisible" title="💡 AI 立项建议" size="480px" direction="rtl">
    <div v-if="aiLoading" style="text-align:center;padding:40px;color:#94A3B8;">
      <div style="font-size:24px;margin-bottom:8px;">✦</div>
      AI 正在分析项目信息…
    </div>
    <div v-else>
      <div v-if="aiSuggestions.length === 0" style="text-align:center;padding:40px;color:#94A3B8;">
        暂无建议，项目信息填写完整 👍
      </div>
      <div v-for="(s, i) in aiSuggestions" :key="i" style="display:flex;gap:12px;padding:14px 0;border-bottom:1px solid #F1F5F9;">
        <div style="font-size:20px;flex-shrink:0;">{{ s.icon }}</div>
        <div>
          <div style="font-weight:600;font-size:14px;color:#0F172A;">{{ s.title }}</div>
          <div style="font-size:13px;color:#64748B;margin-top:4px;line-height:1.6;">{{ s.detail }}</div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="aiDrawerVisible = false">关闭</el-button>
    </template>
  </el-drawer>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

// step-bar
.step-bar { display: flex; gap: 0; padding: 8px 0; }
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
  }
  &:last-child::after { display: none; }
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

// form-section
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
  .budget-total { font-size: 14px; font-weight: 700; color: $color-primary; font-family: $font-family-mono; }
}
.fs-body { padding: 18px 20px; }

// team-search
.team-search { display: flex; gap: 8px; margin-bottom: 16px; }
.search-input {
  height: 32px; padding: 0 12px; border: 1px solid $color-border; border-radius: $radius-sm;
  font-size: 12px; background: #fff;
  &:focus { outline: none; border-color: $color-primary; }
}

// team-grid（design 真实样式）
.team-grid { display: flex; flex-direction: column; gap: 8px; }
.team-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px;
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  img { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
  .info { flex: 1; min-width: 0; }
  .info .n { font-size: 13.5px; font-weight: 600; color: $color-text-primary; }
  .info .r { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  .role-sel {
    height: 28px; padding: 0 10px;
    border: 1px solid $color-border;
    border-radius: $radius-sm;
    font-size: 12px;
    background: #fff;
  }
  .del {
    width: 28px; height: 28px;
    border-radius: 50%;
    color: $color-text-tertiary;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    &:hover { background: $color-danger-bg; color: $color-danger; }
  }
}

// milestone editor
.ms-editor { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.ms-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  .seq {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: $gradient-brand;
    color: #fff;
    display: grid; place-items: center;
    font-size: 12px; font-weight: 600;
    flex-shrink: 0;
  }
  .ms-name { flex: 1; height: 32px; padding: 0 10px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 13px; background: #fff; }
  .ms-date { width: 160px; }
  .ms-status { height: 32px; padding: 0 10px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 12px; background: #fff; }
  .del {
    width: 28px; height: 28px;
    border-radius: 50%;
    color: $color-text-tertiary;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    &:hover { background: $color-danger-bg; color: $color-danger; }
  }
}
.add-ms {
  border: 1.5px dashed $color-border;
  border-radius: $radius-md;
  padding: 12px;
  text-align: center;
  color: $color-text-tertiary;
  font-size: 12.5px;
  cursor: pointer;
  &:hover { border-color: $color-primary; color: $color-primary; background: $color-primary-bg; }
}

// budget-table
.budget-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: $color-bg; text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: $color-text-tertiary; border-bottom: 1px solid $color-border; }
  td { padding: 12px 14px; border-bottom: 1px solid $color-border; }
  tfoot td { background: $color-bg; border-bottom: none; font-weight: 600; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; color: $color-text-primary; text-align: right; }
  .total { color: $color-primary; font-size: 14px; }
}
.budget-bar {
  height: 6px;
  background: $color-bg;
  border-radius: 3px;
  overflow: hidden;
  .fill {
    height: 100%;
    background: $gradient-brand;
    border-radius: 3px;
  }
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
