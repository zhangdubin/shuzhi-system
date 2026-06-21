<script setup lang="ts">
/**
 * 部门管理
 * - 左：组织架构树（el-tree，可拖拽）
 * - 右：选中部门详情 + 成员列表
 * - 顶部：新增 / 编辑 / 删除 / 调整
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

const tree = ref<any[]>([])
const selectedDeptId = ref<number | null>(null)
const members = ref<any[]>([])
const defaultProps = { children: 'children', label: 'name' }

const selectedDept = computed<any | null>(() => {
  function find(nodes: any[]): any | null {
    for (const n of nodes) {
      if (n.id === selectedDeptId.value) return n
      if (n.children) {
        const r = find(n.children)
        if (r) return r
      }
    }
    return null
  }
  return find(tree.value)
})

async function loadTree() {
  const res = await adminApi.deptList().catch(() => null)
  tree.value = (res as any[] | null) || mockTree
  if (!selectedDeptId.value && tree.value.length) selectedDeptId.value = tree.value[0].id
  if (selectedDeptId.value) loadMembers(selectedDeptId.value)
}

async function loadMembers(deptId: number) {
  const res = await adminApi.userList({ departmentId: deptId, pageSize: 50 }).catch(() => null)
  if (res) {
    members.value = (res as any).list || []
  } else {
    // mock：根据部门过滤 user 列表（用 any mock）
    const deptName = selectedDept.value?.name
    members.value = mockUsers.filter(u => u.dept === deptName)
  }
}

function onNodeClick(node: any) {
  selectedDeptId.value = node.id
  loadMembers(node.id)
}

async function onAdd() {
  if (!selectedDept.value) {
    ElMessage.warning('请先选择上级部门')
    return
  }
  try {
    const { value } = await ElMessageBox.prompt(`在「${selectedDept.value.name}」下新建子部门`, '新增部门', {
      inputPattern: /.+/,
      inputErrorMessage: '部门名不能为空',
    })
    const code = `dept_${Date.now()}`.toLowerCase()
    const r: any = await adminApi.deptCreate({
      name: value,
      code,
      parentId: selectedDept.value.id,
      sort: 99,
    } as any).catch(() => null)
    if (r?.code === 0 || r?.id) {
      const newNode = { id: r.id || r.data?.id, name: value, parentId: selectedDept.value.id, manager: '—', memberCount: 0 }
      if (!selectedDept.value.children) selectedDept.value.children = []
      selectedDept.value.children.push(newNode)
      ElMessage.success(`已新增部门「${value}」`)
    } else {
      ElMessage.error(r?.message || '新增失败')
    }
  } catch { /* cancel */ }
}

async function onEdit() {
  if (!selectedDept.value) return
  try {
    const { value } = await ElMessageBox.prompt('修改部门名称', '编辑部门', {
      inputValue: selectedDept.value.name,
      inputPattern: /.+/,
      inputErrorMessage: '部门名不能为空',
    })
    const r: any = await adminApi.deptUpdate(selectedDept.value.id, { name: value }).catch(() => null)
    if (r?.code === 0 || r?.id) {
      selectedDept.value.name = value
      ElMessage.success('已修改')
    } else {
      ElMessage.error(r?.message || '修改失败')
    }
  } catch { /* cancel */ }
}

