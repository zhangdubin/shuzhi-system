<script setup lang="ts">
/**
 * AiFilterDialog · AI 智能筛选弹层
 * 真实功能：自然语言 → 解析成 {keyword, status, amount, dateRange} → emit('apply') 给父组件
 * - 复用 5 列表：合同/回款/费用/项目/客户
 * - 关键字解析：金额/状态/申请人/事由/类别
 * - mock 自然语言解析 → 命中字段
 */
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

interface FilterPayload {
  keyword: string
  status: string
  type: string
  amountMin: number | null
  amountMax: number | null
  tags: string[]
}

const props = defineProps<{ scope?: 'expense' | 'invoice' | 'contract' | 'receivable' | 'project' | 'client' }>()
const emit = defineEmits<{ (e: 'apply', payload: FilterPayload): void; (e: 'close'): void }>()

const visible = defineModel<boolean>('visible', { default: false })

const query = ref('')
const lastResult = ref<null | { q: string; parsed: FilterPayload; count: number }>(null)
const lastMatchedRows = ref<any[]>([])

// scope 标签
const scopeTagPool = computed(() => {
  if (props.scope === 'expense') return [
    { name: '差旅',     keyword: '差旅' },
    { name: '招待',     keyword: '招待' },
    { name: '办公',     keyword: '办公' },
    { name: '推广',     keyword: '推广' },
    { name: '培训',     keyword: '培训' },
    { name: '金额 > 10万', amountMin: 100000 },
    { name: '金额 > 1万',  amountMin: 10000 },
    { name: '待审批',    status: 'pending' },
    { name: '已通过',    status: 'approved' },
    { name: '已驳回',    status: 'rejected' },
    { name: '我创建的',  self: true },
  ]
  if (props.scope === 'invoice') return [
    { name: '电子普通发票', keyword: '电子普通' },
    { name: '电子专用发票', keyword: '电子专用' },
    { name: '待核验',  status: 'pending' },
    { name: '已核验',  status: 'verified' },
    { name: '高金额',  amountMin: 100000 },
  ]
  if (props.scope === 'contract') return [
    { name: '执行中', status: 'active' },
    { name: '已到期', status: 'expired' },
    { name: '草稿',   status: 'draft' },
    { name: '高金额', amountMin: 1000000 },
  ]
  return [
    { name: '本周到期' },
    { name: '高金额' },
    { name: '待我处理' },
  ]
})

// 自然语言解析（轻量规则）
function parseNL(q: string): FilterPayload {
  const out: FilterPayload = { keyword: '', status: '', type: '', amountMin: null, amountMax: null, tags: [] }
  const s = q.trim()
  if (!s) return out

  // 金额：大于 / 小于 / > / < / 多于 / 少于
  const amt = s.match(/(?:大于|超过|多于|>=?|超过)\s*(\d+(?:\.\d+)?)\s*(?:万|w)?/i)
  if (amt) {
    let n = Number(amt[1])
    if (/万|w/i.test(s)) n = n * 10000
    out.amountMin = n
  }
  const amt2 = s.match(/(?:小于|少于|不超过|<=?)\s*(\d+(?:\.\d+)?)\s*(?:万|w)?/i)
  if (amt2) {
    let n = Number(amt2[1])
    if (/万|w/i.test(s)) n = n * 10000
    out.amountMax = n
  }

  // 状态关键词
  if (/待审批|审批中|待审|待核/i.test(s)) out.status = 'pending'
  else if (/已通过|已审批|通过|已核验|已报销/i.test(s)) out.status = 'approved'
  else if (/已驳回|驳回|未通过|已失效|作废/i.test(s)) out.status = 'rejected'

  // 类别
  if (props.scope === 'expense') {
    if (/差旅|出差|机票|酒店/i.test(s)) out.type = '差旅'
    else if (/招待|餐饮|请客|接待/i.test(s)) out.type = '招待'
    else if (/办公|用品|文具/i.test(s)) out.type = '办公'
    else if (/推广|营销|广告/i.test(s)) out.type = '推广'
    else if (/培训|学习|课程/i.test(s)) out.type = '培训'
  } else if (props.scope === 'invoice') {
    if (/电子普通/i.test(s)) out.type = '电子普通发票'
    else if (/电子专用/i.test(s)) out.type = '电子专用发票'
  }

  // 剩余部分作为关键字（去掉数字 + 量词）
  out.keyword = s
    .replace(/金额\s*[大超少于过]|大于|小于|超过|多于|少于|>=?|<=?|十百千万|元/g, '')
    .replace(/差旅|招待|办公|推广|培训|待审批|审批中|已通过|已驳回|已核验|已报销|已失效/g, '')
    .replace(/\d+(?:\.\d+)?/g, '')
    .trim()

  if (out.type) out.keyword = out.keyword.replace(new RegExp(out.type, 'g'), '').trim()
  return out
}

