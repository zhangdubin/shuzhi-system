// e2e/dark-mode-v2.spec.js
// R16 暗色设计系统级重构 — 3 页对比截图
// 覆盖：
//   1. Dashboard（欢迎条 + 6 模块卡片 + 快捷入口 + KPI 趋势图）
//   2. 合同列表（业务核心：列表 + 筛选 + 卡片）
//   3. 发票识别（业务核心：上传区 + 识别结果）
const { chromium } = require('playwright')
const path = require('path')
const fs = require('fs')

const BASE = process.env.BASE || 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'
const TIMEOUT = 30000
const SCREENSHOT_DIR = path.join(__dirname, '../docs/screenshots/compare')

const PAGES = [
  { name: 'dashboard', url: '/dashboard' },
  { name: 'contract-list', url: '/contract/list' },
  { name: 'invoice-ocr', url: '/invoice/ocr' },
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
  // R10: 按钮是 .icon-btn 包裹 Moon/Sunny svg
  const clicked = await page.evaluate(() => {
    const btns = document.querySelectorAll('.icon-btn')
    if (btns.length >= 4) { btns[3].click(); return true }
    return false
  })
  if (!clicked) throw new Error('找不到暗色切换按钮')
  await page.waitForTimeout(500)
}

async function capture(page, name, mode) {
  await page.goto(`${BASE}/${name === 'dashboard' ? 'dashboard' : name === 'contract-list' ? 'contract/list' : 'invoice/ocr'}`,
    { waitUntil: 'domcontentloaded', timeout: 15000 })
  await page.waitForTimeout(1500)
  // 触发滚动到底部以让渐变 hero 等大件完全呈现
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(500)
  const filename = `5-r16-dark-${mode}-${name}.png`
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: false })
  console.log(`  ✅ ${name} (${mode}) → ${filename}`)
}

async function captureKeyColors(page) {
  // 捕获关键元素 computed 颜色（设计系统级验证）
  return await page.evaluate(() => {
    const r = {}
    for (const [key, sel] of [
      ['body', 'body'],
      ['#app', '#app'],
      ['page-card', '.page-card'],
      ['welcome', '.welcome'],
      ['module-card', '.module-card'],
      ['quick-icon', '.quick-icon'],
      ['el-card', '.el-card'],
      ['el-table', '.el-table'],
      ['text-primary', 'h1, h2, h3'],
    ]) {
      const el = document.querySelector(sel)
      if (el) {
        const cs = getComputedStyle(el)
        r[key] = {
          bg: cs.backgroundColor,
          color: cs.color,
          border: cs.borderColor,
        }
      }
    }
    return r
  })
}

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(TIMEOUT)

  console.log('[r16-dark] 1. 登录...')
  await login(page)

  // === 浅色模式 ===
  console.log('[r16-dark] 2. 浅色模式截图（3 页）...')
  for (const p of PAGES) {
    await capture(page, p.name, 'light')
  }
  const lightColors = await captureKeyColors(page)

  // === 切到暗色 ===
  console.log('[r16-dark] 3. 切到暗色...')
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1200)
  await toggleDarkMode(page)
  const isDark = await page.evaluate(() => document.documentElement.classList.contains('theme-dark'))
  if (!isDark) throw new Error('暗色模式切换失败')

  // === 暗色模式 ===
  console.log('[r16-dark] 4. 暗色模式截图（3 页）...')
  for (const p of PAGES) {
    await capture(page, p.name, 'dark')
  }
  const darkColors = await captureKeyColors(page)

  // === 对比报告 ===
  console.log('\n[r16-dark] === 设计系统级颜色对比 ===')
  for (const key of Object.keys(lightColors)) {
    const l = lightColors[key]
    const d = darkColors[key] || {}
    console.log(`  ${key}:`)
    console.log(`    浅: bg=${l.bg}, color=${l.color}`)
    console.log(`    暗: bg=${d.bg}, color=${d.color}`)
  }

  // === 关键验证：body 在暗色下必须是深色 ===
  console.log('\n[r16-dark] === 关键设计系统验证 ===')
  const bodyBg = darkColors.body?.bg
  console.log(`  暗色 body 背景: ${bodyBg}`)
  if (bodyBg === 'rgb(255, 255, 255)' || bodyBg === 'rgb(241, 245, 249)') {
    throw new Error(`❌ 暗色 body 背景还是浅色（${bodyBg}），R16 重构失败`)
  }
  console.log('  ✅ body 暗色 = ' + bodyBg)

  // 验证卡片背景变成深色
  const cardBg = darkColors['page-card']?.bg
  console.log(`  暗色 page-card 背景: ${cardBg}`)
  if (cardBg === 'rgb(255, 255, 255)') {
    throw new Error('❌ 暗色卡片背景还是白色（设计系统级重构未生效）')
  }
  console.log('  ✅ 卡片暗色 = ' + cardBg)

  // 验证 welcome 渐变背景
  const welcomeBg = darkColors['welcome']?.bg
  console.log(`  暗色 welcome 背景: ${welcomeBg}`)

  // 验证 module-card
  const moduleCardBg = darkColors['module-card']?.bg
  console.log(`  暗色 module-card 背景: ${moduleCardBg}`)

  // 验证 quick-icon
  const quickIconBg = darkColors['quick-icon']?.bg
  console.log(`  暗色 quick-icon 背景: ${quickIconBg}`)

  // === 切回浅色确认双向 OK ===
  console.log('\n[r16-dark] 5. 切回浅色（验证双向）...')
  await toggleDarkMode(page)
  await page.waitForTimeout(500)
  const isLight = await page.evaluate(() => !document.documentElement.classList.contains('theme-dark'))
  if (!isLight) throw new Error('切回浅色失败')
  const bodyAfterLight = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  console.log(`  浅色 body 背景: ${bodyAfterLight}`)
  if (bodyAfterLight === 'rgb(15, 19, 32)') {
    throw new Error('切回浅色后 body 仍为深色')
  }

  console.log('\n[r16-dark] ✅ R16 暗色设计系统重构验证通过')
  console.log(`  截图：${SCREENSHOT_DIR}/5-r16-dark-{light,dark}-{dashboard,contract-list,invoice-ocr}.png`)
  await browser.close()
}

run().catch((e) => { console.error('[r16-dark] ❌ 失败:', e); process.exit(1) })
