<script setup lang="ts">
/**
 * Login · 1:1 复刻 design/login.html
 * - 左侧品牌区（深色渐变 + Slogan + features + brand-stats）
 * - 右侧表单（账号/密码 + 记住我/忘记密码 + 登录按钮 + SSO 3 家）
 * - 扫码登录弹层（企业微信/钉码切换）
 * - 后端走 /auth/login（BFF 真后端）
 */
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = reactive({ account: 'admin', password: 'admin123' })
const remember = ref(true)
const loading = ref(false)
const formRef = ref()

const rules = {
  account: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '至少 6 位', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await userStore.login({ ...form, remember: remember.value })
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 扫码弹层
const showScan = ref(false)
const scanTab = ref<'wx' | 'dd'>('wx')

// 6 个 brand stats（design: .brand-stats 6 卡片）
const brandStats = [
  { v: '¥ 1.2亿', l: '累计处理发票' },
  { v: '99.6%',   l: 'OCR 准确率' },
  { v: '186 张',  l: '本月查验' },
  { v: '328 张',  l: '本月识别' },
  { v: '4,250+',  l: '服务企业' },
  { v: '24/7',    l: 'AI 在线' },
]

// 按 ESC 关闭弹层
function onEsc(e: KeyboardEvent) { if (e.key === 'Escape') showScan.value = false }
onMounted(() => window.addEventListener('keydown', onEsc))
onUnmounted(() => window.removeEventListener('keydown', onEsc))

// 触点 #17：智能问数（无需登录）
const aiAskVisible = ref(false)
const askQ = ref('')
const askA = ref('')
async function runAsk() {
  if (!askQ.value.trim()) return
  askA.value = 'AI 正在分析（mock）...\n\n基于公开示例数据：\n- 本月新签合同 8 份，金额 ¥1,234,500\n- 销售费用 12 单，总额 ¥86,500\n- 逾期回款 3 笔，总额 ¥48,600\n- AI 风险项目 2 个\n\n登录后可查看详细数据 ✨'
}
</script>

<template>
  <div class="login-page">
    <!-- 背景光斑 -->
    <div class="login-bg" />

    <div class="login-wrap">
      <!-- 左侧品牌区 -->
      <div class="login-brand">
        <div class="brand-top">
          <div class="brand-logo">
            <div class="brand-icon">数</div>
            <span>数智化管理系统</span>
          </div>
          <h1 class="brand-pitch">
            让发票、合同、费用<br />
            都跑在数智化轨道上
          </h1>
          <p class="brand-desc">
            财务·业务·AI 一体化平台，<br />
            为成长型企业打造可投产的数智化基础设施。
          </p>
          <ul class="features">
            <li><span class="feat-ico">📷</span> AI 智能识别 · 发票 OCR 准确率 99%+</li>
            <li><span class="feat-ico">🔍</span> 国税实时查验 · 100% 合规</li>
            <li><span class="feat-ico">📊</span> 全链路审计 + 智能预警</li>
            <li><span class="feat-ico">🔗</span> 6 大业务模块无缝集成</li>
          </ul>
        </div>
        <div class="brand-stats">
          <div v-for="(s, i) in brandStats" :key="i" class="stat-item">
            <div class="v">{{ s.v }}</div>
            <div class="l">{{ s.l }}</div>
          </div>
        </div>
        <div class="brand-footer">© 2026 Shuzhi v1.0 · Internal Build · Made with 💙</div>
      </div>

      <!-- 右侧表单 -->
      <div class="login-form-wrap">
        <h2 class="form-title">欢迎登录</h2>
        <p class="form-sub">使用您的企业账号继续</p>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
          <el-form-item prop="account">
            <el-input v-model="form.account" placeholder="账号 / 邮箱 / 工号" :prefix-icon="'User'" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="'Lock'" show-password />
          </el-form-item>
        </el-form>

        <div class="form-row">
          <label class="checkbox">
            <input v-model="remember" type="checkbox" />
            <span>记住我（7 天免登录）</span>
          </label>
          <a class="forgot" @click.prevent="ElMessage.info('请联系管理员重置密码')">忘记密码？</a>
        </div>

        <button class="btn-login" :disabled="loading" @click="handleLogin">
          <span v-if="!loading">登 录</span>
          <span v-else>登录中...</span>
        </button>

        <!-- 触点 #17：🤖 智能问数入口（无需登录可问） -->
        <button class="btn-ai-ask" @click="aiAskVisible = true">
          <span class="ico">🤖</span>智能问数（无需登录）
        </button>

        <!-- 触点 #17 弹层 -->
        <el-dialog v-model="aiAskVisible" title="🤖 智能问数" width="480px">
          <div class="ai-ask-pre">
            <p>体验一下 AI 能力（无需登录）：</p>
            <el-input v-model="askQ" type="textarea" :rows="3" placeholder="例：本月签了多少合同？逾期回款有哪些？" />
            <el-button type="primary" class="ai-ask-go" @click="runAsk">✨ 问 AI</el-button>
            <div v-if="askA" class="ai-ask-answer">{{ askA }}</div>
          </div>
        </el-dialog>

        <div class="login-bottom">
          <span>其他登录方式：</span>
          <a class="sso-btn wx" @click.prevent="scanTab='wx'; showScan=true">
            <span class="ico">💬</span>企业微信
          </a>
          <a class="sso-btn dd" @click.prevent="scanTab='dd'; showScan=true">
            <span class="ico">📱</span>钉钉扫码
          </a>
        </div>

        <p class="form-tip">默认账号：admin / admin123 · 测试环境</p>
      </div>
    </div>

    <!-- 扫码弹层 -->
    <div v-if="showScan" class="scan-modal show" @click.self="showScan=false">
      <div class="scan-panel">
        <a class="scan-close" @click="showScan=false">✕</a>
        <h3 style="margin: 0 0 16px; font-size: 17px; font-weight: 600;">扫码登录</h3>
        <div class="scan-tabs">
          <a :class="{ active: scanTab === 'wx' }" @click.prevent="scanTab='wx'">企业微信</a>
          <a :class="{ active: scanTab === 'dd' }" @click.prevent="scanTab='dd'">钉钉</a>
        </div>
        <div class="scan-qr">
          <div class="scan-qr-text">扫码中...</div>
        </div>
        <p class="scan-tip">
          请使用 <strong>{{ scanTab === 'wx' ? '企业微信' : '钉钉' }}</strong> 扫一扫
        </p>
        <p class="scan-tip" style="font-size: 11px; color: #94A3B8;">企业 SSO 集成预留：完整协议 + Mock 模式</p>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
/* 触点 #17：智能问数入口 */
.btn-ai-ask {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%; padding: 10px; margin-top: 12px;
  background: $gradient-brand; color: #fff; border: none;
  border-radius: $radius-md; font-size: 13px; font-weight: 600; cursor: pointer;
  box-shadow: 0 2px 8px rgba(79,107,255,0.25);
  transition: all 0.15s;
  &:hover { opacity: 0.92; }
  .ico { font-size: 16px; }
}
.ai-ask-pre p { font-size: 12px; color: $color-text-secondary; margin-bottom: 8px; }
.ai-ask-go { width: 100%; margin-top: 8px; background: $gradient-brand; border: none; }
.ai-ask-answer {
  margin-top: 12px; padding: 12px;
  background: linear-gradient(135deg, rgba(79,107,255,0.04) 0%, rgba(124,58,237,0.04) 100%);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: $radius-sm;
  font-size: 12px; color: $color-text-primary; line-height: 1.7; white-space: pre-wrap;
}
</style>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;

.login-page {
  position: relative;
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0B1220;
  overflow: hidden;
}

// 背景光斑（design 一致）
.login-bg {
  position: absolute;
  inset: 0;
  &::before, &::after {
    content: '';
    position: absolute;
    width: 500px; height: 500px;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.5;
    pointer-events: none;
  }
  &::before {
    background: radial-gradient(circle, #4F6BFF 0%, transparent 70%);
    top: -100px; left: -100px;
  }
  &::after {
    background: radial-gradient(circle, #7C3AED 0%, transparent 70%);
    bottom: -150px; right: -100px;
  }
}

.login-wrap {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  width: 1000px;
  max-width: 95vw;
  min-height: 600px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 40px 80px -20px rgba(0, 0, 0, 0.4);
}

// 左侧品牌区
.login-brand {
  background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #312E81 100%);
  padding: 48px 40px;
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 20% 20%, rgba(124, 58, 237, 0.4) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(79, 107, 255, 0.3) 0%, transparent 50%);
    pointer-events: none;
  }
  .brand-top { position: relative; z-index: 1; }
  .brand-logo {
    display: flex; align-items: center; gap: 12px;
    font-size: 16px; font-weight: 600;
    margin-bottom: 56px;
  }
  .brand-icon {
    width: 40px; height: 40px;
    border-radius: 10px;
    background: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
    display: grid; place-items: center;
    color: #fff; font-weight: 700; font-size: 17px;
    box-shadow: 0 4px 16px rgba(79, 107, 255, 0.5);
  }
  .brand-pitch {
    font-size: 28px;
    line-height: 1.4;
    font-weight: 700;
    margin: 0 0 14px 0;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #fff 0%, #c7d2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .brand-desc {
    font-size: 13.5px;
    color: rgba(226, 232, 240, 0.75);
    line-height: 1.7;
    margin: 0 0 24px 0;
  }
  .features {
    list-style: none;
    padding: 0;
    margin: 0 0 24px 0;
    li {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
      padding: 8px 0;
      display: flex; align-items: center; gap: 10px;
    }
    .feat-ico {
      width: 28px; height: 28px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      display: grid; place-items: center;
      font-size: 14px;
      flex-shrink: 0;
    }
  }
  .brand-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px 16px;
    padding: 16px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 16px;
    .stat-item {
      .v {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        font-family: $font-family-mono;
        letter-spacing: -0.3px;
      }
      .l {
        font-size: 11px;
        color: rgba(226, 232, 240, 0.6);
        margin-top: 2px;
      }
    }
  }
  .brand-footer {
    font-size: 11px;
    color: rgba(226, 232, 240, 0.4);
    letter-spacing: 0.3px;
  }
}

