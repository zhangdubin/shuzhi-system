<script setup lang="ts">
/**
 * Error403 · 无权访问（1:1 复刻 design/error-403.html）
 */
import ErrorPage from '@/components/common/ErrorPage.vue'
</script>

<template>
  <ErrorPage
    code="403"
    icon="🔒"
    title="无权访问此页面"
    sub="你的账号没有访问该资源的权限。<br/>请联系管理员申请相应权限，或返回首页继续操作。"
  />
</template>
