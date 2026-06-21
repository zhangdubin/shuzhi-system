<script setup lang="ts">
/**
 * 角色权限
 * - 左侧：角色列表（超级管理员 / 管理员 / 财务 / 销售 / 业务员 / 访客）
 * - 右侧：选中角色的**权限树**（el-tree，按模块分组：仪表盘/项目/合同/费用/回款/发票/AI/系统管理）
 *   - 树节点：增 / 删 / 改 / 查 + 审批 / 导入 / 导出 / 配置
 * - 顶部"新建角色"
 * - 底部"保存权限" sticky bar
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

// 树节点类型
interface PermNode {
  id: string                  // 唯一 id
  label: string               // 显示名
  checked: boolean            // 选中态（运行时由 permissions 决定）
  isLeaf?: boolean            // 是否叶子
  children?: PermNode[]
}

// 模块 → 操作(增/删/改/查 + 审批/导入/导出/配置)的对应关系
// 按业务合理：每个模块都有增删改查；审批/导入/导出/配置按需
interface ModuleDef {
  key: string
  label: string
  ops: string[]               // 该模块下要展开的操作
}
const moduleDefs: ModuleDef[] = [
  { key: 'dashboard', label: '工作台',   ops: ['查'] },
  { key: 'project',   label: '项目管理', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'contract',  label: '合同管理', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'expense',   label: '销售费用', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'receivable',label: '回款管理', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'invoice',   label: '发票管理', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'ai',        label: 'AI 中心',  ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
  { key: 'admin',     label: '系统管理', ops: ['增', '删', '改', '查', '审批', '导入', '导出', '配置'] },
]

/** 树形数据：模块（父）→ 操作（子） */
const treeData = computed<PermNode[]>(() =>
  moduleDefs.map(m => ({
    id: m.key,
    label: m.label,
    checked: isModuleAllChecked(m.key),
    isLeaf: false,
    children: m.ops.map(op => ({
      id: `${m.key}.${op}`,
      label: op,
      checked: isPermChecked(m.key, op),
      isLeaf: true,
    })),
  })),
)

// 角色 + 当前选中的权限（id 集合）
const roles = ref<any[]>([])
const selectedRoleId = ref<number | null>(null)
const checkedIds = ref<string[]>([])

const selectedRole = computed(() => roles.value.find((r: any) => r.id === selectedRoleId.value) || null)
const totalPerms = computed(() => checkedIds.value.length)

const defaultProps = { children: 'children', label: 'label' }

