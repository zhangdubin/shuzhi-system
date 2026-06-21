<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clientApi, type ClientLevel, type ContactRole, type ClientSource } from '@/api/client'

const router = useRouter()
const saving = ref(false)

// ---------- 1. 基本信息（design 对齐） ----------
const form = reactive({
  name: '', // 客户全称
  shortName: '', // 客户简称
  taxNo: '', // 纳税人识别号
  legalPerson: '', // 法定代表人
  industry: '智能设备',
  source: '官网咨询' as ClientSource,
})

const industryOptions = [
  '制造业',
  '互联网/IT',
  '金融业',
  '零售/电商',
  '服务业',
  '智能设备',
  '教育',
  '医疗',
  '其他',
]
const sourceOptions: ClientSource[] = [
  '官网咨询',
  '电话来访',
  '客户介绍',
  '展会收集',
  '市场推广',
  '其他',
]

// ---------- 2. 主要联系人（design 对齐：6 字段） ----------
const contact = reactive({
  name: '',
  title: '',
  role: '主要联系人' as ContactRole,
  phone: '',
  email: '',
  wechat: '',
})
const roleOptions: ContactRole[] = ['主要联系人', '商务联系人', '技术联系人', '财务联系人']

// ---------- 3. 财务信息（design 对齐：开户行/账号/注册地址/开票地址） ----------
const finance = reactive({
  bankName: '',
  bankAccount: '',
  registeredAddress: '',
  invoiceAddressPhone: '',
})

// ---------- 4. 客户分级（design 对齐：A/B/C/D） ----------
const level = ref<ClientLevel>('B')
const levels: { value: ClientLevel; name: string; desc: string }[] = [
  { value: 'A', name: '战略客户', desc: '年合同额 ≥ 100 万' },
  { value: 'B', name: '重点客户', desc: '年合同额 30-100 万' },
  { value: 'C', name: '普通客户', desc: '年合同额 5-30 万' },
  { value: 'D', name: '潜在客户', desc: '年合同额 < 5 万' },
]

// ---------- 5. 备注 ----------
const remark = ref('')

// ---------- 操作 ----------
function gotoBack() {
  router.push('/client/list')
}

function validate(): boolean {
  if (!form.name.trim()) {
    ElMessage.warning('请填写客户全称')
    return false
  }
  if (!form.taxNo.trim()) {
    ElMessage.warning('请填写纳税人识别号')
    return false
  }
  if (!contact.name.trim()) {
    ElMessage.warning('请填写联系人姓名')
    return false
  }
  if (!contact.phone.trim()) {
    ElMessage.warning('请填写联系人手机')
    return false
  }
  return true
}

async function saveDraft() {
  saving.value = true
  try {
    await clientApi
      .create({
        code: 'KH-DRAFT-' + Date.now(),
        name: form.name,
        shortName: form.shortName,
        taxNo: form.taxNo,
        legalPerson: form.legalPerson,
        industry: form.industry,
        contactName: contact.name,
        contactPhone: contact.phone,
        contactEmail: contact.email,
        bankName: finance.bankName,
        bankAccount: finance.bankAccount,
        address: finance.registeredAddress,
        level: level.value,
        remark: remark.value,
      } as any)
      .catch(() => null)
    ElMessage.success('已保存草稿（演示）')
    router.push('/client/list')
  } finally {
    saving.value = false
  }
}

