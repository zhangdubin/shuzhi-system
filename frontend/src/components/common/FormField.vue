<script setup lang="ts">
/**
 * FormField · 统一表单字段（design: .field）
 * - label + required/optional + input/select/textarea slot
 * - 3 字段 grid 用 form-row 类
 */
defineProps<{
  label: string
  required?: boolean
  optional?: boolean
  /** 占满整行（grid-column: 1 / -1） */
  full?: boolean
}>()
</script>

<template>
  <div :class="['field', { full }]">
    <label>
      {{ label }}
      <span v-if="required" class="req">*</span>
      <span v-if="optional" class="opt">（可选）</span>
    </label>
    <slot />
  </div>
</template>

<style lang="scss" scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  &.full { grid-column: 1 / -1; }
  label {
    font-size: 12.5px;
    font-weight: 500;
    color: #475569;
    .req { color: #EF4444; }
    .opt { color: #94A3B8; font-weight: 400; font-size: 11px; margin-left: 4px; }
  }
  :slotted(input),
  :slotted(select),
  :slotted(textarea) {
    padding: 10px 14px;
    border: 1.5px solid #E2E8F0;
    border-radius: 10px;
    font-size: 13.5px;
    color: #0F172A;
    background: #fff;
    transition: all 0.15s;
    outline: none;
    font-family: inherit;
    width: 100%;
  }
  :slotted(input:focus),
  :slotted(select:focus),
  :slotted(textarea:focus) {
    border-color: #4F6BFF;
    box-shadow: 0 0 0 4px rgba(79, 107, 255, 0.08);
  }
  :slotted(textarea) { resize: vertical; min-height: 80px; }
}
</style>
