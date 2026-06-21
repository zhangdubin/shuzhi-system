<script setup lang="ts">
/**
 * ClientCreate · 客户创建（1:1 复刻 design/client-create.html）
 * - 5 form-section（基础信息/主要联系人/财务信息/客户分级/备注）
 * - dup-alert 重复检查提示
 * - level-grid 4 客户分级卡片（A 战略 / B 重点 / C 普通 / D 潜在）
 * - form-foot 底部操作条
 */
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clientApi, type Client } from '@/api/client'

const router = useRouter()
const route = useRoute()
const formRef = ref()
const editId = ref<number | null>(null)
const submitting = ref(false)
const isEdit = computed(() => !!editId.value)

// 表单状态（前端 UI 字段 ↔ 后端 Client 表做映射）
const form = reactive({
  name: '',
  shortName: '',
  taxNo: '',
  legalRep: '',         // 前端字段名 → 后端 legalPerson
  industry: '',
  // 联系人
  contactName: '',
  contactTitle: '',
  contactRole: '主要联系人',
  contactPhone: '',
  contactEmail: '',
  contactWechat: '',
  // 财务
  bank: '',             // 前端字段名 → 后端 bankName
  bankAccount: '',
  regAddress: '',       // 前端字段名 → 后端 address
  invoiceAddress: '',
  // 客户分级
  level: 'C',
  // 备注
  notes: '',            // 前端字段名 → 后端 remark
})

/** 前端表单 → 后端 Client payload（驼峰 ↔ 模型字段） */
function toPayload(f: typeof form) {
  return {
    name: f.name,
    shortName: f.shortName || null,
    taxNo: f.taxNo || null,
    legalPerson: f.legalRep || null,
    industry: f.industry || null,
    contactName: f.contactName || null,
    contactPhone: f.contactPhone || null,
    contactEmail: f.contactEmail || null,
    address: f.regAddress || f.invoiceAddress || null,
    bankName: f.bank || null,
    bankAccount: f.bankAccount || null,
    level: f.level || 'C',
    remark: f.notes || null,
  }
}

/** 后端 Client → 前端表单回填 */
function fromClient(c: Client) {
  form.name = c.name || ''
  form.shortName = c.shortName || ''
  form.taxNo = c.taxNo || ''
  form.legalRep = c.legalPerson || ''
  form.industry = c.industry || ''
  form.contactName = c.contactName || ''
  form.contactPhone = c.contactPhone || ''
  form.contactEmail = c.contactEmail || ''
  form.bank = c.bankName || ''
  form.bankAccount = c.bankAccount || ''
  form.regAddress = c.address || ''
  form.invoiceAddress = c.address || ''
  form.level = c.level || 'C'
  form.notes = c.remark || ''
}

const rules = {
  name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  contactName: [{ required: true, message: '请输入联系人姓名', trigger: 'blur' }],
  contactPhone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
}

// 4 客户分级
const levels = ref([
  { code: 'A', name: '战略客户', desc: '年合同额 ≥ 100 万', active: false },
  { code: 'B', name: '重点客户', desc: '年合同额 30-100 万',  active: true  },
  { code: 'C', name: '普通客户', desc: '年合同额 5-30 万',    active: false },
  { code: 'D', name: '潜在客户', desc: '年合同额 < 5 万',     active: false },
])

function selectLevel(c: string) {
  levels.value.forEach(l => l.active = l.code === c)
  form.level = c
}
function addContact() { ElMessage.info('添加更多联系人') }

// ===== 重复客户检查 =====
const dupMatches = ref<Array<{
  id: number; name: string; shortName: string | null;
  taxNo: string | null; level: string; isActive: boolean;
  createdAt: string | null;
}>>([])
const dupChecking = ref(false)
let dupTimer: number | undefined

