<script setup lang="ts">
/**
 * AdminRole · 角色权限（无 design，按 R9 自造权限矩阵 pattern）
 * - 4 KPI（角色总数/启用/用户绑定/权限项）
 * - 左：6 角色列表（带用户数 + 内置 tag）
 * - 右：选中角色的权限矩阵（8 模块 × 8 操作：增/删/改/查/审批/导入/导出/配置）
 * - 底部 sticky 保存栏
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

// 模块定义
interface ModuleDef { key: string; label: string; icon: string; ops: string[] }
const moduleDefs: ModuleDef[] = [
  { key: 'dashboard',  label: '工作台',   icon: '▦', ops: ['查'] },
  { key: 'project',    label: '项目管理', icon: '▥', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'contract',   label: '合同管理', icon: '▤', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'expense',    label: '销售费用', icon: '▣', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'receivable', label: '回款管理', icon: '▩', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'invoice',    label: '发票管理', icon: '▢', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'ai',         label: 'AI 中心',  icon: '✦', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'admin',      label: '系统管理', icon: '⚙', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
]

// 所有操作（矩阵表头）
const allOps = ['增', '删', '改', '查', '审批', '导入', '导出', '配置']

// 4 KPI
const kpis = ref([
  { label: '角色总数', num: 6,  color: 'info',    icon: '👥', trend: '↑ 1 较上月' },
  { label: '启用角色', num: 6,  color: 'success', icon: '✓',  trend: '全部启用' },
  { label: '用户绑定', num: 57, color: 'warning', icon: '🔗', trend: '覆盖率 100%' },
  { label: '权限项',   num: 56, color: 'primary', icon: '🔑', trend: '8 模块 × 8 操作' },
])

// 角色列表
const roles = ref<any[]>([])
const selectedRoleId = ref<number | null>(null)
const checkedIds = ref<string[]>([])

const selectedRole = computed(() => roles.value.find(r => r.id === selectedRoleId.value) || null)
const totalPerms = computed(() => checkedIds.value.length)

function isPermChecked(moduleKey: string, op: string): boolean {
  return checkedIds.value.includes(`${moduleKey}.${op}`)
}

function isModuleAllChecked(moduleKey: string): boolean {
  const m = moduleDefs.find(x => x.key === moduleKey)
  if (!m) return false
  return m.ops.every(op => checkedIds.value.includes(`${moduleKey}.${op}`))
}

function isModulePartialChecked(moduleKey: string): boolean {
  const m = moduleDefs.find(x => x.key === moduleKey)
  if (!m) return false
  const checked = m.ops.filter(op => checkedIds.value.includes(`${moduleKey}.${op}`)).length
  return checked > 0 && checked < m.ops.length
}

function toggleModule(moduleKey: string) {
  const m = moduleDefs.find(x => x.key === moduleKey)
  if (!m) return
  const allChecked = isModuleAllChecked(moduleKey)
  m.ops.forEach(op => {
    const id = `${moduleKey}.${op}`
    if (allChecked) {
      checkedIds.value = checkedIds.value.filter(x => x !== id)
    } else {
      if (!checkedIds.value.includes(id)) checkedIds.value.push(id)
    }
  })
}

function toggleOp(moduleKey: string, op: string) {
  const id = `${moduleKey}.${op}`
  const i = checkedIds.value.indexOf(id)
  if (i >= 0) checkedIds.value.splice(i, 1)
  else checkedIds.value.push(id)
}

async function loadRoles() {
  const res = await adminApi.roleList().catch(() => null)
  roles.value = ((res as any)?.list as any[]) || mockRoles
  if (!selectedRoleId.value && roles.value.length) {
    selectedRoleId.value = roles.value[0].id
    loadPermissions(roles.value[0])
  }
}

function selectRole(r: any) {
  selectedRoleId.value = r.id
  loadPermissions(r)
}

// 后端 Permission.code 格式："<resource>:<action>"，与前端矩阵 "<moduleKey>.<op>" 不一致
// 双向映射：后端 -> 前端（用于读取渲染），前端 -> 后端（用于保存）
// action 集合：read/write/delete/approve/upload/submit/verify/export/extract/ask/risk_scan/model_manage
const BACK_TO_FRONT_OP: Record<string, string[]> = {
  read:        ['查'],
  write:       ['增', '改', '配置'],
  delete:      ['删'],
  approve:     ['审批'],
  upload:      ['导入'],
  submit:      ['导入'],
  verify:      ['配置'],
  export:      ['导出'],
  extract:     ['配置'],
  ask:         ['配置'],
  risk_scan:   ['配置'],
  model_manage:['配置'],
}
// 资源名 (后端 resource) -> 前端模块 key。两者基本一致，只对 admin 做个映射（admin 资源不存在）
const RESOURCE_TO_MODULE: Record<string, string> = {
  dashboard:  'dashboard',
  project:    'project',
  contract:   'contract',
  expense:    'expense',
  receivable: 'receivable',
  invoice:    'invoice',
  template:   'invoice',   // 发票模板归到发票模块
  milestone:  'project',   // 里程碑归到项目
  ai:         'ai',
  user:       'admin',     // 用户管理归到系统管理
  audit:      'admin',     // 审计日志归到系统管理
}

function backendPermsToFrontIds(perms: string[]): string[] {
  const out: string[] = []
  for (const code of perms) {
    const idx = code.indexOf(':')
    if (idx < 0) continue
    const resource = code.slice(0, idx)
    const action = code.slice(idx + 1)
    const moduleKey = RESOURCE_TO_MODULE[resource]
    const ops = BACK_TO_FRONT_OP[action]
    if (!moduleKey || !ops) continue
    for (const op of ops) {
      const id = `${moduleKey}.${op}`
      if (!out.includes(id)) out.push(id)
    }
  }
  return out
}

function loadPermissions(role: any) {
  // 优先从后端返回的 permissions 字段取
  if (role.permissions && Array.isArray(role.permissions) && role.permissions.length) {
    checkedIds.value = backendPermsToFrontIds(role.permissions)
  } else {
    // 从 mockPerms 取（仅在后端未返回时兜底，mock 格式保持前端原始形态）
    const key = role.code || ''
    checkedIds.value = mockPerms[key] || ['dashboard.查']
  }
}

async function onSave() {
  if (!selectedRole.value) return
  const role = selectedRole.value
  const codes = new Set<string>()
  codes.add('dashboard:read')
  // 前端 op -> 后端 action（与 BACK_TO_FRONT_OP 严格对应）
  const FRONT_TO_BACK: Record<string, string> = {
    '增': 'write', '删': 'delete', '改': 'write', '查': 'read',
    '审批': 'approve', '导入': 'upload', '导出': 'export', '配置': 'write',
  }
  for (const id of checkedIds.value) {
    const [moduleKey, op] = id.split('.')
    if (!moduleKey) continue
    const action = FRONT_TO_BACK[op]
    if (action) codes.add(`${moduleKey}:${action}`)
  }
  const r: any = await adminApi.roleUpdate(role.id, {
    name: role.name, description: role.desc, dataScope: role.dataScope || 'self',
    permissionCodes: Array.from(codes),
  } as any).catch((e: any) => ({ message: e?.message || '网络错误' }))
  if (r?.code === 0 || r?.id) {
    ElMessage.success(`已保存「${role.name}」的权限配置（共 ${totalPerms.value} 项）`)
  } else {
    ElMessage.error(r?.message || '保存失败')
  }
}

async function onNewRole() {
  try {
    const { value } = await ElMessageBox.prompt('请输入新角色名称', '新建角色', { inputPattern: /.+/, inputErrorMessage: '角色名不能为空' })
    const code = value.toLowerCase().replace(/\s+/g, '_')
    const r: any = await adminApi.roleCreate({ code, name: value, description: '新建角色' }).catch(() => null)
    if (r?.code === 0 || r?.id) {
      const newRole = r.data || r
      roles.value.push({ ...newRole, desc: newRole.description, builtin: false, userCount: 0 })
      ElMessage.success(`已创建角色「${value}」`)
    } else {
      ElMessage.error(r?.message || '创建失败')
    }
  } catch {}
}

async function onDeleteRole() {
  if (!selectedRole.value) return
  const r = selectedRole.value
  if (r.builtin) return ElMessage.warning('系统内置角色不可删除')
  try {
    await ElMessageBox.confirm(`确定删除角色「${r.name}」？关联用户将失去此角色。`, '删除角色', { type: 'warning' })
    const res: any = await adminApi.roleDelete(r.id).catch(() => null)
    if (res?.code === 0 || res?.deleted) {
      roles.value = roles.value.filter(x => x.id !== r.id)
      selectedRoleId.value = roles.value[0]?.id ?? null
      if (roles.value[0]) loadPermissions(roles.value[0])
      ElMessage.success('已删除')
    } else {
      ElMessage.error(res?.message || '删除失败')
    }
  } catch {}
}

onMounted(loadRoles)

// mock
const mockRoles: any[] = [
  { id: 1, code: 'super_admin', name: '超级管理员', userCount: 2,  desc: '系统最高权限,可管理全部功能与配置', builtin: true,  dataScope: 'all' },
  { id: 2, code: 'admin',       name: '管理员',     userCount: 5,  desc: '业务配置+审批,不含系统级操作',      builtin: true,  dataScope: 'all' },
  { id: 3, code: 'finance',     name: '财务',       userCount: 8,  desc: '费用/回款/发票全流程 + 审批',       builtin: false, dataScope: 'dept' },
  { id: 4, code: 'sales',       name: '销售',       userCount: 12, desc: '客户/合同/回款录入,无审批权限',     builtin: false, dataScope: 'dept' },
  { id: 5, code: 'salesman',    name: '业务员',     userCount: 24, desc: '仅查看自己的项目/合同/回款',         builtin: false, dataScope: 'self' },
  { id: 6, code: 'guest',       name: '访客',       userCount: 6,  desc: '只读,无任何写权限',                  builtin: false, dataScope: 'self' },
]

const mockPerms: Record<string, string[]> = {
  super_admin: [
    'dashboard.查',
    'project.增','project.删','project.改','project.查','project.审批','project.导入','project.导出','project.配置',
    'contract.增','contract.删','contract.改','contract.查','contract.审批','contract.导入','contract.导出','contract.配置',
    'expense.增','expense.删','expense.改','expense.查','expense.审批','expense.导入','expense.导出','expense.配置',
    'receivable.增','receivable.删','receivable.改','receivable.查','receivable.审批','receivable.导入','receivable.导出','receivable.配置',
    'invoice.增','invoice.删','invoice.改','invoice.查','invoice.审批','invoice.导入','invoice.导出','invoice.配置',
    'ai.增','ai.删','ai.改','ai.查','ai.审批','ai.导入','ai.导出','ai.配置',
    'admin.增','admin.删','admin.改','admin.查','admin.审批','admin.导入','admin.导出','admin.配置',
  ],
  admin: [
    'dashboard.查',
    'project.增','project.改','project.查','project.审批',
    'contract.增','contract.改','contract.查','contract.审批','contract.导出',
    'expense.增','expense.改','expense.查','expense.审批','expense.导出',
    'receivable.增','receivable.改','receivable.查','receivable.审批','receivable.导出',
    'invoice.增','invoice.改','invoice.查','invoice.导入','invoice.导出',
    'ai.增','ai.改','ai.查',
  ],
  finance: [
    'dashboard.查',
    'project.查',
    'contract.查','contract.导出',
    'expense.增','expense.改','expense.查','expense.审批','expense.导出',
    'receivable.增','receivable.改','receivable.查','receivable.审批','receivable.导出',
    'invoice.增','invoice.改','invoice.查','invoice.导入','invoice.导出',
    'ai.增','ai.查',
  ],
  sales: [
    'dashboard.查',
    'project.增','project.改','project.查',
    'contract.增','contract.改','contract.查',
    'expense.增','expense.查',
    'receivable.增','receivable.改','receivable.查',
    'invoice.查',
  ],
  salesman: [
    'dashboard.查',
    'project.查',
    'contract.查',
    'expense.查',
    'receivable.查',
  ],
  guest: ['dashboard.查'],
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>🔑 角色权限</h1>
        <p class="page-desc">管理角色及其功能权限，按业务模块矩阵展示</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" @click="onDeleteRole" v-if="selectedRole && !selectedRole.builtin">🗑 删除角色</button>
        <button class="btn btn-primary btn-sm" @click="onNewRole">+ 新建角色</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-head">
          <span class="kpi-label">{{ k.label }}</span>
          <span :class="['kpi-icon', k.color]">{{ k.icon }}</span>
        </div>
        <div class="kpi-num">{{ k.num }}<span v-if="k.label === '权限项'" class="unit">项</span><span v-else-if="k.label === '用户绑定'" class="unit">人</span></div>
        <div class="kpi-trend">{{ k.trend }}</div>
      </div>
    </div>

    <!-- 主体：左角色列表 + 右权限矩阵 -->
    <div class="role-layout">
      <!-- 左：角色列表 -->
      <div class="role-list">
        <div class="rl-head">角色列表（{{ roles.length }}）</div>
        <div class="rl-body">
          <div v-for="r in roles" :key="r.id" :class="['rl-item', { active: selectedRoleId === r.id }]" @click="selectRole(r)">
            <div class="rli-avatar">{{ r.name.charAt(0) }}</div>
            <div class="rli-body">
              <div class="rli-name">
                {{ r.name }}
                <span v-if="r.builtin" class="builtin-tag">内置</span>
              </div>
              <div class="rli-desc">{{ r.desc }}</div>
              <div class="rli-meta">
                <span class="rli-count">{{ r.userCount }} 人</span>
                <span class="rli-scope">数据范围: {{ r.dataScope === 'all' ? '全部' : r.dataScope === 'dept' ? '本部门' : '本人' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：权限矩阵 -->
      <div class="perm-panel" v-if="selectedRole">
        <div class="pp-head">
          <div>
            <h3>{{ selectedRole.name }} · 权限配置</h3>
            <div class="pp-meta">
              <span>已选 <b class="primary">{{ totalPerms }}</b> 项</span>
              <span>·</span>
              <span>{{ selectedRole.desc }}</span>
            </div>
          </div>
        </div>
        <div class="tip-box">
          <div class="ico">i</div>
          <div>勾选单元格即代表该角色拥有对应操作权限。点击模块名可一键全选/全取消该模块所有操作。</div>
        </div>

        <div class="perm-card">
          <table class="perm-table">
            <thead>
              <tr>
                <th class="th-module">模块 / 操作</th>
                <th v-for="op in allOps" :key="op" class="th-op">{{ op }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in moduleDefs" :key="m.key">
                <td class="td-module">
                  <div class="module-name" :class="{ all: isModuleAllChecked(m.key), partial: isModulePartialChecked(m.key) }" @click="toggleModule(m.key)">
                    <span class="module-icon">{{ m.icon }}</span>
                    <span class="module-label">{{ m.label }}</span>
                    <span v-if="isModuleAllChecked(m.key)" class="module-check">✓</span>
                  </div>
                </td>
                <td v-for="op in allOps" :key="op" class="td-op">
                  <label v-if="m.ops.includes(op)" :class="['checkbox', { checked: isPermChecked(m.key, op) }]">
                    <input type="checkbox" :checked="isPermChecked(m.key, op)" @change="toggleOp(m.key, op)" />
                    <span class="cb-mark">{{ isPermChecked(m.key, op) ? '✓' : '' }}</span>
                  </label>
                  <span v-else class="op-empty">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="perm-panel empty-panel">
        <div class="empty-icon">👈</div>
        <div class="empty-text">请从左侧选择一个角色</div>
      </div>
    </div>

    <!-- sticky 保存栏 -->
    <div v-if="selectedRole" class="form-foot">
      <div class="ff-info">
        正在编辑: <b>{{ selectedRole.name }}</b>
        · 共 <b class="primary">{{ totalPerms }}</b> 项权限
      </div>
      <div class="ff-actions">
        <button class="btn btn-outline btn-sm" @click="onDeleteRole" v-if="!selectedRole.builtin">🗑 删除</button>
        <button class="btn btn-primary btn-sm" @click="onSave">💾 保存权限</button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// KPI
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 14px 18px; }
.kpi-card.primary { border-left-color: $color-primary; }
.kpi-card.info    { border-left-color: #64748B; }
.kpi-card.success { border-left-color: $color-success; }
.kpi-card.warning { border-left-color: #F59E0B; }
.kpi-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; }
.kpi-icon { width: 22px; height: 22px; border-radius: $radius-sm; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.kpi-icon.primary { background: $color-primary-bg; color: $color-primary; }
.kpi-icon.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.kpi-icon.success { background: $color-success-bg; color: $color-success; }
.kpi-icon.warning { background: rgba(245, 158, 11, 0.12); color: #F59E0B; }
.kpi-num { font-size: 24px; font-weight: 700; line-height: 1.2; color: $color-text-primary; .unit { font-size: 12px; color: $color-text-tertiary; font-weight: 400; margin-left: 4px; } }
.kpi-trend { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

// 主体
.role-layout { display: grid; grid-template-columns: 280px 1fr; gap: 16px; align-items: start; @media (max-width: 900px) { grid-template-columns: 1fr; } }

// 左：角色列表
.role-list { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; position: sticky; top: 16px; }
.rl-head { padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF; font-size: 13px; font-weight: 600; color: $color-text-primary; }
.rl-body { padding: 8px; max-height: 700px; overflow-y: auto; }
.rl-item { display: flex; gap: 10px; padding: 12px; border-radius: $radius-md; cursor: pointer; transition: all 0.15s; margin-bottom: 4px; border: 1px solid transparent; &:hover { background: $color-bg; } &.active { background: $color-primary-bg; border-color: $color-primary; } }
.rli-avatar { width: 36px; height: 36px; border-radius: 50%; background: $gradient-brand; color: #fff; display: grid; place-items: center; font-size: 14px; font-weight: 600; flex-shrink: 0; }
.rl-item.active .rli-avatar { background: $gradient-brand; }
.rli-body { flex: 1; min-width: 0; }
.rli-name { font-size: 13px; font-weight: 600; color: $color-text-primary; display: flex; align-items: center; gap: 4px; }
.builtin-tag { font-size: 9.5px; padding: 1px 5px; background: rgba(148, 163, 184, 0.15); color: #64748B; border-radius: 9999px; font-weight: 500; }
.rli-desc { font-size: 11.5px; color: $color-text-secondary; line-height: 1.5; margin: 4px 0; }
.rli-meta { display: flex; gap: 8px; font-size: 11px; color: $color-text-tertiary; flex-wrap: wrap; }
.rli-count { color: $color-primary; font-weight: 600; }

// 右：权限矩阵
.perm-panel { display: flex; flex-direction: column; gap: 12px; }
.pp-head h3 { font-size: 15px; font-weight: 600; margin: 0 0 4px 0; }
.pp-meta { font-size: 12px; color: $color-text-secondary; display: flex; gap: 6px; align-items: center; .primary { color: $color-primary; font-weight: 600; } }
.tip-box { display: flex; gap: 10px; padding: 10px 14px; background: rgba(79, 107, 255, 0.05); border: 1px solid rgba(79, 107, 255, 0.2); border-radius: $radius-md; font-size: 12.5px; color: $color-text-secondary; line-height: 1.6; .ico { color: $color-primary; font-size: 16px; flex-shrink: 0; } }
.perm-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.perm-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.perm-table th, .perm-table td { padding: 0; border-bottom: 1px solid $color-border; border-right: 1px solid $color-border; &:last-child { border-right: none; } }
.perm-table th { padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; }
.th-module { width: 180px; text-align: left; }
.th-op { width: 80px; text-align: center; }
.td-module { padding: 0 !important; }
.td-op { text-align: center; height: 44px; vertical-align: middle; }
.module-name { display: flex; align-items: center; gap: 8px; padding: 10px 12px; cursor: pointer; transition: all 0.15s; user-select: none; &:hover { background: $color-bg; } &.all { color: $color-primary; font-weight: 600; .module-icon { background: $color-primary-bg; color: $color-primary; } } &.partial { color: $color-primary; .module-icon { background: $color-primary-bg; color: $color-primary; } } }
.module-icon { width: 24px; height: 24px; border-radius: $radius-sm; background: $color-bg; color: $color-text-secondary; display: grid; place-items: center; font-size: 12px; flex-shrink: 0; }
.module-label { flex: 1; font-size: 12.5px; }
.module-check { font-size: 11px; color: $color-primary; font-weight: 700; }

.checkbox { display: inline-flex; align-items: center; justify-content: center; cursor: pointer; input { display: none; } .cb-mark { width: 18px; height: 18px; border-radius: 4px; border: 1.5px solid $color-border; display: grid; place-items: center; font-size: 12px; color: transparent; transition: all 0.15s; } &.checked .cb-mark { background: $gradient-brand; border-color: transparent; color: #fff; } &:hover .cb-mark { border-color: $color-primary; } }
.op-empty { color: $color-border-strong; font-size: 12px; }

// empty
.empty-panel { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; background: #fff; border: 1px dashed $color-border; border-radius: $radius-lg; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.5; }
.empty-text { font-size: 13px; color: $color-text-tertiary; }

// sticky form-foot
.form-foot { position: sticky; bottom: 0; background: #fff; border-top: 1px solid $color-border; padding: 12px 16px; margin-top: 16px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.04); z-index: 10; }
.ff-info { font-size: 13px; color: $color-text-secondary; .primary { color: $color-primary; } }
.ff-actions { display: flex; gap: 8px; }
</style>
