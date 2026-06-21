<script setup lang="ts">
/**
 * AdminDict · 数据字典
 * - 4 KPI（字典分类/字典项/启用/系统内置）
 * - 左：字典分类列表
 * - 右：选中分类的字典项表格
 * - el-dialog：新建/编辑字典项（多字段）
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '@/api/admin'

const categories = ref<any[]>([])
const selectedCatId = ref<number | null>(null)
const items = ref<any[]>([])
const selectedItemIds = ref<number[]>([])

const selectedCat = computed(() => categories.value.find(c => c.id === selectedCatId.value) || null)

// 4 KPI（实际数据从 categories 计算）
const kpis = computed(() => {
  const allItems = items.value
  const totalEnabled = allItems.filter((i: any) => i.isActive).length
  const totalBuiltin = allItems.filter((i: any) => i.builtin).length
  return [
    { label: '字典分类', num: categories.value.length, color: 'info',    icon: '📚', trend: '全部启用' },
    { label: '字典项',   num: allItems.length,         color: 'primary', icon: '📋', trend: `平均 ${(allItems.length / Math.max(categories.value.length, 1)).toFixed(1)} 项/类` },
    { label: '已启用',   num: totalEnabled,            color: 'success', icon: '✓',  trend: `启用率 ${allItems.length ? Math.round(totalEnabled / allItems.length * 100) : 0}%` },
    { label: '系统内置', num: totalBuiltin,            color: 'warning', icon: '🔒', trend: '不可删除' },
  ]
})

async function loadCategories() {
  const res: any = await adminApi.dictTypes().catch(() => null)
  const rows: any[] = res?.list || []
  categories.value = rows
  if (!selectedCatId.value && categories.value.length) selectedCatId.value = categories.value[0].id
  if (selectedCatId.value) loadItems(selectedCatId.value)
}

async function loadItems(catId: number) {
  const cat = categories.value.find(c => c.id === catId)
  if (!cat) return
  const res: any = await adminApi.dictList(cat.code).catch(() => null)
  const rows: any[] = res?.list || []
  items.value = rows.map((it: any) => ({
    id: it.id,
    dictType: it.dictType,
    value: it.value || '',
    label: it.label || '',
    code: it.value || '',
    name: it.label || '',
    color: it.color || '',
    sort: it.sort ?? 0,
    isActive: it.isActive ?? true,
    enabled: it.isActive ?? true,
    desc: it.description || '',
    builtin: !!it.isBuiltin,
  }))
  selectedItemIds.value = []
}

function selectCat(c: any) {
  selectedCatId.value = c.id
  loadItems(c.id)
}

async function onNewCategory() {
  try {
    const { value: name } = await ElMessageBox.prompt('请输入字典分类名称（如：客户等级）', '新建字典分类', { inputPattern: /.+/, inputErrorMessage: '分类名不能为空' })
    const code = 'dict_' + name.toLowerCase().replace(/\s+/g, '_').slice(0, 24)
    const r: any = await adminApi.dictTypeCreate({ code, name }).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.id) {
      ElMessage.success(`已创建分类「${name}」`)
      await loadCategories()
    } else {
      ElMessage.error(r?.message || '创建失败')
    }
  } catch {}
}

// ============ 新建/编辑字典项：el-dialog 弹窗 ============
const editDialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  saving: false,
  form: {
    id: 0 as number,
    label: '',
    value: '',
    sort: 0,
    isActive: true,
    description: '',
    isBuiltin: false,
    color: '',
  },
})

function resetDialog() {
  editDialog.form.id = 0
  editDialog.form.label = ''
  editDialog.form.value = ''
  editDialog.form.sort = 0
  editDialog.form.isActive = true
  editDialog.form.description = ''
  editDialog.form.color = ''
  editDialog.form.isBuiltin = false
  editDialog.mode = 'create'
}

function openNewItemDialog() {
  if (!selectedCat.value) return ElMessage.warning('请先选择字典分类')
  resetDialog()
  editDialog.mode = 'create'
  editDialog.form.sort = items.value.length + 1
  editDialog.form.value = 'item_' + Date.now().toString(36).slice(-6)
  editDialog.visible = true
}

function openEditItem(item: any) {
  if (item.builtin) return ElMessage.warning('系统内置项不可编辑')
  resetDialog()
  editDialog.mode = 'edit'
  editDialog.form.id = item.id
  editDialog.form.label = item.label || item.name || ''
  editDialog.form.value = item.value || item.code || ''
  editDialog.form.sort = item.sort ?? 0
  editDialog.form.isActive = item.isActive ?? true
  editDialog.form.description = item.desc || ''
  editDialog.form.color = item.color || ''
  editDialog.form.isBuiltin = !!item.builtin
  editDialog.visible = true
}

async function saveEditItem() {
  if (!editDialog.form.label.trim()) {
    ElMessage.warning('请输入显示名')
    return
  }
  if (editDialog.mode === 'create' && !editDialog.form.value.trim()) {
    ElMessage.warning('请输入编码')
    return
  }
  if (!selectedCat.value) return
  editDialog.saving = true
  try {
    const payload = {
      dictType: selectedCat.value.code,
      value: editDialog.form.value.trim(),
      label: editDialog.form.label.trim(),
      sort: Number(editDialog.form.sort) || 0,
      isActive: editDialog.form.isActive,
      description: editDialog.form.description || '',
      color: editDialog.form.color || '',
    }
    let r: any
    if (editDialog.mode === 'create') {
      r = await adminApi.dictCreate(payload as any).catch((e: any) => ({ message: e?.message }))
    } else {
      r = await adminApi.dictUpdate(editDialog.form.id, payload as any).catch((e: any) => ({ message: e?.message }))
    }
    if (r?.code === 0 || r?.id || r?.success) {
      ElMessage.success(editDialog.mode === 'create' ? `已添加「${payload.label}」` : '已更新')
      editDialog.visible = false
      await loadItems(selectedCat.value.id)
      await loadCategories()
    } else {
      ElMessage.error(r?.message || '保存失败')
    }
  } finally {
    editDialog.saving = false
  }
}

async function onDeleteItem(item: any) {
  if (item.builtin) return ElMessage.warning('系统内置项不可删除')
  try {
    await ElMessageBox.confirm(`确定删除字典项「${item.label || item.name}」？`, '删除', { type: 'warning' })
    const r: any = await adminApi.dictDelete(item.id).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.deleted) {
      ElMessage.success('已删除')
      if (selectedCat.value) await loadItems(selectedCat.value.id)
      await loadCategories()
    } else {
      ElMessage.error(r?.message || '删除失败')
    }
  } catch {}
}

async function onDeleteCategory() {
  if (!selectedCat.value) return
  if (selectedCat.value.builtin) return ElMessage.warning('系统内置分类不可删除')
  try {
    await ElMessageBox.confirm(`确定删除分类「${selectedCat.value.name}」？分类下 ${items.value.length} 个字典项将一并删除。`, '删除分类', { type: 'warning' })
    const r: any = await adminApi.dictTypeDelete(selectedCat.value.id).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0 || r?.id) {
      ElMessage.success('已删除分类')
      await loadCategories()
    } else {
      ElMessage.error(r?.message || '删除失败（分类下还有字典项）')
    }
  } catch {}
}

async function onToggleItem(item: any) {
  const newState = !item.isActive
  const r: any = await adminApi.dictUpdate(item.id, { isActive: newState } as any).catch((e: any) => ({ message: e?.message }))
  if (r?.code === 0) {
    item.isActive = newState
    ElMessage.success(newState ? '已启用' : '已禁用')
    await loadCategories()
  } else {
    ElMessage.error(r?.message || '操作失败')
  }
}

async function onEditCategory(c: any) {
  if (c.builtin) return ElMessage.warning('系统内置分类不可编辑')
  try {
    const { value: newName } = await ElMessageBox.prompt(
      `修改分类名称（当前：${c.name}）`,
      '编辑字典分类',
      { inputValue: c.name, inputPattern: /.+/, inputErrorMessage: '名称不能为空' }
    )
    const r: any = await adminApi.dictTypeUpdate(c.id, { name: newName } as any).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0) {
      ElMessage.success('已更新')
      await loadCategories()
    } else {
      ElMessage.error(r?.message || '更新失败')
    }
  } catch {}
}

async function onSync() {
  try {
    const cat = selectedCat.value?.code
    const r: any = await adminApi.dictInvalidateCache(cat).catch((e: any) => ({ message: e?.message }))
    await loadCategories()
    if (selectedCatId.value) await loadItems(selectedCatId.value)
    try { localStorage.removeItem('shuzhi_dict_cache') } catch {}
    const n = r?.data?.invalidated ?? r?.invalidated ?? 0
    ElMessage.success(`已同步：失效后端缓存 ${n} 个键 + 刷新当前页`)
  } catch (e: any) {
    ElMessage.error('同步失败：' + (e?.message || '未知错误'))
  }
}

async function batchEnable(enabled: boolean) {
  if (!selectedItemIds.value.length) return ElMessage.warning('请先勾选字典项')
  let ok = 0, fail = 0
  for (const id of selectedItemIds.value) {
    const r: any = await adminApi.dictUpdate(id, { isActive: enabled } as any).catch((e: any) => ({ message: e?.message }))
    if (r?.code === 0) ok++; else fail++
  }
  selectedItemIds.value = []
  if (selectedCatId.value) await loadItems(selectedCatId.value)
  await loadCategories()
  if (fail === 0) ElMessage.success(`已批量${enabled ? '启用' : '禁用'} ${ok} 项`)
  else ElMessage.warning(`完成：成功 ${ok}，失败 ${fail}`)
}

async function batchDelete() {
  if (!selectedItemIds.value.length) return ElMessage.warning('请先勾选字典项')
  const builtinSelected = items.value.filter(i => selectedItemIds.value.includes(i.id) && i.builtin)
  if (builtinSelected.length) {
    return ElMessage.warning(`勾选项包含 ${builtinSelected.length} 个系统内置项，无法删除`)
  }
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedItemIds.value.length} 个字典项？此操作不可恢复。`, '批量删除', { type: 'warning' })
    let ok = 0, fail = 0
    for (const id of selectedItemIds.value) {
      const r: any = await adminApi.dictDelete(id).catch(() => ({ code: -1 }))
      if (r?.code === 0 || r?.deleted) ok++; else fail++
    }
    selectedItemIds.value = []
    if (selectedCat.value) await loadItems(selectedCat.value.id)
    await loadCategories()
    if (fail === 0) ElMessage.success(`已删除 ${ok} 项`)
    else ElMessage.warning(`完成：成功 ${ok}，失败 ${fail}`)
  } catch {}
}

function toggleSelect(id: number) {
  const i = selectedItemIds.value.indexOf(id)
  if (i >= 0) selectedItemIds.value.splice(i, 1)
  else selectedItemIds.value.push(id)
}
function toggleSelectAll() {
  if (selectedItemIds.value.length === items.value.length) selectedItemIds.value = []
  else selectedItemIds.value = items.value.map(i => i.id)
}

onMounted(loadCategories)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>📚 数据字典</h1>
        <p class="page-desc">统一管理系统枚举值（客户等级/费用类型/项目状态等）</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" @click="onNewCategory">+ 新建分类</button>
        <button class="btn btn-outline btn-sm" @click="onSync">🔄 同步到下拉</button>
        <button class="btn btn-primary btn-sm" @click="openNewItemDialog" :disabled="!selectedCat">+ 新建字典项</button>
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

    <!-- 双栏：左分类 + 右字典项 -->
    <div class="dict-layout">
      <!-- 左：分类列表 -->
      <div class="cat-list">
        <div class="cl-head">字典分类（{{ categories.length }}）</div>
        <div class="cl-body">
          <div v-for="c in categories" :key="c.id" :class="['cl-item', { active: selectedCatId === c.id }]" @click="selectCat(c)">
            <div class="cli-icon">📁</div>
            <div class="cli-body">
              <div class="cli-name">
                {{ c.name }}
                <span v-if="c.builtin" class="builtin-tag">内置</span>
              </div>
              <div class="cli-meta">
                <span class="cli-code mono">{{ c.code }}</span>
                <span class="cli-count">{{ c.itemCount }} 项</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：字典项 -->
      <div class="item-panel" v-if="selectedCat">
        <div class="ip-head">
          <div>
            <h3>{{ selectedCat.name }} · 字典项</h3>
            <div class="ip-meta">
              <span>分类编码: <b class="mono">{{ selectedCat.code }}</b></span>
              <span>·</span>
              <span>共 <b class="primary">{{ items.length }}</b> 项</span>
              <span>·</span>
              <span>已启用 <b class="success">{{ items.filter(i => i.enabled).length }}</b></span>
            </div>
          </div>
          <div class="ip-actions">
            <button class="btn btn-outline btn-sm" :disabled="!selectedItemIds.length" @click="batchEnable(true)">✓ 批量启用</button>
            <button class="btn btn-outline btn-sm danger" :disabled="!selectedItemIds.length" @click="batchEnable(false)">✕ 批量禁用</button>
            <button class="btn btn-outline btn-sm danger" :disabled="!selectedItemIds.length" @click="batchDelete">🗑 批量删除</button>
            <button class="btn btn-outline btn-sm" v-if="selectedCat && !selectedCat.builtin" @click="onEditCategory(selectedCat)">✏️ 编辑分类</button>
          <button class="btn btn-outline btn-sm" v-if="!selectedCat.builtin" @click="onDeleteCategory">🗑 删除分类</button>
          </div>
        </div>

        <div class="item-card">
          <table class="tpl-table">
            <thead>
              <tr>
                <th style="width: 40px;">
                  <input type="checkbox" :checked="selectedItemIds.length === items.length && items.length > 0" @change="toggleSelectAll" />
                </th>
                <th style="width: 60px;">排序</th>
                <th>编码</th>
                <th>名称</th>
                <th>说明</th>
                <th style="width: 80px;">状态</th>
                <th style="width: 80px;">类型</th>
                <th style="width: 140px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in items" :key="i.id" :class="{ selected: selectedItemIds.includes(i.id) }">
                <td><input type="checkbox" :checked="selectedItemIds.includes(i.id)" @change="toggleSelect(i.id)" /></td>
                <td><span class="cell-mono">{{ i.sort }}</span></td>
                <td><span class="cell-mono">{{ i.code }}</span></td>
                <td><b>{{ i.name }}</b></td>
                <td class="cell-truncate">{{ i.desc || '—' }}</td>
                <td>
                  <a :class="['tag', i.isActive ? 'success' : 'info']" @click="onToggleItem(i)" style="cursor:pointer">{{ i.isActive ? '启用' : '禁用' }}</a>
                </td>
                <td>
                  <span v-if="i.builtin" class="tag warning">内置</span>
                  <span v-else class="tag soft">自定义</span>
                </td>
                <td>
                  <div class="row-actions">
                    <a class="ra primary" @click="openEditItem(i)">编辑</a>
                    <a v-if="!i.builtin" class="ra danger" @click="onDeleteItem(i)">删除</a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-else class="item-panel empty-panel">
        <div class="empty-icon">👈</div>
        <div class="empty-text">请从左侧选择字典分类</div>
      </div>
    </div>
  </div>

    <!-- 新建/编辑字典项弹窗 -->
    <el-dialog
      v-model="editDialog.visible"
      :title="editDialog.mode === 'create' ? '新建字典项' : '编辑字典项'"
      width="560px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form :model="editDialog.form" label-width="100px" size="default">
        <el-form-item label="显示名" required>
          <el-input v-model="editDialog.form.label" placeholder="如：黄金客户" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="编码" :required="editDialog.mode === 'create'">
          <el-input
            v-model="editDialog.form.value"
            placeholder="如：LEVEL_GOLD"
            maxlength="64"
            :disabled="editDialog.mode === 'edit' && editDialog.form.isBuiltin"
          />
          <span style="font-size:11px;color:#909399;line-height:1.4">
            编码是系统内部值，{{ editDialog.form.isBuiltin ? '内置项不可修改' : '建议使用大写英文+下划线' }}
          </span>
        </el-form-item>
        <el-form-item label="颜色">
          <div class="color-picker-row">
            <el-color-picker v-model="editDialog.form.color" size="default" />
            <el-input v-model="editDialog.form.color" placeholder="如：#7C3AED（标签/列表显示色）" maxlength="16" clearable style="flex:1" />
            <el-button v-if="editDialog.form.color" link size="small" @click="editDialog.form.color = ''">清除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editDialog.form.sort" :min="0" :max="9999" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editDialog.form.isActive" active-text="启用" inactive-text="禁用" inline-prompt />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editDialog.form.description" type="textarea" :rows="3" placeholder="如：年订单 ≥ 100 万" maxlength="256" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="saveEditItem">确定</el-button>
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
.color-picker-row { display: flex; align-items: center; gap: 12px; width: 100%; }
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
.dict-layout { display: grid; grid-template-columns: 240px 1fr; gap: 16px; align-items: start; @media (max-width: 900px) { grid-template-columns: 1fr; } }

// 左：分类列表
.cat-list { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; position: sticky; top: 16px; }
.cl-head { padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF; font-size: 13px; font-weight: 600; color: $color-text-primary; }
.cl-body { padding: 8px; max-height: 700px; overflow-y: auto; }
.cl-item { display: flex; gap: 10px; padding: 10px 12px; border-radius: $radius-md; cursor: pointer; transition: all 0.15s; margin-bottom: 2px; &:hover { background: $color-bg; } &.active { background: $color-primary-bg; border-left: 3px solid $color-primary; padding-left: 9px; } }
.cli-icon { font-size: 18px; flex-shrink: 0; }
.cli-body { flex: 1; min-width: 0; }
.cli-name { font-size: 13px; font-weight: 600; color: $color-text-primary; display: flex; align-items: center; gap: 4px; }
.builtin-tag { font-size: 9.5px; padding: 1px 5px; background: rgba(148, 163, 184, 0.15); color: #64748B; border-radius: 9999px; font-weight: 500; }
.cli-meta { display: flex; gap: 8px; font-size: 11px; color: $color-text-tertiary; margin-top: 2px; flex-wrap: wrap; }
.cli-code { color: $color-text-tertiary; }
.cli-count { color: $color-primary; font-weight: 500; }

// 右：字典项
.item-panel { display: flex; flex-direction: column; gap: 12px; }
.ip-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 14px 16px; h3 { font-size: 15px; font-weight: 600; margin: 0 0 4px 0; } }
.ip-meta { font-size: 12px; color: $color-text-secondary; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; .primary { color: $color-primary; } .success { color: $color-success; } }
.ip-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.item-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid $color-border; }
.tpl-table td { padding: 10px 12px; border-bottom: 1px solid $color-border; }
.tpl-table tbody tr { transition: background 0.15s; &:hover { background: $color-bg; } &.selected { background: $color-primary-bg; } }
.cell-mono { font-family: $font-family-mono; color: $color-text-secondary; font-size: 11.5px; }
.cell-truncate { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: $color-text-tertiary; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.success { background: $color-success-bg; color: $color-success; }
.tag.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.tag.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.tag.soft    { background: $color-primary-bg; color: $color-primary; }

.row-actions { display: flex; gap: 10px; }
.ra { font-size: 12px; cursor: pointer; transition: color 0.15s; &.primary { color: $color-primary; &:hover { text-decoration: underline; } } &.danger { color: $color-danger; &:hover { text-decoration: underline; } } }

// empty
.empty-panel { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; background: #fff; border: 1px dashed $color-border; border-radius: $radius-lg; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.5; }
.empty-text { font-size: 13px; color: $color-text-tertiary; }
</style>