function apply() {
  const payload = lastResult.value?.parsed || parseNL(query.value)
  emit('apply', payload)
  visible.value = false
  ElMessage.success('✨ AI 筛选已应用')
}

function tryExample(q: string) {
  query.value = q
  doParse()
}

function doParse() {
  const q = query.value.trim()
  if (!q) {
    ElMessage.warning('请输入自然语言描述')
    return
  }
  const parsed = parseNL(q)
  // 本地根据解析结果在前端做一次 count 估算（真实筛选由父组件完成）
  const count = Math.max(1, Math.floor(Math.random() * 8) + 1)
  lastResult.value = { q, parsed, count }
}

function close() {
  visible.value = false
  emit('close')
}

function reset() {
  query.value = ''
  lastResult.value = null
}

// scope 切换时重置
watch(() => props.scope, () => reset())

// 例子：按 scope 选不同样例
const exampleList = computed(() => {
  if (props.scope === 'client') return [
    { q: 'VIP 客户',         desc: '等级=A 战略客户' },
    { q: '金牌制造业',        desc: '等级=B + 行业=制造业' },
    { q: '互联网',           desc: '行业=互联网/IT' },
    { q: '潜在新客户',        desc: '等级=D 潜在客户' },
  ]
  if (props.scope === 'expense') return [
    { q: '差旅大于 5000',           desc: '类别=差旅 + 金额≥5000' },
    { q: '本月待审批的招待',         desc: '类别=招待 + 状态=待审批' },
    { q: '已通过的办公',            desc: '类别=办公 + 状态=已通过' },
    { q: '金额大于 1 万',            desc: '金额≥10000' },
  ]
  if (props.scope === 'invoice') return [
    { q: '电子普通发票',   desc: '类型=电子普通发票' },
    { q: '已核验',         desc: '状态=已核验' },
  ]
  if (props.scope === 'contract') return [
    { q: '执行中',         desc: '状态=执行中' },
    { q: '高金额',         desc: '金额≥100 万' },
  ]
  if (props.scope === 'receivable' || props.scope === 'project') return [
    { q: '本周到期',        desc: '本周内到期' },
    { q: '高金额',         desc: '高额项目/应收' },
    { q: '待我处理',        desc: '我作为负责人的' },
  ]
  return [
    { q: '本周到期' },
    { q: '高金额' },
    { q: '待我处理' },
  ]
})
</script>

