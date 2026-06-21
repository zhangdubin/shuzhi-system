<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()

// 合同模板数据（design 风格：tpl-card 网格）
const templates = ref([
  {
    id: 1, name: 'SaaS 销售标准合同', desc: '适用于 SaaS 产品的销售，含标准 SLA、付款条款、知识产权',
    icon: '售', gradient: 'linear-gradient(135deg,#4F6BFF,#7C3AED)',
    fields: 24, projects: 12, usage: 156, rating: 4.9, status: 'active', pinned: true,
    creator: '张明', updatedAt: '2 天前', category: 'sales',
  },
  {
    id: 2, name: '软件采购框架协议', desc: '适用于批量采购软件授权，含年付、季度结算',
    icon: '采', gradient: 'linear-gradient(135deg,#10B981,#059669)',
    fields: 18, projects: 6, usage: 88, rating: 4.7, status: 'active', pinned: true,
    creator: '李明', updatedAt: '1 周前', category: 'purchase',
  },
  {
    id: 3, name: '系统集成服务合同', desc: '含项目交付、验收、维护条款',
    icon: '集', gradient: 'linear-gradient(135deg,#F59E0B,#D97706)',
    fields: 32, projects: 18, usage: 124, rating: 4.8, status: 'active', pinned: false,
    creator: '王芳', updatedAt: '3 天前', category: 'service',
  },
  {
    id: 4, name: '咨询服务合同', desc: '管理咨询 / 财务咨询 / IT 咨询',
    icon: '咨', gradient: 'linear-gradient(135deg,#8B5CF6,#6D28D9)',
    fields: 16, projects: 4, usage: 42, rating: 4.6, status: 'active', pinned: false,
    creator: '陈思琪', updatedAt: '1 月前', category: 'service',
  },
  {
    id: 5, name: '设备采购合同', desc: '硬件设备采购，含保修、运输、安装',
    icon: '设', gradient: 'linear-gradient(135deg,#EC4899,#BE185D)',
    fields: 22, projects: 8, usage: 67, rating: 4.5, status: 'paused', pinned: false,
    creator: '刘洋', updatedAt: '2 月前', category: 'purchase',
  },
  {
    id: 6, name: '通用框架协议', desc: '通用框架，可二次定义子合同',
    icon: '框', gradient: 'linear-gradient(135deg,#06B6D4,#0891B2)',
    fields: 12, projects: 3, usage: 28, rating: 4.3, status: 'draft', pinned: false,
    creator: '张明', updatedAt: '3 月前', category: 'framework',
  },
])

const activeCat = ref('all')
const searchKey = ref('')

const filteredTemplates = computedByFilter()

function computedByFilter() {
  return templates.value.filter(t => {
    if (activeCat.value === 'mine' && t.creator !== '张明') return false
    if (activeCat.value === 'pinned' && !t.pinned) return false
    if (searchKey.value && !t.name.includes(searchKey.value)) return false
    return true
  })
}

function statusTag(s: string) {
  return { active: { label: '启用中', type: 'success' }, paused: { label: '已停用', type: 'warning' }, draft: { label: '草稿', type: 'info' } }[s] || { label: s, type: 'info' }
}

function onNew() {
  ElMessageBox.prompt('请输入模板名称', '新建合同模板', { inputPattern: /.+/, inputErrorMessage: '名称不能为空' })
    .then(({ value }) => {
      templates.value.unshift({
        id: Date.now(), name: value, desc: '新创建的模板，编辑完善后启用',
        icon: value.charAt(0), gradient: 'linear-gradient(135deg,#94A3B8,#64748B)',
        fields: 0, projects: 0, usage: 0, rating: 0, status: 'draft', pinned: false,
        creator: '张明', updatedAt: '刚刚', category: 'sales',
      })
      ElMessage.success(`已创建模板「${value}」`)
    })
    .catch(() => {})
}

function onEdit(t: any) {
  ElMessage.info(`打开模板编辑器：${t.name}（编辑器开发中）`)
}

function onCopy(t: any) {
  templates.value.unshift({ ...t, id: Date.now(), name: t.name + ' (副本)', status: 'draft', usage: 0, updatedAt: '刚刚' })
  ElMessage.success('已复制')
}

function onDelete(t: any) {
  ElMessageBox.confirm(`确定删除模板「${t.name}」？`, '删除确认', { type: 'warning' })
    .then(() => {
      templates.value = templates.value.filter(x => x.id !== t.id)
      ElMessage.success('已删除')
    })
    .catch(() => {})
}

