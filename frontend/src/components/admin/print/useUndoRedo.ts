/**
 * useUndoRedo · 撤销/重做历史栈 composable (M3 阶段 6)
 *
 * 用法:
 *   const { push, undo, redo, canUndo, canRedo } = useUndoRedo(visualBody, 50)
 *
 * - push(): 在每次 visualBody 变化前手动调用，保存当前快照
 * - undo(): 撤销到上一步
 * - redo(): 重做到下一步
 * - canUndo / canRedo: computed<boolean>，用于按钮 disabled
 */
import { ref, computed, type Ref } from 'vue'

export interface UndoRedoReturn {
  push: () => void
  undo: () => void
  redo: () => void
  canUndo: Ref<boolean>
  canRedo: Ref<boolean>
  clear: () => void
  historyLength: Ref<number>
  pointer: Ref<number>
}

export function useUndoRedo(
  target: Ref<Record<string, any>[]>,
  maxHistory: number = 50,
): UndoRedoReturn {
  const history = ref<string[]>([])
  const pointer = ref(-1)
  let _suppress = false  // 防止 undo/redo 触发 push

  /** 深拷贝快照 (JSON 序列化，剔除临时 id 以外的引用问题) */
  function snapshot(): string {
    return JSON.stringify(target.value)
  }

  /** 保存当前状态到历史栈（剪断 redo 分支） */
  function push() {
    if (_suppress) return
    const snap = snapshot()
    // 如果和栈顶相同就不重复压入
    if (history.value.length > 0 && history.value[pointer.value] === snap) return
    // 剪断 pointer 之后的分支
    history.value = history.value.slice(0, pointer.value + 1)
    history.value.push(snap)
    // 超过上限裁剪前面的
    if (history.value.length > maxHistory) {
      history.value = history.value.slice(history.value.length - maxHistory)
    }
    pointer.value = history.value.length - 1
  }

  function undo() {
    if (pointer.value <= 0) return
    _suppress = true
    pointer.value--
    target.value = JSON.parse(history.value[pointer.value])
    _suppress = false
  }

  function redo() {
    if (pointer.value >= history.value.length - 1) return
    _suppress = true
    pointer.value++
    target.value = JSON.parse(history.value[pointer.value])
    _suppress = false
  }

  function clear() {
    history.value = []
    pointer.value = -1
  }

  const canUndo = computed(() => pointer.value > 0)
  const canRedo = computed(() => pointer.value < history.value.length - 1)
  const historyLength = computed(() => history.value.length)

  return { push, undo, redo, canUndo, canRedo, clear, historyLength, pointer }
}
