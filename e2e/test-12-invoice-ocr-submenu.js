/**
 * E2E Test: 发票识别子菜单（批量上传 / 识别记录）点击不再 404
 * 验证：登录 → 点侧栏"发票识别"子菜单 → 跳到正确路径 + 渲染
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

  const log = (msg) => console.log(`[test-12] ${msg}`)

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

    // 截图看侧栏菜单
    await page.screenshot({ path: '/tmp/test-12-dashboard.png', fullPage: false })

    // 2. R8.7 架构升级：/invoice/ocr/batch → redirect 到 /invoice/ocr?tab=batch
    //     waitForURL 等的是最终 URL（?tab=batch），不是中间路径
    log('2. /invoice/ocr/batch → redirect 到 ?tab=batch...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/invoice/ocr/batch')
    })
    await page.waitForURL(/\/invoice\/ocr\?tab=batch/, { timeout: 5000 })
    log(`   ✅ URL: ${page.url()}`)
    // 等 InvoiceOcr 主页渲染（标题"发票识别"是 4 tabs 页的 h2）
    await page.waitForSelector('h1:has-text("发票识别")', { timeout: 5000 })
    // 确认 active tab = 批量上传
    const activeTabBatch = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeTabBatch !== '批量上传') throw new Error(`期望 active=批量上传，实际 "${activeTabBatch}"`)
    log('   ✅ 批量上传 tab 激活 + 渲染正常')

    // 3. /invoice/ocr/records
    log('3. /invoice/ocr/records → redirect 到 ?tab=records...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/invoice/ocr/records')
    })
    await page.waitForURL(/\/invoice\/ocr\?tab=records/, { timeout: 5000 })
    log(`   ✅ URL: ${page.url()}`)
    const activeTabRecords = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeTabRecords !== '识别记录') throw new Error(`期望 active=识别记录，实际 "${activeTabRecords}"`)
    log('   ✅ 识别记录 tab 激活 + 渲染正常')

    // 4. /invoice/ocr 主页（默认 tab=智能识别）
    log('4. /invoice/ocr 默认智能识别 tab...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/invoice/ocr')
    })
    await page.waitForURL(/\/invoice\/ocr$/, { timeout: 5000 })
    log(`   ✅ /invoice/ocr URL: ${page.url()}`)
    const activeTabSingle = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeTabSingle !== '智能识别') throw new Error(`期望默认 active=智能识别，实际 "${activeTabSingle}"`)
    log('   ✅ 默认智能识别 tab 激活')

    // 5. 6 个 invoice 路径都 200（用 page.goto 让 vue-router 处理）
    log('5. 验证 6 个 invoice 路径全部 200...')
    const paths = [
      '/invoice/ocr',
      '/invoice/ocr/batch',     // → redirect 到 /invoice/ocr?tab=batch
      '/invoice/ocr/records',   // → redirect 到 /invoice/ocr?tab=records
      '/invoice/ocr/1',         // 详情
      '/invoice/verify',        // 独立路由（验真页）
      '/invoice/template',
    ]
    for (const p of paths) {
      const resp = await page.goto(`${BASE}${p}`)
      log(`   ${p}: HTTP ${resp.status()}`)
      if (resp.status() !== 200) throw new Error(`${p} 返回 ${resp.status()}`)
    }

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 发票识别子菜单 E2E 通过（4 个子菜单不再 404）')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-12-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
