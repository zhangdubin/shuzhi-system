/**
 * E2E Test Runner — 一次跑完所有测试
 * 用法: node e2e/run-all.js
 */
const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')

const tests = [
  'test-01-login-dashboard.js',
  'test-02-contract-list.js',
  'test-03-ai-ask.js',
  'test-04-sse-realtime.js',
  'test-05-permission.js',
  'test-06-notice-cron.js',
  'test-07-cron-scheduler.js',
  'test-08-paddleocr-real.js',
  'test-09-nuonuo-verify.js',
  'test-10-wechat-work-sso.js',
  'test-11-monitoring.js',
  'test-12-invoice-ocr-submenu.js',
  'test-13-parent-menu-404.js',
  'test-14-invoice-ocr-tabs.js',
]

async function runTest(file) {
  return new Promise((resolve) => {
    const start = Date.now()
    const proc = spawn('node', [path.join(__dirname, file)], { stdio: 'inherit' })
    proc.on('close', (code) => {
      const duration = ((Date.now() - start) / 1000).toFixed(1)
      resolve({ file, code, duration })
    })
  })
}

;(async () => {
  console.log('='.repeat(60))
  console.log('  E2E Test Suite — 数智化管理系统')
  console.log('='.repeat(60))

  const results = []
  for (const test of tests) {
    console.log(`\n▶ ${test}\n${'─'.repeat(60)}`)
    const r = await runTest(test)
    results.push(r)
    console.log(`\n  → ${r.code === 0 ? '✅ PASS' : '❌ FAIL'} (${r.duration}s)\n`)
  }

  // 汇总
  console.log('='.repeat(60))
  console.log('  Summary')
  console.log('='.repeat(60))
  const passed = results.filter(r => r.code === 0).length
  const failed = results.length - passed
  results.forEach(r => {
    const icon = r.code === 0 ? '✅' : '❌'
    console.log(`  ${icon} ${r.file.padEnd(35)} ${r.duration}s`)
  })
  console.log('─'.repeat(60))
  console.log(`  ${passed} passed / ${failed} failed / ${results.length} total`)
  console.log('='.repeat(60))

  // 写报告
  const reportPath = path.join(__dirname, `report-${Date.now()}.md`)
  const report = [
    '# E2E Test Report',
    `> 时间: ${new Date().toISOString()}`,
    '',
    '## Summary',
    `- **通过**: ${passed}`,
    `- **失败**: ${failed}`,
    `- **总计**: ${results.length}`,
    '',
    '## Details',
    '',
    '| Test | Result | Duration |',
    '|------|--------|----------|',
    ...results.map(r => `| ${r.file} | ${r.code === 0 ? '✅ PASS' : '❌ FAIL'} | ${r.duration}s |`),
    '',
  ].join('\n')
  fs.writeFileSync(reportPath, report)
  console.log(`\n📄 报告已写入: ${reportPath}`)

  process.exit(failed > 0 ? 1 : 0)
})()