async function onDelete() {
  if (!selectedDept.value) return
  const d = selectedDept.value
  if (d.children && d.children.length) {
    ElMessage.warning('该部门存在子部门,请先删除子部门')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除部门「${d.name}」？部门下 ${d.memberCount} 名成员将需要重新分配。`, '删除部门', { type: 'warning' })
    const r: any = await adminApi.deptDelete(d.id).catch(() => null)
    if (r?.code === 0 || r?.deleted) {
      function del(nodes: any[]): boolean {
        const idx = nodes.findIndex(n => n.id === d.id)
        if (idx >= 0) { nodes.splice(idx, 1); return true }
        for (const n of nodes) if (n.children && del(n.children)) return true
        return false
      }
      del(tree.value)
      selectedDeptId.value = tree.value[0]?.id ?? null
      ElMessage.success('已删除')
    } else {
      ElMessage.error(r?.message || '删除失败')
    }
  } catch { /* cancel */ }
}

function onAdjust() {
  ElMessage.info('演示模式：拖拽树节点已开启,松开会自动调整')
}

function flatIds(): number[] {
  const out: number[] = []
  function walk(nodes: any[]) {
    for (const n of nodes) { out.push(n.id); if (n.children) walk(n.children) }
  }
  walk(tree.value)
  return out
}

function allowDrop(_draggingNode: any, _dropNode: any, type: string) {
  // 只允许 inner（成为子部门）
  return type === 'inner'
}

function onNodeDrop() {
  ElMessage.success('部门层级已调整')
}

function findParentName(parentId: number): string {
  if (parentId === 0) return ''
  function walk(nodes: any[]): string | null {
    for (const n of nodes) {
      if (n.id === parentId) return n.name
      if (n.children) { const r = walk(n.children); if (r) return r }
    }
    return null
  }
  return walk(tree.value) || ''
}

onMounted(loadTree)

// ---- mock ----
const mockTree: any[] = [
  {
    id: 1, name: '总经理办公室', parentId: 0, manager: '张明', memberCount: 3, order: 1,
    children: [
      { id: 11, name: '行政助理组', parentId: 1, manager: '王助理', memberCount: 2, order: 1 },
    ],
  },
  {
    id: 2, name: '财务部', parentId: 0, manager: '李财务', memberCount: 8, order: 2,
    children: [
      { id: 21, name: '出纳组', parentId: 2, manager: '钱出纳', memberCount: 2, order: 1 },
      { id: 22, name: '核算组', parentId: 2, manager: '孙会计', memberCount: 4, order: 2 },
    ],
  },
  {
    id: 3, name: '销售部', parentId: 0, manager: '王销售', memberCount: 28, order: 3,
    children: [
      { id: 31, name: '销售一部', parentId: 3, manager: '陈丽', memberCount: 12, order: 1 },
      { id: 32, name: '销售二部', parentId: 3, manager: '郑亮', memberCount: 10, order: 2 },
      { id: 33, name: '销售三部', parentId: 3, manager: '—',    memberCount: 6,  order: 3 },
    ],
  },
  {
    id: 4, name: '项目部', parentId: 0, manager: '刘工', memberCount: 14, order: 4,
    children: [
      { id: 41, name: '项目一组', parentId: 4, manager: '—', memberCount: 5, order: 1 },
      { id: 42, name: '项目二组', parentId: 4, manager: '—', memberCount: 4, order: 2 },
    ],
  },
  {
    id: 5, name: '人力资源部', parentId: 0, manager: '赵敏', memberCount: 4, order: 5,
  },
]

const mockUsers: any[] = [
  { id: 1, account: 'admin', name: '张明', roles: ['超级管理员'], dept: '总经理办公室', email: 'zhangming@company.com', phone: '13800138001', status: 'active', lastLogin: '2026-06-13 09:12', online: true },
  { id: 2, account: 'finance01', name: '李财务', roles: ['财务'], dept: '财务部', email: 'li@company.com', phone: '13800138002', status: 'active', lastLogin: '2026-06-13 08:30', online: true },
  { id: 3, account: 'sales01', name: '王销售', roles: ['销售'], dept: '销售部', email: 'wang@company.com', phone: '13800138003', status: 'active', lastLogin: '2026-06-13 10:45', online: true },
  { id: 4, account: 'sales02', name: '陈丽', roles: ['销售'], dept: '销售一部', email: 'chen@company.com', phone: '13800138004', status: 'active', lastLogin: '2026-06-13 11:02', online: false },
  { id: 5, account: 'pm01', name: '刘工', roles: ['项目经理'], dept: '项目部', email: 'liu@company.com', phone: '13800138005', status: 'active', lastLogin: '2026-06-12 18:21', online: false },
  { id: 6, account: 'hr01', name: '赵敏', roles: ['HR'], dept: '人力资源部', email: 'zhao@company.com', phone: '13800138006', status: 'active', lastLogin: '2026-06-13 09:55', online: true },
  { id: 10, account: 'cfo01', name: '周总', roles: ['财务', '管理员'], dept: '财务部', email: 'zhou@company.com', phone: '13800138010', status: 'active', lastLogin: '2026-06-13 08:00', online: true },
  { id: 12, account: 'sales04', name: '郑亮', roles: ['业务员', '销售'], dept: '销售二部', email: 'zheng@company.com', phone: '13800138012', status: 'active', lastLogin: '2026-06-12 17:30', online: false },
]
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>部门管理</h2>
        <p class="page-desc">组织架构、负责人、成员统一管理</p>
      </div>
      <div style="display:flex;gap:8px;">
        <el-button :icon="'Plus'" type="primary" @click="onAdd">新增部门</el-button>
        <el-button :icon="'Edit'" :disabled="!selectedDept" @click="onEdit">编辑</el-button>
        <el-button :icon="'Setting'" :disabled="!selectedDept" @click="onAdjust">调整</el-button>
        <el-button :icon="'Delete'" :disabled="!selectedDept" type="danger" plain @click="onDelete">删除</el-button>
      </div>
    </div>

    <div class="admin-split">
      <!-- 左：组织树 -->
      <div class="admin-split-left">
        <div class="tip-box" style="margin-bottom:12px;">
          <span class="ico">i</span>
          <span>可拖拽节点调整上下级关系</span>
        </div>
        <el-tree
          :data="tree"
          :props="defaultProps"
          node-key="id"
          :default-expanded-all="true"
          :highlight-current="true"
          :expand-on-click-node="false"
          :draggable="true"
          :allow-drop="allowDrop"
          @node-click="onNodeClick"
          @node-drop="onNodeDrop"
        >
          <template #default="{ node, data }">
            <span class="tree-node">
              <span class="tn-name">{{ node.label }}</span>
              <span class="tn-count">{{ data.memberCount }}人</span>
            </span>
          </template>
        </el-tree>
      </div>

      <!-- 右：部门详情 + 成员 -->
      <div class="admin-split-right" v-if="selectedDept">
        <h3 class="admin-section-title">{{ selectedDept.name }} · 详情</h3>

        <div class="info-grid" style="margin-bottom: 20px;">
          <div class="info-row">
            <div class="l">部门名称</div>
            <div class="v">{{ selectedDept.name }}</div>
          </div>
          <div class="info-row">
            <div class="l">部门编号</div>
            <div class="v mono">D-{{ String(selectedDept.id).padStart(4, '0') }}</div>
          </div>
          <div class="info-row">
            <div class="l">部门负责人</div>
            <div class="v">{{ selectedDept.manager }}</div>
          </div>
          <div class="info-row">
            <div class="l">成员数量</div>
            <div class="v">{{ members.length }} 人</div>
          </div>
          <div class="info-row">
            <div class="l">排序</div>
            <div class="v">{{ selectedDept.order }}</div>
          </div>
          <div class="info-row">
            <div class="l">父级部门</div>
            <div class="v">{{ findParentName(selectedDept.parentId) || '— (顶级)' }}</div>
          </div>
        </div>

        <h4 class="admin-section-title" style="font-size:14px;">部门成员 ({{ members.length }})</h4>
        <el-table :data="members" stripe>
          <el-table-column prop="account" label="账号" width="120" />
          <el-table-column prop="name" label="姓名" width="120" />
          <el-table-column label="角色" min-width="180">
            <template #default="{ row }">
              <el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right:4px;">{{ r }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
          <el-table-column prop="phone" label="手机" width="130" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                {{ row.status === 'active' ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default>
              <el-button link type="primary" size="small">调整部门</el-button>
              <el-button link type="primary" size="small">查看详情</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="该部门暂无成员" /></template>
        </el-table>
      </div>
      <div v-else class="admin-split-right" style="display:flex;align-items:center;justify-content:center;color:var(--el-text-color-secondary);">
        请从左侧选择部门
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tree-node {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%;
  padding-right: 8px;
  .tn-count { font-size: 11.5px; color: var(--el-text-color-tertiary); }
}
</style>
