<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="error-page">
    <div class="error-code">403</div>
    <h1>没有访问权限</h1>
    <p>您没有访问该资源的权限，请联系管理员</p>
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<style lang="scss" scoped>
.error-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: $color-bg;
  text-align: center;
  .error-code { font-size: 120px; font-weight: 800; background: $gradient-brand; -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  h1 { margin: 12px 0; }
  p { color: $color-text-secondary; margin-bottom: 24px; }
}
</style>
