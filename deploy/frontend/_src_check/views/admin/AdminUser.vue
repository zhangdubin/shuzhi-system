<script setup lang="ts">
/**
 * 用户管理
 * - 顶部：搜索 + 新建用户 + 批量导入
 * - 统计卡 4 个：用户总数 / 在线 / 今日活跃 / 待审核
 * - 表格列：账号/姓名/角色(多 tag)/部门/邮箱/手机/状态/最后登录/操作
 * - 行操作：编辑 / 重置密码 / 禁用 / 分配角色
 * - 顶部按钮：批量启用/禁用
 *
 * 真实后端待接：所有 API 调用 .catch(() => null)，回退到本地 mock
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

interface UserRow {
  id: number
  account: string
  name: string
  roles: string[]         // 多角色 → 多个 tag
  dept: string
  email: string
  phone: string
  status: 'active' | 'disabled' | 'pending'
  lastLogin: string
  online?: boolean
}

const loading = ref(false)
const list = ref<UserRow[]>([])
const selected = ref<UserRow[]>([])
const query = reactive({ keyword: '', dept: '' as string, status: '' as string })

const stats = computed(() => {
  const total = list.value.length
  const online = list.value.filter(u => u.online).length
  const todayActive = list.value.filter(u => {
    if (!u.lastLogin) return false
    return u.lastLogin.startsWith('2026-06-13')
  }).length
  const pending = list.value.filter(u => u.status === 'pending').length
  return { total, online, todayActive, pending }
})

async function loadList() {
  loading.value = true
  try {
    // 调真实后端，失败回退到 mock
    const res = await adminApi.userList(query).catch(() => null)
    list.value = (res?.list as any) || mockUsers
  } finally {
    loading.value = false
  }
}

function handleSearch() { loadList() }
function handleReset() { query.keyword = ''; query.dept = ''; query.status = ''; loadList() }
function handleSelection(rows: UserRow[]) { selected.value = rows }

async function resetPwd(row: UserRow) {
  try {
    await ElMessageBox.confirm(`确定重置用户「${row.name}」的密码？\n重置后初始密码为 123456，请通知本人及时修改。`, '重置密码', { type: 'warning' })
    const r: any = await adminApi.userResetPwd(row.id, '123456').catch(() => null)
    if (r?.code === 0 || r?.ok) {
      ElMessage.success('密码已重置为初始密码 123456')
    } else {
      ElMessage.error(r?.message || '重置失败')
    }
  } catch { /* cancel */ }
}

async function toggleStatus(row: UserRow) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(`确定${next === 'active' ? '启用' : '禁用'}用户「${row.name}」？`, '状态变更', { type: 'warning' })
    const r: any = await adminApi.userToggleActive(row.id, next === 'active').catch(() => null)
    if (r?.code === 0 || r?.ok) {
      row.status = next
      ElMessage.success(`已${next === 'active' ? '启用' : '禁用'}`)
    } else {
      ElMessage.error(r?.message || '操作失败')
    }
  } catch { /* cancel */ }
}

function batchUpdate(target: 'active' | 'disabled') {
  if (!selected.value.length) {
    ElMessage.warning('请先勾选用户')
    return
  }
  ElMessageBox.confirm(`确定将 ${selected.value.length} 个用户${target === 'active' ? '启用' : '禁用'}？`, '批量操作', { type: 'warning' })
    .then(() => {
      selected.value.forEach(u => { u.status = target })
      ElMessage.success('批量操作完成')
    })
    .catch(() => {})
}

function onNewUser() { ElMessage.info('演示模式：未连接后端') }
function onImport()   { ElMessage.info('演示模式：未连接后端') }
function onAssignRole(row: UserRow) { ElMessage.info(`为「${row.name}」分配角色`) }

onMounted(loadList)

// ---- 本地 mock 数据（后端待接） ----
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
  { id: 10,account: 'cfo01',     name: '周总',   roles: ['财务', '管理员'], dept: '财务部',     email: 'zhou@company.com',       phone: '13800138010', status: 'active',   lastLogin: '2026-06-13 08:00', online: true },
  { id: 11,account: 'intern01',  name: '吴桐',   roles: ['访客'],       dept: '项目部',       email: 'wu@company.com',         phone: '13800138011', status: 'pending',  lastLogin: '—',                online: false },
  { id: 12,account: 'sales04',   name: '郑亮',   roles: ['业务员', '销售'], dept: '销售一部',   email: 'zheng@company.com',      phone: '13800138012', status: 'active',   lastLogin: '2026-06-12 17:30', online: false },
]

