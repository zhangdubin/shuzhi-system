<script setup lang="ts">
/**
 * 系统设置页（admin only）
 * - 左侧：分组导航（应用/数据库/Redis/JWT/OCR/诺诺/企业微信/AI/MinIO/Sentry）
 * - 右侧：当前分组的设置项表单
 * - 敏感字段：默认脱敏显示，点击"修改"展开输入框
 * - 底部："测试连通性" + "保存更改"
 */
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { settingsApi, type SettingItem } from '@/api/modules'

const groups = ref<Record<string, SettingItem[]>>({})
const envFilePath = ref('')
const runtimeEnv = ref('')
const version = ref('')
const activeGroup = ref<string>('')
const loading = ref(false)
const saving = ref(false)
const testing = ref<string | null>(null)
// 触点 #52：备份/导入/更新
const exportLoading = ref(false)
const importDialogVisible = ref(false)
const importPayloadText = ref('')
const importLoading = ref(false)
const updateDialogVisible = ref(false)
const updateInfo = ref<any>(null)
const updateLoading = ref(false)

// 本地编辑态：key -> value（所有非敏感字段预填 displayValue，避免 v-model undefined；敏感字段留空）
const edits = reactive<Record<string, string>>({})
// 哪些 key 正在被编辑（敏感字段）
const editing = reactive<Set<string>>(new Set())
// 哪些 key 被用户真正改动过（触点 #51 修复初始 34 项误报问题）
const dirty = reactive<Set<string>>(new Set())

// 触点：扩展能力
const totalItems = computed(() => Object.values(groups.value).reduce((sum, arr) => sum + (arr?.length || 0), 0))
function hasGroupDirty(g: string) {
  return (groups.value[g] || []).some(it => dirty.has(it.key))
}
const groupFilter = ref('')
const filteredGroupItems = computed(() => {
  const arr = groups.value[activeGroup.value] || []
  if (!groupFilter.value.trim()) return arr
  const kw = groupFilter.value.toLowerCase()
  return arr.filter(it => it.label.toLowerCase().includes(kw) || it.key.toLowerCase().includes(kw))
})
const showSecrets = reactive<Record<string, boolean>>({})
const isEdited = (key: string) => dirty.has(key)

function markDirty(key: string) {
  dirty.add(key)
}
function clearDirty(key: string) {
  dirty.delete(key)
}

const groupList = computed(() => Object.keys(groups.value))
const groupIcon: Record<string, string> = {
  '应用': '⚙',
  '数据库': '🗄',
  'Redis': '🔴',
  'JWT 安全': '🔐',
  'CORS': '🌐',
  'OCR 识别': '🔍',
  '诺诺发票云': '🧾',
  '企业微信 SSO': '💬',
  'AI 平台': '🤖',
  '对象存储 MinIO': '🗃',
  'Sentry 监控': '🛡',
}

