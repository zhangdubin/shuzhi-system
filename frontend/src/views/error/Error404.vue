<script setup lang="ts">
/**
 * Error404 · 页面未找到（1:1 复刻 design/error-404.html）
 */
import ErrorPage from '@/components/common/ErrorPage.vue'
</script>

<template>
  <ErrorPage
    code="404"
    icon="🔍"
    title="页面走丢了"
    sub="你访问的页面不存在、已被移除或暂时无法访问。<br/>请检查 URL 是否正确，或返回首页继续操作。"
  />
</template>
