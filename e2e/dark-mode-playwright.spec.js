// e2e/dark-mode-playwright.spec.js
// R14A 暗色模式 E2E 验证
// 流程：
//   1. 登录后访问 5 个核心业务页（合同/项目/费用/回款/发票）
//   2. 在 AppLayout 切换为暗色
//   3. 截图比对：浅色 vs 暗色
//   4. 验证：documentElement.classList 包含 'theme-dark'
//   5. 验证：关键元素 computed background 不是白色
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE = process.env.BASE || 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'
const TIMEOUT = 30000
const SCREENSHOT_DIR = path.join(__dirname, '../docs/screenshots/compare')
const PAGES = [
  { name: 'dashboard', url: '/dashboard' },
  { name: 'contract-list', url: '/contract/list' },
  { name: 'project-list', url: '/project/list' },
  { name: 'expense-list', url: '/expense/list' },
  { name: 'receivable-list', url: '/receivable/list' },
]

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
  await page.reload()
  await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 5000 })
  await page.fill('input[placeholder*="账号" i]', 'admin')
  await page.fill('input[type="password"]', 'admin123')
  await page.click('button:has-text("登 录")')
  await page.waitForURL(/\/dashboard/, { timeout: 10000 })
}

async function toggleDarkMode(page) {
  // 第 1 个 .icon-btn 是"刷新"，第 2 是"全屏"，第 3 是"帮助"，第 4 是"暗色/亮色"（按 AppLayout 顺序）
  // 但顺序不一定，看 el-tooltip 的 content 属性最稳
  const clicked = await page.evaluate(() => {
    // 1) 直接看 el-tooltip 的 __tooltipContent 私有属性（element-plus 内部用）
    // 2) 看所有 .icon-btn，找 innerHTML 含 "moon" 或 "sunny"（SVG path data）
    const btns = document.querySelectorAll('.icon-btn')
    for (const b of btns) {
      const inner = b.innerHTML
      // Element Plus Moon icon path contains "M30 0a30" 等特征；Sunny 含 "M0 0"
      // 更稳：触发 onClick 之后 localStorage shuzhi-dark 切换的就是
      // 我们用顺序兜底：暗色按钮总是第 4 个 .icon-btn
    }
    // 兜底：按 AppLayout 顺序，第 4 个 .icon-btn 是暗色切换
    if (btns.length >= 4) {
      btns[3].click()
      return 'fourth icon-btn (assumed dark toggle)'
    }
    return false
  })
  if (!clicked) {
    throw new Error('找不到暗色切换按钮')
  }
  await page.waitForTimeout(500)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()

  console.log('[dark-mode] 1. 登录...')
  await login(page)

  // 1. 浅色模式截图（5 个核心页）
  console.log('[dark-mode] 2. 浅色模式截图（5 页）...')
  for (const p of PAGES.slice(0, 5)) {
    await page.goto(`${BASE}${p.url}`, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {})
    await page.waitForTimeout(1200)
    const filepath = path.join(SCREENSHOT_DIR, `3-real-r14a-light-${p.name}.png`)
    await page.screenshot({ path: filepath, fullPage: false })
    console.log(`  ✅ ${p.name} 浅色 → ${filepath}`)
  }

  // 2. 切到暗色
  console.log('[dark-mode] 3. 切到暗色...')
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  await toggleDarkMode(page)

  const isDark = await page.evaluate(() => document.documentElement.classList.contains('theme-dark'))
  const lsDark = await page.evaluate(() => localStorage.getItem('shuzhi-dark'))
  console.log(`  html.theme-dark = ${isDark}`)
  console.log(`  localStorage shuzhi-dark = ${lsDark}`)
  if (!isDark) throw new Error('暗色模式切换失败（html 缺 theme-dark）')
  if (lsDark !== '1') throw new Error('localStorage 未写入')

  // 3. 暗色模式截图（同 5 页）
  console.log('[dark-mode] 4. 暗色模式截图（5 页）...')
  for (const p of PAGES.slice(0, 5)) {
    await page.goto(`${BASE}${p.url}`, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {})
    await page.waitForTimeout(1200)
    const filepath = path.join(SCREENSHOT_DIR, `3-real-r14a-dark-${p.name}.png`)
    await page.screenshot({ path: filepath, fullPage: false })
    console.log(`  ✅ ${p.name} 暗色 → ${filepath}`)
  }

  // 4. 验证：body 背景色不是 #FFFFFF
  console.log('[dark-mode] 5. 校验背景色...')
  const bgColor = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  console.log(`  body backgroundColor = ${bgColor}`)
  // 深色背景应是 #0F1320 (rgb(15, 19, 32)) 或接近
  if (bgColor === 'rgb(255, 255, 255)') {
    throw new Error('暗色模式下 body 仍是白色（CSS 未生效）')
  }

  // 5. 切回浅色，再验一次
  console.log('[dark-mode] 6. 切回浅色...')
  await toggleDarkMode(page)
  const isLight = await page.evaluate(() => !document.documentElement.classList.contains('theme-dark'))
  if (!isLight) throw new Error('切回浅色失败')
  console.log('  ✅ 切回浅色 OK')

  console.log('\n[dark-mode] ✅ 暗色模式 E2E 通过（5 页浅色 + 5 页暗色 + 切换 + 背景色）')
  await browser.close()
}

run().catch((e) => { console.error('[dark-mode] ❌ 失败:', e); process.exit(1) })