function onUse(t: any) {
  ElMessage.success(`已应用模板「${t.name}」到新建合同`)
  router.push('/contract/create')
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>合同模板</h2>
        <p class="page-desc">合同模板管理 · 共 {{ templates.length }} 个</p>
      </div>
      <el-button type="primary" :icon="'Plus'" @click="onNew">+ 新建模板</el-button>
    </div>

    <!-- 4 KPI -->
    <div class="tpl-stats">
      <div class="stat-card">
        <div class="stat-label">模板总数 <span class="stat-icon" style="background:rgba(79,107,255,0.12);color:#4F6BFF;">▣</span></div>
        <div class="stat-value">{{ templates.length }} <span class="unit">个</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">本月使用次数 <span class="stat-icon" style="background:rgba(16,185,129,0.12);color:#10B981;">↻</span></div>
        <div class="stat-value">{{ templates.reduce((s, t) => s + t.usage, 0) }} <span class="unit">次</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">启用中 <span class="stat-icon" style="background:rgba(124,58,237,0.12);color:#7C3AED;">✓</span></div>
        <div class="stat-value">{{ templates.filter(t => t.status === 'active').length }} <span class="unit">个</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已固定 <span class="stat-icon" style="background:rgba(245,158,11,0.12);color:#F59E0B;">📌</span></div>
        <div class="stat-value">{{ templates.filter(t => t.pinned).length }} <span class="unit">个</span></div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="page-card">
      <div class="filter-bar">
        <a :class="['filter-chip', { active: activeCat === 'all' }]" @click="activeCat = 'all'">全部 ({{ templates.length }})</a>
        <a :class="['filter-chip', { active: activeCat === 'mine' }]" @click="activeCat = 'mine'">我创建的</a>
        <a :class="['filter-chip', { active: activeCat === 'pinned' }]" @click="activeCat = 'pinned'">已固定</a>
        <el-input v-model="searchKey" placeholder="搜索模板名..." style="width: 200px; margin-left: auto" clearable />
      </div>

      <!-- 模板网格 -->
      <div class="tpl-grid">
        <div v-for="t in filteredTemplates" :key="t.id" class="tpl-card">
          <div class="tpl-status">
            <el-tag v-if="t.pinned" size="small" type="warning" effect="dark">📌 已固定</el-tag>
            <el-tag :type="statusTag(t.status).type as any" size="small">{{ statusTag(t.status).label }}</el-tag>
          </div>
          <div class="tpl-head">
            <div class="tpl-icon" :style="{ background: t.gradient }">{{ t.icon }}</div>
            <div class="tpl-info">
              <h4>{{ t.name }}</h4>
              <p>{{ t.desc }}</p>
            </div>
          </div>
          <div class="tpl-tags">
            <span class="tpl-tag">{{ t.fields }} 字段</span>
            <span class="tpl-tag" v-if="t.usage > 100">🔥 热门</span>
          </div>
          <div class="tpl-stats">
            <div class="tpl-stat"><div class="v">{{ t.usage }}</div><div class="l">使用次数</div></div>
            <div class="tpl-stat"><div class="v">{{ t.projects }}</div><div class="l">关联项目</div></div>
            <div class="tpl-stat"><div class="v">⭐ {{ t.rating }}</div><div class="l">评分</div></div>
          </div>
          <div class="tpl-foot">
            <div class="tpl-creator">👤 {{ t.creator }} · {{ t.updatedAt }}</div>
            <div class="tpl-actions">
              <el-button type="primary" size="small" link @click="onUse(t)">使用</el-button>
              <el-button type="primary" size="small" link @click="onEdit(t)">编辑</el-button>
              <el-button type="primary" size="small" link @click="onCopy(t)">复制</el-button>
              <el-button type="danger" size="small" link @click="onDelete(t)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="filteredTemplates.length === 0" description="暂无模板" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.tpl-stats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
  .stat-card {
    background: var(--color-bg-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    .stat-label { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px;
      .stat-icon { width: 26px; height: 26px; border-radius: 6px; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
    }
    .stat-value { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-family: var(--font-family-mono);
      .unit { font-size: 12px; color: var(--color-text-tertiary); font-weight: 400; margin-left: 4px; }
    }
  }
}
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center;
  .filter-chip {
    padding: 6px 14px; font-size: 13px; color: var(--color-text-tertiary);
    background: var(--color-bg); border-radius: 20px; cursor: pointer; transition: all 0.15s;
    &:hover { color: var(--color-primary); }
    &.active { background: var(--color-primary); color: #fff; font-weight: 500; }
  }
}
.tpl-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;
}
.tpl-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.18s;
  &:hover { transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.06); }
  .tpl-status { display: flex; gap: 6px; margin-bottom: 12px; }
  .tpl-head { display: flex; gap: 12px; margin-bottom: 14px; }
  .tpl-icon {
    width: 44px; height: 44px; border-radius: 10px;
    color: #fff; font-size: 18px; font-weight: 700;
    display: grid; place-items: center; flex-shrink: 0;
  }
  .tpl-info { flex: 1;
    h4 { margin: 0 0 4px; font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
    p { margin: 0; font-size: 12px; color: var(--color-text-tertiary); line-height: 1.4; }
  }
  .tpl-tags { display: flex; gap: 6px; margin-bottom: 14px;
    .tpl-tag { padding: 2px 8px; font-size: 11px; background: var(--color-bg); border-radius: 4px; color: var(--color-text-tertiary); }
  }
  .tpl-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 10px 0; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); margin-bottom: 12px;
    .tpl-stat { text-align: center;
      .v { font-size: 14px; font-weight: 700; color: var(--color-text-primary); }
      .l { font-size: 11px; color: var(--color-text-tertiary); }
    }
  }
  .tpl-foot { display: flex; justify-content: space-between; align-items: center;
    .tpl-creator { font-size: 11px; color: var(--color-text-tertiary); }
    .tpl-actions { display: flex; gap: 0; }
  }
}
</style>
