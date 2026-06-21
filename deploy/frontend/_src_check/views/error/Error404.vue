<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="error-page">
    <div class="error-code">404</div>
    <h1>页面不存在</h1>
    <p>您访问的页面已被删除或不存在</p>
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<style lang="scss" scoped>
.error-page { height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: $color-bg; text-align: center; .error-code { font-size: 120px; font-weight: 800; background: $gradient-brand; -webkit-background-clip: text; -webkit-text-fill-color: transparent; } h1 { margin: 12px 0; } p { color: $color-text-secondary; margin-bottom: 24px; } }
</style>
