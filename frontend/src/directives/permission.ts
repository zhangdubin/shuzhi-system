/**
 * v-permission · R11B 权限指令
 * 用法：<button v-permission="'contract:write'">编辑</button>
 *      <button v-permission:any="['contract:write', 'contract:read']">查看</button>  (任一)
 *      <button v-permission:all="['contract:write', 'contract:approve']">提交审批</button>  (全部)
 *
 * - super admin 自动放行（user.is_admin）
 * - 没权限 → 移除元素（display: none 等价）
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'

type PermMode = 'any' | 'all' | undefined

function check(mode: PermMode, codes: string[], hasPerm: (c: string) => boolean): boolean {
  if (mode === 'all') return codes.every(c => hasPerm(c))
  // 默认 any
  return codes.some(c => hasPerm(c))
}

function update(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
  const userStore = useUserStore()
  const value = binding.value
  if (!value) return

  const codes = Array.isArray(value) ? value : [value]
  const hasPerm = (c: string) => userStore.hasPerm(c)

  // super admin 自动放行：isAdmin=true / '*' 通配符 / 显式 'admin' 权限码
  if (userStore.isAdmin || userStore.permissions.includes('*')) {
    el.style.display = ''
    el.removeAttribute('disabled')
    return
  }

  const ok = check(binding.arg as PermMode, codes, hasPerm)
  if (ok) {
    el.style.display = ''
    el.removeAttribute('disabled')
  } else {
    el.style.display = 'none'
    el.setAttribute('disabled', 'disabled')
  }
}

const directive: Directive<HTMLElement, string | string[]> = {
  mounted: update,
  updated: update,
}

export default directive
