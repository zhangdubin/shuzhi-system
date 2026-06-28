<script setup lang="ts">
/**
 * AdminPrintLog · 打印日志查询（M2 阶段 7：补前端模块）
 *
 * 后端端点：POST /api/v1/print/log
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { printApi } from '@/api/print'

const logs = ref<any[]>([])
const loading = ref(false)
const total = ref(0)

const filter = reactive<{ templateCode: string; status: string }>({
  templateCode: '',
  status: '',
})

const kpis = computed(() => {
  const all = logs.value
  return [
    { label: '本次查询', num: total.value, color: 'primary', icon: '📋' },
    { label: '成功', num: all.filter(l => l.status === 'success').length, color: 'success', icon: '✓' },
    { label: '失败', num: all.filter(l => l.status === 'failed').length, color: 'danger', icon: '✗' },
    { label: 'PDF 总大小', num: formatSize(all.reduce((s, l) => s + (l.pdfSize || 0), 0)), color: 'info', icon: '💾' },
    { label: '平均耗时', num: `${avgElapsed(all)}ms`, color: 'warning', icon: '⚡' },
  ]
})

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function avgElapsed(rows: any[]): number {
  const valid = rows.filter(r => typeof r.elapsedMs === 'number')
  if (!valid.length) return 0
  return Math.round(valid.reduce((s, r) => s + r.elapsedMs, 0) / valid.length)
}

async function loadList() {
  loading.value = true
  try {
    const r = await printApi.listLogs({
      page: 1,
      pageSize: 50,
      templateCode: filter.templateCode || undefined,
    }).catch(() => ({ list: [], total: 0 }))
    logs.value = r.list || []
    total.value = r.total || 0
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

function statusTag(s: string) {
  return s === 'success' ? 'success' : 'danger'
}

function statusLabel(s: string) {
  return s === 'success' ? '成功' : '失败'
}

function actionLabel(a: string) {
  return a === 'pdf' ? 'PDF' : a === 'html' ? '预览' : a
}

// M5 阶段 3: 用量统计
const stats = ref<any>(null)
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await printApi.getStats(30)
  } catch { /* ignore */ }
  finally { statsLoading.value = false }
}

