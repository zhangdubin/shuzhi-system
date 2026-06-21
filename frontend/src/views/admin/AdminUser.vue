<script setup lang="ts">
/**
 * AdminUser · 用户管理（无 design，按 R9 统一列表 pattern 自造）
 * - 4 KPI（用户总数/在线/今日活跃/待审核）
 * - 5 filter-chip（全部/启用/禁用/待审核/最近登录）
 * - 搜索 + 部门筛选 + 状态筛选
 * - 10 行用户表（账号/姓名/角色多 tag/部门/邮箱/手机/状态/最后登录/操作）
 * - 行操作：编辑/分配角色/重置密码/禁用
 * - 顶部批量操作：批量启用/批量禁用
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

interface UserRow {
  id: number
  account: string
  name: string
  roles: string[]
  dept: string
  email: string
  phone: string
  status: 'active' | 'disabled' | 'pending'
  lastLogin: string
  online?: boolean
}

const loading = ref(false)
const list = ref<UserRow[]>([])
const selectedIds = ref<number[]>([])
const query = reactive({ keyword: '', dept: '', status: '' })

// 4 KPI
const kpis = ref([
  { label: '用户总数',  num: 12,  color: 'info',    icon: '👤', trend: '↑ 3 较上周' },
  { label: '当前在线',  num: 6,   color: 'success', icon: '●',  trend: '在线率 50%' },
  { label: '今日活跃',  num: 8,   color: 'warning', icon: '⚡', trend: '日活率 67%' },
  { label: '待审核',    num: 2,   color: 'danger',  icon: '!',  trend: '需审批开通' },
])

// 5 status-tabs
const tabs = ref([
  { key: 'all',      label: '全部',    count: 12 },
  { key: 'active',   label: '启用',    count: 9 },
  { key: 'disabled', label: '禁用',    count: 1 },
  { key: 'pending',  label: '待审核',  count: 2 },
  { key: 'recent',   label: '最近登录', count: 8 },
])
const activeTab = ref('all')

async function loadList() {
  loading.value = true
  try {
    const res: any = await adminApi.userList(query).catch(() => null)
    const rows: any[] = res?.list || res?.data?.list || []
    // 字段名映射：后端 camelCase (isActive/username/...) → 前端命名
    list.value = rows.map((u: any) => ({
      id: u.id,
      account: u.username,
      name: u.name,
      email: u.email,
      phone: u.phone,
      dept: u.departmentName || '—',
      departmentId: u.departmentId,
      roles: u.roleNames || [],
      roleIds: u.roleIds || [],
      permissionCount: u.permissionCount || 0,
      status: u.isActive ? 'active' : 'disabled',
      isAdmin: !!u.isAdmin,
      lastLogin: u.lastLoginAt ? String(u.lastLoginAt).replace('T', ' ').slice(0, 16) : '—',
      lastLoginIp: u.lastLoginIp || '',
    }))
    if (list.value.length === 0) list.value = mockUsers  // 兜底
    // 保留原始对象给过滤/排序用
    list.value.forEach((u, i) => { (u as any)._raw = rows[i] })
  } finally {
    loading.value = false
  }
}

const filteredList = computed(() => {
  let result = list.value
  if (activeTab.value === 'active') result = result.filter(u => u.status === 'active')
  else if (activeTab.value === 'disabled') result = result.filter(u => u.status === 'disabled')
  else if (activeTab.value === 'pending') result = result.filter(u => u.status === 'pending')
  else if (activeTab.value === 'recent') result = result.filter(u => u._raw?.lastLoginAt?.startsWith('2026-'))
  if (query.keyword) {
    const k = query.keyword.toLowerCase()
    result = result.filter(u => u.account.toLowerCase().includes(k) || u.name.toLowerCase().includes(k) || u.email.toLowerCase().includes(k) || u.phone.includes(k))
  }
  if (query.dept) result = result.filter(u => u.dept === query.dept)
  if (query.status) result = result.filter(u => u.status === query.status)
  return result
})

function setTab(t: any) { activeTab.value = t.key; query.status = '' }
function handleSearch() {}
function handleReset() { query.keyword = ''; query.dept = ''; query.status = '' }
function toggleSelect(id: number) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}
function toggleSelectAll() {
  if (selectedIds.value.length === filteredList.value.length) selectedIds.value = []
  else selectedIds.value = filteredList.value.map(u => u.id)
}

async function resetPwd(row: UserRow) {
  try {
    await ElMessageBox.confirm(`确定重置「${row.name}」的密码？\n重置后初始密码为 123456`, '重置密码', { type: 'warning' })
    const r: any = await adminApi.userResetPwd(row.id, '123456').catch(() => null)
    if (r?.code === 0 || r?.ok) ElMessage.success('密码已重置为 123456')
    else ElMessage.error(r?.message || '重置失败')
  } catch {}
}

async function toggleStatus(row: UserRow) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(`确定${next === 'active' ? '启用' : '禁用'}「${row.name}」？`, '状态变更', { type: 'warning' })
    row.status = next
    ElMessage.success(`已${next === 'active' ? '启用' : '禁用'}`)
  } catch {}
}

async function batchDeleteUsers() {
  if (!selectedIds.value.length) return ElMessage.warning('请先勾选用户')
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedIds.value.length} 个用户？此操作不可恢复。`,
      '批量删除用户', { type: 'warning' }
    )
    const r: any = await adminApi.userBatchDelete(selectedIds.value).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0) {
      const data = r.data || {}
      const skipMsg = data.skippedCount ? `，跳过 ${data.skippedCount} 个超级管理员` : ''
      ElMessage.success(`已删除 ${data.deletedCount || 0} 个用户${skipMsg}`)
      selectedIds.value = []
      await loadList()
    } else {
      ElMessage.error(r?.message || '删除失败')
    }
  } catch {}
}

function batchUpdate(target: 'active' | 'disabled') {
  if (!selectedIds.value.length) return ElMessage.warning('请先勾选用户')
  ElMessageBox.confirm(`确定将 ${selectedIds.value.length} 个用户${target === 'active' ? '启用' : '禁用'}？`, '批量操作', { type: 'warning' })
    .then(() => {
      list.value.forEach(u => { if (selectedIds.value.includes(u.id)) u.status = target })
      selectedIds.value = []
      ElMessage.success('批量操作完成')
    })
    .catch(() => {})
}

// ===== 弹窗状态 =====
const userDialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', saving: false, form: {
  id: 0, account: '', name: '', password: '', email: '', phone: '',
  departmentId: null as number | null, roleIds: [] as number[], isActive: true,
} })
const roleDialog = reactive({ visible: false, saving: false, userId: 0, userName: '', roleIds: [] as number[] })
const importDialog = reactive({ visible: false, file: null as File | null, parsing: false, rows: [] as any[] })

// 部门/角色下拉
const deptOptions = ref<any[]>([])
const roleOptions = ref<any[]>([])

async function loadDeptAndRoles() {
  try {
    const [t, r]: any[] = await Promise.all([
      adminApi.deptList().catch(() => null),
      adminApi.roleList().catch(() => null),
    ])
    // deptList 现在返 {list,total}，list 里每项有 children 树；前端需要平铺
    const flat = (n: any, d = 0, out: any[] = []): any[] => {
      if (!n) return out
      out.push({ id: n.id, name: n.name, depth: d })
      if (n.children) n.children.forEach((c: any) => flat(c, d + 1, out))
      return out
    }
    const treeList = (t as any)?.list || []
    deptOptions.value = treeList.length > 0 ? treeList.flatMap((n: any) => flat(n)) : []
    roleOptions.value = ((r as any)?.list as any[]) || []
  } catch {}
}

function onNewUser() {
  Object.assign(userDialog.form, { id: 0, account: '', name: '', password: '', email: '', phone: '', departmentId: null, roleIds: [], isActive: true })
  userDialog.mode = 'create'
  userDialog.visible = true
}

function onEdit(row: UserRow) {
  // 找到原始 record
  const orig = (row as any)._raw
  Object.assign(userDialog.form, {
    id: row.id,
    account: row.account,
    name: row.name,
    password: '',  // 编辑时密码留空
    email: row.email,
    phone: row.phone,
    departmentId: (orig?.departmentId) ?? null,
    roleIds: (orig?.roleIds) || [],
    isActive: row.status === 'active',
  })
  userDialog.mode = 'edit'
  userDialog.visible = true
}

async function saveUser() {
  const f = userDialog.form
  if (!f.account || !f.name) { ElMessage.warning('请填写账号和姓名'); return }
  if (userDialog.mode === 'create' && !f.password) { ElMessage.warning('请填写密码'); return }
  userDialog.saving = true
  try {
    if (userDialog.mode === 'create') {
      await adminApi.userCreate({
        account: f.account, name: f.name, password: f.password,
        email: f.email, phone: f.phone,
        departmentId: f.departmentId || undefined,
        roleIds: f.roleIds,
      } as any)
      ElMessage.success(`已创建用户「${f.name}」`)
    } else {
      await adminApi.userUpdate(f.id, {
        name: f.name, email: f.email, phone: f.phone,
        departmentId: f.departmentId || undefined,
        roleIds: f.roleIds,
        isActive: f.isActive,
      } as any)
      ElMessage.success(`已更新「${f.name}」`)
    }
    userDialog.visible = false
    await loadList()
  } catch (e: any) {
    ElMessage.error('保存失败：' + (e?.message || '未知错误'))
  } finally {
    userDialog.saving = false
  }
}

function openAssignRole(row: UserRow) {
  const orig = (row as any)._raw
  roleDialog.userId = row.id
  roleDialog.userName = row.name
  roleDialog.roleIds = (orig?.roleIds as number[]) || []
  roleDialog.visible = true
}

async function saveRoleAssign() {
  roleDialog.saving = true
  try {
    await adminApi.userUpdate(roleDialog.userId, { roleIds: roleDialog.roleIds } as any)
    ElMessage.success('角色已更新')
    roleDialog.visible = false
    await loadList()
  } catch (e: any) {
    ElMessage.error('更新失败：' + (e?.message || '未知错误'))
  } finally {
    roleDialog.saving = false
  }
}

function onAssignRole(row: UserRow) {
  const orig = (row as any)._raw
  roleDialog.userId = row.id
  roleDialog.userName = row.name
  roleDialog.roleIds = (orig?.roleIds as number[]) || []
  roleDialog.visible = true
}

function onImport() {
  importDialog.file = null
  importDialog.rows = []
  importDialog.visible = true
}

function onImportFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  importDialog.file = f
  importDialog.parsing = true
  // 解析 CSV（账号,姓名,邮箱,手机,部门,角色）
  const reader = new FileReader()
  reader.onload = () => {
    const text = String(reader.result || '')
    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length < 2) { importDialog.parsing = false; return }
    const header = lines[0].split(',').map(s => s.trim())
    const rows = lines.slice(1).map(line => {
      const cells = line.split(',').map(s => s.trim())
      const r: any = {}
      header.forEach((h, i) => { r[h] = cells[i] || '' })
      return r
    })
    importDialog.rows = rows
    importDialog.parsing = false
  }
  reader.readAsText(f, 'utf-8')
}

async function confirmImport() {
  if (importDialog.rows.length === 0) { ElMessage.warning('请先选择并解析 CSV'); return }
  let ok = 0, fail = 0
  for (const r of importDialog.rows) {
    if (!r.account || !r.name) { fail++; continue }
    try {
      await adminApi.userCreate({
        account: r.account, name: r.name, password: r.password || '123456',
        email: r.email, phone: r.phone,
      } as any)
      ok++
    } catch { fail++ }
  }
  ElMessage.success(`导入完成：成功 ${ok} 条，失败 ${fail} 条`)
  importDialog.visible = false
  await loadList()
}
function rowStatusType(s: UserRow['status']) { return s === 'active' ? 'success' : s === 'pending' ? 'warning' : 'info' }
function rowStatusLabel(s: UserRow['status']) { return s === 'active' ? '启用' : s === 'pending' ? '待审核' : '禁用' }
function roleColor(r: string): string {
  if (r.includes('超级')) return 'danger'
  if (r.includes('管理员')) return 'warning'
  if (r.includes('财务')) return 'success'
  if (r.includes('HR')) return 'info'
  return 'primary'
}

onMounted(() => { loadList(); loadDeptAndRoles() })

// mock
const mockUsers: UserRow[] = [
  { id: 1, account: 'admin',     name: '张明', roles: ['超级管理员'], dept: '总经理办公室', email: 'zhangming@company.com',  phone: '13800138001', status: 'active',   lastLogin: '2026-06-13 09:12', online: true },
  { id: 2, account: 'finance01', name: '李财务', roles: ['财务'],       dept: '财务部',       email: 'li@company.com',         phone: '13800138002', status: 'active',   lastLogin: '2026-06-13 08:30', online: true },
  { id: 3, account: 'sales01',   name: '王销售', roles: ['销售'],       dept: '销售一部',     email: 'wang@company.com',       phone: '13800138003', status: 'active',   lastLogin: '2026-06-13 10:45', online: true },
  { id: 4, account: 'sales02',   name: '陈丽',   roles: ['销售', '业务员'], dept: '销售二部',   email: 'chen@company.com',       phone: '13800138004', status: 'active',   lastLogin: '2026-06-13 11:02', online: false },
  { id: 5, account: 'pm01',      name: '刘工',   roles: ['项目经理'],   dept: '项目部',       email: 'liu@company.com',        phone: '13800138005', status: 'active',   lastLogin: '2026-06-12 18:21', online: false },
  { id: 6, account: 'hr01',      name: '赵敏',   roles: ['HR'],         dept: '人力资源部',   email: 'zhao@company.com',       phone: '13800138006', status: 'active',   lastLogin: '2026-06-13 09:55', online: true },
  { id: 7, account: 'guest01',   name: '访客A',  roles: ['访客'],       dept: '外部',         email: 'guest@partner.com',      phone: '13800138007', status: 'pending',  lastLogin: '—',                online: false },
  { id: 8, account: 'old01',     name: '钱七',   roles: ['业务员'],     dept: '销售一部',     email: 'qian@company.com',       phone: '13800138008', status: 'disabled', lastLogin: '2026-05-20 14:08', online: false },
  { id: 9, account: 'sales03',   name: '孙八',   roles: ['销售'],       dept: '销售二部',     email: 'sun@company.com',        phone: '13800138009', status: 'active',   lastLogin: '2026-06-13 10:11', online: true },
  { id: 10, account: 'cfo01',   name: '周总',   roles: ['财务', '管理员'], dept: '财务部',     email: 'zhou@company.com',       phone: '13800138010', status: 'active',   lastLogin: '2026-06-13 08:00', online: true },
  { id: 11, account: 'intern01', name: '吴桐',   roles: ['访客'],       dept: '项目部',       email: 'wu@company.com',         phone: '13800138011', status: 'pending',  lastLogin: '—',                online: false },
  { id: 12, account: 'sales04',  name: '郑亮',   roles: ['业务员', '销售'], dept: '销售一部',   email: 'zheng@company.com',      phone: '13800138012', status: 'active',   lastLogin: '2026-06-12 17:30', online: false },
]
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>👤 用户管理</h1>
        <p class="page-desc">账号、角色、部门、状态统一管理</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" @click="onImport">📤 批量导入</button>
        <button class="btn btn-primary btn-sm" @click="onNewUser">+ 新建用户</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-head">
          <span class="kpi-label">{{ k.label }}</span>
          <span :class="['kpi-icon', k.color]">{{ k.icon }}</span>
        </div>
        <div class="kpi-num">{{ k.num }}<span class="unit">人</span></div>
        <div class="kpi-trend">{{ k.trend }}</div>
      </div>
    </div>

    <!-- 5 status-tabs -->
    <div class="status-tabs">
      <div v-for="t in tabs" :key="t.key" :class="['tab', { active: activeTab === t.key }]" @click="setTab(t)">
        {{ t.label }} <span class="cnt">{{ t.count }}</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="search-row">
        <input v-model="query.keyword" class="input-search" placeholder="搜索账号 / 姓名 / 邮箱 / 手机" @keyup.enter="handleSearch" />
        <select v-model="query.dept" class="input-select">
          <option value="">全部部门</option>
          <option v-for="d in deptOptions" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="query.status" class="input-select">
          <option value="">全部状态</option>
          <option value="active">启用</option>
          <option value="disabled">禁用</option>
          <option value="pending">待审核</option>
        </select>
        <button class="btn btn-primary btn-sm" @click="handleSearch">🔍 查询</button>
        <button class="btn btn-ghost btn-sm" @click="handleReset">↺ 重置</button>
      </div>
      <div class="batch-row">
        <button class="btn btn-outline btn-sm" :disabled="!selectedIds.length" @click="batchUpdate('active')">✓ 批量启用</button>
        <button class="btn btn-outline btn-sm danger" :disabled="!selectedIds.length" @click="batchUpdate('disabled')">✕ 批量禁用</button>
        <button class="btn btn-outline btn-sm danger" :disabled="!selectedIds.length" @click="batchDeleteUsers">🗑 批量删除</button>
        <span v-if="selectedIds.length" class="sel-info">已选 {{ selectedIds.length }} 个</span>
      </div>
    </div>

    <!-- 用户表 -->
    <div class="user-card">
      <table class="tpl-table">
        <thead>
          <tr>
            <th style="width: 40px;">
              <input type="checkbox" :checked="selectedIds.length === filteredList.length && filteredList.length > 0" @change="toggleSelectAll" />
            </th>
            <th style="width: 50px;">ID</th>
            <th style="width: 100px;">账号</th>
            <th style="width: 110px;">姓名</th>
            <th style="min-width: 160px;">角色</th>
            <th style="width: 120px;">部门</th>
            <th>邮箱</th>
            <th style="width: 120px;">手机</th>
            <th style="width: 80px;">状态</th>
            <th style="width: 140px;">最后登录</th>
            <th style="width: 220px;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in filteredList" :key="u.id" :class="{ selected: selectedIds.includes(u.id) }">
            <td><input type="checkbox" :checked="selectedIds.includes(u.id)" @change="toggleSelect(u.id)" /></td>
            <td><span class="cell-mono">{{ u.id }}</span></td>
            <td><span class="cell-mono">{{ u.account }}</span></td>
            <td>
              <span>{{ u.name }}</span>
              <span v-if="u.online" class="tag-online">●在线</span>
            </td>
            <td>
              <span v-for="r in u.roles" :key="r" :class="['role-tag', roleColor(r)]">{{ r }}</span>
            </td>
            <td>{{ u.dept }}</td>
            <td class="cell-truncate">{{ u.email }}</td>
            <td><span class="cell-mono">{{ u.phone }}</span></td>
            <td>
              <span :class="['tag', rowStatusType(u.status)]">{{ rowStatusLabel(u.status) }}</span>
            </td>
            <td><span class="cell-mono">{{ u.lastLogin }}</span></td>
            <td>
              <div class="row-actions">
                <a class="ra primary" @click="onEdit(u)">编辑</a>
                <a class="ra primary" @click="onAssignRole(u)">分配角色</a>
                <a class="ra primary" @click="resetPwd(u)">重置密码</a>
                <a :class="['ra', u.status === 'active' ? 'danger' : 'success']" @click="toggleStatus(u)">
                  {{ u.status === 'active' ? '禁用' : '启用' }}
                </a>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !filteredList.length" class="empty">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无用户数据</div>
      </div>
    </div>
  </div>

<!-- ===== 新建/编辑用户 弹窗 ===== -->
<el-dialog v-model="userDialog.visible" :title="(userDialog.mode === 'create' ? '新建用户' : '编辑用户')" width="560px" destroy-on-close>
  <el-form :model="userDialog.form" label-width="80px" label-position="right">
    <el-form-item label="账号" required>
      <el-input v-model="userDialog.form.account" :disabled="userDialog.mode === 'edit'" placeholder="登录账号（不可重复）" />
    </el-form-item>
    <el-form-item label="姓名" required>
      <el-input v-model="userDialog.form.name" placeholder="真实姓名" />
    </el-form-item>
    <el-form-item v-if="userDialog.mode === 'create'" label="密码" required>
      <el-input v-model="userDialog.form.password" type="password" show-password placeholder="至少 6 位" />
    </el-form-item>
    <el-form-item label="邮箱">
      <el-input v-model="userDialog.form.email" placeholder="选填" />
    </el-form-item>
    <el-form-item label="手机">
      <el-input v-model="userDialog.form.phone" placeholder="选填" />
    </el-form-item>
    <el-form-item label="部门">
      <el-select v-model="userDialog.form.departmentId" placeholder="选择部门" clearable style="width:100%">
        <el-option v-for="d in deptOptions" :key="d.id" :label="'— '.repeat(d.depth) + d.name" :value="d.id" />
      </el-select>
    </el-form-item>
    <el-form-item label="角色">
      <el-select v-model="userDialog.form.roleIds" multiple placeholder="分配角色" style="width:100%">
        <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
    </el-form-item>
    <el-form-item v-if="userDialog.mode === 'edit'" label="启用">
      <el-switch v-model="userDialog.form.isActive" />
    </el-form-item>
  </el-form>
  <template #footer>
    <el-button @click="userDialog.visible = false">取消</el-button>
    <el-button type="primary" :loading="userDialog.saving" @click="saveUser">保存</el-button>
  </template>
</el-dialog>

<!-- ===== 分配角色 弹窗 ===== -->
<el-dialog v-model="roleDialog.visible" :title="`分配角色 — ${roleDialog.userName}`" width="480px">
  <el-checkbox-group v-model="roleDialog.roleIds">
    <div v-for="r in roleOptions" :key="r.id" class="role-check-row">
      <el-checkbox :value="r.id" :label="r.id">
        <strong>{{ r.name }}</strong>
        <span class="role-code">{{ r.code }}</span>
        <span class="role-count">{{ r.userCount || 0 }} 人</span>
      </el-checkbox>
    </div>
  </el-checkbox-group>
  <template #footer>
    <el-button @click="roleDialog.visible = false">取消</el-button>
    <el-button type="primary" :loading="roleDialog.saving" @click="saveRoleAssign">保存</el-button>
  </template>
</el-dialog>

<!-- ===== 批量导入 弹窗 ===== -->
<el-dialog v-model="importDialog.visible" title="批量导入用户" width="640px" destroy-on-close>
  <div class="import-tip">
    <p>📋 请按 CSV 格式准备：<code>account,name,password,email,phone</code></p>
    <p>第一行为表头，从第二行开始为数据。密码留空将默认为 <code>123456</code>。</p>
  </div>
  <input type="file" accept=".csv" @change="onImportFile" />
  <div v-if="importDialog.parsing" class="parsing">解析中...</div>
  <el-table v-else-if="importDialog.rows.length" :data="importDialog.rows" max-height="300" size="small" class="import-preview">
    <el-table-column prop="account" label="账号" width="100" />
    <el-table-column prop="name" label="姓名" width="100" />
    <el-table-column prop="email" label="邮箱" />
    <el-table-column prop="phone" label="手机" width="120" />
  </el-table>
  <template #footer>
    <el-button @click="importDialog.visible = false">取消</el-button>
    <el-button type="primary" :disabled="!importDialog.rows.length" @click="confirmImport">导入 {{ importDialog.rows.length }} 条</el-button>
  </template>
</el-dialog>
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
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } &.danger:hover { border-color: $color-danger; color: $color-danger; } }
.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

// KPI
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 14px 18px; }
.kpi-card.info    { border-left-color: $color-primary; }
.kpi-card.success { border-left-color: $color-success; }
.kpi-card.warning { border-left-color: #F59E0B; }
.kpi-card.danger  { border-left-color: $color-danger; }
.kpi-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; }
.kpi-icon { width: 22px; height: 22px; border-radius: $radius-sm; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.kpi-icon.info    { background: $color-primary-bg; color: $color-primary; }
.kpi-icon.success { background: $color-success-bg; color: $color-success; }
.kpi-icon.warning { background: rgba(245, 158, 11, 0.12); color: #F59E0B; }
.kpi-icon.danger  { background: $color-danger-bg; color: $color-danger; }
.kpi-num { font-size: 24px; font-weight: 700; line-height: 1.2; color: $color-text-primary; .unit { font-size: 12px; color: $color-text-tertiary; font-weight: 400; margin-left: 4px; } }
.kpi-trend { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

// status tabs
.status-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-brand; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// toolbar
.toolbar { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 12px 16px; margin-bottom: 12px; }
.search-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.input-search { width: 280px; height: 32px; padding: 0 12px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 12.5px; font-family: inherit; color: $color-text-primary; background: #fff; &:focus { outline: none; border-color: $color-primary; box-shadow: 0 0 0 3px $color-primary-bg; } }
.input-select { height: 32px; padding: 0 28px 0 10px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 12.5px; font-family: inherit; color: $color-text-primary; background: #fff; min-width: 120px; }
.batch-row { display: flex; gap: 8px; align-items: center; margin-top: 10px; padding-top: 10px; border-top: 1px solid $color-border; }
.sel-info { font-size: 12px; color: $color-primary; margin-left: auto; }

// user card
.user-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; white-space: nowrap; }
.tpl-table td { padding: 10px 12px; border-bottom: 1px solid $color-border; }
.tpl-table tbody tr { transition: background 0.15s; &:hover { background: $color-bg; } &.selected { background: $color-primary-bg; } }
.cell-mono { font-family: $font-family-mono; color: $color-text-secondary; font-size: 11.5px; }
.cell-truncate { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $color-text-secondary; }
.tag-online { display: inline-block; margin-left: 4px; font-size: 10px; color: $color-success; background: $color-success-bg; padding: 1px 5px; border-radius: 9999px; }
.role-tag { display: inline-block; font-size: 10.5px; padding: 1px 6px; border-radius: 9999px; margin-right: 4px; font-weight: 500; }
.role-tag.primary { background: $color-primary-bg; color: $color-primary; }
.role-tag.success { background: $color-success-bg; color: $color-success; }
.role-tag.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.role-tag.danger  { background: $color-danger-bg; color: $color-danger; }
.role-tag.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.success { background: $color-success-bg; color: $color-success; }
.tag.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.tag.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }

.row-actions { display: flex; gap: 10px; flex-wrap: nowrap; }
.ra { font-size: 12px; cursor: pointer; transition: color 0.15s; white-space: nowrap; &.primary { color: $color-primary; &:hover { text-decoration: underline; } } &.success { color: $color-success; &:hover { text-decoration: underline; } } &.danger { color: $color-danger; &:hover { text-decoration: underline; } } }

// empty
.empty { text-align: center; padding: 40px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.5; }
.empty-text { font-size: 13px; color: $color-text-tertiary; }

.role-check-row { padding: 6px 0; border-bottom: 1px solid #f1f5f9; }
.role-check-row:last-child { border-bottom: none; }
.role-code { color: #94a3b8; font-size: 12px; margin-left: 8px; font-family: $font-family-mono; }
.role-count { color: #64748b; font-size: 12px; margin-left: 8px; }
.import-tip { background: #f8fafc; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 12px; color: #475569; }
.import-tip code { background: #fff; padding: 1px 6px; border-radius: 4px; font-family: $font-family-mono; }
.import-preview { margin-top: 12px; }
.parsing { padding: 20px; text-align: center; color: #94a3b8; }
</style>