async function runDupCheck() {
  const name = (form.name || '').trim()
  const tax = (form.taxNo || '').trim()
  if (!name && !tax) { dupMatches.value = []; return }
  dupChecking.value = true
  try {
    const res: any = await clientApi.dupCheck({
      name, taxNo: tax, excludeId: editId.value ?? null,
    })
    dupMatches.value = res?.matches || []
  } catch (e) {
    console.warn('[dup-check] failed', e)
    dupMatches.value = []
  } finally {
    dupChecking.value = false
  }
}
function scheduleDupCheck() {
  if (dupTimer) clearTimeout(dupTimer)
  dupTimer = window.setTimeout(runDupCheck, 350)
}
function viewDup(id: number) {
  router.push({ path: `/client/${id}` })
}
function mergeDup() {
  ElMessage.warning('请到详情页手动迁移数据后停用旧记录（合并迁移暂未实现）')
}
function saveDraft() { ElMessage.success('草稿已保存') }
async function submitCreate() {
  if (!form.name) { ElMessage.error('请填写客户名称'); return }
  if (submitting.value) return
  submitting.value = true
  try {
    const payload = toPayload(form)
    if (isEdit.value && editId.value) {
      await clientApi.update(editId.value, payload)
      ElMessage.success('客户已更新')
    } else {
      await clientApi.create(payload)
      ElMessage.success('客户已创建')
    }
    setTimeout(() => router.push('/client/list'), 600)
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || '未知错误'
    ElMessage.error((isEdit.value ? '更新失败：' : '创建失败：') + msg)
  } finally {
    submitting.value = false
  }
}
function cancel() { router.push('/client/list') }

watch(() => [form.name, form.taxNo], scheduleDupCheck)

onMounted(async () => {
  const idParam = route.query.id
  if (idParam) {
    const id = Number(idParam)
    if (!Number.isNaN(id)) {
      editId.value = id
      try {
        const c: any = await clientApi.detail(id)
        fromClient(c as Client)
        // 同步激活等级卡片
        levels.value.forEach(l => l.active = l.code === (form.level || 'C'))
      } catch (e: any) {
        ElMessage.error('加载客户详情失败：' + (e?.message || '未知错误'))
      }
    }
  }
})

// 触点 #20：AI 自动识别名片
const aiCardVisible = ref(false)
const aiCardLoading = ref(false)
const aiCardResult = ref<null | { name: string; company: string; position: string; phone: string; email: string; address: string; confidence: number }>(null)

async function runAiCard() {
  aiCardLoading.value = true
  try {
    await new Promise(r => setTimeout(r, 1500))
    aiCardResult.value = {
      name: '李建国',
      company: '万象科技有限公司',
      position: 'CTO',
      phone: '138 0011 2233',
      email: 'lijianguo@wanxiang.tech',
      address: '上海市浦东新区张江高科技园区',
      confidence: 0.94,
    }
  } finally {
    aiCardLoading.value = false
  }
}