onMounted(() => { loadList(); loadStats() })
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>📜 打印日志</h1>
        <p class="page-desc">UDPE 渲染 / 导出审计记录 · 评审决策 #5：完整 request_data 快照</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadList">🔄 刷新</el-button>
      </div>
    </div>

    <!-- 用量统计 (M5 阶段 3) -->
    <div v-if="stats" class="stats-section">
      <div class="stats-grid">
        <div class="stat-card stat-primary">
          <div class="stat-num">{{ stats.total }}</div>
          <div class="stat-label">30 天总调用</div>
        </div>
        <div class="stat-card stat-success">
          <div class="stat-num">{{ stats.success }}</div>
          <div class="stat-label">成功</div>
        </div>
        <div class="stat-card stat-danger">
          <div class="stat-num">{{ stats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
        <div class="stat-card stat-info">
          <div class="stat-num">{{ stats.avgElapsedMs }}ms</div>
          <div class="stat-label">平均耗时</div>
        </div>
        <div class="stat-card stat-warning">
          <div class="stat-num">{{ stats.totalPdfSizeMb }}MB</div>
          <div class="stat-label">PDF 总量</div>
        </div>
      </div>
      <!-- 最近 7 天趋势 -->
      <div class="trend-row">
        <div class="trend-label">最近 7 天：</div>
        <div class="trend-bars">
          <div v-for="d in stats.daily" :key="d.date" class="trend-bar-wrap" :title="`${d.date}: ${d.count} 次`">
            <div class="trend-bar" :style="{ height: Math.max(4, d.count * 8) + 'px' }" />
            <div class="trend-day">{{ d.date.slice(5) }}</div>
          </div>
        </div>
      </div>
      <!-- Top 模板 -->
      <div v-if="stats.topTemplates.length" class="top-templates">
        <span class="top-label">热门模板：</span>
        <el-tag v-for="t in stats.topTemplates" :key="t.code" size="small" style="margin-right: 6px;">
          {{ t.code }} ({{ t.count }})
        </el-tag>
      </div>
    </div>

    <div class="kpi-grid">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', `kpi-${k.color}`]">
        <div class="kpi-icon">{{ k.icon }}</div>
        <div class="kpi-body">
          <div class="kpi-num">{{ k.num }}</div>
          <div class="kpi-label">{{ k.label }}</div>
        </div>
      </div>
    </div>

    <div class="filter-bar">
      <span class="filter-label">模板 code：</span>
      <el-input v-model="filter.templateCode" placeholder="留空查全部" size="small" style="width: 240px;" clearable @keyup.enter="loadList" @clear="loadList" />
      <el-button size="small" type="primary" style="margin-left: 8px;" @click="loadList">查询</el-button>
    </div>

    <div class="detail-section">
      <div class="detail-section-body">
        <el-table v-loading="loading" :data="logs" stripe>
          <el-table-column label="log# / 时间" width="180">
            <template #default="{ row }">
              <div class="log-id">#{{ row.id }}</div>
              <div class="log-time">{{ row.createdAt || '—' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.action === 'pdf' ? 'primary' : 'info'">
                {{ actionLabel(row.action) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="模板" min-width="200">
            <template #default="{ row }">
              <div class="tpl-row">
                <span class="tpl-code">{{ row.templateCode }}</span>
                <span class="tpl-doctype">{{ row.docType }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status) as any" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作员" min-width="120">
            <template #default="{ row }">{{ row.operatorName || '—' }}</template>
          </el-table-column>
          <el-table-column label="来源" min-width="160">
            <template #default="{ row }">
              <span v-if="row.sourceModule">{{ row.sourceModule }} #{{ row.sourceId || '—' }}</span>
              <span v-else style="color:#9CA3AF;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="80">
            <template #default="{ row }">
              <span v-if="row.elapsedMs !== null && row.elapsedMs !== undefined">{{ row.elapsedMs }}ms</span>
              <span v-else style="color:#9CA3AF;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="PDF 大小" width="100">
            <template #default="{ row }">
              <span v-if="row.pdfSize">{{ formatSize(row.pdfSize) }}</span>
              <span v-else style="color:#9CA3AF;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.errorMsg" style="color:#DC2626;">{{ row.errorMsg }}</span>
              <span v-else style="color:#9CA3AF;">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; margin: 0 0 4px 0; }
.page-desc { font-size: 13px; color: #6B7280; margin: 0; }
.page-actions { display: flex; gap: 8px; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; padding: 0 24px 16px; }
.kpi-card { background: #FFFFFF; border-radius: 10px; padding: 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kpi-icon { font-size: 24px; }
.kpi-num { font-size: 22px; font-weight: 600; line-height: 1.2; color: #0F172A; }
.kpi-label { font-size: 12px; color: #6B7280; }
.kpi-primary { border-left: 3px solid #4F6BFF; }
.kpi-success { border-left: 3px solid #10B981; }
.kpi-warning { border-left: 3px solid #F59E0B; }
.kpi-info { border-left: 3px solid #6B7280; }
.kpi-danger { border-left: 3px solid #DC2626; }

.filter-bar { display: flex; align-items: center; padding: 0 24px 12px; }
.filter-label { font-size: 13px; color: #6B7280; }

.detail-section { background: #FFFFFF; border-radius: 12px; margin: 0 24px 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.detail-section-body { padding: 12px 16px; }

.log-id { font-family: 'SF Mono', Menlo, monospace; font-size: 13px; color: #4F6BFF; font-weight: 500; }
.log-time { font-size: 11px; color: #6B7280; margin-top: 2px; }

.tpl-row { display: flex; flex-direction: column; gap: 2px; }
.tpl-code { font-family: 'SF Mono', Menlo, monospace; font-size: 12.5px; color: #1F2937; }
.tpl-doctype { font-size: 11px; color: #9CA3AF; }
.stats-section {
  padding: 0 24px 16px;
}
.stats-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;
  margin-bottom: 12px;
}
.stat-card {
  background: #FFFFFF; border-radius: 10px; padding: 16px;
  text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.stat-num { font-size: 24px; font-weight: 700; color: #0F172A; }
.stat-label { font-size: 12px; color: #6B7280; margin-top: 4px; }
.stat-primary { border-top: 3px solid #4F6BFF; }
.stat-success { border-top: 3px solid #10B981; }
.stat-danger { border-top: 3px solid #DC2626; }
.stat-info { border-top: 3px solid #6B7280; }
.stat-warning { border-top: 3px solid #F59E0B; }
.trend-row { display: flex; align-items: flex-end; gap: 12px; margin-bottom: 8px; }
.trend-label { font-size: 12px; color: #6B7280; flex-shrink: 0; }
.trend-bars { display: flex; gap: 6px; align-items: flex-end; }
.trend-bar-wrap { display: flex; flex-direction: column; align-items: center; }
.trend-bar { width: 24px; background: #4F6BFF; border-radius: 3px 3px 0 0; min-height: 4px; }
.trend-day { font-size: 10px; color: #9CA3AF; margin-top: 2px; }
.top-templates { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #6B7280; }
.top-label { flex-shrink: 0; }
</style>
