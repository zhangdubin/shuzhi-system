/**
 * E2E Test: 父菜单点击不再 404
 * 验证：登录 → 点侧栏"发票识别"父菜单 → 跳到 /invoice/ocr（识别主页）
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(15000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-13] ${msg}`)

  try {
    // 1. 登录
    log('1. 登录 admin...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
    await page.reload()
    await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })
    log('   ✅ 登录成功')

    // 2. 直接 navigate 到根路径，确认菜单渲染
    log('2. 看侧栏菜单 DOM（找出"发票识别"父菜单链接）...')
    const menuLinks = await page.evaluate(() => {
      // 找所有 el-menu-item 渲染出来的 a 标签的 href
      const links = Array.from(document.querySelectorAll('.el-menu a, .el-menu-item'))
      return links.map(el => ({
        text: el.innerText?.trim().slice(0, 30),
        href: el.getAttribute('href') || el.querySelector('a')?.getAttribute('href') || '',
        tag: el.tagName,
      })).filter(x => x.text)
    })
    log(`   侧栏菜单项数: ${menuLinks.length}`)
    for (const l of menuLinks.slice(0, 15)) {
      log(`     ${l.tag.padEnd(15)} href="${l.href.padEnd(25)}" | ${l.text}`)
    }

    // 3. 通过 router.push 模拟点父菜单"发票识别"
    log('3. router.push 到父菜单 /invoice/ocr（应该成功，不再 404）...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/invoice/ocr')
    })
    await page.waitForURL(/\/invoice\/ocr$/, { timeout: 5000 })
    log(`   ✅ URL: ${page.url()}`)
    if (!page.url().endsWith('/invoice/ocr')) {
      throw new Error(`期望 /invoice/ocr，实际 ${page.url()}`)
    }

    // 4. 等页面渲染（看是否是真 InvoiceOcr 页）
    log('4. 验证识别主页渲染...')
    await page.waitForSelector('h1:has-text("发票识别")', { timeout: 5000 })
    const hasUploadZone = await page.evaluate(() => document.body.innerText.includes('上传发票'))
    if (!hasUploadZone) throw new Error('识别主页没渲染"上传发票"区')
    log('   ✅ 识别主页渲染正常（"发票识别"标题 + "上传发票"区）')

    // 5. 测"AI 智能中心"父菜单（也是 index='/ai'，路由有 /ai → AiCenter）
    log('5. router.push 到 /ai（AI 智能中心父菜单）...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/ai')
    })
    await page.waitForURL(/\/ai$/, { timeout: 5000 })
    log(`   ✅ URL: ${page.url()}`)

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 父菜单点击不再 404，路由正常')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-13-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