// 右侧表单
.login-form-wrap {
  padding: 56px 56px 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  .form-title {
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 6px 0;
    background: $gradient-brand;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .form-sub {
    color: $color-text-secondary;
    font-size: 13px;
    margin: 0 0 28px 0;
  }
  .form-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: -8px 0 20px;
    font-size: 13px;
  }
  .checkbox {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: $color-text-secondary;
    user-select: none;
    input {
      width: 16px; height: 16px;
      accent-color: $color-primary;
      cursor: pointer;
    }
  }
  .forgot {
    color: $color-primary;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.15s;
    &:hover { opacity: 0.8; }
  }
  .btn-login {
    width: 100%;
    height: 48px;
    background: $gradient-brand;
    color: #fff;
    border-radius: $radius-md;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 4px;
    box-shadow: $shadow-glow;
    transition: all 0.18s;
    border: none;
    cursor: pointer;
    margin-top: 8px;
    &:hover { transform: translateY(-1px); box-shadow: 0 12px 32px -4px rgba(79, 107, 255, 0.5); }
    &:active { transform: translateY(0); }
    &:disabled { opacity: 0.6; cursor: not-allowed; }
  }
  .login-bottom {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-top: 24px;
    font-size: 12.5px;
    color: $color-text-tertiary;
    flex-wrap: wrap;
  }
  .sso-btn {
    height: 32px;
    padding: 0 12px;
    background: #fff;
    border: 1px solid $color-border;
    border-radius: $radius-sm;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: $color-text-secondary;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    .ico { font-size: 14px; }
    &:hover { border-color: $color-primary; color: $color-primary; background: $color-primary-bg; }
    &.wx:hover { color: #07C160; border-color: #07C160; background: rgba(7, 193, 96, 0.06); }
    &.dd:hover { color: #1677FF; border-color: #1677FF; background: rgba(22, 119, 255, 0.06); }
  }
  .form-tip {
    margin-top: 16px;
    text-align: center;
    font-size: 11px;
    color: $color-text-tertiary;
  }
}

// 扫码弹层
.scan-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.18s ease-out;
}
.scan-panel {
  position: relative;
  background: #fff;
  border-radius: 20px;
  width: 380px;
  padding: 32px;
  text-align: center;
  box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.3);
  animation: pop 0.25s ease-out;
}
.scan-close {
  position: absolute;
  top: 16px; right: 16px;
  width: 28px; height: 28px;
  border-radius: 50%;
  display: grid; place-items: center;
  color: $color-text-tertiary;
  cursor: pointer;
  font-size: 16px;
  &:hover { background: $color-bg; color: $color-text-primary; }
}
.scan-tabs {
  display: flex;
  gap: 4px;
  background: $color-bg;
  border-radius: $radius-md;
  padding: 4px;
  margin-bottom: 24px;
  a {
    flex: 1;
    padding: 8px 0;
    font-size: 13px;
    color: $color-text-secondary;
    border-radius: $radius-sm;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    &.active {
      background: #fff;
      color: $color-primary;
      box-shadow: $shadow-sm;
    }
  }
}
.scan-qr {
  width: 200px; height: 200px;
  margin: 0 auto 16px;
  background: $color-bg;
  border-radius: $radius-md;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    inset: 12px;
    background:
      linear-gradient(45deg, #0F172A 25%, transparent 25%, transparent 75%, #0F172A 75%) 0 0/16px 16px,
      linear-gradient(45deg, #0F172A 25%, transparent 25%, transparent 75%, #0F172A 75%) 8px 8px/16px 16px;
    border-radius: 6px;
    opacity: 0.85;
  }
  &::after {
    content: '';
    position: absolute;
    left: 0; right: 0;
    height: 2px;
    background: $color-primary;
    box-shadow: 0 0 10px $color-primary;
    animation: scan 2s linear infinite;
  }
  .scan-qr-text {
    position: relative;
    z-index: 1;
    color: $color-primary;
    font-size: 13px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.95);
    padding: 4px 10px;
    border-radius: 4px;
  }
}
.scan-tip {
  font-size: 13px;
  color: $color-text-secondary;
  margin: 0 0 6px 0;
  strong { color: $color-primary; }
}
@keyframes scan { 0% { top: 12px; } 50% { top: calc(100% - 12px); } 100% { top: 12px; } }
@keyframes pop { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
