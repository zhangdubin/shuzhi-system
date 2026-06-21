<script setup lang="ts">
/**
 * AdminAuditLog · 审计日志
 * - 4 KPI
 * - 搜索（操作人/资源/动作/方法/路径）
 * - 表格：时间/操作人/动作/资源/方法/路径/状态码/IP/UA/耗时
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi, type AuditLogItem } from '@/api/admin'

const list = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)

const filter = reactive({
  keyword: '',
  action: '' as string,
  resourceType: '' as string,
  statusCode: '' as string,
})

async function loadList() {
  loading.value = true
  try {
    const res: any = await adminApi.auditLogList({
      page: 1,
      pageSize: 50,
      keyword: filter.keyword || undefined,
      action: filter.action || undefined,
      resourceType: filter.resourceType || undefined,
      statusCode: filter.statusCode ? Number(filter.statusCode) : undefined,
    } as any)
    list.value = (res?.list || res?.items || []) as AuditLogItem[]
    total.value = res?.total ?? list.value.length
  } catch (e: any) {
    ElMessage.error('加载审计日志失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function fmtTime(s: string | null | undefined) {
  if (!s) return '-'
  try {
    const d = new Date(s)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch { return s }
}

const todayCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return list.value.filter(x => (x.createdAt || '').slice(0, 10) === today).length
})
const errCount = computed(() => list.value.filter(x => (x.statusCode ?? 0) >= 400).length)

const actionOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
]
const resourceOptions = [
  { label: 'admin', value: 'admin' },
  { label: 'invoice', value: 'invoice' },
  { label: 'expense', value: 'expense' },
  { label: 'contract', value: 'contract' },
  { label: 'project', value: 'project' },
  { label: 'client', value: 'client' },
  { label: 'receivable', value: 'receivable' },
  { label: 'auth', value: 'auth' },
]

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">审计日志</h2>
        <p class="page-sub">全量记录所有写操作与异常请求，支持按操作人、资源、动作筛选</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadList" :loading="loading">刷新</el-button>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">本页条数</div>
        <div class="kpi-value">{{ list.length }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">今日操作</div>
        <div class="kpi-value">{{ todayCount }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">本页错误</div>
        <div class="kpi-value" :class="{ 'is-err': errCount > 0 }">{{ errCount }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">服务器总数</div>
        <div class="kpi-value">{{ total }}</div>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="filter.keyword" placeholder="搜索路径/操作人/资源" clearable style="width:240px" @keyup.enter="loadList" />
      <el-select v-model="filter.action" placeholder="动作" clearable style="width:120px">
        <el-option v-for="o in actionOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="filter.resourceType" placeholder="资源类型" clearable style="width:140px">
        <el-option v-for="o in resourceOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-input v-model="filter.statusCode" placeholder="状态码 (如 200/4xx)" clearable style="width:140px" @keyup.enter="loadList" />
      <el-button type="primary" @click="loadList" :loading="loading">查询</el-button>
      <el-button @click="() => { filter.keyword=''; filter.action=''; filter.resourceType=''; filter.statusCode=''; loadList() }">重置</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe border max-height="640">
      <el-table-column prop="createdAt" label="时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column prop="operatorName" label="操作人" width="140" show-overflow-tooltip />
      <el-table-column prop="action" label="动作" width="80" />
      <el-table-column prop="resourceType" label="资源" width="110" />
      <el-table-column prop="resourceCode" label="资源编码" width="160" show-overflow-tooltip />
      <el-table-column prop="method" label="方法" width="80" />
      <el-table-column prop="path" label="路径" min-width="280" show-overflow-tooltip />
      <el-table-column prop="statusCode" label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="(row.statusCode??0) < 400" type="success" size="small">{{ row.statusCode }}</el-tag>
          <el-tag v-else-if="(row.statusCode??0) < 500" type="warning" size="small">{{ row.statusCode }}</el-tag>
          <el-tag v-else type="danger" size="small">{{ row.statusCode }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="140" />
      <el-table-column prop="elapsedMs" label="耗时(ms)" width="100" />
      <el-table-column prop="userAgent" label="UA" min-width="200" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<style scoped>
.page-container { padding: 16px 20px; }
.page-header { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:14px; }
.page-title { font-size:20px; font-weight:600; margin:0; color:#1f2937; }
.page-sub { font-size:12px; color:#909399; margin:4px 0 0; }
.kpi-row { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:14px; }
.kpi-card { background:#fff; border:1px solid #ebeef5; border-radius:8px; padding:14px 16px; }
.kpi-label { font-size:12px; color:#909399; }
.kpi-value { font-size:24px; font-weight:600; color:#1f2937; margin-top:4px; }
.kpi-value.is-err { color:#f56c6c; }
.filter-bar { display:flex; gap:8px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
</style>
