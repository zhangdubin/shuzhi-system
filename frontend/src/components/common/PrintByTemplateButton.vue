<!--
  PrintByTemplateButton · UDPE "按模板打印" 通用按钮
  ======================================================================
  设计文档：plans/udpe-design/design.md §十
  阶段：M2 阶段 6（消除 4 处样板代码）

  用法（直接当按钮用）：
    <PrintByTemplateButton
      template-code="invoice_v1"
      :business-id="invoiceId"
      source-module="invoice"
      label="按模板打印"
      icon="🧾"
    />

  用法（弹窗已由调用方控制）：
    <PrintByTemplateButton
      template-code="invoice_v1"
      :business-id="invoiceId"
      source-module="invoice"
      :embedded="true"
      @click="printDialogVisible = true"
    />

  Permission：默认要 print:document:export，无权限时按钮自动隐藏。
-->
<template>
  <component
    :is="tag"
    v-if="hasPermission"
    v-permission="'print:document:export'"
    :class="['udpe-print-btn', buttonClass]"
    :type="elType"
    :size="size"
    @click="onClick"
  >
    <span v-if="icon" class="udpe-icon">{{ icon }}</span>
    <span>{{ label }}</span>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const props = withDefaults(defineProps<{
  /** UDPE 模板 code（必填） */
  templateCode: string
  /** 业务单据 ID（必填，data._resolver） */
  businessId: string | number
  /** 业务模块名（必填，写 print_logs） */
  sourceModule: string
  /** 按钮文字 */
  label?: string
  /** 按钮图标 */
  icon?: string
  /** 自定义 CSS class（让按钮风格融入各页面） */
  buttonClass?: string
  /** 嵌入模式：只渲染按钮 + 触发 click，由调用方控制 dialog */
  embedded?: boolean
  /** 渲染元素：button（默认） | el-button */
  tag?: 'button' | 'el-button'
  /** el-button 风格 */
  elType?: 'primary' | 'success' | 'warning' | 'info' | 'danger' | 'default'
  /** el-button size */
  size?: 'small' | 'default' | 'large'
  /** 显式传 false 跳过权限检查（管理员内部跳转用） */
  bypassPermission?: boolean
}>(), {
  label: '按模板打印',
  icon: '🧾',
  embedded: false,
  tag: 'el-button',
  elType: 'primary',
  size: 'default',
  bypassPermission: false,
})

const emit = defineEmits<{
  (e: 'click', payload: { templateCode: string; businessId: string | number; sourceModule: string }): void
}>()

const userStore = useUserStore()
const hasPermission = computed(() => {
  if (props.bypassPermission) return true
  return userStore.permissions?.includes?.('print:document:export') ?? false
})

function onClick() {
  emit('click', {
    templateCode: props.templateCode,
    businessId: props.businessId,
    sourceModule: props.sourceModule,
  })
}
</script>

<style scoped>
.udpe-print-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.udpe-icon { font-size: 14px; line-height: 1; }
</style>