function adoptAiCard() {
  const r = aiCardResult.value
  if (!r) return
  ElMessage.success('已采纳名片识别结果到表单（演示用，未实际写入）')
  aiCardVisible.value = false
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/client/list')">业务</a>
          <span class="sep">/</span>
          <a @click="router.push('/client/list')">客户管理</a>
          <span class="sep">/</span>
          <span class="current">新建客户</span>
        </div>
        <h1>新建客户</h1>
        <p class="page-desc">客户档案 · 联系信息 · 财务信息 · 客户分级</p>
      </div>
      <div class="page-actions">
        <!-- 触点 #20：AI 自动识别名片（演示功能，TODO: 接入真实 OCR + 名片抽取后开启） -->
        <el-tooltip content="该功能为演示版（OCR 服务当前仅支持发票抽取），暂未对接真实名片识别" placement="bottom">
          <button class="btn-ai-card" disabled style="opacity:0.5;cursor:not-allowed">📇 AI 自动识别名片（演示）</button>
        </el-tooltip>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
    </div>

    <!-- tip-box -->
    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>客户分级将影响：</strong>
        销售策略（VIP 自动绑定专属客户经理）、审批权限（A 级需总经理审批）、信用额度。
      </div>
    </div>

    <!-- 1. 基础信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>🏢 基础信息 <span class="req">* 必填</span></h3>
      </div>
      <div class="fs-body">
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="客户名称" prop="name" required>
                <el-input v-model="form.name" placeholder="营业执照上的法定名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="客户简称">
                <el-input v-model="form.shortName" placeholder="用于列表显示，可选" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="纳税人识别号" prop="taxNo">
                <el-input v-model="form.taxNo" style="font-family: var(--font-family-mono); font-size: 13px;" placeholder="18 位统一社会信用代码" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="法定代表人">
                <el-input v-model="form.legalRep" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="所属行业">
                <el-select v-model="form.industry" style="width: 100%">
                  <el-option label="制造业" value="制造业" />
                  <el-option label="互联网/IT" value="互联网/IT" />
                  <el-option label="金融业" value="金融业" />
                  <el-option label="零售/电商" value="零售/电商" />
                  <el-option label="服务业" value="服务业" />
                  <el-option label="智能设备" value="智能设备" />
                  <el-option label="教育" value="教育" />
                  <el-option label="医疗" value="医疗" />
                  <el-option label="其他" value="其他" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <!-- 重复检查提示：实时按 name / taxNo 查重，无结果不显示 -->
          <div v-if="dupMatches.length > 0" class="dup-alert">
            <div class="ico">⚠</div>
            <div class="body">
              <div class="t">系统检测到 {{ dupMatches.length }} 个相似客户，请确认是否重复</div>
              <div v-for="m in dupMatches" :key="m.id" class="item">
                <div>
                  <div class="name">
                    {{ m.name }}
                    <span v-if="!m.isActive" class="badge-inactive">已停用</span>
                  </div>
                  <div class="m">
                    <template v-if="m.taxNo">税号 {{ m.taxNo }} · </template>
                    <template v-if="m.shortName">简称 {{ m.shortName }} · </template>
                    <template v-if="m.createdAt">创建于 {{ m.createdAt.slice(0, 10) }}</template>
                  </div>
                </div>
                <div class="actions">
                  <a @click="viewDup(m.id)">查看</a>
                  <a @click="mergeDup">合并到此客户</a>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="dupChecking" class="dup-alert" style="background:#f1f5f9;border-color:#cbd5e1">
            <div class="ico" style="color:#64748b">⏳</div>
            <div class="body">
              <div class="t" style="color:#64748b">正在检查相似客户...</div>
            </div>
          </div>
        </el-form>
      </div>
    </div>

    <!-- 2. 主要联系人 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>👤 主要联系人 <span class="req">至少 1 位</span></h3>
        <a class="link-primary" @click="addContact">+ 添加更多联系人</a>
      </div>
      <div class="fs-body">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="联系人姓名" required>
              <el-input v-model="form.contactName" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="职位">
              <el-input v-model="form.contactTitle" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="角色">
              <el-select v-model="form.contactRole" style="width: 100%">
                <el-option label="主要联系人" value="主要联系人" />
                <el-option label="商务联系人" value="商务联系人" />
                <el-option label="技术联系人" value="技术联系人" />
                <el-option label="财务联系人" value="财务联系人" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="手机" required>
              <el-input v-model="form.contactPhone" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="邮箱">
              <el-input v-model="form.contactEmail" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="微信">
              <el-input v-model="form.contactWechat" placeholder="选填" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 3. 财务信息 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>💳 财务信息 <span class="req">开票与回款所需</span></h3>
      </div>
      <div class="fs-body">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开户银行">
              <el-input v-model="form.bank" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="银行账号">
              <el-input v-model="form.bankAccount" style="font-family: var(--font-family-mono); font-size: 12.5px;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="注册地址">
              <el-input v-model="form.regAddress" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开票地址电话">
              <el-input v-model="form.invoiceAddress" placeholder="用于开发票" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 4. 客户分级 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>⭐ 客户分级 <span class="req">影响销售策略与审批权限</span></h3>
      </div>
      <div class="fs-body">
        <div class="level-grid">
          <div v-for="l in levels" :key="l.code" :class="['level-card', { active: l.active }]" :data-level="l.code" @click="selectLevel(l.code)">
            <div class="badge">{{ l.code }}</div>
            <div class="name">{{ l.name }}</div>
            <div class="desc">{{ l.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. 备注 -->
    <div class="form-section">
      <div class="fs-head">
        <h3>📝 备注 <span class="opt">（可选）</span></h3>
      </div>
      <div class="fs-body">
        <el-input v-model="form.notes" type="textarea" :rows="4" placeholder="客户特殊要求、合作历史、风险提示等（500 字以内）" />
      </div>
    </div>

    <!-- form-foot 底部 -->
    <div class="form-foot">
      <div>
        <button class="btn btn-ghost btn-sm" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-outline btn-sm" @click="cancel">取消</button>
      </div>
      <div>
        <button class="btn btn-outline btn-sm">👁 预览</button>
        <button class="btn btn-primary btn-sm" :disabled="submitting" @click="submitCreate">
              {{ submitting ? '提交中...' : (isEdit ? '✓ 更新客户' : '✓ 创建客户') }}
            </button>
      </div>
    </div>
  </div>

  <!-- 触点 #20：AI 名片识别 Drawer -->
  <el-drawer v-model="aiCardVisible" title="📇 AI 自动识别名片" direction="rtl" size="480px">
    <div class="ai-card-drawer">
      <div class="ai-card-zone" @click="runAiCard">
        <div class="ai-card-icon">📷</div>
        <h3>点击上传名片照片</h3>
        <p>支持 JPG / PNG · 自动识别姓名/公司/职位/电话/邮箱/地址</p>
      </div>
      <el-progress v-if="aiCardLoading" :percentage="75" :stroke-width="6" status="success" />
      <div v-if="aiCardResult" class="ai-card-result">
        <h4>✨ 识别结果（置信度 {{ (aiCardResult.confidence * 100).toFixed(0) }}%）</h4>
        <div class="ai-card-fields">
          <div v-for="(v, k) in { 姓名: aiCardResult.name, 公司: aiCardResult.company, 职位: aiCardResult.position, 电话: aiCardResult.phone, 邮箱: aiCardResult.email, 地址: aiCardResult.address }" :key="k" class="ai-card-row">
            <span class="ai-card-k">{{ k }}</span>
            <span class="ai-card-v">{{ v }}</span>
          </div>
        </div>
        <div class="ai-card-actions">
          <el-button type="primary" @click="adoptAiCard">✓ 采纳到表单</el-button>
          <el-button @click="aiCardResult = null">重新识别</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
/* 触点 #20：AI 名片识别 */
.btn-ai-card {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 12px; font-size: 12px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none;
  border-radius: $radius-sm; cursor: pointer;
  box-shadow: 0 2px 6px rgba(79,107,255,0.2);
  &:hover { opacity: 0.92; }
}
.ai-card-drawer { padding: 0 4px; }
.ai-card-zone {
  padding: 40px 20px; text-align: center;
  background: linear-gradient(135deg, rgba(79,107,255,0.05) 0%, rgba(124,58,237,0.05) 100%);
  border: 2px dashed rgba(124,58,237,0.4);
  border-radius: $radius-md; cursor: pointer;
  &:hover { border-color: #7C3AED; }
  .ai-card-icon { font-size: 48px; margin-bottom: 12px; }
  h3 { font-size: 14px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  p { font-size: 12px; color: $color-text-secondary; }
}
.ai-card-result { margin-top: 20px; padding: 14px; background: linear-gradient(135deg, rgba(79,107,255,0.03) 0%, rgba(124,58,237,0.03) 100%); border: 1px solid rgba(124,58,237,0.25); border-radius: $radius-md; }
.ai-card-result h4 { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 12px; }
.ai-card-fields { display: flex; flex-direction: column; gap: 6px; }
.ai-card-row { display: flex; justify-content: space-between; padding: 6px 10px; background: #fff; border-radius: $radius-sm; font-size: 12px; }
.ai-card-k { color: $color-text-tertiary; }
.ai-card-v { color: $color-text-primary; font-weight: 600; }
.ai-card-actions { display: flex; gap: 8px; margin-top: 12px; }
</style>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

// tip-box
.tip-box {
  display: flex; gap: 10px;
  padding: 12px 14px;
  background: rgba(79,107,255,0.05);
  border: 1px solid rgba(79,107,255,0.2);
  border-radius: $radius-md;
  font-size: 12.5px;
  color: $color-text-secondary;
  line-height: 1.6;
  margin-bottom: 16px;
  .ico { color: $color-primary; font-size: 16px; flex-shrink: 0; }
  strong { color: $color-text-primary; }
}

// form-section
.form-section {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  margin-bottom: 16px;
  overflow: hidden;
}
.fs-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid $color-border;
  background: #FAFBFF;
  h3 { font-size: 14.5px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; }
  .req { font-size: 11.5px; color: $color-text-tertiary; font-weight: 400; }
  .opt { font-size: 11.5px; color: $color-text-tertiary; font-weight: 400; }
}
.fs-body { padding: 18px 20px; }
.link-primary { font-size: 12px; color: $color-primary; cursor: pointer; }
.link-primary:hover { text-decoration: underline; }

// dup-alert（design 重复检查提示）
.dup-alert {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: $color-warning-bg;
  border: 1px solid rgba(245,158,11,0.3);
  border-radius: $radius-md;
  margin-top: 8px;
  .ico { font-size: 20px; color: $color-warning; flex-shrink: 0; }
  .body { flex: 1; min-width: 0; }
  .t { font-size: 13px; font-weight: 600; color: #B45309; margin-bottom: 8px; }
  .item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: rgba(255,255,255,0.6);
    border-radius: $radius-sm;
  }
  .name { font-size: 12.5px; font-weight: 500; color: $color-text-primary; }
  .m { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; }
  .actions { display: flex; gap: 12px; }
  .actions a {
    font-size: 12px; color: $color-primary; cursor: pointer; font-weight: 500;
    &:hover { text-decoration: underline; }
  }
}

// level-grid 4 客户分级卡片
.level-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
}
.level-card {
  border: 1.5px solid $color-border;
  border-radius: $radius-md;
  padding: 18px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
  &:hover { border-color: $color-primary; transform: translateY(-2px); box-shadow: $shadow-md; }
  &.active {
    border-color: $color-primary;
    background: $color-primary-bg;
    box-shadow: 0 0 0 2px rgba(79,107,255,0.2);
  }
  .badge {
    width: 40px; height: 40px;
    margin: 0 auto 8px;
    border-radius: 50%;
    background: $gradient-brand;
    color: #fff;
    display: grid; place-items: center;
    font-size: 18px;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(79,107,255,0.3);
  }
  .name { font-size: 13.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; }
  .desc { font-size: 11.5px; color: $color-text-tertiary; }
}

// form-foot
.form-foot {
  position: sticky;
  bottom: 0;
  background: #fff;
  border-top: 1px solid $color-border;
  padding: 14px 0;
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
  box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.04);
}

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
}

// Element Plus form-item
:deep(.el-form-item__label) { font-weight: 500; color: $color-text-secondary; font-size: 12.5px; }
:deep(.el-form-item.is-required .el-form-item__label::before) { content: '*'; color: $color-danger; margin-right: 4px; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner), :deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px $color-border inset !important;
  border-radius: $radius-md !important;
  &:hover { box-shadow: 0 0 0 1px $color-primary inset !important; }
  &.is-focus { box-shadow: 0 0 0 1px $color-primary inset, 0 0 0 4px rgba(79,107,255,0.08) !important; }
}
</style>
