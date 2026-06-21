<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi } from '@/api/modules'

const form = ref({ invoiceCode: '011002600111', invoiceNo: '12345000', issueDate: '2026-06-08', totalAmount: 28000 })
const loading = ref(false)
const result = ref<Awaited<ReturnType<typeof invoiceOcrApi.verify>> | null>(null)

const resultColorMap: Record<string, string> = {
  pass: 'success',
  risk: 'warning',
  repeat: 'danger',
  not_found: 'info',
}
const resultTextMap: Record<string, string> = {
  pass: '✓ 查验通过',
  risk: '⚠ 存在风险',
  repeat: '✗ 已报销（重复）',
  not_found: '? 未查到',
}

async function handleVerify() {
  loading.value = true
  result.value = null
  try {
    result.value = await invoiceOcrApi.verify(form.value)
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div><h2>发票查验</h2><p class="page-desc">实时对接国税总局 / 诺诺发票云，4 类结果（pass / risk / repeat / not_found）</p></div>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <div class="page-card">
          <h3 class="panel-title">发票信息</h3>
          <el-form :model="form" label-width="100px">
            <el-form-item label="发票代码">
              <el-input v-model="form.invoiceCode" placeholder="如 011002600111" />
            </el-form-item>
            <el-form-item label="发票号码">
              <el-input v-model="form.invoiceNo" placeholder="8-20 位" />
            </el-form-item>
            <el-form-item label="开票日期">
              <el-date-picker v-model="form.issueDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="金额(元)">
              <el-input-number v-model="form.totalAmount" :min="0" :precision="2" :step="100" style="width: 100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleVerify" style="width: 100%">🔍 立即查验</el-button>
            </el-form-item>
          </el-form>
          <el-alert type="info" :closable="false" style="margin-top: 12px">
            <p style="margin: 0; font-size: 12px">💡 <strong>演示技巧</strong>：发票号码后 4 位 mod 5 决定结果</p>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #475569">0/1 → pass, 2 → risk, 3 → repeat, 4 → not_found</p>
          </el-alert>
        </div>
      </el-col>

      <el-col :span="14">
        <div class="page-card">
          <h3 class="panel-title">查验结果</h3>
          <el-skeleton v-if="loading" :rows="4" animated />
          <el-empty v-else-if="!result" description="提交查验后查看结果" />
          <div v-else>
            <div class="result-banner" :class="`result-${result.result}`">
              <div class="result-title">{{ resultTextMap[result.result] || result.result }}</div>
              <div class="result-meta">
                <el-tag size="small">{{ result.source }}</el-tag>
                <el-tag size="small" type="info">耗时 {{ result.elapsed }} ms</el-tag>
                <el-tag size="small" type="info">查验号 {{ result.verifyId }}</el-tag>
              </div>
            </div>

            <el-alert v-if="result.riskReason" type="warning" :title="result.riskReason" :closable="false" style="margin-top: 12px" />

            <el-descriptions :column="2" border style="margin-top: 16px" title="发票信息回执">
              <el-descriptions-item label="发票代码">{{ result.verifyId }}</el-descriptions-item>
              <el-descriptions-item label="查验时间">{{ result.verifiedAt }}</el-descriptions-item>
              <el-descriptions-item label="数据源">{{ result.source }}</el-descriptions-item>
              <el-descriptions-item label="查验状态">{{ result.result }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
.result-banner {
  border-radius: $radius-lg;
  padding: 24px;
  text-align: center;
  color: #fff;
  background: $gradient-brand;
  &.result-pass { background: linear-gradient(135deg, #10B981, #06B6D4); }
  &.result-risk { background: linear-gradient(135deg, #F59E0B, #EF4444); }
  &.result-repeat { background: linear-gradient(135deg, #EF4444, #B91C1C); }
  &.result-not_found { background: linear-gradient(135deg, #6B7280, #4B5563); }

  .result-title { font-size: 28px; font-weight: 700; margin-bottom: 12px; }
  .result-meta { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
}
</style>
