<script setup lang="ts">
/**
 * 数据字典
 * - 左：字典分类
 * - 右：选中分类的字典项表格（编码/名称/排序/启用/操作）
 * - 顶部：新建字典项 / 批量启用 / 同步到下拉
 * - 可新增字典分类
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

const categories = ref<any[]>([])
const selectedCatId = ref<number | null>(null)
const items = ref<any[]>([])
const selectedItems = ref<any[]>([])

const selectedCat = computed(() => categories.value.find(c => c.id === selectedCatId.value) || null)

async function loadCategories() {
  // 后端 /admin/dicts/list?dictType=... 直接列项；前端把"分类"模拟出来
  categories.value = mockCategories
  if (!selectedCatId.value && categories.value.length) selectedCatId.value = categories.value[0].id
  if (selectedCatId.value) loadItems(selectedCatId.value)
}

async function loadItems(catId: number) {
  const cat = categories.value.find((c: any) => c.id === catId)
  if (!cat) return
  const res = await adminApi.dictList(cat.code).catch(() => null)
  if (res) {
    items.value = ((res as any).list as any[]) || []
  } else {
    items.value = mockItems[cat.code] || []
  }
  selectedItems.value = []
}

function selectCat(c: any) {
  selectedCatId.value = c.id
  loadItems(c.id)
}

function onNewCategory() {
  ElMessageBox.prompt('请输入字典分类名称（如：客户等级）', '新建字典分类', {
    inputPattern: /.+/,
    inputErrorMessage: '分类名不能为空',
  })
    .then(({ value }) => {
      const id = Math.max(0, ...categories.value.map((c: any) => c.id)) + 1
      const code = 'cat_' + id
      categories.value.push({ id, code, name: value, desc: '新建分类', itemCount: 0 })
      ElMessage.success(`已新建字典分类「${value}」`)
    })
    .catch(() => {})
}

function onNewItem() {
  if (!selectedCat.value) {
    ElMessage.warning('请先选择字典分类')
    return
  }
  ElMessageBox.prompt(`在「${selectedCat.value.name}」下新建字典项`, '新建字典项', {
    inputPattern: /.+/,
    inputErrorMessage: '字典项名不能为空',
  })
    .then(({ value }) => {
      const id = Math.max(0, ...items.value.map((i: any) => i.id)) + 1
      items.value.push({
        id,
        categoryId: selectedCat.value!.id,
        code: selectedCat.value!.code + '_' + id,
        name: value,
        order: items.value.length + 1,
        enabled: true,
      })
      ElMessage.success('已新增')
    })
    .catch(() => {})
}

function onEditItem(row: any) {
  ElMessageBox.prompt('修改字典项名称', '编辑字典项', {
    inputValue: row.name,
    inputPattern: /.+/,
    inputErrorMessage: '字典项名不能为空',
  })
    .then(({ value }) => {
      row.name = value
      ElMessage.success('已修改')
    })
    .catch(() => {})
}

async function onDeleteItem(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除字典项「${row.name}」？相关下拉选项也会一并移除。`, '删除字典项', { type: 'warning' })
    const r: any = await adminApi.dictDelete(row.id).catch(() => null)
    if (r?.code === 0 || r?.deleted) {
      items.value = items.value.filter(i => i.id !== row.id)
      ElMessage.success('已删除')
    } else {
      ElMessage.error(r?.message || '删除失败')
    }
  } catch { /* cancel */ }
}

function onBatchEnable(enabled: boolean) {
  if (!selectedItems.value.length) {
    ElMessage.warning('请先勾选字典项')
    return
  }
  selectedItems.value.forEach((i: any) => { i.enabled = enabled })
  ElMessage.success(`已${enabled ? '启用' : '禁用'} ${selectedItems.value.length} 项`)
}

function onSyncToDropdown() {
  ElMessage.success(`已将「${selectedCat.value?.name}」的 ${items.value.length} 项同步至下拉选项`)
}

function onSelection(rows: any[]) { selectedItems.value = rows }

onMounted(loadCategories)

// ---- mock 数据 ----
const mockCategories: any[] = [
  { id: 1, code: 'industry',      name: '行业分类',  desc: '客户所属行业',                  itemCount: 6 },
  { id: 2, code: 'customer_lvl',  name: '客户等级',  desc: 'A/B/C/D 四级,影响审批与折扣',  itemCount: 4 },
  { id: 3, code: 'expense_type',  name: '费用类型',  desc: '差旅/办公/招待/其他',          itemCount: 8 },
  { id: 4, code: 'contract_status', name: '合同状态', desc: '草稿/审批中/已签/已归档',     itemCount: 5 },
  { id: 5, code: 'project_status', name: '项目状态', desc: '待启动/进行中/已验收/已关闭', itemCount: 4 },
  { id: 6, code: 'invoice_type',  name: '发票类型',  desc: '增值税专用/普通/电子发票',     itemCount: 5 },
]

