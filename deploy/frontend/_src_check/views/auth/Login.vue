<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = reactive({ account: 'admin', password: 'admin123' })
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
    await userStore.login(form)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e) {
    // 拦截器已弹错误
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg" />
    <div class="login-card">
      <div class="login-left">
        <div class="brand">
          <div class="brand-logo">数</div>
          <div class="brand-name">数智化管理系统</div>
        </div>
        <h1 class="slogan">让发票、合同、费用<br />都跑在数智化轨道上</h1>
        <ul class="features">
          <li>📷 AI 智能识别：发票 OCR 准确率 95%+</li>
          <li>🔍 实时查验：国税总局合规核验</li>
          <li>📊 数据回流：全链路审计 + 智能预警</li>
        </ul>
        <div class="version">Shuzhi v1.0 · Internal Build</div>
      </div>

      <div class="login-right">
        <h2>欢迎登录</h2>
        <p class="hint">使用您的企业账号继续</p>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
          <el-form-item prop="account">
            <el-input v-model="form.account" placeholder="账号" :prefix-icon="'User'" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="'Lock'" show-password />
          </el-form-item>
          <el-button class="login-btn" :loading="loading" @click="handleLogin">登 录</el-button>
        </el-form>

        <div class="login-tip">
          <el-text size="small" type="info">默认账号：admin / admin123</el-text>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
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

.login-bg {
  position: absolute;
  inset: 0;
  background: $gradient-hero;
  &::before, &::after {
    content: '';
    position: absolute;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.4;
  }
  &::before {
    background: #4F6BFF;
    top: -200px;
    left: -200px;
  }
  &::after {
    background: #7C3AED;
    bottom: -200px;
    right: -200px;
  }
}

.login-card {
  position: relative;
  z-index: 1;
  display: flex;
  width: 920px;
  height: 540px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  box-shadow: 0 24px 80px -20px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  backdrop-filter: blur(20px);
}

.login-left {
  width: 420px;
  padding: 48px 40px;
  background: $gradient-hero;
  color: #fff;
  display: flex;
  flex-direction: column;
  position: relative;

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
    .brand-logo {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: $gradient-brand;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
      box-shadow: $shadow-glow;
    }
    .brand-name {
      font-size: 15px;
      font-weight: 600;
    }
  }

  .slogan {
    font-size: 26px;
    font-weight: 700;
    line-height: 1.5;
    margin: 80px 0 32px 0;
    background: linear-gradient(135deg, #fff 0%, #c7d2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .features {
    list-style: none;
    padding: 0;
    margin: 0;
    li {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
      padding: 10px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
  }

  .version {
    margin-top: auto;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.5);
    letter-spacing: 1px;
  }
}

.login-right {
  flex: 1;
  padding: 64px 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;

  h2 {
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 8px 0;
    background: $gradient-brand;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .hint {
    color: $color-text-secondary;
    font-size: 13px;
    margin-bottom: 32px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  background: $gradient-brand !important;
  border: none !important;
  color: #fff !important;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  margin-top: 8px;
  &:hover {
    opacity: 0.92;
  }
}

.login-tip {
  margin-top: 16px;
  text-align: center;
}
</style>
