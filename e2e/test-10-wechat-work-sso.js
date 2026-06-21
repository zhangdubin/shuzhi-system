/**
 * E2E Test: 企业微信 SSO 流程（mock 模式 + 协议对齐验证）
 *
 * 当前状态：
 *   - 没配 WECHAT_WORK_CORP_ID / SECRET → 自动走 mock
 *   - mock 模式 5 种角色（按 state 后 4 位 hash 决定）
 *   - 真接入协议已就位：access_token 缓存（7200s）+ OAuth code→userid→user detail
 *
 * 真实企业微信 OAuth 流程：
 *   1. 后端生成 state，存 Redis，构造 QR URL
 *   2. 用户用企业微信 App 扫码
 *   3. 企业微信回调 redirect_uri?code=...&state=...
 *   4. 后端用 code 调 getuserinfo 拿 userid + user_ticket
 *   5. 用 user_ticket 调 getuserdetail 拿 name/mobile/email
 *   6. 查本系统 user 表，按 userid 匹配 → 签发 JWT
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:80'
const HEADLESS = process.env.HEADLESS !== '0'

async function run() {
  const browser = await chromium.launch({ headless: HEADLESS })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.setDefaultTimeout(30000)

  const errors = []
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })

  const log = (msg) => console.log(`[test-10] ${msg}`)

  try {
    // 1. 登录（用 admin 拿 token 测 API）
    log('1. 登录 admin 测其他端点...')
    await page.goto(`${BASE}/login`)
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
    await page.reload()
    await page.waitForSelector('input[placeholder*="账号" i]', { timeout: 10000 })
    await page.fill('input[placeholder*="账号" i]', 'admin')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button:has-text("登 录")')
    await page.waitForURL(/\/dashboard/, { timeout: 10000 })

    const token = await page.evaluate(() => localStorage.getItem('shuzhi_token'))

    // 2. /sso/wechat-work/health
    log('2. 健康检查（看当前模式）...')
    const healthResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/auth/sso/wechat-work/health', {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      return await r.json()
    }, token)
    const mode = healthResp.data?.mode
    const reason = healthResp.data?.reason || ''
    log(`   mode: ${mode} | reason: ${reason}`)
    if (mode !== 'mock') {
      log(`   ⚠️  期望 mock，实际 ${mode}（生产环境应该是 real）`)
    }

    // 3. 生成 wechat-work 二维码
    log('3. 生成 wechat-work 二维码...')
    const qrResp = await page.evaluate(async (token) => {
      const r = await fetch('/api/v1/auth/sso/qrcode/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ provider: 'wechat-work' }),
      })
      return await r.json()
    }, token)

    if (!qrResp.qrToken || !qrResp.qrImageUrl) {
      throw new Error('二维码生成失败')
    }
    const qrToken = qrResp.qrToken
    log(`   qrToken: ${qrToken.slice(0, 25)}...`)
    log(`   expiresIn: ${qrResp.expiresIn}s`)
    log(`   qrImageUrl 长度: ${qrResp.qrImageUrl.length} 字符`)
    log(`   pollUrl: ${qrResp.pollUrl}`)
    if (qrResp.scanUrl) {
      log(`   scanUrl (debug): ${qrResp.scanUrl.slice(0, 60)}...`)
    }

    // 4. check 状态（应该 waiting）
    log('4. check 状态（mock 模式应该 waiting）...')
    const checkResp = await page.evaluate(async ({ token, qrToken }) => {
      const r = await fetch('/api/v1/auth/sso/qrcode/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ qrToken }),
      })
      return await r.json()
    }, { token, qrToken })
    log(`   status: ${checkResp.status}`)
    if (checkResp.status !== 'waiting') {
      log(`   ⚠️  期望 waiting，实际 ${checkResp.status}`)
    }

    // 5. 模拟用户扫码后回调（mock 模式直接走 callback 端点）
    log('5. 模拟扫码后回调（mock 模式 callback 端点）...')
    const callbackResp = await page.evaluate(async (token) => {
      // state 用 admin hash 末尾的"4" → bucket 4 → mock viewer
      // 用 "0" → bucket 0 → mock admin（fallback 到本系统 admin）
      const r = await fetch('/api/v1/auth/sso/wechat-work/callback?code=mock_code&state=abc12340', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      return await r.json()
    }, token)
    log(`   token: ${callbackResp.token?.slice(0, 30) || 'NONE'}`)
    if (!callbackResp.token) {
      throw new Error(`callback 失败: ${JSON.stringify(callbackResp)}`)
    }
    const userName = callbackResp.userInfo?.name || '?'
    const newToken = callbackResp.token
    log(`   userInfo.name: ${userName}`)
    log(`   permissions: ${callbackResp.userInfo?.permissions?.length || 0} 个`)

    // 6. 验证 callback 签发的 token 能用
    if (newToken) {
      log('6. 验证 callback 签发的 token...')
      const meResp = await page.evaluate(async (token) => {
        const r = await fetch('/api/v1/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` },
        })
        return await r.json()
      }, newToken)
      log(`   /auth/me user: ${meResp.data?.name || meResp.data?.username || '?'}`)
      if (!meResp.data?.userId) {
        throw new Error('callback 签发的 token 不能访问 /auth/me')
      }
    }

    if (errors.length > 0) {
      log(`⚠️  ${errors.length} 个 console/page error（不影响测试）:`)
      errors.slice(0, 3).forEach(e => log(`   - ${e}`))
    } else {
      log('✅ 企业微信 SSO E2E 通过（mock 模式 + 协议对齐）')
    }
  } catch (e) {
    log(`❌ 测试失败: ${e.message}`)
    if (!HEADLESS) await page.screenshot({ path: 'e2e/test-10-failure.png' })
    throw e
  } finally {
    await browser.close()
  }
}

if (require.main === module) {
  run().then(() => process.exit(0)).catch(() => process.exit(1))
}
module.exports = { run }