async function load() {
  loading.value = true
  try {
    const r: any = await settingsApi.getAll()
    groups.value = r.groups
    envFilePath.value = r.envFilePath
    runtimeEnv.value = r.runtimeEnv
    version.value = r.version
    // 初始化 edits：所有非敏感字段先用 displayValue 占位，避免 el-switch/el-input
    // v-model undefined 时报 "Cannot set properties of undefined (setting 'checked')"
    for (const g of groupList.value) {
      for (const it of groups.value[g] || []) {
        if (!it.sensitive && edits[it.key] === undefined) {
          edits[it.key] = it.displayValue ?? ''
        }
      }
    }
    if (!activeGroup.value && groupList.value.length > 0) {
      activeGroup.value = groupList.value[0]
    }
  } catch (e: any) {
    ElMessage.error('加载配置失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function startEdit(item: SettingItem) {
  if (item.sensitive) {
    // 敏感字段：空值代表新增；非空代表"修改"
    edits[item.key] = ''
    editing.add(item.key)
    markDirty(item.key)  // 触点 #51：敏感字段进入编辑态就视为已改
  } else {
    edits[item.key] = item.displayValue
    // 非敏感字段：仅当 v-model 实际变化时通过 @change / @input 加 dirty，不在这里加
  }
}

function clearAllEdits() {
  // 清空所有 dirty，同时把所有 edits 还原为 displayValue
  for (const k of Array.from(dirty)) {
    for (const g of groupList.value) {
      const item = groups.value[g]?.find(i => i.key === k)
      if (item) {
        edits[item.key] = item.displayValue ?? ''
        editing.delete(item.key)
        break
      }
    }
  }
  // 同时清掉那些"预填了但没改"的非敏感字段的脏标记（理论上 dirty 本来就只是用户改的）
  dirty.clear()
}

function cancelEdit(item: SettingItem) {
  // 还原为 displayValue（避免下一次显示 v-model undefined）
  edits[item.key] = item.displayValue ?? ''
  editing.delete(item.key)
  clearDirty(item.key)
}

function displaySecret(item: SettingItem): string {
  // 安全策略：前端永远拿不到明文
  if (!item.isSet) return '未配置'
  if (showSecrets[item.key]) {
    return `${item.displayValue}（已设置）`
  }
  return item.displayValue
}

const isEditing = (key: string) => editing.has(key)
const editedKeys = computed(() => Array.from(dirty))

const editedItems = computed(() => {
  const out: Array<{ key: string; group: string; label: string; oldValue: string; newValue: string; sensitive: boolean; hotReload: boolean; warning?: string }> = []
  for (const k of editedKeys.value) {
    for (const g of groupList.value) {
      const item = groups.value[g].find(i => i.key === k)
      if (item) {
        out.push({
          key: k,
          group: g,
          label: item.label,
          oldValue: item.displayValue,
          newValue: edits[k],
          sensitive: !!item.sensitive,
          hotReload: item.hotReload,
          warning: item.warning,
        })
        break
      }
    }
  }
  return out
})

async function save() {
  if (editedKeys.value.length === 0) {
    ElMessage.warning('没有需要保存的修改')
    return
  }
  // 二次确认
  const list = editedItems.value
  const sensitive = list.filter(i => i.sensitive)
  if (sensitive.length > 0) {
    try {
      await ElMessageBox.confirm(
        `即将保存 ${sensitive.length} 个敏感字段，修改后立即生效且不可撤销。确认？`,
        '敏感配置变更',
        { type: 'warning', confirmButtonText: '确认保存', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  } else {
    try {
      await ElMessageBox.confirm(`即将保存 ${list.length} 个配置项，确认？`, '保存配置', {
        type: 'info',
      })
    } catch {
      return
    }
  }
  saving.value = true
  try {
    const updates: Record<string, string> = {}
    for (const k of editedKeys.value) {
      updates[k] = edits[k]
    }
    const r: any = await settingsApi.update(updates)
    if (r.rejected && r.rejected.length > 0) {
      ElMessage.warning(`${r.applied.length} 项应用成功，${r.rejected.length} 项被拒绝：${r.rejected.map((x: any) => x.key + ' ' + x.reason).join('; ')}`)
    } else {
      const needRestart = r.applied.filter((x: any) => !x.hotReload)
      if (needRestart.length > 0) {
        ElMessageBox.alert(
          `<div style="line-height:1.7">
            已保存 <b>${r.applied.length}</b> 项配置（${r.envWritten ? '已写入 .env' : '仅内存生效'}）<br/>
            其中 <b>${needRestart.length}</b> 项需要<b style="color:#e6a23c">重启后端容器</b>才生效：<br/>
            <code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;margin-top:6px;display:inline-block">${needRestart.map((x: any) => x.key).join(', ')}</code><br/><br/>
            <code style="background:#f5f5f5;padding:4px 8px;border-radius:4px">docker restart shuzhi-backend</code>
          </div>`,
          '保存成功',
          { dangerouslyUseHTMLString: true, confirmButtonText: '我知道了' }
        )
      } else {
        ElMessage.success(`已保存 ${r.applied.length} 项配置（已热加载，立即生效）`)
      }
    }
    // 清空编辑态
    for (const k of editedKeys.value) {
      clearDirty(k)
      editing.delete(k)
      // edits[key] 不删，保留 displayValue 作为下次 v-model 兜底
    }
    await load()
  } catch (e: any) {
    ElMessage.error('保存失败：' + (e?.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

// 触点 #52：导出 / 导入 / 检查更新
async function doExport() {
  exportLoading.value = true
  try {
    const r: any = await settingsApi.exportSettings()
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19)
    a.download = `shuzhi-settings_${stamp}.json`
    a.href = URL.createObjectURL(blob)
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success(`配置已导出（${r.safeItems.length} 个非敏感项 + ${r.sensitiveKeys.length} 个敏感项标记）`)
  } catch (e: any) {
    ElMessage.error('导出失败：' + (e?.message || '未知错误'))
  } finally {
    exportLoading.value = false
  }
}

function openImportDialog() {
  importPayloadText.value = ''
  importDialogVisible.value = true
}

function pickImportFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'application/json,.json'
  input.onchange = async (e: any) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    importPayloadText.value = text
  }
  input.click()
}

async function doImport() {
  if (!importPayloadText.value.trim()) {
    ElMessage.warning('请粘贴或上传配置 JSON')
    return
  }
  let payload: any
  try {
    payload = JSON.parse(importPayloadText.value)
  } catch (e: any) {
    ElMessage.error('JSON 解析失败：' + e.message)
    return
  }
  try {
    await ElMessageBox.confirm(
      '导入将覆盖当前非敏感配置（敏感字段不会导入）。确认？',
      '导入配置',
      { type: 'warning' },
    )
  } catch { return }
  importLoading.value = true
  try {
    const r: any = await settingsApi.importSettings(payload)
    if (r.rejected && r.rejected.length > 0) {
      ElMessage.warning(`应用 ${r.applied.length} 项，拒绝 ${r.rejected.length} 项`)
    } else {
      ElMessage.success(`已导入 ${r.applied.length} 项配置`)
    }
    importDialogVisible.value = false
    await load()
  } catch (e: any) {
    ElMessage.error('导入失败：' + (e?.message || '未知错误'))
  } finally {
    importLoading.value = false
  }
}

async function checkUpdate() {
  updateLoading.value = true
  try {
    updateInfo.value = await settingsApi.checkUpdate()
    updateDialogVisible.value = true
  } catch (e: any) {
    ElMessage.error('检查更新失败：' + (e?.message || '未知错误'))
  } finally {
    updateLoading.value = false
  }
}

async function testConn(target: string) {
  testing.value = target
  try {
    const r: any = await settingsApi.testConnection(target as any)
    const status = r.status
    const tag = status === 'reachable' || status === 'mock' ? 'success' : status === 'degraded' ? 'warning' : 'error'
    const message = {
      reachable: `${target} 可达`,
      mock: `${target} 处于 Mock 模式`,
      degraded: `${target} 响应异常，已自动回退`,
      down: `${target} 不可达：${r.error || ''}`,
    }[status] || `${target} 状态：${status}`
    ElMessage({ type: tag as any, message, duration: 4000 })
  } catch (e: any) {
    ElMessage.error('测试失败：' + (e?.message || '未知错误'))
  } finally {
    testing.value = null
  }
}

function openEnvFile() {
  if (!envFilePath.value) {
    ElMessage.warning('未找到 .env 文件路径')
    return
  }
  ElMessage.info(`配置文件：${envFilePath.value}\n（直接编辑也可，建议先用本页 UI）`)
}

onMounted(load)
</script>

<template>
  <div class="settings-page">
    <!-- 顶部信息条 -->
    <header class="ss-header">
      <div class="ss-header__left">
        <h2 class="ss-header__title">系统设置</h2>
        <span class="ss-header__sub">· {{ totalItems }} 项配置 · {{ activeGroup || '请选择分组' }}</span>
      </div>
      <div class="ss-header__right">
        <span :class="['ss-env-chip', runtimeEnv]">{{ runtimeEnv }}</span>
        <span class="ss-stat-mini"><span class="ss-stat-mini__lbl">版本</span>v{{ version }}</span>
        <span class="ss-stat-mini" v-if="envFilePath" @click="openEnvFile" style="cursor:pointer">
          <span class="ss-stat-mini__lbl">.env</span>{{ envFilePath.split('/').pop() }}
        </span>
        <span class="ss-stat-mini ss-stat-mini--warn" v-if="editedItems.length > 0">
          <span class="ss-stat-mini__lbl">待保存</span>{{ editedItems.length }} 项
        </span>
      </div>
    </header>

    <div class="ss-toolbar">
      <button class="tb-btn" :class="{active: loading}" @click="load" title="重新加载"><span class="tb-icon">↻</span><span>重新加载</span></button>
      <span class="tb-sep">|</span>
      <button class="tb-btn" :class="{active: testing==='ocr'}" @click="testConn('ocr')">🔍 OCR</button>
      <button class="tb-btn" :class="{active: testing==='nuonuo'}" @click="testConn('nuonuo')">🧾 诺诺</button>
      <button class="tb-btn" :class="{active: testing==='redis'}" @click="testConn('redis')">🔴 Redis</button>
      <button class="tb-btn" :class="{active: testing==='database'}" @click="testConn('database')">🗄 数据库</button>
      <button class="tb-btn" :class="{active: testing==='storage'}" @click="testConn('storage')">🗃 对象存储</button>
      <span class="tb-sep">|</span>
      <button class="tb-btn" :class="{active: exportLoading}" @click="doExport">📦 备份</button>
      <button class="tb-btn" @click="openImportDialog">📥 导入</button>
      <button class="tb-btn" :class="{active: updateLoading}" @click="checkUpdate">🔄 检查更新</button>
      <div class="tb-spacer"></div>
      <button class="tb-btn tb-btn--primary" :class="{disabled: editedKeys.length === 0}" @click="save">
        💾 保存
        <span v-if="editedKeys.length > 0" class="tb-badge">{{ editedKeys.length }}</span>
      </button>
    </div>

    <div class="ss-body">
      <aside class="ss-nav">
        <div class="ss-nav__head">分组</div>
        <div
          v-for="g in groupList"
          :key="g"
          :class="['ss-nav__item', { active: activeGroup === g, dirty: hasGroupDirty(g) }]"
          @click="activeGroup = g"
        >
          <span class="ss-nav__icon">{{ groupIcon[g] || '•' }}</span>
          <span class="ss-nav__label">{{ g }}</span>
          <span class="ss-nav__count">{{ groups[g].length }}</span>
        </div>
        <div class="ss-nav__foot">💡 新分组：后端 <code>SETTING_METAS</code> 加 group</div>
      </aside>

      <main class="ss-main">
        <div v-if="!activeGroup" class="ss-empty">
          <div class="ss-empty__icon">👈</div>
          <div>请选择左侧分组</div>
        </div>
        <div v-else class="ss-list">
          <div class="ss-list__head">
            <div class="ss-list__title">
              <span class="ss-list__icon">{{ groupIcon[activeGroup] || '•' }}</span>
              <h3>{{ activeGroup }}</h3>
              <span class="ss-list__count">{{ groups[activeGroup].length }} 项</span>
            </div>
            <input v-model="groupFilter" class="ss-list__search" placeholder="🔍 搜索配置项..." />
          </div>

          <div class="ss-list__body">
            <div
              v-for="item in filteredGroupItems"
              :key="item.key"
              :class="['ss-row', { 'ss-row--dirty': isEdited(item.key), 'ss-row--sensitive': item.sensitive, 'ss-row--unset': !item.isSet }]"
            >
              <div class="ss-row__l">
                <div class="ss-row__top">
                  <span class="ss-row__label">{{ item.label }}</span>
                  <span v-if="item.sensitive" class="ss-tag ss-tag--secret">密钥</span>
                  <span v-if="item.hotReload" class="ss-tag ss-tag--hot">热加载</span>
                  <span v-else-if="!item.sensitive" class="ss-tag ss-tag--restart">需重启</span>
                </div>
                <code class="ss-row__key">{{ item.key }}</code>
                <div v-if="item.help" class="ss-row__help">💡 {{ item.help }}</div>
                <div v-if="item.warning" class="ss-row__warn">⚠ {{ item.warning }}</div>
              </div>

              <div class="ss-row__r">
                <template v-if="item.sensitive && !isEditing(item.key)">
                  <div v-if="!item.isSet" class="ss-row__empty">○ 未配置</div>
                  <div v-else class="ss-row__secret">
                    <code>{{ displaySecret(item) }}</code>
                    <a class="ss-link" @click="showSecrets[item.key] = !showSecrets[item.key]">
                      {{ showSecrets[item.key] ? '🙈' : '👁' }}
                    </a>
                    <a class="ss-link ss-link--primary" @click="startEdit(item)">修改</a>
                  </div>
                </template>
                <template v-else-if="item.sensitive && isEditing(item.key)">
                  <el-input
                    v-model="edits[item.key]"
                    type="password" show-password
                    placeholder="输入新值覆盖原密钥"
                    class="ss-row__input"
                    @input="markDirty(item.key)"
                  />
                  <a class="ss-link ss-link--danger" @click="cancelEdit(item)">取消</a>
                </template>
                <template v-else>
                  <el-switch
                    v-if="item.type === 'bool'"
                    v-model="edits[item.key]"
                    :active-value="'True'" :inactive-value="'False'"
                    @change="markDirty(item.key)"
                  />
                  <el-select
                    v-else-if="item.type === 'enum' && item.options"
                    v-model="edits[item.key]"
                    :placeholder="item.displayValue || '请选择'"
                    class="ss-row__input"
                    @change="markDirty(item.key)"
                  >
                    <el-option v-for="opt in item.options" :key="opt" :label="opt" :value="opt" />
                  </el-select>
                  <el-input-number
                    v-else-if="item.type === 'int' || item.type === 'float'"
                    v-model="edits[item.key]"
                    :min="item.min" :max="item.max" :step="item.step || 1"
                    :precision="item.type === 'float' ? 2 : 0"
                    class="ss-row__input"
                    @change="markDirty(item.key)"
                  />
                  <el-input
                    v-else
                    v-model="edits[item.key]"
                    :placeholder="item.placeholder || item.displayValue || '请输入'"
                    class="ss-row__input"
                    @input="markDirty(item.key)"
                  />
                </template>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>


    <!-- 触点 #49：生产部署清单（只读，告诉运维上线要做什么） -->
    <div class="deploy-checklist">
      <div class="dc-head">
        <h3>🚀 生产部署清单</h3>
        <span class="dc-sub">上线前逐项确认 · 仅展示，不可编辑</span>
      </div>

      <div class="dc-grid">
        <!-- 1. 域名/证书 -->
        <div class="dc-card">
          <div class="dc-num">1</div>
          <div class="dc-body">
            <div class="dc-title">域名 + HTTPS 证书</div>
            <ul class="dc-list">
              <li>配置生产域名，<code>A</code> 记录到服务器公网 IP</li>
              <li>申请 <code>Let's Encrypt</code> 免费证书 或购买商业证书</li>
              <li>Nginx 反向代理：<code>listen 443 ssl</code> + 证书路径</li>
              <li>HTTP → HTTPS 301 跳转，避免明文传输敏感数据</li>
            </ul>
          </div>
        </div>

        <!-- 2. 密钥/连接串 -->
        <div class="dc-card">
          <div class="dc-num">2</div>
          <div class="dc-body">
            <div class="dc-title">密钥 + 连接串</div>
            <ul class="dc-list">
              <li>左侧分组「JWT 安全」→ 重置 <code>JWT_SECRET_KEY</code>（强随机 64 字符以上）</li>
              <li>「数据库」→ 使用强密码的 PostgreSQL 连接串</li>
              <li>「Redis」→ 设置密码 <code>requirepass</code></li>
              <li>所有密钥通过左侧表单写入 <code>backend/.env</code>，<b>禁止</b>提交到 Git</li>
            </ul>
          </div>
        </div>

        <!-- 3. 诺诺发票云 -->
        <div class="dc-card">
          <div class="dc-num">3</div>
          <div class="dc-body">
            <div class="dc-title">诺诺发票云（生产凭证）</div>
            <ul class="dc-list">
              <li>企业资质：营业执照 + 银行账户（个人无法签约）</li>
              <li>登录 <a href="https://open.nuonuocs.cn" target="_blank">open.nuonuocs.cn</a> 申请 AppKey/Secret/Token</li>
              <li>左侧「诺诺发票云」分组填入真实凭证，<code>NUONUO_MODE=real</code></li>
              <li><code>NUONUO_USE_SANDBOX=False</code>，<code>NUONUO_API_URL=https://sdk.nuonu.com/open/v1/services</code></li>
              <li>每日配额 5000 次/组，按需申请多组</li>
            </ul>
          </div>
        </div>

        <!-- 4. 对象存储 -->
        <div class="dc-card">
          <div class="dc-num">4</div>
          <div class="dc-body">
            <div class="dc-title">对象存储（MinIO / 阿里云 OSS）</div>
            <ul class="dc-list">
              <li>本项目 <code>shuzhi-minio</code> 容器为开发用，生产替换为 OSS/S3</li>
              <li>左侧「对象存储」分组：填入 <code>endpoint/access_key/secret/bucket</code></li>
              <li>Bucket 启用版本控制 + 跨区域复制（灾备）</li>
              <li>PDF/图片访问走 CDN，避免直接暴露对象存储地址</li>
            </ul>
          </div>
        </div>

        <!-- 5. 备份/监控 -->
        <div class="dc-card">
          <div class="dc-num">5</div>
          <div class="dc-body">
            <div class="dc-title">备份 + 监控</div>
            <ul class="dc-list">
              <li>PostgreSQL：<code>pg_dump</code> 每日凌晨 3 点全量 + binlog 增量</li>
              <li>MinIO/OSS：启用跨区域复制，保留 ≥ 90 天</li>
              <li>Prometheus + Grafana 已内置，对接告警（飞书/钉钉/邮件）</li>
              <li>配置关键指标阈值：API 错误率 &gt; 1% 告警、容器重启 &gt; 3次/小时 告警</li>
            </ul>
          </div>
        </div>

        <!-- 6. 安全 -->
        <div class="dc-card">
          <div class="dc-num">6</div>
          <div class="dc-body">
            <div class="dc-title">安全加固</div>
            <ul class="dc-list">
              <li>关闭 <code>DEBUG=True</code>，避免泄露堆栈</li>
              <li>CORS 白名单：只允许生产域名（左侧「CORS」分组）</li>
              <li>登录失败 5 次锁 15 分钟（已内置），生产再加 IP 维度</li>
              <li>审计日志保留 ≥ 1 年，合规要求</li>
            </ul>
          </div>
        </div>

        <!-- 7. 系统更新 SOP（触点 #52）-->
        <div class="dc-card dc-card-wide">
          <div class="dc-num">7</div>
          <div class="dc-body">
            <div class="dc-title">系统更新 SOP</div>
            <p style="font-size: 12px; color: #94A3B8; margin: 0 0 8px;">
              <strong>核心原则：</strong>本项目不提供前端"一键更新"按钮。涉及 <code>git pull</code> + <code>docker compose pull</code> + 容器重启，会短暂中断服务，必须在服务器终端手动执行。
            </p>
            <ul class="dc-list">
              <li><strong>① 检查新版本</strong>：在本页右上角点「🔄 检查更新」，会调 GitHub API 对比最新 release</li>
              <li><strong>② 备份配置</strong>：点「📦 备份配置」导出当前 JSON（含非敏感项 + 敏感项标记），便于回滚</li>
              <li><strong>③ 备份数据库</strong>：<code>docker exec shuzhi-postgres pg_dump -U shuzhi shuzhi &gt; backup_$(date +%F).sql</code></li>
              <li><strong>④ 看 Release Notes</strong>：重点关注「⚠ Breaking Changes」「数据库迁移」「依赖升级」，按需调整 <code>.env</code></li>
              <li><strong>⑤ 拉取新代码</strong>（在项目根）：<code>git pull origin main</code></li>
              <li><strong>⑥ 拉取新镜像</strong>：<code>docker compose pull backend frontend</code>（不要 pull 所有，只拉改动的）</li>
              <li><strong>⑦ 数据库迁移</strong>：<code>docker compose run --rm backend alembic upgrade head</code>（如有 alembic 配置）</li>
              <li><strong>⑧ 重启服务</strong>：<code>docker compose up -d backend frontend</code>（先 backend 再 frontend，灰度）</li>
              <li><strong>⑨ 验证</strong>：访问首页 → 登录 → 跑 1 个核心流程（如新建发票）→ 看日志 <code>docker logs -f shuzhi-backend</code></li>
              <li><strong>⑩ 失败回滚</strong>：<code>git checkout HEAD~1</code> + <code>docker compose up -d --force-recreate backend frontend</code> + 恢复数据库备份</li>
            </ul>
            <p style="font-size: 11.5px; color: #B45309; margin: 8px 0 0;">
              ⚠ 升级窗口期建议：低峰时段（如凌晨 2-4 点）、先在测试环境演练、提前通知用户。蓝绿发布/灰度发布需要双套环境 + 负载均衡，本项目暂未支持。
            </p>
          </div>
        </div>
      </div>

      <div class="dc-foot">
        💡 上线后第一周建议每日检查「审计日志」+ 监控告警；遇到问题查 <code>backend/logs/</code>。
      </div>
    </div>

    <!-- 触点 #52：导入配置弹窗 -->
    <el-dialog v-model="importDialogVisible" title="📥 导入配置" width="640px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" style="margin-bottom: 12px">
        <p style="margin: 0; line-height: 1.6; font-size: 12.5px;">
          导入将覆盖当前<strong>非敏感</strong>配置（数据库密码、Token、密钥等敏感字段<strong>不会</strong>被导入，需在目标环境手动配置）。
        </p>
      </el-alert>
      <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 12.5px; color: #475569;">上传 JSON 文件：</span>
        <el-button size="small" @click="pickImportFile">📁 选择文件</el-button>
        <span style="font-size: 11px; color: #94A3B8;">（或直接粘贴到下方文本框）</span>
      </div>
      <el-input
        v-model="importPayloadText"
        type="textarea"
        :rows="14"
        placeholder='把导出的 JSON 粘到这里，或点击"选择文件"上传'
        style="font-family: monospace; font-size: 12px;"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importLoading" @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 触点 #52：检查更新弹窗 -->
    <el-dialog v-model="updateDialogVisible" title="🔄 系统更新检查" width="560px" :close-on-click-modal="false">
      <div v-if="updateInfo" class="update-dialog">
        <div class="ud-row">
          <span class="ud-lbl">当前版本：</span>
          <code class="ud-val">{{ updateInfo.currentVersion || 'unknown' }}</code>
        </div>
        <div class="ud-row">
          <span class="ud-lbl">最新版本：</span>
          <code class="ud-val">{{ updateInfo.latestVersion || '—' }}</code>
        </div>
        <div v-if="updateInfo.error" class="ud-error">⚠ {{ updateInfo.error }}</div>
        <el-alert v-else-if="updateInfo.hasUpdate" type="success" :closable="false" style="margin: 12px 0">
          ✅ 有新版本可用，详见下方更新说明
        </el-alert>
        <el-alert v-else type="info" :closable="false" style="margin: 12px 0">
          已是最新版本
        </el-alert>
        <div v-if="updateInfo.publishedAt" class="ud-row">
          <span class="ud-lbl">发布时间：</span>
          <span class="ud-val">{{ updateInfo.publishedAt }}</span>
        </div>
        <div v-if="updateInfo.assetSizeMB !== undefined" class="ud-row">
          <span class="ud-lbl">资源大小：</span>
          <span class="ud-val">{{ updateInfo.assetSizeMB }} MB</span>
        </div>
        <div v-if="updateInfo.releaseNotes" class="ud-notes">
          <div class="ud-lbl">Release Notes：</div>
          <pre class="ud-pre">{{ updateInfo.releaseNotes }}</pre>
        </div>
        <el-alert v-if="updateInfo.releaseUrl" type="info" :closable="false" style="margin-top: 12px">
          <p style="margin: 0; line-height: 1.6; font-size: 12.5px;">
            ⚠ <strong>请勿直接在前端点"更新"</strong>。系统更新会涉及 git pull + docker compose pull + 容器重启，会中断服务。<br>
            请在 <strong>服务器终端</strong> 按 <a :href="updateInfo.releaseUrl" target="_blank" style="color: #4F6BFF">发布说明</a> 的步骤手动执行。
          </p>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="updateDialogVisible = false">关闭</el-button>
        <el-button v-if="updateInfo && updateInfo.releaseUrl" type="primary" @click="window.open(updateInfo.releaseUrl, '_blank')">查看发布页</el-button>
      </template>
    </el-dialog>

    <!-- 待保存修改浮层 -->
    <transition name="el-fade-in">
      <div v-if="editedItems.length > 0" class="pending-bar">
        <div class="pending-info">
          <span class="pending-count">{{ editedItems.length }}</span>
          项配置已修改
          <span v-if="editedItems.filter(i=>i.sensitive).length > 0" class="pending-sensitive">
            （含 {{ editedItems.filter(i=>i.sensitive).length }} 项敏感字段）
          </span>
        </div>
        <div class="pending-actions">
          <el-button size="small" @click="clearAllEdits">清空</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="save">确认保存</el-button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style lang="scss" scoped>
@import "@/assets/styles/variables.scss";

$ss-bg-page:    #FAFAFA;
$ss-bg-card:    #FFFFFF;
$ss-bg-muted:   #F4F4F5;
$ss-bg-soft:    #F9FAFB;
$ss-border:     #E4E4E7;
$ss-border-2:   #D4D4D8;
$ss-text:       #18181B;
$ss-text-2:     #52525B;
$ss-text-3:     #A1A1AA;
$ss-primary:    #4F46E5;
$ss-primary-2:  #4338CA;
$ss-primary-bg: #EEF2FF;
$ss-warning:    #D97706;
$ss-warning-bg: #FEF3C7;
$ss-danger:     #DC2626;
$ss-danger-bg:  #FEE2E2;
$ss-success:    #059669;
$ss-radius:     8px;
$ss-radius-sm:  6px;

.settings-page { padding: 16px 20px 24px; min-height: calc(100vh - 100px); background: $ss-bg-page; }

/* 极简顶栏 */
.ss-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 18px; background: #FFFFFF; border: 1px solid $ss-border;
  border-radius: $ss-radius; margin-bottom: 8px;
}
.ss-header__left { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.ss-header__title { margin: 0; font-size: 17px; font-weight: 600; color: $ss-text; }
.ss-header__sub { font-size: 12px; color: $ss-text-3; }
.ss-header__right { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.ss-env-chip {
  font-size: 10.5px; font-weight: 600; padding: 2px 7px; border-radius: 4px;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.ss-env-chip.development { background: $ss-warning-bg; color: $ss-warning; }
.ss-env-chip.production  { background: $ss-danger-bg; color: $ss-danger; }
.ss-env-chip.staging     { background: $ss-primary-bg; color: $ss-primary; }
.ss-stat-mini {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11.5px; color: $ss-text-2; padding: 2px 8px;
  background: $ss-bg-muted; border-radius: 4px;
}
.ss-stat-mini__lbl { color: $ss-text-3; font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.5px; }
.ss-stat-mini--warn { background: $ss-warning-bg; color: $ss-warning; }

/* 工具条 */
.ss-toolbar {
  display: flex; align-items: center; gap: 3px; flex-wrap: wrap;
  background: #FFFFFF; border: 1px solid $ss-border;
  border-radius: $ss-radius; padding: 5px 10px; margin-bottom: 8px;
}
.tb-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; font-size: 12.5px; color: $ss-text-2;
  background: transparent; border: 1px solid transparent; border-radius: $ss-radius-sm;
  cursor: pointer; transition: all 0.12s; font-family: inherit; white-space: nowrap;
}
.tb-btn:hover { background: $ss-bg-muted; color: $ss-text; }
.tb-btn.active { background: $ss-primary-bg; color: $ss-primary-2; }
.tb-btn--primary { background: $ss-primary; color: #FFFFFF; padding: 4px 14px; font-weight: 500; }
.tb-btn--primary:hover:not(.disabled) { background: $ss-primary-2; }
.tb-btn--primary.disabled { opacity: 0.4; cursor: not-allowed; }
.tb-icon { font-size: 14px; }
.tb-sep { color: $ss-border-2; margin: 0 2px; }
.tb-spacer { flex: 1; }
.tb-badge {
  display: inline-block; margin-left: 6px; padding: 1px 6px;
  background: rgba(255,255,255,0.25); color: #FFFFFF; border-radius: 8px;
  font-size: 10.5px; font-weight: 600;
}

/* Body */
.ss-body { display: flex; gap: 8px; align-items: flex-start; }

/* 左侧 nav */
.ss-nav {
  flex: 0 0 200px;
  background: #FFFFFF; border: 1px solid $ss-border;
  border-radius: $ss-radius; padding: 6px;
  position: sticky; top: 16px; max-height: calc(100vh - 120px); overflow-y: auto;
}
.ss-nav__head {
  font-size: 10px; color: $ss-text-3; text-transform: uppercase;
  letter-spacing: 0.5px; padding: 6px 8px; font-weight: 600;
}
.ss-nav__item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: $ss-radius-sm; cursor: pointer;
  font-size: 12.5px; color: $ss-text-2; transition: background 0.1s; margin-bottom: 1px;
}
.ss-nav__item:hover { background: $ss-bg-muted; color: $ss-text; }
.ss-nav__item.active { background: $ss-primary-bg; color: $ss-primary-2; font-weight: 600; }
.ss-nav__item.dirty .ss-nav__count { background: $ss-warning; color: #FFFFFF; }
.ss-nav__icon { font-size: 13px; width: 16px; text-align: center; flex-shrink: 0; }
.ss-nav__label { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ss-nav__count {
  background: $ss-bg-muted; color: $ss-text-2;
  padding: 0 6px; border-radius: 8px; font-size: 10px; font-weight: 600;
  min-width: 20px; text-align: center; line-height: 16px;
}
.ss-nav__item.active .ss-nav__count { background: $ss-primary; color: #FFFFFF; }
.ss-nav__foot {
  margin-top: 6px; padding: 6px 8px; background: $ss-bg-muted;
  border-radius: $ss-radius-sm; font-size: 11px; color: $ss-text-2; line-height: 1.5;
}
.ss-nav__foot code { background: #FFFFFF; padding: 1px 3px; border-radius: 3px; font-size: 10px; color: $ss-text; }

/* 主区 */
.ss-main { flex: 1 1 0; min-width: 0; }
.ss-empty {
  background: #FFFFFF; border: 1px dashed $ss-border-2;
  border-radius: $ss-radius; padding: 100px 20px;
  text-align: center; color: $ss-text-3; font-size: 14px;
}
.ss-empty__icon { font-size: 40px; margin-bottom: 8px; opacity: 0.4; }

/* 配置项列表 */
.ss-list {
  background: #FFFFFF; border: 1px solid $ss-border;
  border-radius: $ss-radius; overflow: hidden;
}
.ss-list__head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; border-bottom: 1px solid $ss-border; background: $ss-bg-soft;
}
.ss-list__title { display: flex; align-items: center; gap: 8px; }
.ss-list__icon { font-size: 14px; }
.ss-list__title h3 { margin: 0; font-size: 13.5px; font-weight: 600; color: $ss-text; }
.ss-list__count {
  font-size: 10.5px; color: $ss-text-3;
  padding: 1px 6px; background: $ss-bg-muted; border-radius: 8px; font-weight: 500;
}
.ss-list__search {
  border: 1px solid $ss-border; background: #FFFFFF;
  padding: 4px 10px; font-size: 12px; border-radius: $ss-radius-sm;
  width: 220px; color: $ss-text; outline: none; font-family: inherit;
}
.ss-list__search:focus { border-color: $ss-primary; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08); }
.ss-list__body { padding: 0; }

/* 单条配置项（行式布局）*/
.ss-row {
  display: flex; gap: 16px; padding: 12px 16px;
  border-bottom: 1px solid $ss-border; transition: background 0.1s;
  align-items: flex-start;
}
.ss-row:last-child { border-bottom: none; }
.ss-row:hover { background: $ss-bg-soft; }
.ss-row--dirty { background: #FFFBEB; }
.ss-row--dirty:hover { background: #FEF3C7; }
.ss-row--sensitive { border-left: 3px solid $ss-danger; padding-left: 13px; }
.ss-row--unset .ss-row__label { color: $ss-text-3; }
.ss-row__l { flex: 1 1 0; min-width: 0; }
.ss-row__top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ss-row__label { font-size: 13.5px; font-weight: 600; color: $ss-text; }
.ss-row__key {
  display: inline-block; margin-top: 2px;
  font-size: 10.5px; color: $ss-text-3; font-family: $font-family-mono;
}
.ss-row__help { margin-top: 4px; font-size: 11.5px; color: $ss-text-2; line-height: 1.5; }
.ss-row__help code { background: $ss-bg-muted; padding: 1px 4px; border-radius: 3px; font-size: 10.5px; color: $ss-text; }
.ss-row__warn {
  margin-top: 4px; font-size: 11.5px; color: $ss-warning;
  background: $ss-warning-bg; padding: 4px 8px; border-radius: $ss-radius-sm; display: inline-block;
}
.ss-row__r { flex: 0 0 360px; display: flex; align-items: center; gap: 8px; min-width: 0; }
.ss-row__input { flex: 1; min-width: 0; }
.ss-row__input.el-select,
.ss-row__input.el-input-number { width: 100%; }
.ss-row__empty { font-size: 12px; color: $ss-text-3; font-style: italic; }
.ss-row__secret {
  flex: 1; display: flex; align-items: center; gap: 8px;
  background: $ss-bg-muted; padding: 4px 10px; border-radius: $ss-radius-sm; min-width: 0;
}
.ss-row__secret code {
  flex: 1; font-family: $font-family-mono; font-size: 11.5px;
  color: $ss-text; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ss-link { color: $ss-primary !important; font-size: 11.5px; cursor: pointer; user-select: none; }
.ss-link:hover { text-decoration: underline; }
.ss-link--primary { color: $ss-primary !important; font-weight: 500; }
.ss-link--danger { color: $ss-danger !important; }

/* Tags */
.ss-tag { display: inline-block; padding: 0 5px; font-size: 9.5px; border-radius: 3px; font-weight: 500; line-height: 15px; }
.ss-tag--secret   { background: $ss-danger-bg; color: $ss-danger; }
.ss-tag--hot      { background: #D1FAE5; color: $ss-success; }
.ss-tag--restart  { background: $ss-warning-bg; color: $ss-warning; }

/* Dialog */
.update-dialog { padding: 4px 0; }
.ud-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; font-size: 13px; }
.ud-lbl { color: $ss-text-2; min-width: 80px; }
.ud-val { color: $ss-text; font-family: $font-family-mono; }
.ud-error { color: $ss-warning; padding: 8px 0; }
.ud-notes { margin-top: 12px; }
.ud-pre {
  background: $ss-bg-muted; padding: 12px; border-radius: $ss-radius-sm;
  font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap;
  font-family: $font-family-mono; line-height: 1.5;
}

/* Pending bar */
.pending-bar {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #FFFFFF; border: 1px solid $ss-border;
  border-radius: $ss-radius; padding: 10px 20px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.1), 0 4px 10px rgba(0,0,0,0.05);
  display: flex; align-items: center; gap: 16px; z-index: 100;
}
.pending-info { font-size: 13px; color: $ss-text; }
.pending-count {
  display: inline-block; background: $ss-warning; color: #FFFFFF;
  padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-right: 4px;
}
.pending-sensitive { color: $ss-text-2; font-size: 12px; margin-left: 4px; }
.pending-actions { display: flex; gap: 8px; }

/* Deploy checklist */
.deploy-checklist { margin-top: 16px; }
.deploy-checklist .dc-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; padding: 0 2px; }
.deploy-checklist h3 { margin: 0; font-size: 14px; font-weight: 600; color: $ss-text; }
.deploy-checklist .dc-sub { font-size: 12px; color: $ss-text-3; }
.deploy-checklist .dc-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.deploy-checklist .dc-card {
  background: #FFFFFF; border: 1px solid $ss-border;
  border-left: 3px solid $ss-primary; border-radius: $ss-radius;
  padding: 10px 14px; display: flex; gap: 10px;
}
.deploy-checklist .dc-num {
  width: 22px; height: 22px; flex-shrink: 0;
  background: $ss-primary; color: #FFFFFF; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; align-self: flex-start;
}
.deploy-checklist .dc-body { flex: 1; min-width: 0; }
.deploy-checklist .dc-title { font-size: 12.5px; font-weight: 600; color: $ss-text; margin-bottom: 3px; }
.deploy-checklist .dc-list { margin: 0; padding-left: 14px; font-size: 11.5px; color: $ss-text-2; line-height: 1.6; }
.deploy-checklist .dc-list code { background: $ss-bg-muted; padding: 1px 3px; border-radius: 3px; font-size: 10.5px; color: $ss-text; }
.deploy-checklist .dc-list a { color: $ss-primary; text-decoration: none; }
.deploy-checklist .dc-list a:hover { text-decoration: underline; }
.deploy-checklist .dc-card-wide { grid-column: 1 / -1; }
.deploy-checklist .dc-foot {
  margin-top: 10px; padding: 8px 14px; background: $ss-bg-muted;
  border-radius: $ss-radius-sm; font-size: 11.5px; color: $ss-text-2;
}
.deploy-checklist .dc-foot code { background: #FFFFFF; padding: 1px 4px; border-radius: 3px; font-size: 10.5px; }

/* Responsive */
@media (max-width: 1100px) {
  .ss-body { flex-direction: column; }
  .ss-nav { position: static; max-height: none; flex: 0 0 auto; }
  .ss-row__r { flex: 0 0 280px; }
}
@media (max-width: 768px) {
  .ss-row { flex-direction: column; }
  .ss-row__r { flex: 0 0 auto; width: 100%; }
  .deploy-checklist .dc-grid { grid-template-columns: 1fr; }
}
</style>
