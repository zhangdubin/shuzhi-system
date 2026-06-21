/**
 * 截 P5C 5 页 design vs 实际对比
 * - ReceivableCreate / ReceivableDetail / InvoiceDetail / InvoiceTemplateEdit / InvoiceTemplateDetail
 * - design: 找 design/ 对应 html；无 design 的用"无 design 标记"
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_FRONTEND = 'http://localhost:80'
const BASE_DESIGN = 'http://localhost:8090'

async function run() {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1100 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(20000)

  // 1. 登录
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
  // 5 个 P5C 页面
  // ============================================================
  const pages = [
    { name: 'p5c-receivable-create',    realPath: '/receivable/create',             designFile: 'receivable-create.html' },
    { name: 'p5c-receivable-detail',    realPath: '/receivable/1',                  designFile: 'receivable-detail.html' },
    { name: 'p5c-invoice-detail',       realPath: '/invoice/ocr/1',                designFile: 'invoice-detail.html' },
    { name: 'p5c-invoice-template-edit', realPath: '/invoice/template/1/edit',     designFile: 'invoice-template-edit.html' },
    { name: 'p5c-invoice-template-detail', realPath: '/invoice/template/1',         designFile: 'none' },
  ]

  for (const p of pages) {
    // 1. 实际页面
    console.log(`[compare] 截实际: ${p.name}`)
    await page.goto(`${BASE_FRONTEND}${p.realPath}`)
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(outDir, `2-real-${p.name}.png`), fullPage: true })

    // 2. 设计稿（如果存在）
    if (p.designFile !== 'none') {
      try {
        const res = await page.goto(`${BASE_DESIGN}/${p.designFile}`)
        if (res && res.status() === 200) {
          await page.waitForTimeout(800)
          await page.screenshot({ path: path.join(outDir, `1-design-${p.name}.png`), fullPage: true })
          console.log(`  ✅ design saved`)
        } else {
          console.log(`  ⚠️ design ${p.designFile} HTTP ${res?.status()}`)
        }
      } catch (e) {
        console.log(`  ⚠️ design skip: ${e.message}`)
      }
    } else {
      console.log(`  ⚠️ no design (自造)`)
    }
  }

  await browser.close()
  console.log('[compare] ✅ P5C 5 页对比图完成')
}

run().catch(e => { console.error(e); process.exit(1) })
