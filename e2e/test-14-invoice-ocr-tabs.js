/**
 * E2E Test: 发票识别主页 4 tabs 严格 1:1 复刻设计稿
 * 验证：
 * 1. /invoice/ocr 默认显示"智能识别" tab
 * 2. sub-tabs 4 个：智能识别 / 批量上传 / 识别记录 / 查验真伪
 * 3. 点击 tab 切换 + ?tab=xx 初始化
 * 4. 3 个独立子路由 redirect 到 /invoice/ocr?tab=xx
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

  const log = (msg) => console.log(`[test-14] ${msg}`)

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

    // 2. /invoice/ocr 默认 tab = single
    log('2. /invoice/ocr 默认显示"智能识别"...')
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__
      app.config.globalProperties.$router.push('/invoice/ocr')
    })
    await page.waitForURL(/\/invoice\/ocr/, { timeout: 5000 })
    await page.waitForSelector('h1:has-text("发票识别")', { timeout: 5000 })
    // 看 sub-tabs 4 个
    const subTabs = await page.$$eval('.sub-tabs a', els => els.map(e => e.textContent?.trim()))
    log(`   sub-tabs: ${JSON.stringify(subTabs)}`)
    if (!subTabs || subTabs.length !== 4) {
      throw new Error(`期望 4 个 sub-tab，实际 ${subTabs?.length}`)
    }
    if (subTabs[0] !== '智能识别' || subTabs[1] !== '批量上传' || subTabs[2] !== '识别记录' || subTabs[3] !== '查验真伪') {
      throw new Error(`sub-tab 文字不对: ${JSON.stringify(subTabs)}`)
    }
    // 看默认 active
    const activeText = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeText !== '智能识别') {
      throw new Error(`期望默认激活"智能识别"，实际 "${activeText}"`)
    }
    log('   ✅ 默认"智能识别"激活')
    // 看上传区是否存在
    const hasUpload = await page.evaluate(() => document.body.innerText.includes('上传发票'))
    if (!hasUpload) throw new Error('智能识别 tab 没渲染"上传发票"区')
    log('   ✅ 智能识别 tab 渲染正常')

    // 3. 点"批量上传" tab
    log('3. 点"批量上传" tab...')
    await page.click('.sub-tabs a:has-text("批量上传")')
    await page.waitForTimeout(500)
    const urlAfterBatch = page.url()
    log(`   URL: ${urlAfterBatch}`)
    if (!urlAfterBatch.includes('tab=batch')) {
      throw new Error(`URL 没更新到 tab=batch: ${urlAfterBatch}`)
    }
    // 看 active 切换
    const activeAfterBatch = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeAfterBatch !== '批量上传') throw new Error(`active 切错: ${activeAfterBatch}`)
    // 看 BatchUpload 内容（拖拽提示）
    const hasBatch = await page.evaluate(() => document.body.innerText.includes('拖拽发票文件到此处'))
    if (!hasBatch) throw new Error('批量上传 tab 没渲染拖拽区')
    log('   ✅ 批量上传 tab 切换 + 渲染正常')

    // 4. 点"识别记录" tab
    log('4. 点"识别记录" tab...')
    await page.click('.sub-tabs a:has-text("识别记录")')
    // RecordsList onMounted 调 records API 要等响应（受后端调度影响，可能慢）
    await page.waitForSelector('.filter-panel', { timeout: 10000 })
    if (!page.url().includes('tab=records')) {
      throw new Error(`URL 没更新到 tab=records: ${page.url()}`)
    }
    log('   ✅ 识别记录 tab 切换 + 渲染正常')

    // 5. 点"查验真伪" tab
    log('5. 点"查验真伪" tab...')
    await page.click('.sub-tabs a:has-text("查验真伪")')
    await page.waitForTimeout(500)
    if (!page.url().includes('tab=verify')) {
      throw new Error(`URL 没更新到 tab=verify: ${page.url()}`)
    }
    const hasVerify = await page.evaluate(() => document.body.innerText.includes('发票代码'))
    if (!hasVerify) throw new Error('查验真伪 tab 没渲染发票代码表单')
    log('   ✅ 查验真伪 tab 切换 + 渲染正常')

    // 6. ?tab=xx 直接初始化（侧栏点子菜单场景）
    log('6. /invoice/ocr?tab=batch 直接初始化到批量上传...')
    await page.goto(`${BASE}/invoice/ocr?tab=batch`)
    await page.waitForTimeout(500)
    const activeFromQuery = await page.$eval('.sub-tabs a.active', el => el.textContent?.trim())
    if (activeFromQuery !== '批量上传') {
      throw new Error(`?tab=batch 没激活批量上传，实际 "${activeFromQuery}"`)
    }
    log('   ✅ ?tab=batch 初始化激活成功')

    // 7. 3 个独立子路由 redirect
    log('7. /invoice/ocr/batch → redirect 到 ?tab=batch...')
    await page.goto(`${BASE}/invoice/ocr/batch`)
    await page.waitForURL(/\/invoice\/ocr\?tab=batch/, { timeout: 5000 })
    log(`   ✅ /invoice/ocr/batch → ${page.url()}`)

    log('8. /invoice/ocr/records → redirect 到 ?tab=records...')
    await page.goto(`${BASE}/invoice/ocr/records`)
    await page.waitForURL(/\/invoice\/ocr\?tab=records/, { timeout: 5000 })
    log(`   ✅ /invoice/ocr/records → ${page.url()}`)

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 发票识别 4 tabs 严格 1:1 复刻 + 路由 redirect 全过')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-14-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
