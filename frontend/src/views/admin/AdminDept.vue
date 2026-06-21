<script setup lang="ts">
/**
 * AdminDept · 部门管理（无 design，按 R9 自造 pattern）
 * - 4 KPI（部门总数/成员总数/顶级部门/含子部门）
 * - 左：自造组织架构树（递归渲染，支持展开/折叠）
 * - 右：选中部门详情 + 成员列表
 * - 顶部：新增/编辑/调整/删除
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

const tree = ref<any[]>([])
const expanded = ref<Set<number>>(new Set())
const selectedDeptId = ref<number | null>(null)
const members = ref<any[]>([])

// 4 KPI
const kpis = ref([
  { label: '部门总数', num: 14, color: 'info',    icon: '🏢', trend: '5 顶级 / 9 子级' },
  { label: '成员总数', num: 57, color: 'primary', icon: '👥', trend: '本月 +3' },
  { label: '顶级部门', num: 5,  color: 'success', icon: '▦',  trend: '含 4 个业务部' },
  { label: '含子部门', num: 9,  color: 'warning', icon: '▤',  trend: '平均 1.8 子级/部' },
])

const selectedDept = computed<any | null>(() => {
  function find(nodes: any[]): any | null {
    for (const n of nodes) {
      if (n.id === selectedDeptId.value) return n
      if (n.children) { const r = find(n.children); if (r) return r }
    }
    return null
  }
  return find(tree.value)
})

async function loadTree() {
  const res = await adminApi.deptList().catch(() => null)
  tree.value = (res as any)?.list || mockTree
  expanded.value = new Set(tree.value.map(n => n.id))
  if (!selectedDeptId.value && tree.value.length) selectedDeptId.value = tree.value[0].id
  if (selectedDeptId.value) loadMembers(selectedDeptId.value)
}

async function loadMembers(deptId: number) {
  const res = await adminApi.userList({ departmentId: deptId, pageSize: 50 }).catch(() => null)
  if (res) members.value = ((res as any)?.list as any[]) || (Array.isArray(res) ? res : [])
  else {
    const deptName = selectedDept.value?.name
    members.value = mockUsers.filter(u => u.dept === deptName)
  }
}

function toggleExpand(id: number) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
  // 触发响应式
  expanded.value = new Set(expanded.value)
}

function selectDept(node: any) {
  selectedDeptId.value = node.id
  loadMembers(node.id)
}

async function onAdd() {
  if (!selectedDept.value) return ElMessage.warning('请先选择上级部门')
  try {
    const { value } = await ElMessageBox.prompt(`在「${selectedDept.value.name}」下新建子部门`, '新增部门', { inputPattern: /.+/, inputErrorMessage: '部门名不能为空' })
    const newNode = { id: Date.now(), name: value, parentId: selectedDept.value.id, manager: '—', memberCount: 0, order: 99 }
    if (!selectedDept.value.children) selectedDept.value.children = []
    selectedDept.value.children.push(newNode)
    expanded.value.add(selectedDept.value.id)
    expanded.value = new Set(expanded.value)
    ElMessage.success(`已新增部门「${value}」`)
  } catch {}
}

async function onEdit() {
  if (!selectedDept.value) return
  try {
    const { value } = await ElMessageBox.prompt('修改部门名称', '编辑部门', { inputValue: selectedDept.value.name, inputPattern: /.+/, inputErrorMessage: '不能为空' })
    const r: any = await adminApi.deptUpdate(selectedDept.value.id, { name: value }).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.id) {
      selectedDept.value.name = value
      ElMessage.success('已修改')
      await loadTree()
    } else {
      ElMessage.error(r?.message || '修改失败')
    }
  } catch (e: any) { console.warn(e) }
}

async function onDelete() {
  if (!selectedDept.value) return
  const d = selectedDept.value
  if (d.children && d.children.length) return ElMessage.warning('该部门存在子部门，请先删除子部门')
  try {
    await ElMessageBox.confirm(`确定删除部门「${d.name}」？部门下 ${d.memberCount} 名成员将需要重新分配。`, '删除部门', { type: 'warning' })
    const r: any = await adminApi.deptDelete(d.id).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.deleted) {
      function del(nodes: any[]): boolean {
        const idx = nodes.findIndex(n => n.id === d.id)
        if (idx >= 0) { nodes.splice(idx, 1); return true }
        for (const n of nodes) if (n.children && del(n.children)) return true
        return false
      }
      del(tree.value)
      selectedDeptId.value = tree.value[0]?.id ?? null
      if (selectedDeptId.value) loadMembers(selectedDeptId.value)
      ElMessage.success('已删除')
      await loadTree()
    } else {
      ElMessage.error(r?.message || '删除失败')
    }
  } catch {}
}

async function onCreateChild() {
  if (!selectedDept.value) return ElMessage.warning('请先选择父部门')
  try {
    const { value: name } = await ElMessageBox.prompt('新部门名称', '新建部门', { inputPattern: /.+/, inputErrorMessage: '不能为空' })
    const code = 'D' + Date.now().toString().slice(-6)
    const r: any = await adminApi.deptCreate({ name, code, parentId: selectedDept.value.id, sort: 99 }).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.id) {
      ElMessage.success(`已创建部门「${name}」`)
      await loadTree()
    } else {
      ElMessage.error(r?.message || '创建失败')
    }
  } catch {}
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

// mock
const mockTree: any[] = [
  { id: 1, name: '总经理办公室', parentId: 0, manager: '张明', memberCount: 3, order: 1, children: [
    { id: 11, name: '行政助理组', parentId: 1, manager: '王助理', memberCount: 2, order: 1 },
  ]},
  { id: 2, name: '财务部', parentId: 0, manager: '李财务', memberCount: 8, order: 2, children: [
    { id: 21, name: '出纳组', parentId: 2, manager: '钱出纳', memberCount: 2, order: 1 },
    { id: 22, name: '核算组', parentId: 2, manager: '孙会计', memberCount: 4, order: 2 },
  ]},
  { id: 3, name: '销售部', parentId: 0, manager: '王销售', memberCount: 28, order: 3, children: [
    { id: 31, name: '销售一部', parentId: 3, manager: '陈丽', memberCount: 12, order: 1 },
    { id: 32, name: '销售二部', parentId: 3, manager: '郑亮', memberCount: 10, order: 2 },
    { id: 33, name: '销售三部', parentId: 3, manager: '—',    memberCount: 6,  order: 3 },
  ]},
  { id: 4, name: '项目部', parentId: 0, manager: '刘工', memberCount: 14, order: 4, children: [
    { id: 41, name: '项目一组', parentId: 4, manager: '—', memberCount: 5, order: 1 },
    { id: 42, name: '项目二组', parentId: 4, manager: '—', memberCount: 4, order: 2 },
  ]},
  { id: 5, name: '人力资源部', parentId: 0, manager: '赵敏', memberCount: 4, order: 5 },
]

const mockUsers: any[] = [
  { id: 1, account: 'admin',     name: '张明',   roles: ['超级管理员'], dept: '总经理办公室', email: 'zhangming@company.com', phone: '13800138001', status: 'active' },
  { id: 2, account: 'finance01', name: '李财务', roles: ['财务'],       dept: '财务部',       email: 'li@company.com',         phone: '13800138002', status: 'active' },
  { id: 3, account: 'sales01',   name: '王销售', roles: ['销售'],       dept: '销售部',       email: 'wang@company.com',       phone: '13800138003', status: 'active' },
  { id: 4, account: 'sales02',   name: '陈丽',   roles: ['销售'],       dept: '销售一部',     email: 'chen@company.com',       phone: '13800138004', status: 'active' },
  { id: 5, account: 'pm01',      name: '刘工',   roles: ['项目经理'],   dept: '项目部',       email: 'liu@company.com',        phone: '13800138005', status: 'active' },
  { id: 6, account: 'hr01',      name: '赵敏',   roles: ['HR'],         dept: '人力资源部',   email: 'zhao@company.com',       phone: '13800138006', status: 'active' },
  { id: 10, account: 'cfo01',   name: '周总',   roles: ['财务', '管理员'], dept: '财务部',     email: 'zhou@company.com',       phone: '13800138010', status: 'active' },
  { id: 12, account: 'sales04',  name: '郑亮',   roles: ['业务员', '销售'], dept: '销售二部',   email: 'zheng@company.com',      phone: '13800138012', status: 'active' },
]
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>🏢 部门管理</h1>
        <p class="page-desc">组织架构、负责人、成员统一管理</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" :disabled="!selectedDept" @click="onCreateChild">+ 新建子部门</button>
        <button class="btn btn-outline btn-sm" :disabled="!selectedDept" @click="onEdit">✎ 编辑</button>
        <button class="btn btn-outline btn-sm danger" :disabled="!selectedDept" @click="onDelete">🗑 删除</button>
        <button class="btn btn-primary btn-sm" @click="onAdd">+ 新增部门</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-head">
          <span class="kpi-label">{{ k.label }}</span>
          <span :class="['kpi-icon', k.color]">{{ k.icon }}</span>
        </div>
        <div class="kpi-num">{{ k.num }}</div>
        <div class="kpi-trend">{{ k.trend }}</div>
      </div>
    </div>

    <!-- 主体：左树 + 右详情 -->
    <div class="dept-layout">
      <!-- 左：自造组织树 -->
      <div class="tree-card">
        <div class="tc-head">
          <h4>📂 组织架构</h4>
          <span class="tc-count">{{ tree.length }} 顶级部门</span>
        </div>
        <div class="tip-box">
          <div class="ico">i</div>
          <div>点击节点查看详情，可拖拽调整上下级</div>
        </div>
        <div class="tree-body">
          <TreeNode
            v-for="node in tree"
            :key="node.id"
            :node="node"
            :expanded="expanded"
            :selected-id="selectedDeptId ?? undefined"
            :depth="0"
            @toggle="toggleExpand"
            @select="selectDept"
          />
        </div>
      </div>

      <!-- 右：详情 + 成员 -->
      <div class="dept-panel" v-if="selectedDept">
        <div class="dp-head">
          <div>
            <h3>{{ selectedDept.name }} · 详情</h3>
            <div class="dp-meta">
              <span>编号: <b class="mono">D-{{ String(selectedDept.id).padStart(4, '0') }}</b></span>
              <span>·</span>
              <span>负责人: <b>{{ selectedDept.manager }}</b></span>
              <span>·</span>
              <span>成员: <b class="primary">{{ members.length }}</b> 人</span>
            </div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-section">
            <div class="section-title">📋 部门信息</div>
            <div class="info-grid">
              <div class="info-row"><span class="lbl">部门名称</span><span class="val">{{ selectedDept.name }}</span></div>
              <div class="info-row"><span class="lbl">部门编号</span><span class="val mono">D-{{ String(selectedDept.id).padStart(4, '0') }}</span></div>
              <div class="info-row"><span class="lbl">部门负责人</span><span class="val">{{ selectedDept.manager }}</span></div>
              <div class="info-row"><span class="lbl">成员数量</span><span class="val">{{ members.length }} 人</span></div>
              <div class="info-row"><span class="lbl">排序</span><span class="val">{{ selectedDept.order }}</span></div>
              <div class="info-row"><span class="lbl">父级部门</span><span class="val">{{ findParentName(selectedDept.parentId) || '— (顶级)' }}</span></div>
            </div>
          </div>
        </div>

        <div class="member-card">
          <div class="mc-head">
            <h4>部门成员（{{ members.length }}）</h4>
            <button class="btn btn-outline btn-sm" @click="ElMessage.info('添加成员')">+ 添加成员</button>
          </div>
          <table class="tpl-table">
            <thead>
              <tr>
                <th style="width: 50px;">ID</th>
                <th style="width: 100px;">账号</th>
                <th style="width: 100px;">姓名</th>
                <th>角色</th>
                <th>邮箱</th>
                <th style="width: 120px;">手机</th>
                <th style="width: 80px;">状态</th>
                <th style="width: 130px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in members" :key="m.id">
                <td><span class="cell-mono">{{ m.id }}</span></td>
                <td><span class="cell-mono">{{ m.account }}</span></td>
                <td>{{ m.name }}</td>
                <td>
                  <span v-for="r in m.roles" :key="r" class="role-tag">{{ r }}</span>
                </td>
                <td class="cell-truncate">{{ m.email }}</td>
                <td><span class="cell-mono">{{ m.phone }}</span></td>
                <td><span :class="['tag', m.status === 'active' ? 'success' : 'info']">{{ m.status === 'active' ? '启用' : '禁用' }}</span></td>
                <td>
                  <div class="row-actions">
                    <a class="ra primary" @click="ElMessage.info('调整部门')">调整</a>
                    <a class="ra primary" @click="ElMessage.info('查看详情')">详情</a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!members.length" class="empty">
            <div class="empty-icon">📭</div>
            <div class="empty-text">该部门暂无成员</div>
          </div>
        </div>
      </div>
      <div v-else class="dept-panel empty-panel">
        <div class="empty-icon">👈</div>
        <div class="empty-text">请从左侧选择部门</div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// 递归 TreeNode 子组件（手写，避免额外文件）
import { defineComponent, h } from 'vue'

const TreeNode = defineComponent({
  name: 'TreeNode',
  props: { node: { type: Object, required: true }, expanded: { type: Object, required: true }, selectedId: { type: Number, default: null }, depth: { type: Number, default: 0 } },
  emits: ['toggle', 'select'],
  setup(props, { emit }) {
    return () => {
      const n = props.node
      const hasChildren = n.children && n.children.length > 0
      const isExpanded = props.expanded.has(n.id)
      const isSelected = props.selectedId === n.id
      const indent = props.depth * 18

      return h('div', { class: 'tree-row-wrap' }, [
        h('div', { class: ['tn-row', { active: isSelected }], onClick: () => emit('select', n) }, [
          hasChildren
            ? h('span', { class: ['tn-toggle', { expanded: isExpanded }], onClick: (e: Event) => { e.stopPropagation(); emit('toggle', n.id) } }, '▶')
            : h('span', { class: 'tn-toggle leaf' }, '·'),
          h('span', { class: 'tn-icon' }, props.depth === 0 ? '🏢' : '📁'),
          h('span', { class: 'tn-name' }, n.name),
          h('span', { class: 'tn-count' }, `${n.memberCount} 人`),
        ]),
        hasChildren && isExpanded
          ? h('div', { class: 'tn-children' }, n.children.map((c: any) => h(TreeNode, { key: c.id, node: c, expanded: props.expanded, selectedId: props.selectedId, depth: props.depth + 1, onToggle: (id: number) => emit('toggle', id), onSelect: (node: any) => emit('select', node) })))
          : null,
      ])
    }
  },
})
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-brand; color: #fff; &:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover:not(:disabled) { border-color: $color-primary; color: $color-primary; } &.danger:hover:not(:disabled) { border-color: $color-danger; color: $color-danger; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

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
.kpi-num { font-size: 24px; font-weight: 700; line-height: 1.2; color: $color-text-primary; }
.kpi-trend { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

// 主体
.dept-layout { display: grid; grid-template-columns: 320px 1fr; gap: 16px; align-items: start; @media (max-width: 900px) { grid-template-columns: 1fr; } }

// 左：组织树
.tree-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; position: sticky; top: 16px; }
.tc-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF; h4 { font-size: 13.5px; font-weight: 600; margin: 0; } .tc-count { font-size: 11.5px; color: $color-text-tertiary; } }
.tip-box { display: flex; gap: 10px; padding: 10px 14px; background: rgba(79, 107, 255, 0.05); border: 1px solid rgba(79, 107, 255, 0.2); border-radius: $radius-md; margin: 12px 12px 0 12px; font-size: 12px; color: $color-text-secondary; line-height: 1.5; .ico { color: $color-primary; font-size: 14px; flex-shrink: 0; } }
.tree-body { padding: 8px 0; max-height: 700px; overflow-y: auto; }

// 自造树
:deep(.tn-row) { display: flex; align-items: center; gap: 6px; padding: 6px 12px; cursor: pointer; transition: all 0.15s; font-size: 13px; &:hover { background: $color-bg; } &.active { background: $color-primary-bg; color: $color-primary; font-weight: 500; } }
:deep(.tn-toggle) { width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; font-size: 9px; color: $color-text-tertiary; transition: transform 0.2s; &.expanded { transform: rotate(90deg); color: $color-primary; } &.leaf { color: $color-border-strong; cursor: default; } }
:deep(.tn-icon) { font-size: 14px; }
:deep(.tn-name) { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.tn-count) { font-size: 11px; color: $color-text-tertiary; padding: 1px 6px; background: $color-bg; border-radius: 9999px; }

// 右：详情
.dept-panel { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.dp-head h3 { font-size: 15px; font-weight: 600; margin: 0 0 4px 0; }
.dp-meta { font-size: 12px; color: $color-text-secondary; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; .primary { color: $color-primary; } }

.detail-section { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 14px 16px; }
.section-title { font-size: 13.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 10px; }
.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px 24px; }
.info-row { display: flex; gap: 12px; font-size: 12.5px; padding: 3px 0; .lbl { color: $color-text-tertiary; min-width: 72px; flex-shrink: 0; } .val { color: $color-text-primary; } .val.mono { font-family: $font-family-mono; font-size: 12px; } }

.member-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-md; overflow: hidden; }
.mc-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF; h4 { font-size: 13.5px; font-weight: 600; margin: 0; } }
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; }
.tpl-table td { padding: 10px 12px; border-bottom: 1px solid $color-border; }
.tpl-table tbody tr { transition: background 0.15s; &:hover { background: $color-bg; } }
.cell-mono { font-family: $font-family-mono; color: $color-text-secondary; font-size: 11.5px; }
.cell-truncate { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $color-text-secondary; }
.role-tag { display: inline-block; font-size: 10.5px; padding: 1px 6px; background: $color-primary-bg; color: $color-primary; border-radius: 9999px; margin-right: 4px; font-weight: 500; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.success { background: $color-success-bg; color: $color-success; }
.tag.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.row-actions { display: flex; gap: 10px; }
.ra { font-size: 12px; cursor: pointer; &.primary { color: $color-primary; &:hover { text-decoration: underline; } } }

// empty
.empty { text-align: center; padding: 30px 20px; }
.empty-icon { font-size: 36px; margin-bottom: 6px; opacity: 0.5; }
.empty-text { font-size: 12.5px; color: $color-text-tertiary; }
.empty-panel { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; background: #fff; border: 1px dashed $color-border; border-radius: $radius-lg; }
</style>