const mockItems: Record<string, any[]> = {
  industry: [
    { id: 101, categoryId: 1, code: 'manufacture', name: '制造业',   order: 1, enabled: true },
    { id: 102, categoryId: 1, code: 'finance',     name: '金融业',   order: 2, enabled: true },
    { id: 103, categoryId: 1, code: 'retail',      name: '零售批发', order: 3, enabled: true },
    { id: 104, categoryId: 1, code: 'it',          name: 'IT/互联网', order: 4, enabled: true },
    { id: 105, categoryId: 1, code: 'education',   name: '教育',     order: 5, enabled: false },
    { id: 106, categoryId: 1, code: 'medical',     name: '医疗',     order: 6, enabled: true },
  ],
  customer_lvl: [
    { id: 201, categoryId: 2, code: 'A', name: 'A级·战略客户', order: 1, enabled: true },
    { id: 202, categoryId: 2, code: 'B', name: 'B级·重点客户', order: 2, enabled: true },
    { id: 203, categoryId: 2, code: 'C', name: 'C级·普通客户', order: 3, enabled: true },
    { id: 204, categoryId: 2, code: 'D', name: 'D级·潜在客户', order: 4, enabled: true },
  ],
  expense_type: [
    { id: 301, categoryId: 3, code: 'travel_trans', name: '差旅·交通', order: 1, enabled: true },
    { id: 302, categoryId: 3, code: 'travel_hotel', name: '差旅·住宿', order: 2, enabled: true },
    { id: 303, categoryId: 3, code: 'office',       name: '办公用品',  order: 3, enabled: true },
    { id: 304, categoryId: 3, code: 'entertain',    name: '业务招待',  order: 4, enabled: true },
    { id: 305, categoryId: 3, code: 'meals',        name: '工作餐',    order: 5, enabled: true },
    { id: 306, categoryId: 3, code: 'comm',         name: '通讯费',    order: 6, enabled: true },
    { id: 307, categoryId: 3, code: 'training',     name: '培训费',    order: 7, enabled: true },
    { id: 308, categoryId: 3, code: 'other',        name: '其他',      order: 8, enabled: true },
  ],
  contract_status: [
    { id: 401, categoryId: 4, code: 'draft',   name: '草稿',   order: 1, enabled: true },
    { id: 402, categoryId: 4, code: 'approving', name: '审批中', order: 2, enabled: true },
    { id: 403, categoryId: 4, code: 'signed',  name: '已签订', order: 3, enabled: true },
    { id: 404, categoryId: 4, code: 'archived', name: '已归档', order: 4, enabled: true },
    { id: 405, categoryId: 4, code: 'cancelled', name: '已取消', order: 5, enabled: true },
  ],
  project_status: [
    { id: 501, categoryId: 5, code: 'pending', name: '待启动',   order: 1, enabled: true },
    { id: 502, categoryId: 5, code: 'active',  name: '进行中',   order: 2, enabled: true },
    { id: 503, categoryId: 5, code: 'accepted', name: '已验收',  order: 3, enabled: true },
    { id: 504, categoryId: 5, code: 'closed',  name: '已关闭',   order: 4, enabled: true },
  ],
  invoice_type: [
    { id: 601, categoryId: 6, code: 'special_vat', name: '增值税专用发票', order: 1, enabled: true },
    { id: 602, categoryId: 6, code: 'general_vat', name: '增值税普通发票', order: 2, enabled: true },
    { id: 603, categoryId: 6, code: 'electronic',   name: '电子发票',       order: 3, enabled: true },
    { id: 604, categoryId: 6, code: 'roll',         name: '卷式发票',       order: 4, enabled: false },
    { id: 605, categoryId: 6, code: 'custom',       name: '海关代征',       order: 5, enabled: true },
  ],
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>数据字典</h2>
        <p class="page-desc">维护业务下拉、状态、类型等基础数据</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="onNewCategory">新建分类</el-button>
    </div>

    <div class="admin-split">
      <!-- 左：字典分类 -->
      <div class="admin-split-left">
        <div
          v-for="c in categories"
          :key="c.id"
          class="admin-list-item"
          :class="{ active: selectedCatId === c.id }"
          @click="selectCat(c)"
        >
          <span class="ali-icon">📖</span>
          <div style="flex:1; min-width:0;">
            <div class="ali-name">{{ c.name }}</div>
            <div style="font-size:11.5px; color:var(--el-text-color-secondary); margin-top:2px;">{{ c.desc }}</div>
          </div>
          <span class="ali-count">{{ c.itemCount }}</span>
        </div>
      </div>

      <!-- 右：字典项表格 -->
      <div class="admin-split-right" v-if="selectedCat">
        <h3 class="admin-section-title">
          {{ selectedCat.name }} · 字典项
          <el-tag size="small" type="primary" effect="plain" style="margin-left:6px;">{{ items.length }} 项</el-tag>
        </h3>
        <div class="tip-box">
          <span class="ico">i</span>
          <span>字典项会作为下拉选项、筛选条件被前端各模块引用,修改后请执行「同步到下拉」。</span>
        </div>

        <div class="admin-toolbar">
          <el-button type="primary" :icon="'Plus'" @click="onNewItem">新建字典项</el-button>
          <el-button :disabled="!selectedItems.length" @click="onBatchEnable(true)">批量启用</el-button>
          <el-button :disabled="!selectedItems.length" type="danger" plain @click="onBatchEnable(false)">批量禁用</el-button>
          <span class="spacer" />
          <el-button :icon="'Refresh'" @click="onSyncToDropdown">同步到下拉</el-button>
        </div>

        <el-table :data="items" stripe @selection-change="onSelection">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="code" label="编码" width="180" />
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="order" label="排序" width="80" align="center" />
          <el-table-column label="启用" width="100">
            <template #default="{ row }">
              <el-switch :model-value="row.enabled" disabled />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="onEditItem(row as any)">编辑</el-button>
              <el-button link type="primary" size="small">{{ row.enabled ? '禁用' : '启用' }}</el-button>
              <el-button link type="danger" size="small" @click="onDeleteItem(row as any)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="该分类暂无字典项" /></template>
        </el-table>
      </div>
      <div v-else class="admin-split-right" style="display:flex;align-items:center;justify-content:center;color:var(--el-text-color-secondary);">
        请从左侧选择字典分类
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
</style>
