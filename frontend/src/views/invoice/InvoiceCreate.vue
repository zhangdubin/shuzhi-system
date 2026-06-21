<script setup lang="ts">
/**
 * 手动新增发票（手动录入票面信息，对标设计稿识别结果卡片字段）
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

const form = reactive({
  invoiceType: '',
  invoiceCode: '',
  invoiceNo: '',
  issueDate: '',
  sellerName: '',
  sellerTaxNo: '',
  buyerName: '',
  buyerTaxNo: '',
  taxRate: '',
  taxAmount: '',
  totalAmount: '',
  expenseType: '',
  reimburser: '',
  remarks: '',
})

// 明细行
interface InvoiceItem { name: string; qty: number; price: number; taxRate: string; tax: number; amount: number }
const items = ref<InvoiceItem[]>([
  { name: '', qty: 1, price: 0, taxRate: '6%', tax: 0, amount: 0 },
])

function addItem() {
  items.value.push({ name: '', qty: 1, price: 0, taxRate: '6%', tax: 0, amount: 0 })
}
function removeItem(i: number) {
  items.value.splice(i, 1)
}
function calcAmount(item: InvoiceItem) {
  item.amount = Number(item.price) * item.qty
  item.tax = parseFloat((item.amount * (parseFloat(item.taxRate) / 100)).toFixed(2))
}

function handleSave() {
  if (!form.invoiceNo) { ElMessage.warning('请填写发票号码'); return }
  if (!form.totalAmount) { ElMessage.warning('请填写价税合计'); return }
  ElMessage.success('发票已保存（手动录入）')
  router.push('/invoice/ocr?tab=records')
}
function handleSubmit() {
  if (!form.invoiceNo) { ElMessage.warning('请填写发票号码'); return }
  if (!form.totalAmount) { ElMessage.warning('请填写价税合计'); return }
  ElMessage.success('发票已提交入账')
  router.push('/invoice/ocr?tab=records')
}
</script>

<template>
  <div class="page-card invoice-create-page">
    <div class="page-header">
      <h1 class="page-title">手动新增发票</h1>
      <p class="page-sub">手工录入票面信息，或使用 <a href="#" @click.prevent="router.push('/invoice/ocr')">发票识别</a> 自动提取</p>
    </div>

    <!-- 基础信息区块 -->
    <div class="form-section">
      <div class="form-section-title">票面信息</div>
      <div class="field-grid">
        <div class="field">
          <label>发票类型 <span class="ai-tag">AI</span></label>
          <select v-model="form.invoiceType">
            <option value="">请选择</option>
            <option>增值税电子普通发票</option>
            <option>增值税专用发票</option>
            <option>数电发票</option>
          </select>
        </div>
        <div class="field">
          <label>发票代码 <span class="ai-tag">AI</span></label>
          <input type="text" v-model="form.invoiceCode" placeholder="AI 已提取" />
        </div>
        <div class="field">
          <label>发票号码 <span class="ai-tag">AI</span></label>
          <input type="text" v-model="form.invoiceNo" placeholder="AI 已提取" />
        </div>
        <div class="field">
          <label>开票日期 <span class="ai-tag">AI</span></label>
          <input type="date" v-model="form.issueDate" />
        </div>
        <div class="field full">
          <label>销售方名称 <span class="ai-tag">AI</span></label>
          <input type="text" v-model="form.sellerName" placeholder="AI 已提取" />
        </div>
        <div class="field">
          <label>销售方税号</label>
          <input type="text" v-model="form.sellerTaxNo" />
        </div>
        <div class="field">
          <label>购买方名称 <span class="ai-tag">AI</span></label>
          <input type="text" v-model="form.buyerName" placeholder="AI 已提取" />
        </div>
        <div class="field">
          <label>购买方税号</label>
          <input type="text" v-model="form.buyerTaxNo" />
        </div>
        <div class="field">
          <label>税率</label>
          <select v-model="form.taxRate">
            <option value="">请选择</option>
            <option>3%</option>
            <option>6%</option>
            <option>13%</option>
          </select>
        </div>
        <div class="field">
          <label>税额</label>
          <input type="text" v-model="form.taxAmount" placeholder="¥ 0.00" />
        </div>
        <div class="field full">
          <label>价税合计（小写） <span class="ai-tag">AI</span></label>
          <div class="amount-display">
            <div class="amount-label">本张发票总金额</div>
            <div class="amount-value">
              <span>¥</span>
              <input type="number" v-model="form.totalAmount" placeholder="0.00" class="amount-input" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 明细行区块 -->
    <div class="form-section">
      <div class="form-section-title">发票明细</div>
      <table class="items-table">
        <thead>
          <tr>
            <th>货物或应税劳务、服务名称</th>
            <th style="width:80px;">数量</th>
            <th style="width:120px;">单价</th>
            <th style="width:80px;">税率</th>
            <th style="width:120px;">税额</th>
            <th style="width:120px;">金额</th>
            <th style="width:40px;"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in items" :key="i">
            <td><input type="text" v-model="item.name" placeholder="如：*软件服务*技术服务费" /></td>
            <td><input type="number" v-model.number="item.qty" min="1" @input="calcAmount(item)" /></td>
            <td><input type="number" v-model.number="item.price" min="0" step="0.01" @input="calcAmount(item)" /></td>
            <td>
              <select v-model="item.taxRate" @change="calcAmount(item)">
                <option>3%</option><option>6%</option><option>13%</option>
              </select>
            </td>
            <td class="num">¥ {{ item.tax.toFixed(2) }}</td>
            <td class="num">¥ {{ item.amount.toFixed(2) }}</td>
            <td>
              <button v-if="items.length > 1" class="btn-icon" @click="removeItem(i)" title="删除行">⊘</button>
            </td>
          </tr>
        </tbody>
      </table>
      <button class="btn btn-outline btn-sm" style="margin-top:8px" @click="addItem">+ 添加明细行</button>
    </div>

    <!-- 关联信息区块 -->
    <div class="form-section">
      <div class="form-section-title">关联信息</div>
      <div class="field-grid">
        <div class="field full">
          <label>关联合同 / 项目</label>
          <select v-model="form.expenseType">
            <option value="">请选择关联合同或项目</option>
            <option>HT-2026-028 · 万象科技 SaaS 服务合同</option>
            <option>PRJ-2026-018 · 数智化二期</option>
          </select>
        </div>
        <div class="field">
          <label>费用类型</label>
          <select v-model="form.expenseType">
            <option value="">请选择</option>
            <option>差旅</option>
            <option>办公</option>
            <option>招待</option>
            <option>餐饮</option>
            <option>通讯</option>
            <option>软件服务费</option>
            <option>咨询服务费</option>
          </select>
        </div>
        <div class="field">
          <label>报销人</label>
          <select v-model="form.reimburser">
            <option value="">请选择</option>
            <option>张工</option>
            <option>王芳</option>
            <option>李明</option>
          </select>
        </div>
        <div class="field full">
          <label>备注</label>
          <textarea v-model="form.remarks" placeholder="可补充说明，例如分摊比例、审批意见等"></textarea>
        </div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="form-actions">
      <button class="btn btn-outline" @click="router.push('/invoice/ocr')">取消</button>
      <button class="btn btn-outline" @click="handleSave">存为草稿</button>
      <button class="btn btn-primary" @click="handleSubmit">✓ 提交入账</button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import "@/assets/styles/variables.scss";

.invoice-create-page {
  max-width: 900px;
  padding: 24px;
  @media (max-width: 639px) { padding: 12px; }
}

.page-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid $color-border;
}
.page-title {
  font-size: 18px;
  font-weight: 700;
  color: $color-text-primary;
  margin: 0 0 4px 0;
}
.page-sub {
  font-size: 13px;
  color: $color-text-secondary;
  margin: 0;
  a { color: $color-primary; text-decoration: none; &:hover { text-decoration: underline; } }
}

.form-section {
  margin-bottom: 24px;
  @media (max-width: 639px) { margin-bottom: 16px; }
}
.form-section-title {
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid $color-border;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
  @media (max-width: 639px) { grid-template-columns: 1fr; }
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  &.full { grid-column: 1 / -1; }
  label {
    font-size: 11px;
    color: $color-text-secondary;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  input, select, textarea {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid $color-border;
    border-radius: $radius-sm;
    font-size: 13px;
    color: $color-text-primary;
    background: $color-bg;
    box-sizing: border-box;
    &:focus { outline: none; border-color: $color-primary; background: #fff; }
  }
  input.ai-filled, select.ai-filled {
    background: linear-gradient(135deg, rgba(79,107,255,0.06) 0%, rgba(124,58,237,0.06) 100%);
    border-color: rgba(124,58,237,0.3);
    font-weight: 500;
  }
  select { cursor: pointer; }
  textarea { resize: vertical; min-height: 64px; }
}

.ai-tag {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  color: #7c3aed;
  background: rgba(124,58,237,0.1);
  border-radius: 3px;
  padding: 1px 4px;
}

.amount-display {
  background: linear-gradient(135deg, $color-primary-bg 0%, rgba(124,58,237,0.08) 100%);
  border-radius: $radius-md;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid rgba(124,58,237,0.2);
}
.amount-label {
  font-size: 13px;
  font-weight: 500;
  color: $color-text-secondary;
}
.amount-value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 26px;
  font-weight: 700;
  color: $color-primary;
}
.amount-input {
  width: 160px !important;
  font-size: 26px !important;
  font-weight: 700 !important;
  color: $color-primary !important;
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
  text-align: right;
  &::-webkit-inner-spin-button, &::-webkit-outer-spin-button { -webkit-appearance: none; }
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  overflow-x: auto;
  display: block;
  -webkit-overflow-scrolling: touch;
  @media (max-width: 639px) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
  th {
    text-align: left;
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 600;
    color: $color-text-secondary;
    border-bottom: 1px solid $color-border;
    background: $color-bg;
  }
  td {
    padding: 6px 8px;
    border-bottom: 1px solid $color-border;
    input, select {
      width: 100%;
      padding: 5px 8px;
      border: 1px solid $color-border;
      border-radius: $radius-sm;
      font-size: 12px;
      color: $color-text-primary;
      background: $color-bg;
      box-sizing: border-box;
      &:focus { outline: none; border-color: $color-primary; }
    }
    select { padding: 4px 6px; }
  }
  tr:last-child td { border-bottom: none; }
  .num { text-align: right; font-weight: 600; color: $color-text-primary; }
}

.btn-icon {
  background: none;
  border: none;
  color: $color-text-tertiary;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  &:hover { color: #ef4444; background: rgba(239,68,68,0.08); }
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid $color-border;
}
.btn {
  padding: 8px 16px;
  border-radius: $radius-md;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  &.btn-outline {
    background: #fff;
    border-color: $color-border-strong;
    color: $color-text-primary;
    &:hover { border-color: $color-primary; color: $color-primary; }
  }
  &.btn-primary {
    background: $color-primary;
    color: #fff;
    &:hover { opacity: 0.9; }
  }
  &.btn-sm { padding: 5px 10px; font-size: 12px; }
}
</style>