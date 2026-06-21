<script setup lang="ts">
/**
 * ErrorNetwork · 网络中断（1:1 复刻 design/error-network.html）
 */
import ErrorPage from '@/components/common/ErrorPage.vue'
</script>

<template>
  <ErrorPage
    :code="''"
    icon="📡"
    title="网络连接中断"
    sub="无法连接到服务器，请检查你的网络设置。<br/>如果网络正常，可能是服务暂时不可用。"
  />
</template>
