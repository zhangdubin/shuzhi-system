#!/usr/bin/env node
/**
 * R10A 5 截图 — 验证 P0 5 触点
 * 1. Dashboard 今日 AI 提醒条（触点 #5）
 * 2. ProjectList AI 风险评级列（触点 #3）
 * 3. ProjectDetail ✨ AI 分析 Tab（触点 #4）
 * 4. InvoiceOcr 一键 AI 抽取（触点 #1）
 * 5. BatchUpload AI 开关 + SSE 进度（触点 #2）
 */
const { chromium } = require('playwright')
const path = require('path')
const fs = require('fs')

const SHOT_DIR = path.join(__dirname, '../docs/screenshots/compare')
fs.mkdirSync(SHOT_DIR, { recursive: true })

async function login(page) {
  await page.goto('http://localhost/login', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await page.fill('input[placeholder*="账号"]', 'admin')
  await page.fill('input[placeholder*="密码"]', 'admin123')
  await page.click('button[type="submit"], .login-btn, .btn-primary')
  await page.waitForURL(/dashboard/, { timeout: 10000 })
}

async function shot(page, name, desc) {
  const file = path.join(SHOT_DIR, `2-real-r10a-${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  console.log(`[R10A] 截图: ${name}（${desc}）`)
  return file
}

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  try {
    await login(page)
    await page.waitForTimeout(2000)
    await shot(page, '01-dashboard-ai-alerts', '触点 #5：今日 AI 提醒条')

    await page.goto('http://localhost/project/list', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1500)
    await shot(page, '02-project-list-ai-risk', '触点 #3：项目列表 AI 风险评级列')

    await page.goto('http://localhost/project/1', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1500)
    // 切到 AI Tab
    const aiTab = page.locator('text=/✨ AI/').first()
    if (await aiTab.count() > 0) {
      await aiTab.click()
      await page.waitForTimeout(2500) // 等 AiRiskScanPanel mock 加载
    }
    await shot(page, '03-project-detail-ai-tab', '触点 #4：项目详情 AI 分析 Tab')

    await page.goto('http://localhost/invoice/ocr', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    // 触发示例图
    const sampleBtn = page.locator('button:has-text("示例")').first()
    if (await sampleBtn.count() > 0) {
      await sampleBtn.click()
      await page.waitForTimeout(2500) // 等 OCR + AI 抽取
    }
    await shot(page, '04-invoice-ocr-ai-extract', '触点 #1：InvoiceOcr 一键 AI 抽取')

    await page.goto('http://localhost/invoice/ocr?tab=batch', { waitUntil: 'networkidle' })
    await page.waitForTimeout(1000)
    await shot(page, '05-batch-upload-ai-sse', '触点 #2：BatchUpload AI 开关 + SSE 实时进度')

    console.log('[R10A] ✅ 5 截图完成')
  } catch (e) {
    console.error('[R10A] ❌', e.message)
    process.exit(1)
  } finally {
    await browser.close()
  }
})()
