/**
 * 截 4 个设计稿 + 4 个实际页面的对比图
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_FRONTEND = 'http://localhost:80'
const BASE_DESIGN = 'http://localhost:8090'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(15000)

  const log = (msg) => console.log(`[compare] ${msg}`)

  // 1. 登录真实系统
  log('登录真实系统...')
  await page.goto(`${BASE_FRONTEND}/login`)
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
  await page.reload()
  await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
  await page.fill('input[placeholder*="账号" i]', 'admin')
  await page.fill('input[type="password"]', 'admin123')
  await page.click('button:has-text("登 录")')
  await page.waitForURL(/\/dashboard/, { timeout: 10000 })

  const outDir = '/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare'
  fs.mkdirSync(outDir, { recursive: true })

  // ============================================================
  // 4 个 tab × 2 套 = 8 张图
  // ============================================================
  const tabs = [
    { key: 'single',  label: '智能识别', designFile: 'invoice-ocr.html',         realPath: '/invoice/ocr' },
    { key: 'batch',   label: '批量上传', designFile: 'invoice-ocr-batch.html',   realPath: '/invoice/ocr?tab=batch' },
    { key: 'records', label: '识别记录', designFile: 'invoice-ocr-records.html', realPath: '/invoice/ocr?tab=records' },
    { key: 'verify',  label: '查验真伪', designFile: 'invoice-ocr-verify.html',  realPath: '/invoice/ocr?tab=verify' },
  ]

  for (const t of tabs) {
    // 截设计稿（直接在 design 服务看）
    log(`截设计稿: ${t.designFile}`)
    await page.goto(`${BASE_DESIGN}/${t.designFile}`)
    await page.waitForTimeout(1500)
    const designPath = path.join(outDir, `1-design-${t.key}.png`)
    await page.screenshot({ path: designPath, fullPage: true })

    // 截实际页面
    log(`截实际: ${t.label}`)
    await page.goto(`${BASE_FRONTEND}${t.realPath}`)
    await page.waitForTimeout(2000)
    const realPath = path.join(outDir, `2-real-${t.key}.png`)
    await page.screenshot({ path: realPath, fullPage: true })

    log(`✅ ${t.label}: 设计稿→${designPath}, 实际→${realPath}`)
  }

  await browser.close()
  log('---')
  log('完成！截图在：' + outDir)
  log('对比 4 个 tab 的设计稿（1-design-*.png） vs 实际（2-real-*.png）')
}

run().catch(e => { console.error(e); process.exit(1) })
