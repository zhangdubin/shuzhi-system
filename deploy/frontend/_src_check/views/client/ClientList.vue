<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clientApi, type Client, type ClientLevel, type ClientStatus } from '@/api/client'

const router = useRouter()

const loading = ref(false)
const list = ref<Client[]>([])
const total = ref(0)
const query = reactive({ page: 1, pageSize: 10, keyword: '' })

// 统计卡（接口 mock 阶段前端给默认 0，失败时静默）
const stats = reactive({
  total: 0,
  active: 0,
  newThisMonth: 0,
  pending: 0,
})

async function loadList() {
  loading.value = true
  try {
    const res = await clientApi
      .list(query)
      .catch(() => ({ list: [], total: 0, page: 1, pageSize: 10 }))
    list.value = (res as any).list || []
    total.value = (res as any).total || 0
  } catch {
    ElMessage.error('加载客户列表失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const res = await clientApi.stats().catch(() => null)
    if (res) Object.assign(stats, res)
  } catch {
    /* 静默 */
  }
}

function handleSearch() {
  query.page = 1
  loadList()
}

function handlePageChange(p: number) {
  query.page = p
  loadList()
}

function gotoCreate() {
  router.push('/client/create')
}

function gotoDetail(row: Client) {
  // 客户详情路由暂未实现，给个友好提示并跳编辑/创建
  ElMessage.info(`客户详情开发中：${row.name}`)
}

function gotoEdit(row: Client) {
  ElMessage.info(`编辑功能开发中：${row.name}`)
}

function followUp(row: Client) {
  ElMessage.success(`已记录跟进：${row.name}`)
}

function convertToContract(row: Client) {
  ElMessage.success(`已发起转合同：${row.name}`)
}

function handleDelete(row: Client) {
  ElMessage.success(`已删除（演示）：${row.name}`)
}

// ---------- 等级 / 状态 配色（与 design 稿 A/B/C/D 对齐） ----------
const levelOptions: { value: ClientLevel; label: string; cls: string }[] = [
  { value: 'A', label: 'A · 战略', cls: 'tag tag-warning' },
  { value: 'B', label: 'B · 重点', cls: 'tag tag-primary' },
  { value: 'C', label: 'C · 普通', cls: 'tag tag-success' },
  { value: 'D', label: 'D · 潜在', cls: 'tag tag-info' },
]

function levelTagClass(level: ClientLevel) {
  return levelOptions.find((o) => o.value === level)?.cls ?? 'tag tag-info'
}

function levelLabel(level: ClientLevel) {
  return levelOptions.find((o) => o.value === level)?.label ?? level
}

const statusMap: Record<ClientStatus, { label: string; cls: string }> = {
  active: { label: '合作中', cls: 'tag tag-success' },
  paused: { label: '暂停', cls: 'tag tag-warning' },
  lost: { label: '已流失', cls: 'tag tag-danger' },
}

function statusTagClass(s: ClientStatus) {
  return statusMap[s]?.cls ?? 'tag tag-info'
}

const statCards = computed(() => [
  { key: 'total', label: '客户总数', value: stats.total, tone: 'primary', icon: '👥' },
  { key: 'active', label: '活跃客户', value: stats.active, tone: 'success', icon: '🤝' },
  { key: 'new', label: '本月新增', value: stats.newThisMonth, tone: 'warning', icon: '✨' },
  { key: 'pending', label: '待跟进', value: stats.pending, tone: 'danger', icon: '⏰' },
])

onMounted(() => {
  loadStats()
  loadList()
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部：标题 + 搜索 + 新建 -->
    <div class="page-header">
      <div>
        <h2>客户管理</h2>
        <p class="page-desc">客户档案全生命周期管理 · 合同/回款/发票均可引用</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="gotoCreate">新建客户</el-button>
    </div>

    <!-- 统计卡 4 个 -->
    <div class="stat-grid">
      <div v-for="s in statCards" :key="s.key" :class="['stat-card', `stat-${s.tone}`]">
        <div class="ic">{{ s.icon }}</div>
        <div class="meta">
          <div class="l">{{ s.label }}</div>
          <div class="v">{{ s.value.toLocaleString() }}</div>
        </div>
      </div>
    </div>

    <!-- 列表卡 -->
    <div class="page-card">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索客户名 / 纳税人识别号 / 联系人"
          clearable
          style="width: 320px"
          @keyup.enter="handleSearch"
        />
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button :icon="'Refresh'" @click="handleSearch">刷新</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="list"
        stripe
        @row-click="gotoDetail"
        row-class-name="clickable"
      >
        <el-table-column prop="code" label="客户编号" width="160" />
        <el-table-column prop="name" label="客户名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="contactName" label="联系人" width="100" />
        <el-table-column prop="contactPhone" label="电话" width="140" />
        <el-table-column prop="industry" label="行业" width="120" />
        <el-table-column label="等级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="(row as Client).level === 'A' ? 'danger' : (row as Client).level === 'B' ? 'warning' : 'info'" size="small">
              {{ (row as Client).level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contactEmail" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(row as Client).isActive === false ? 'danger' : 'success'" size="small">
              {{ (row as Client).isActive === false ? '已停用' : '合作中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="row-actions" @click.stop>
              <el-button link type="primary" size="small" @click="gotoEdit(row as Client)">编辑</el-button>
              <el-button link type="primary" size="small" @click="followUp(row as Client)">跟进</el-button>
              <el-button link type="primary" size="small" @click="convertToContract(row as Client)">转合同</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无客户数据" /></template>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="pager"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

:deep(.clickable) {
  cursor: pointer;
}

// ---------- 统计卡 ----------
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  position: relative;
  overflow: hidden;
  transition: all 0.15s;
  &::after {
    content: '';
    position: absolute;
    right: -30px;
    top: -30px;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    opacity: 0.12;
  }
  .ic {
    width: 44px;
    height: 44px;
    border-radius: $radius-md;
    display: grid;
    place-items: center;
    font-size: 22px;
    flex-shrink: 0;
  }
  .meta .l {
    font-size: 12px;
    color: $color-text-tertiary;
    margin-bottom: 4px;
  }
  .meta .v {
    font-size: 22px;
    font-weight: 700;
    color: $color-text-primary;
    line-height: 1.1;
  }

  &.stat-primary .ic { background: $color-primary-bg; color: $color-primary; }
  &.stat-primary::after { background: $color-primary; }
  &.stat-success .ic { background: $color-success-bg; color: $color-success; }
  &.stat-success::after { background: $color-success; }
  &.stat-warning .ic { background: $color-warning-bg; color: $color-warning; }
  &.stat-warning::after { background: $color-warning; }
  &.stat-danger .ic { background: $color-danger-bg; color: $color-danger; }
  &.stat-danger::after { background: $color-danger; }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
  }
}

// ---------- 表格 ----------
.row-actions {
  display: flex;
  gap: 4px;
  flex-wrap: nowrap;
}

.num {
  font-family: $font-family-mono;
  font-weight: 600;
}
</style>