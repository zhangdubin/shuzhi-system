<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { receivableApi } from '@/api/modules'

const router = useRouter()
const saving = ref(false)

// 1. 关联合同（select，可远程搜索）
const contracts = ref([
  { code: 'HT-2026-030', title: '北辰集团 BI 系统升级服务合同', customer: '北辰实业集团', amount: 286000, invoiced: 86500, received: 86500, remaining: 199500, startDate: '2026-06-10', endDate: '2026-12-31', owner: '刘洋', term: '30 天' },
  { code: 'HT-2026-029', title: '朗驰智能设备改造工程合同', customer: '朗驰智能科技', amount: 158000, invoiced: 0, received: 0, remaining: 158000, startDate: '2026-05-20', endDate: '2026-11-30', owner: '陈思琪', term: '45 天' },
  { code: 'HT-2026-028', title: '数智化二期 SaaS 平台年度服务', customer: '万象科技有限公司', amount: 365000, invoiced: 120000, received: 120000, remaining: 245000, startDate: '2026-04-01', endDate: '2027-03-31', owner: '张明', term: '30 天' },
  { code: 'HT-2026-024', title: '财务系统年度服务合同', customer: '明远咨询', amount: 98000, invoiced: 49000, received: 49000, remaining: 49000, startDate: '2026-03-01', endDate: '2027-02-28', owner: '刘洋', term: '30 天' },
])
const contractSearch = ref('')
const selectedContractCode = ref('HT-2026-030')

const filteredContracts = computed(() => {
  if (!contractSearch.value) return contracts.value
  const kw = contractSearch.value.toLowerCase()
  return contracts.value.filter((c) => c.code.toLowerCase().includes(kw) || c.title.toLowerCase().includes(kw))
})

const selectedContract = computed(() => contracts.value.find((c) => c.code === selectedContractCode.value) || null)

// 回款类型
const receivableType = ref('按里程碑')

// 2. 基础信息
const form = reactive({
  totalAmount: 199500,
  paymentTerm: '30 天',
  startDate: '2026-07-10',
})

// 3. 分期行（动态）
const scheduleRows = ref([
  { seq: 1, name: '首期款（30%）', amount: 59850, planDate: '2026-07-10', owner: '刘洋' },
  { seq: 2, name: '中期款（40%）', amount: 79800, planDate: '2026-09-30', owner: '刘洋' },
  { seq: 3, name: '尾款（30%）', amount: 59850, planDate: '2026-12-15', owner: '刘洋' },
])

const totalScheduleAmount = computed(() =>
  scheduleRows.value.reduce((sum, r) => sum + (Number(r.amount) || 0), 0)
)
const totalMatches = computed(() => Math.abs(totalScheduleAmount.value - form.totalAmount) < 0.01)

function addRow() {
  const next = scheduleRows.value.length + 1
  scheduleRows.value.push({
    seq: next,
    name: `第 ${next} 期`,
    amount: 0,
    planDate: '',
    owner: '刘洋',
  })
}

function removeRow(idx: number) {
  if (scheduleRows.value.length <= 1) {
    ElMessage.warning('至少保留 1 期分期')
    return
  }
  scheduleRows.value.splice(idx, 1)
  // 重排序号
  scheduleRows.value.forEach((r, i) => (r.seq = i + 1))
}

// 自动均分（等额分期）
function autoSplit() {
  const n = scheduleRows.value.length
  if (n === 0) return
  const each = Math.floor((form.totalAmount / n) * 100) / 100
  let acc = 0
  scheduleRows.value.forEach((r, i) => {
    if (i === n - 1) {
      r.amount = Math.round((form.totalAmount - acc) * 100) / 100
    } else {
      r.amount = each
      acc += each
    }
  })
  ElMessage.success(`已按 ${n} 期等额均分`)
}

// 4. 收款账户
const bank = reactive({
  bankName: '招商银行上海分行',
  account: '6225 **** **** 1234',
  accountName: '上海数智信息技术有限公司',
})

const bankOptions = ['招商银行上海分行', '工商银行上海分行', '建设银行上海分行', '交通银行上海分行', '+ 添加新账户']

// 5. 备注
const remarks = ref('')

// 操作
function gotoBack() { router.push('/receivable/list') }