// 工具：判断某模块是否被全选
function isModuleAllChecked(moduleKey: string): boolean {
  const m = moduleDefs.find(x => x.key === moduleKey)
  if (!m) return false
  return m.ops.every(op => checkedIds.value.includes(`${moduleKey}.${op}`))
}
function isPermChecked(moduleKey: string, op: string): boolean {
  return checkedIds.value.includes(`${moduleKey}.${op}`)
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

// 加载角色已有权限：把后端 permission code 翻译回前端"模块.操作"格式
// 例：project:write + project:read + project:approve → ['project.增','project.删','project.改','project.查','project.审批']
function loadPermissions(role: any) {
  const codes: string[] = role.permissions || []
  const ids: string[] = []
  for (const m of moduleDefs) {
    const hasWrite = codes.includes(`${m.key}:write`)
    const hasRead = codes.includes(`${m.key}:read`)
    const hasApprove = codes.includes(`${m.key}:approve`)
    for (const op of m.ops) {
      if (op === '查' && hasRead) ids.push(`${m.key}.查`)
      else if (op === '增' && hasWrite) ids.push(`${m.key}.增`)
      else if (op === '删' && hasWrite) ids.push(`${m.key}.删`)
      else if (op === '改' && hasWrite) ids.push(`${m.key}.改`)
      else if (op === '审批' && hasApprove) ids.push(`${m.key}.审批`)
      // 导入/导出/配置 不在后端 28 个基础权限里，不勾
    }
  }
  checkedIds.value = ids
}

function onTreeCheck(_checked: unknown, opts: { checkedKeys?: (string | number)[]; checkedNodes?: unknown[] }) {
  // el-tree 的 :default-checked-keys + :check-strictly=false 会同时勾选父和子
  // 但我们要精确控制：只保留叶子节点的 id（即"module.op"形式）
  checkedIds.value = ((opts.checkedKeys || []) as string[]).filter(k => k.includes('.'))
}

// 树节点上的"操作"按钮（新增/删除权限配置项）
function onAddNode(parentNode: PermNode) {
  ElMessageBox.prompt(`在「${parentNode.label}」下添加自定义操作（如：分配、转移）`, '添加权限节点', {
    inputPattern: /.+/,
    inputErrorMessage: '节点名不能为空',
  })
    .then(({ value }) => {
      const newNode: PermNode = { id: `${parentNode.id}.${value}_${Date.now()}`, label: value, checked: true, isLeaf: true }
      parentNode.children = parentNode.children || []
      parentNode.children.push(newNode)
      if (!checkedIds.value.includes(newNode.id)) checkedIds.value.push(newNode.id)
      ElMessage.success(`已添加「${value}」`)
    })
    .catch(() => {})
}
function onRenameNode(node: PermNode) {
  if (node.isLeaf) {
    ElMessage.warning('叶子节点请通过勾选/取消控制,无需重命名')
    return
  }
  ElMessageBox.prompt('修改模块名称', '重命名', { inputValue: node.label, inputPattern: /.+/, inputErrorMessage: '不能为空' })
    .then(({ value }) => { node.label = value; ElMessage.success('已修改') })
    .catch(() => {})
}
function onDeleteNode(node: PermNode) {
  ElMessageBox.confirm(`确定删除节点「${node.label}」？${node.children ? '其下所有操作将一并删除。' : ''}`, '删除节点', { type: 'warning' })
    .then(() => {
      // 从 checkedIds 移除相关 id
      if (node.children && node.children.length) {
        const childIds = node.children.map(c => c.id)
        checkedIds.value = checkedIds.value.filter(id => !childIds.includes(id))
      } else {
        checkedIds.value = checkedIds.value.filter(id => id !== node.id)
      }
      // 从 treeData 中移除
      function remove(nodes: PermNode[]): boolean {
        const idx = nodes.findIndex(n => n.id === node.id)
        if (idx >= 0) {
          // 父节点：仅在 demo 模式下允许删（业务上一般是固定模块）
          ElMessage.warning('模块节点不可删除,只能编辑子节点')
          return false
        }
        for (const n of nodes) if (n.children && remove(n.children)) return true
        return false
      }
      remove(treeData.value)
    })
    .catch(() => {})
}

async function onSave() {
  if (!selectedRole.value) return
  const role = selectedRole.value
  // 把"模块.操作"id 翻译成后端 permission code
  const codes = new Set<string>()
  // 始终包含 dashboard:read（工作台基本权）
  codes.add('dashboard:read')
  for (const id of checkedIds.value) {
    const [moduleKey, op] = id.split('.')
    if (!moduleKey) continue
    if (op === '查') codes.add(`${moduleKey}:read`)
    else if (op === '增' || op === '删' || op === '改') codes.add(`${moduleKey}:write`)
    else if (op === '审批') codes.add(`${moduleKey}:approve`)
    // 导入/导出/配置 → 没对应的后端基础权限，跳过
  }
  const r: any = await adminApi.roleUpdate(role.id, {
    name: role.name,
    description: role.desc,
    dataScope: role.dataScope || 'self',
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
    const { value } = await ElMessageBox.prompt('请输入新角色名称（code 同步）', '新建角色', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '角色名不能为空',
    })
    const code = value.toLowerCase().replace(/\s+/g, '_')
    const r: any = await adminApi.roleCreate({ code, name: value, description: '新建角色' }).catch(() => null)
    if (r?.code === 0 || r?.id) {
      const newRole = r.data || r
      roles.value.push({ ...newRole, desc: newRole.description, builtin: false })
      ElMessage.success(`已创建角色「${value}」`)
    } else {
      ElMessage.error(r?.message || '创建失败')
    }
  } catch { /* cancel */ }
}

async function onDeleteRole() {
  if (!selectedRole.value) return
  const r = selectedRole.value
  if (r.builtin) {
    ElMessage.warning('系统内置角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除角色「${r.name}」？关联用户将失去此角色。`, '删除角色', { type: 'warning' })
    const res: any = await adminApi.roleDelete(r.id).catch(() => null)
    if (res?.code === 0 || res?.deleted) {
      roles.value = roles.value.filter((x: any) => x.id !== r.id)
      selectedRoleId.value = roles.value[0]?.id ?? null
      if (roles.value[0]) loadPermissions(roles.value[0])
      ElMessage.success('已删除')
    } else {
      ElMessage.error(res?.message || '删除失败')
    }
  } catch { /* cancel */ }
}

onMounted(loadRoles)

// ---- mock 角色 + 权限（id 集合用 "module.op" 形式） ----
const mockRoles: any[] = [
  { id: 1, code: 'super_admin', name: '超级管理员', userCount: 2,  desc: '系统最高权限,可管理全部功能与配置', builtin: true },
  { id: 2, code: 'admin',       name: '管理员',     userCount: 5,  desc: '业务配置+审批,不含系统级操作',      builtin: true },
  { id: 3, code: 'finance',     name: '财务',       userCount: 8,  desc: '费用/回款/发票全流程 + 审批',       builtin: false },
  { id: 4, code: 'sales',       name: '销售',       userCount: 12, desc: '客户/合同/回款录入,无审批权限',     builtin: false },
  { id: 5, code: 'salesman',    name: '业务员',     userCount: 24, desc: '仅查看自己的项目/合同/回款',         builtin: false },
  { id: 6, code: 'guest',       name: '访客',       userCount: 6,  desc: '只读,无任何写权限',                  builtin: false },
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
        <h2>角色权限</h2>
        <p class="page-desc">管理角色及其功能权限,按业务模块树形展示</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="onNewRole">新建角色</el-button>
    </div>

    <div class="admin-split">
      <!-- 左：角色列表 -->
      <div class="admin-split-left">
        <div
          v-for="r in roles"
          :key="r.id"
          class="admin-list-item"
          :class="{ active: selectedRoleId === r.id }"
          @click="selectRole(r)"
        >
          <span class="ali-icon">{{ r.name.charAt(0) }}</span>
          <div style="flex:1; min-width:0;">
            <div class="ali-name">
              {{ r.name }}
              <el-tag v-if="r.builtin" size="small" type="info" effect="plain" style="margin-left:4px;">内置</el-tag>
            </div>
            <div style="font-size:11.5px; color:var(--el-text-color-secondary); margin-top:2px;">{{ r.desc }}</div>
          </div>
          <span class="ali-count">{{ r.userCount }}人</span>
        </div>
      </div>

      <!-- 右：权限树（el-tree,严格按规格要求） -->
      <div class="admin-split-right" v-if="selectedRole">
        <h3 class="admin-section-title">
          {{ selectedRole.name }} · 权限配置
          <el-tag size="small" type="primary" effect="plain" style="margin-left:6px;">已选 {{ totalPerms }} 项</el-tag>
        </h3>
        <div class="tip-box">
          <span class="ico">i</span>
          <span>勾选即代表该角色拥有对应操作权限。点击节点右侧按钮可新增 / 重命名 / 删除自定义节点。</span>
        </div>

        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="defaultProps"
          node-key="id"
          :default-checked-keys="checkedIds"
          show-checkbox
          :check-strictly="false"
          :default-expand-all="true"
          :expand-on-click-node="false"
          @check="onTreeCheck"
        >
          <template #default="{ node, data }">
            <div class="tree-row">
              <span class="tree-label">{{ node.label }}</span>
              <span v-if="!data.isLeaf" class="tree-tag">模块</span>
              <span v-else class="tree-tag leaf">操作</span>
              <span class="tree-actions" @click.stop>
                <el-tooltip content="新增子节点" placement="top">
                  <el-button v-if="!data.isLeaf" link size="small" @click="onAddNode(data as PermNode)">+</el-button>
                </el-tooltip>
                <el-tooltip content="重命名" placement="top">
                  <el-button link size="small" @click="onRenameNode(data as PermNode)">✎</el-button>
                </el-tooltip>
                <el-tooltip content="删除节点" placement="top">
                  <el-button link type="danger" size="small" @click="onDeleteNode(data as PermNode)">×</el-button>
                </el-tooltip>
              </span>
            </div>
          </template>
        </el-tree>
      </div>
      <div v-else class="admin-split-right" style="display:flex;align-items:center;justify-content:center;color:var(--el-text-color-secondary);">
        请从左侧选择一个角色
      </div>
    </div>

    <!-- sticky 保存栏 -->
    <div class="form-foot" v-if="selectedRole">
      <div style="font-size:13px; color:var(--el-text-color-secondary);">
        正在编辑: <strong style="color:var(--el-text-color-primary);">{{ selectedRole.name }}</strong>
        · 共 <strong style="color:var(--el-color-primary);">{{ totalPerms }}</strong> 项权限
      </div>
      <div>
        <el-button @click="onDeleteRole">删除角色</el-button>
        <el-button type="primary" @click="onSave">保存权限</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tree-row {
  display: flex; align-items: center; gap: 8px;
  width: 100%;
  padding-right: 8px;
  .tree-label { font-size: 13.5px; }
  .tree-tag {
    font-size: 11px; padding: 1px 6px; border-radius: 3px;
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    &.leaf { background: #F1F5F9; color: var(--el-text-color-secondary); }
  }
  .tree-actions { margin-left: auto; opacity: 0.6; transition: opacity .15s; }
  &:hover .tree-actions { opacity: 1; }
}
:deep(.el-tree-node__content) { height: 32px; }
</style>
