<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { invoiceTemplateApi } from '@/api/modules'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const query = reactive({ page: 1, pageSize: 12, keyword: '', category: '' })

// 4 KPI 统计
const stats = computed(() => {
  const all = list.value
  return {
    total: total.value,
    active: all.filter(t => t.status === 'active').length,
    market: all.filter(t => t.isMarket).length,
    pinned: all.filter(t => t.isPinned).length,
  }
})

const CAT_OPTIONS = [
  { value: '差旅', label: '差旅' },
  { value: '招待', label: '招待' },
  { value: '办公', label: '办公' },
  { value: '推广', label: '推广' },
  { value: '培训', label: '培训' },
  { value: '其他', label: '其他' },
]

const CAT_GRADIENT: Record<string, string> = {
  差旅: 'linear-gradient(135deg,#4F6BFF,#7C3AED)',
  招待: 'linear-gradient(135deg,#EC4899,#BE185D)',
  办公: 'linear-gradient(135deg,#10B981,#059669)',
  推广: 'linear-gradient(135deg,#F59E0B,#D97706)',
  培训: 'linear-gradient(135deg,#8B5CF6,#6D28D9)',
  其他: 'linear-gradient(135deg,#06B6D4,#0891B2)',
}

async function load() {
  loading.value = true
  try {
    const res: any = await invoiceTemplateApi.list(query).catch(() => ({ list: [], total: 0 }))
    list.value = res.list || []
    total.value = res.total || 0
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; load() }
function gotoDetail(row: any) { router.push(`/invoice/template/${row.templateId || row.id}`) }
function gotoEdit(row: any) { router.push(`/invoice/template/${row.templateId || row.id}/edit`) }
function onNew() { router.push('/invoice/template/edit') }
function onCopy(row: any) {
  ElMessageBox.prompt('复制模板名称', '复制模板', { inputValue: row.name + ' (副本)', inputPattern: /.+/, inputErrorMessage: '名称不能为空' })
    .then(() => ElMessage.success('已复制（演示）'))
    .catch(() => {})
}
function onDelete(row: any) {
  ElMessageBox.confirm(`确定删除模板「${row.name}」？`, '删除确认', { type: 'warning' })
    .then(() => { list.value = list.value.filter(x => x.id !== row.id); ElMessage.success('已删除') })
    .catch(() => {})
}
function fmtDate(s?: string) { return s ? s.slice(0, 10) : '—' }
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>发票模板</h2>
        <p class="page-desc">按业务场景配置的发票模板库 · 共 {{ total }} 个</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="onNew">+ 新建模板</el-button>
    </div>

    <!-- 4 KPI 卡 -->
    <div class="kpi-grid">
      <div class="kpi-card tone-primary">
        <div class="ic">▣</div>
        <div class="meta"><div class="l">模板总数</div><div class="v">{{ stats.total }}</div></div>
      </div>
      <div class="kpi-card tone-success">
        <div class="ic">✓</div>
        <div class="meta"><div class="l">启用中</div><div class="v">{{ stats.active }}</div></div>
      </div>
      <div class="kpi-card tone-info">
        <div class="ic">🏪</div>
        <div class="meta"><div class="l">模板市场</div><div class="v">{{ stats.market }}</div></div>
      </div>
      <div class="kpi-card tone-warning">
        <div class="ic">📌</div>
        <div class="meta"><div class="l">已固定</div><div class="v">{{ stats.pinned }}</div></div>
      </div>
    </div>

    <div class="page-card">
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="搜索模板名 / 编号" clearable style="width: 240px" @keyup.enter="handleSearch" />
        <el-select v-model="query.category" placeholder="类别" clearable style="width: 140px">
          <el-option v-for="c in CAT_OPTIONS" :key="c.value" :label="c.label" :value="c.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.keyword='';query.category='';handleSearch()">重置</el-button>
      </div>

      <div v-loading="loading" class="tpl-grid">
        <div v-for="t in list" :key="t.id" class="tpl-card" @click="gotoDetail(t)">
          <div class="tpl-status">
            <el-tag v-if="t.isPinned" size="small" type="warning" effect="dark">📌</el-tag>
            <el-tag v-if="t.isMarket" size="small" type="success">🏪 市场</el-tag>
            <el-tag :type="t.status === 'active' ? 'success' : 'info'" size="small">
              {{ t.status === 'active' ? '启用中' : '已停用' }}
            </el-tag>
          </div>
          <div class="tpl-head">
            <div class="tpl-icon" :style="{ background: CAT_GRADIENT[t.category] || CAT_GRADIENT['其他'] }">
              {{ t.category ? t.category.charAt(0) : '?' }}
            </div>
            <div class="tpl-info">
              <h4>{{ t.name }}</h4>
              <p class="mono">{{ t.code }}</p>
            </div>
          </div>
          <div class="tpl-desc" v-if="t.description">{{ t.description }}</div>
          <div class="tpl-tags">
            <span class="tpl-tag">{{ t.fieldCount || (t.fields?.length || 0) }} 字段</span>
            <span class="tpl-tag">使用 {{ t.usageCount || 0 }} 次</span>
            <span class="tpl-tag" v-if="t.rating">⭐ {{ t.rating }}</span>
          </div>
          <div class="tpl-foot">
            <div class="tpl-creator">👤 {{ t.creator || '—' }} · {{ fmtDate(t.updatedAt) }}</div>
            <div class="tpl-actions" @click.stop>
              <el-button type="primary" link size="small" @click.stop="gotoDetail(t)">查看</el-button>
              <el-button type="primary" link size="small" @click.stop="gotoEdit(t)">编辑</el-button>
              <el-button type="primary" link size="small" @click.stop="onCopy(t)">复制</el-button>
              <el-button type="danger" link size="small" @click.stop="onDelete(t)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="!loading && list.length === 0" description="暂无模板" :image-size="80" />
      </div>

      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[6, 12, 24]"
        class="pager"
        @current-change="load"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.kpi-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 18px 20px;
  display: flex; align-items: center; gap: 14px;
  .ic { width: 44px; height: 44px; border-radius: var(--radius-md); display: grid; place-items: center; font-size: 22px; font-weight: 700; }
  .meta .l { font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 4px; }
  .meta .v { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-family: var(--font-family-mono); }
  &.tone-primary .ic { background: var(--color-primary-bg); color: var(--color-primary); }
  &.tone-success .ic { background: var(--color-success-bg); color: var(--color-success); }
  &.tone-warning .ic { background: var(--color-warning-bg); color: var(--color-warning); }
  &.tone-info .ic { background: rgba(124,58,237,0.12); color: #7C3AED; }
}
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.tpl-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;
}
.tpl-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 20px;
  cursor: pointer; transition: all 0.18s;
  &:hover { transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.06); }
  .tpl-status { display: flex; gap: 6px; margin-bottom: 12px; min-height: 22px; }
  .tpl-head { display: flex; gap: 12px; margin-bottom: 12px; }
  .tpl-icon {
    width: 44px; height: 44px; border-radius: 10px;
    color: #fff; font-size: 18px; font-weight: 700;
    display: grid; place-items: center; flex-shrink: 0;
  }
  .tpl-info { flex: 1;
    h4 { margin: 0 0 4px; font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
    p { margin: 0; font-size: 11px; color: var(--color-text-tertiary); }
  }
  .tpl-desc { font-size: 12px; color: var(--color-text-tertiary); line-height: 1.5; margin-bottom: 10px; }
  .tpl-tags { display: flex; gap: 6px; margin-bottom: 12px;
    .tpl-tag { padding: 2px 8px; font-size: 11px; background: var(--color-bg); border-radius: 4px; color: var(--color-text-tertiary); }
  }
  .tpl-foot { display: flex; justify-content: space-between; align-items: center;
    .tpl-creator { font-size: 11px; color: var(--color-text-tertiary); }
    .tpl-actions { display: flex; gap: 0; }
  }
}
.mono { font-family: var(--font-family-mono); }
.pager { margin-top: 16px; justify-content: flex-end; }
</style>