async function saveDraft() {
  saving.value = true
  try {
    await receivableApi.create({
      code: 'HK-DRAFT-' + Date.now(),
      contractCode: selectedContractCode.value,
      planAmount: form.totalAmount,
      planDate: scheduleRows.value[0]?.planDate || form.startDate,
      status: '草稿',
    } as any).catch(() => null)
    ElMessage.success('已保存草稿（演示）')
    router.push('/receivable/list')
  } finally {
    saving.value = false
  }
}

async function submit() {
  if (!selectedContractCode.value) {
    ElMessage.warning('请先选择关联合同')
    return
  }
  if (!totalMatches.value) {
    ElMessage.warning('分期合计 ≠ 应收总额，请调整')
    return
  }
  saving.value = true
  try {
    await receivableApi.create({
      code: 'HK-2026-' + String(Math.floor(Math.random() * 900 + 100)),
      contractCode: selectedContractCode.value,
      planAmount: form.totalAmount,
      planDate: scheduleRows.value[0]?.planDate || form.startDate,
      status: '待收',
    }).catch(() => null)
    ElMessage.success('已提交，创建成功（演示）')
    router.push('/receivable/list')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- 顶部 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/receivable/list" style="color: var(--color-text-tertiary)">回款管理</router-link> / 新建回款计划
        </div>
        <h2>新建回款计划</h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button :icon="'Back'" @click="gotoBack">返回</el-button>
        <el-button type="primary" :icon="'Check'" @click="submit" :loading="saving">✓ 保存</el-button>
      </div>
    </div>

    <!-- 顶部 tip -->
    <div class="tip-box">
      <div style="color: var(--color-primary); font-size: 16px">ⓘ</div>
      <div>
        <strong>回款计划：</strong> 按合同约定拆分回款节点。计划创建后，到期前 7 天自动提醒，到期日未收到款项标记为<strong>逾期</strong>，触发催收流程。
      </div>
    </div>

    <!-- 1. 关联合同 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📄 关联合同 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">* 选择一个执行中的合同</span></h3>
        <span class="req">必填</span>
      </div>
      <div class="fs-body">
        <div class="form-row-2" style="margin-bottom: 16px">
          <div class="field">
            <label>选择合同 <span class="req-mark">*</span></label>
            <el-select v-model="selectedContractCode" placeholder="搜索合同编号或名称" filterable clearable style="width: 100%">
              <el-option v-for="c in filteredContracts" :key="c.code" :value="c.code" :label="`${c.code} · ${c.title}`" />
            </el-select>
          </div>
          <div class="field">
            <label>回款类型 <span class="req-mark">*</span></label>
            <el-select v-model="receivableType" style="width: 100%">
              <el-option value="按合同节点" label="按合同节点" />
              <el-option value="按里程碑" label="按里程碑" />
              <el-option value="按月平均" label="按月平均" />
              <el-option value="一次性" label="一次性" />
            </el-select>
          </div>
        </div>

        <!-- 选中合同的摘要 -->
        <div v-if="selectedContract" class="contract-card">
          <div class="item">
            <div class="l">合同编号</div>
            <div class="v mono">{{ selectedContract.code }}</div>
          </div>
          <div class="item">
            <div class="l">合同金额</div>
            <div class="v amount">¥ {{ selectedContract.amount.toLocaleString() }}.00</div>
          </div>
          <div class="item">
            <div class="l">已开票 / 已回款</div>
            <div class="v">¥ {{ selectedContract.invoiced.toLocaleString() }} / ¥ {{ selectedContract.received.toLocaleString() }}</div>
          </div>
          <div class="item">
            <div class="l">剩余应收</div>
            <div class="v amount">¥ {{ selectedContract.remaining.toLocaleString() }}.00</div>
          </div>
          <div class="item">
            <div class="l">客户</div>
            <div class="v">{{ selectedContract.customer }}</div>
          </div>
          <div class="item">
            <div class="l">合同期限</div>
            <div class="v">{{ selectedContract.startDate }} ~ {{ selectedContract.endDate }}</div>
          </div>
          <div class="item">
            <div class="l">负责人</div>
            <div class="v">{{ selectedContract.owner }}</div>
          </div>
          <div class="item">
            <div class="l">付款账期</div>
            <div class="v">{{ selectedContract.term }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 基础信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💼 回款基础信息</h3>
      </div>
      <div class="fs-body">
        <div class="form-row-3">
          <div class="field">
            <label>应收总额（元） <span class="req-mark">*</span></label>
            <el-input v-model="form.totalAmount" type="number" placeholder="请输入应收总额">
              <template #prefix>¥</template>
            </el-input>
          </div>
          <div class="field">
            <label>账期 <span class="req-mark">*</span></label>
            <el-select v-model="form.paymentTerm" style="width: 100%">
              <el-option value="15 天" label="15 天" />
              <el-option value="30 天" label="30 天" />
              <el-option value="45 天" label="45 天" />
              <el-option value="60 天" label="60 天" />
              <el-option value="90 天" label="90 天" />
            </el-select>
          </div>
          <div class="field">
            <label>起始日期 <span class="req-mark">*</span></label>
            <el-date-picker v-model="form.startDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 回款计划 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💰 回款计划 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">动态分期行 · 支持自动均分</span></h3>
        <span class="req">分期合计需等于应收总额</span>
      </div>
      <div class="fs-body">
        <!-- 工具栏 -->
        <div class="schedule-tools">
          <span class="l">💡 系统建议 {{ scheduleRows.length }} 期，按合同节点付款</span>
          <el-button size="small" @click="autoSplit">等额分期</el-button>
          <el-button size="small" @click="autoSplit">按月平均</el-button>
          <el-button size="small" @click="autoSplit">季度分期</el-button>
          <el-button type="primary" size="small" @click="addRow">+ 添加分期</el-button>
        </div>

        <!-- 分期表 -->
        <table class="schedule-table">
          <thead>
            <tr>
              <th style="width: 60px">序号</th>
              <th>分期名称</th>
              <th style="width: 160px">计划回款日</th>
              <th style="width: 160px">回款金额（元）</th>
              <th style="width: 120px">负责人</th>
              <th style="width: 70px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in scheduleRows" :key="idx">
              <td><span class="seq">{{ row.seq }}</span></td>
              <td>
                <el-input v-model="row.name" placeholder="如：首期款" size="small" />
              </td>
              <td>
                <el-date-picker v-model="row.planDate" type="date" value-format="YYYY-MM-DD" size="small" style="width: 100%" />
              </td>
              <td>
                <el-input v-model="row.amount" type="number" size="small" style="text-align: right; font-weight: 600">
                  <template #prefix>¥</template>
                </el-input>
              </td>
              <td>
                <el-select v-model="row.owner" size="small" style="width: 100%">
                  <el-option value="刘洋" label="刘洋" />
                  <el-option value="陈思琪" label="陈思琪" />
                  <el-option value="张明" label="张明" />
                  <el-option value="李明" label="李明" />
                </el-select>
              </td>
              <td>
                <button class="del-btn" @click="removeRow(idx)">×</button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 总计 -->
        <div :class="['schedule-total', totalMatches ? '' : 'warn']">
          <div class="l">分期合计</div>
          <div class="v">¥ {{ totalScheduleAmount.toLocaleString() }}.00</div>
        </div>
        <div style="margin-top: 8px; font-size: 11.5px; text-align: right" :style="{ color: totalMatches ? 'var(--color-success)' : 'var(--color-danger)' }">
          <span v-if="totalMatches">✓ 与应收总额一致</span>
          <span v-else>✗ 差额 ¥ {{ Math.abs(totalScheduleAmount - form.totalAmount).toLocaleString() }}，请调整</span>
        </div>
      </div>
    </div>

    <!-- 4. 时间线预览 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📅 时间线预览 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">2026 下半年</span></h3>
      </div>
      <div class="fs-body">
        <div class="timeline-preview">
          <div class="tl-bar">
            <div
              v-for="(row, idx) in scheduleRows"
              :key="idx"
              class="seg"
              :style="{ left: (idx / scheduleRows.length * 100) + '%', width: (100 / scheduleRows.length) + '%' }"
            >
              ①{{ row.seq }} · ¥ {{ Number(row.amount || 0).toLocaleString() }}
            </div>
          </div>
          <div class="tl-labels">
            <span>2026-07</span>
            <span>2026-08</span>
            <span>2026-09</span>
            <span>2026-10</span>
            <span>2026-11</span>
            <span>2026-12</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. 收款账户 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🏦 收款账户 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">客户打款到此账户</span></h3>
      </div>
      <div class="fs-body">
        <div class="form-row-2" style="margin-bottom: 12px">
          <div class="field">
            <label>开户银行 <span class="req-mark">*</span></label>
            <el-select v-model="bank.bankName" style="width: 100%">
              <el-option v-for="opt in bankOptions" :key="opt" :value="opt" :label="opt" />
            </el-select>
          </div>
          <div class="field">
            <label>银行账号 <span class="req-mark">*</span></label>
            <el-input v-model="bank.account" placeholder="银行账号" style="font-family: $font-family-mono" />
          </div>
        </div>
        <div class="field">
          <label>账户名 <span class="req-mark">*</span></label>
          <el-input v-model="bank.accountName" placeholder="收款账户名" />
        </div>
        <div class="tip-box" style="margin-top: 16px; margin-bottom: 0">
          <div style="color: var(--color-primary); font-size: 16px">💡</div>
          <div>系统将自动监控该账户到账流水，到账后自动核销对应回款计划（需财务复核）</div>
        </div>
      </div>
    </div>

    <!-- 6. 备注 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📝 备注</h3>
      </div>
      <div class="fs-body">
        <el-input v-model="remarks" type="textarea" :rows="3" placeholder="如：客户对账特殊要求、付款条件等" />
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot">
      <div style="font-size: 12px; color: var(--color-text-tertiary)">
        💾 计划创建后将通知相关负责人，<a href="javascript:;" style="color: var(--color-primary)" @click="gotoBack">前往回款列表</a>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">⊗ 取消</el-button>
        <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
        <el-button type="primary" @click="submit" :loading="saving">✓ 提交</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a { color: var(--color-text-tertiary); }

// 合同摘要卡（design 1:1）
.contract-card {
  background: linear-gradient(135deg, rgba(79,107,255,0.04), rgba(124,58,237,0.04));
  border: 1.5px solid $color-primary;
  border-radius: $radius-md;
  padding: 18px 20px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  .item .l { font-size: 11.5px; color: $color-text-tertiary; margin-bottom: 4px; }
  .item .v { font-size: 14px; font-weight: 600; color: $color-text-primary; }
  .item .v.mono { font-family: $font-family-mono; color: $color-primary; }
  .item .v.amount {
    font-size: 18px;
    background: $gradient-brand;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

// 分期表
.schedule-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  overflow: hidden;
  th {
    background: #F8FAFC; text-align: left;
    padding: 10px 12px;
    font-size: 11.5px; font-weight: 600;
    color: $color-text-secondary;
    border-bottom: 1px solid $color-border;
  }
  td {
    padding: 8px 10px;
    border-bottom: 1px solid $color-border;
  }
  tr:last-child td { border-bottom: none; }
  .seq {
    display: inline-grid; place-items: center;
    width: 26px; height: 26px;
    border-radius: 50%;
    background: $gradient-brand;
    color: #fff;
    font-size: 12px; font-weight: 600;
  }
  .del-btn {
    color: $color-text-tertiary;
    padding: 4px 8px;
    border-radius: $radius-sm;
    font-size: 14px;
    background: transparent;
    border: none;
    cursor: pointer;
    &:hover { background: $color-danger-bg; color: $color-danger; }
  }
}

// 分期工具栏
.schedule-tools {
  display: flex; gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  align-items: center;
  .l { font-size: 12.5px; color: $color-text-secondary; margin-right: auto; }
}

// 总计
.schedule-total {
  margin-top: 12px;
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(79,107,255,0.05), rgba(124,58,237,0.05));
  border: 1px solid $color-primary;
  border-radius: $radius-md;
  display: flex; justify-content: space-between; align-items: center;
  .l { font-size: 12.5px; color: $color-text-secondary; }
  .v { font-size: 18px; font-weight: 700; color: $color-primary; }
  &.warn {
    background: rgba(239,68,68,0.06);
    border-color: $color-danger;
    .v { color: $color-danger; }
  }
}

// 时间线预览
.timeline-preview {
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 16px 20px;
}
.tl-bar {
  position: relative;
  height: 36px;
  background: #F1F5F9;
  border-radius: $radius-md;
  overflow: hidden;
  margin-bottom: 8px;
  .seg {
    position: absolute; top: 0; bottom: 0;
    background: $gradient-brand;
    display: flex; align-items: center;
    padding: 0 8px;
    font-size: 11px; color: #fff; font-weight: 600;
    border-right: 2px solid rgba(255,255,255,0.3);
    &:last-child { border-right: none; }
  }
}
.tl-labels {
  display: flex; justify-content: space-between;
  font-size: 10.5px; color: $color-text-tertiary;
  margin-top: 4px;
}
</style>