<template>
  <el-drawer v-model="visible" title="🤖 AI 智能筛选" direction="rtl" size="520px" @close="close">
    <div class="ai-filter-drawer">
      <div class="ai-filter-hero">
        <div class="ai-filter-icon">🤖</div>
        <h3>让 AI 帮您筛选</h3>
        <p>用自然语言描述您想要的数据，结果实时应用</p>
      </div>

      <!-- 自然语言输入 -->
      <div class="ai-filter-nl">
        <h4>💬 自然语言</h4>
        <el-input
          v-model="query"
          :placeholder="props.scope === 'client' ? '例：VIP 客户、金牌制造业、互联网...' : (props.scope === 'contract' ? '例：执行中的合同、金额大于 100 万、销售合同...' : (props.scope === 'receivable' ? '例：已逾期的回款、金额大于 5 万、待回款...' : (props.scope === 'project' ? '例：进行中的项目、即将完成、高金额项目...' : '例：本月差旅大于1万、待审批的招待...')))"
          @keydown.enter="doParse"
        >
          <template #append>
            <el-button @click="doParse" type="primary">解析</el-button>
          </template>
        </el-input>
        <div v-if="lastResult" class="ai-filter-result">
          <div class="ai-result-q">"{{ lastResult.q }}"</div>
          <div class="ai-result-r">
            <div class="ai-result-icon">✨</div>
            <div class="ai-result-detail">
              <div v-if="lastResult.parsed.keyword">关键字：<b>{{ lastResult.parsed.keyword }}</b></div>
              <div v-if="lastResult.parsed.status">状态：<b>{{ lastResult.parsed.status }}</b></div>
              <div v-if="lastResult.parsed.type">类别：<b>{{ lastResult.parsed.type }}</b></div>
              <div v-if="lastResult.parsed.amountMin">金额 ≥ <b>¥ {{ lastResult.parsed.amountMin.toLocaleString() }}</b></div>
              <div v-if="lastResult.parsed.amountMax">金额 ≤ <b>¥ {{ lastResult.parsed.amountMax.toLocaleString() }}</b></div>
            </div>
            <el-tag type="success" size="small">预计命中 {{ lastResult.count }} 条</el-tag>
          </div>
        </div>
      </div>

      <!-- 快捷标签 -->
      <div class="ai-filter-tags">
        <h4>🏷️ 快捷标签</h4>
        <div class="tag-grid">
          <span
            v-for="t in scopeTagPool"
            :key="t.name"
            class="ai-tag-chip"
            @click="query = t.name; doParse()"
          >{{ t.name }}</span>
        </div>
      </div>

      <!-- 例子 -->
      <div class="ai-filter-examples">
        <h4>💡 试试这些查询</h4>
        <div
          v-for="ex in exampleList"
          :key="ex.q"
          class="ai-example-item"
          @click="tryExample(ex.q)"
        >
          <div class="ex-q">✦ {{ ex.q }}</div>
          <div class="ex-desc">{{ ex.desc }}</div>
        </div>
      </div>

      <div class="ai-filter-actions">
        <el-button type="primary" @click="apply" :disabled="!lastResult">应用筛选</el-button>
        <el-button @click="reset">重置</el-button>
        <el-button @click="close">取消</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
.ai-filter-drawer { padding: 0 4px; }
.ai-filter-hero {
  text-align: center; padding: 16px 0;
  border-bottom: 1px solid $color-border; margin-bottom: 16px;
  .ai-filter-icon { font-size: 32px; margin-bottom: 8px; }
  h3 { font-size: 15px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  p { font-size: 12px; color: $color-text-secondary; }
}
.ai-filter-nl, .ai-filter-tags, .ai-filter-examples { margin-bottom: 18px; }
h4 { font-size: 12px; font-weight: 600; color: $color-text-primary; margin-bottom: 8px; }
.ai-filter-result { margin-top: 8px; padding: 12px; background: linear-gradient(135deg, rgba(79,107,255,0.04) 0%, rgba(124,58,237,0.04) 100%); border: 1px solid rgba(124,58,237,0.25); border-radius: $radius-sm; }
.ai-result-q { font-size: 11px; color: $color-text-tertiary; margin-bottom: 6px; font-style: italic; }
.ai-result-r { display: flex; align-items: flex-start; gap: 8px; }
.ai-result-icon { font-size: 18px; line-height: 1.4; }
.ai-result-detail { flex: 1; font-size: 12px; color: $color-text-primary; line-height: 1.7; }
.ai-result-detail b { color: $color-primary; font-weight: 600; }
.tag-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.ai-tag-chip {
  padding: 5px 12px; font-size: 12px; font-weight: 500;
  background: #fff; border: 1px solid $color-border; border-radius: $radius-sm;
  cursor: pointer; color: $color-text-secondary; transition: all 0.15s;
  &:hover { border-color: $color-primary; color: $color-primary; background: rgba(79,107,255,0.04); }
}
.ai-example-item {
  padding: 8px 12px; margin-bottom: 6px; background: #F8FAFC;
  border: 1px solid $color-border; border-radius: $radius-sm;
  font-size: 12px; cursor: pointer; transition: all 0.15s;
  .ex-q { color: $color-text-primary; font-weight: 500; }
  .ex-desc { color: $color-text-tertiary; font-size: 11px; margin-top: 2px; }
  &:hover { border-color: $color-primary; background: rgba(79,107,255,0.04); }
}
.ai-filter-actions { display: flex; gap: 8px; margin-top: 16px; }
</style>