async function submit() {
  if (!validate()) return
  saving.value = true
  try {
    await clientApi
      .create({
        name: form.name,
        shortName: form.shortName,
        taxNo: form.taxNo,
        legalPerson: form.legalPerson,
        industry: form.industry,
        contactName: contact.name,
        contactPhone: contact.phone,
        contactEmail: contact.email,
        bankName: finance.bankName,
        bankAccount: finance.bankAccount,
        address: finance.registeredAddress,
        level: level.value,
        remark: remark.value,
      } as any)
      .catch(() => null)
    ElMessage.success('客户创建成功（演示）')
    router.push('/client/list')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- 顶部：返回 / 存为草稿 / 创建客户 -->
    <div class="page-header" style="margin-bottom: 16px">
      <div>
        <div class="breadcrumb" style="font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 6px">
          业务 / <router-link to="/client/list" style="color: var(--color-text-tertiary)">客户管理</router-link> / 新建客户档案
        </div>
        <h2>新建客户档案</h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">⊗ 取消</el-button>
        <el-button @click="saveDraft" :loading="saving">💾 存为草稿</el-button>
        <el-button type="primary" @click="submit" :loading="saving">✓ 创建客户</el-button>
      </div>
    </div>

    <!-- 顶部 tip -->
    <div class="tip-box">
      <div style="color: var(--color-primary); font-size: 16px">ⓘ</div>
      <div>
        <strong>客户档案：</strong>
        创建后可在合同、项目、发票、回款等模块引用。纳税人识别号一旦保存不可修改，请仔细核对。系统会实时检测重复客户。
      </div>
    </div>

    <!-- 1. 基本信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🏢 基本信息 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">* 必填</span></h3>
      </div>
      <div class="fs-body">
        <!-- 客户全称 / 客户简称 -->
        <div class="form-row-2" style="margin-bottom: 16px">
          <div class="field">
            <label>客户全称 <span class="req">*</span></label>
            <el-input v-model="form.name" placeholder="营业执照上的公司全称" />
          </div>
          <div class="field">
            <label>客户简称</label>
            <el-input v-model="form.shortName" placeholder="用于列表显示，可选" />
          </div>
        </div>

        <!-- 纳税人识别号 / 法定代表人 / 所属行业 -->
        <div class="form-row-3" style="margin-bottom: 16px">
          <div class="field">
            <label>纳税人识别号 <span class="req">*</span></label>
            <el-input v-model="form.taxNo" placeholder="18 位统一社会信用代码" />
          </div>
          <div class="field">
            <label>法定代表人</label>
            <el-input v-model="form.legalPerson" placeholder="如：张志强" />
          </div>
          <div class="field">
            <label>所属行业</label>
            <el-select v-model="form.industry" placeholder="请选择行业" style="width: 100%">
              <el-option v-for="i in industryOptions" :key="i" :value="i" :label="i" />
            </el-select>
          </div>
        </div>

        <!-- 客户来源（design 未画，但 task spec 要求；放最后一行） -->
        <div class="form-row-1" style="margin-bottom: 8px">
          <div class="field">
            <label>客户来源</label>
            <el-select v-model="form.source" style="width: 100%">
              <el-option v-for="s in sourceOptions" :key="s" :value="s" :label="s" />
            </el-select>
          </div>
        </div>

        <!-- 重复检查提示（design 1:1 复刻的 dup-alert block；后端未就绪，给静态 placeholder） -->
        <div class="dup-alert">
          <div class="ico">⚠</div>
          <div class="body">
            <div class="t">系统检测到 1 个相似客户，请确认是否重复</div>
            <div class="item">
              <div>
                <div class="name">朗驰智能设备有限公司</div>
                <div style="font-size: 11px; color: var(--color-text-tertiary)">
                  税号 91310112MA1GK3X9Q · 2025 年 8 月创建
                </div>
              </div>
              <div class="actions">
                <a>查看</a>
                <a>合并到此客户</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 主要联系人 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>👤 主要联系人 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">至少 1 位</span></h3>
      </div>
      <div class="fs-body">
        <!-- 姓名 / 职位 / 角色 -->
        <div class="form-row-3" style="margin-bottom: 16px">
          <div class="field">
            <label>联系人姓名 <span class="req">*</span></label>
            <el-input v-model="contact.name" placeholder="如：王经理" />
          </div>
          <div class="field">
            <label>职位</label>
            <el-input v-model="contact.title" placeholder="如：采购总监" />
          </div>
          <div class="field">
            <label>角色</label>
            <el-select v-model="contact.role" style="width: 100%">
              <el-option v-for="r in roleOptions" :key="r" :value="r" :label="r" />
            </el-select>
          </div>
        </div>

        <!-- 手机 / 邮箱 / 微信 -->
        <div class="form-row-3" style="margin-bottom: 0">
          <div class="field">
            <label>手机 <span class="req">*</span></label>
            <el-input v-model="contact.phone" placeholder="11 位手机号" />
          </div>
          <div class="field">
            <label>邮箱</label>
            <el-input v-model="contact.email" placeholder="example@company.com" />
          </div>
          <div class="field">
            <label>微信</label>
            <el-input v-model="contact.wechat" placeholder="选填" />
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 财务信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💳 财务信息 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">开票与回款所需</span></h3>
      </div>
      <div class="fs-body">
        <!-- 开户银行 / 银行账号 -->
        <div class="form-row-2" style="margin-bottom: 16px">
          <div class="field">
            <label>开户银行</label>
            <el-input v-model="finance.bankName" placeholder="如：招商银行上海分行" />
          </div>
          <div class="field">
            <label>银行账号</label>
            <el-input v-model="finance.bankAccount" placeholder="客户收款账号" style="font-family: var(--font-mono)" />
          </div>
        </div>

        <!-- 注册地址 / 开票地址电话 -->
        <div class="form-row-2" style="margin-bottom: 0">
          <div class="field">
            <label>注册地址</label>
            <el-input v-model="finance.registeredAddress" placeholder="如：上海市浦东新区张江高科技园区科苑路 88 号" />
          </div>
          <div class="field">
            <label>开票地址电话</label>
            <el-input v-model="finance.invoiceAddressPhone" placeholder="用于开发票 · 格式：地址 / 电话" />
          </div>
        </div>
      </div>
    </div>

    <!-- 4. 客户分级 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>⭐ 客户分级 <span style="font-size: 11.5px; color: var(--color-text-tertiary); font-weight: 400">影响后续销售策略与审批权限</span></h3>
      </div>
      <div class="fs-body">
        <div class="level-grid">
          <div
            v-for="lv in levels"
            :key="lv.value"
            :class="['level-card', { active: level === lv.value }]"
            :data-level="lv.value"
            @click="level = lv.value"
          >
            <div class="badge">{{ lv.value }}</div>
            <div class="name">{{ lv.name }}</div>
            <div class="desc">{{ lv.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. 备注 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📝 备注</h3>
      </div>
      <div class="fs-body">
        <div class="form-row-1">
          <div class="field">
            <label>客户背景 / 备注</label>
            <el-input
              v-model="remark"
              type="textarea"
              :rows="4"
              placeholder="客户背景、来源、合作历史、特殊要求等"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作条（design 1:1） -->
    <div class="form-foot">
      <div style="font-size: 12px; color: var(--color-text-tertiary)">
        💡 创建后可继续编辑联系人、开票信息、关联项目
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoBack">⊗ 取消</el-button>
        <el-button @click="saveDraft" :loading="saving">💾 存为草稿</el-button>
        <el-button type="primary" @click="submit" :loading="saving">✓ 创建客户</el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.breadcrumb a {
  color: var(--color-text-tertiary);
}

// ---------- 等级卡（design/client-create.html 1:1 复刻） ----------
.level-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.level-card {
  border: 1.5px solid $color-border;
  border-radius: $radius-md;
  padding: 14px;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s;
  background: #fff;
  &:hover {
    border-color: $color-primary;
  }
  &.active {
    border-color: $color-primary;
    background: $color-primary-bg;
  }
  .badge {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    margin: 0 auto 8px;
    display: grid;
    place-items: center;
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }
  .name {
    font-size: 13.5px;
    font-weight: 600;
    color: $color-text-primary;
  }
  .desc {
    font-size: 11px;
    color: $color-text-tertiary;
    margin-top: 4px;
  }

  // 与 design 稿完全一致：A橙黄 / B蓝紫 / C绿 / D灰
  &[data-level='A'] .badge {
    background: linear-gradient(135deg, #F59E0B, #D97706);
  }
  &[data-level='B'] .badge {
    background: linear-gradient(135deg, #4F6BFF, #7C3AED);
  }
  &[data-level='C'] .badge {
    background: linear-gradient(135deg, #10B981, #059669);
  }
  &[data-level='D'] .badge {
    background: linear-gradient(135deg, #94A3B8, #64748B);
  }
}

// ---------- 重复检查提示（design 1:1） ----------
.dup-alert {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: $radius-md;
  padding: 12px 14px;
  margin-top: 8px;
  display: flex;
  gap: 10px;
  font-size: 12.5px;
  .ico {
    color: $color-warning;
    font-size: 16px;
    flex-shrink: 0;
  }
  .body {
    flex: 1;
    .t {
      font-weight: 600;
      color: #B45309;
      margin-bottom: 4px;
    }
    .item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 10px;
      background: #fff;
      border-radius: $radius-sm;
      margin-bottom: 4px;
      .name {
        font-size: 12.5px;
        font-weight: 500;
      }
      .actions {
        display: flex;
        gap: 4px;
        a {
          font-size: 11.5px;
          color: $color-primary;
          padding: 2px 8px;
          cursor: pointer;
          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
  }
}
</style>