const statusType = (s: UserRow['status']) =>
  s === 'active' ? 'success' : s === 'pending' ? 'warning' : 'info'
const statusLabel = (s: UserRow['status']) =>
  s === 'active' ? '启用' : s === 'pending' ? '待审核' : '禁用'
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p class="page-desc">账号、角色、部门、状态统一管理</p>
      </div>
      <div style="display:flex;gap:8px;">
        <el-button :icon="'Upload'" @click="onImport">批量导入</el-button>
        <el-button type="primary" :icon="'Plus'" @click="onNewUser">新建用户</el-button>
      </div>
    </div>

    <!-- 统计卡 4 个 -->
    <div class="admin-stats-grid">
      <div class="admin-stat-card">
        <div class="asc-label">
          <span>用户总数</span>
          <span class="asc-icon" style="background:rgba(79,107,255,0.12);color:#4F6BFF;">👤</span>
        </div>
        <div class="asc-value">{{ stats.total }}<span class="unit">人</span></div>
        <div class="asc-delta">较上周 <span class="up">↑ 3</span></div>
      </div>
      <div class="admin-stat-card">
        <div class="asc-label">
          <span>当前在线</span>
          <span class="asc-icon" style="background:rgba(16,185,129,0.12);color:#10B981;">●</span>
        </div>
        <div class="asc-value">{{ stats.online }}<span class="unit">人</span></div>
        <div class="asc-delta">在线率 {{ stats.total ? Math.round(stats.online / stats.total * 100) : 0 }}%</div>
      </div>
      <div class="admin-stat-card">
        <div class="asc-label">
          <span>今日活跃</span>
          <span class="asc-icon" style="background:rgba(245,158,11,0.12);color:#F59E0B;">⚡</span>
        </div>
        <div class="asc-value">{{ stats.todayActive }}<span class="unit">人</span></div>
        <div class="asc-delta">日活率 {{ stats.total ? Math.round(stats.todayActive / stats.total * 100) : 0 }}%</div>
      </div>
      <div class="admin-stat-card">
        <div class="asc-label">
          <span>待审核</span>
          <span class="asc-icon" style="background:rgba(239,68,68,0.12);color:#EF4444;">!</span>
        </div>
        <div class="asc-value">{{ stats.pending }}<span class="unit">人</span></div>
        <div class="asc-delta">需管理员审批开通</div>
      </div>
    </div>

    <div class="page-card">
      <div class="admin-toolbar">
        <el-input v-model="query.keyword" placeholder="搜索账号 / 姓名 / 邮箱 / 手机" clearable style="width:280px" @keyup.enter="handleSearch" />
        <el-select v-model="query.dept" placeholder="部门" clearable style="width:160px">
          <el-option label="总经理办公室" value="总经理办公室" />
          <el-option label="财务部" value="财务部" />
          <el-option label="销售一部" value="销售一部" />
          <el-option label="销售二部" value="销售二部" />
          <el-option label="项目部" value="项目部" />
          <el-option label="人力资源部" value="人力资源部" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width:120px">
          <el-option label="启用" value="active" />
          <el-option label="禁用" value="disabled" />
          <el-option label="待审核" value="pending" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <span class="spacer" />
        <el-button :disabled="!selected.length" @click="batchUpdate('active')">批量启用</el-button>
        <el-button :disabled="!selected.length" type="danger" plain @click="batchUpdate('disabled')">批量禁用</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        stripe
        @selection-change="handleSelection"
        row-class-name="clickable"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="64" />
        <el-table-column prop="account" label="账号" width="120" />
        <el-table-column label="姓名" width="120">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.online" size="small" type="success" effect="plain" style="margin-left:6px;">在线</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r" size="small" class="role-tag">{{ r }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept" label="部门" width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLogin" label="最后登录" width="160" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">编辑</el-button>
            <el-button link type="primary" size="small" @click="onAssignRole(row as UserRow)">分配角色</el-button>
            <el-button link type="primary" size="small" @click="resetPwd(row as UserRow)">重置密码</el-button>
            <el-button link :type="row.status === 'active' ? 'danger' : 'success'" size="small" @click="toggleStatus(row as UserRow)">
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无用户数据" /></template>
      </el-table>
    </div>
  </div>
</template>

<style lang="scss" scoped>
:deep(.clickable) { cursor: default; }
:deep(.role-tag) { margin-right: 4px; }
:deep(.role-tag:last-child) { margin-right: 0; }
</style>
