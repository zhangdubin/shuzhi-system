/**
 * 一键从 OpenAPI 生成前端 TS 类型 + SDK
 * 用法：node scripts/gen-sdk.js
 * 前置：后端跑在 localhost:8000
 */
const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'
const ROOT = path.resolve(__dirname, '..')
const OPENAPI_JSON = path.join(ROOT, 'openapi.json')
const SCHEMA_TS = path.join(ROOT, 'frontend', 'src', 'api', 'generated', 'schema.ts')

async function main() {
  console.log(`▶ 下载 OpenAPI: ${BACKEND}/openapi.json`)
  const resp = await fetch(`${BACKEND}/openapi.json`)
  if (!resp.ok) {
    console.error(`❌ 后端不可达：${resp.status} ${resp.statusText}`)
    console.error('   请先启动后端 (cd deploy && docker compose up -d backend)')
    process.exit(1)
  }
  const spec = await resp.json()
  fs.writeFileSync(OPENAPI_JSON, JSON.stringify(spec, null, 2))
  const size = (fs.statSync(OPENAPI_JSON).size / 1024).toFixed(1)
  console.log(`✅ OpenAPI 已保存: ${OPENAPI_JSON} (${size} KB)`)
  console.log(`   端点数: ${Object.keys(spec.paths).length}, schema: ${Object.keys(spec.components?.schemas || {}).length}`)

  console.log('\n▶ 生成 TypeScript 类型...')
  fs.mkdirSync(path.dirname(SCHEMA_TS), { recursive: true })
  execSync(
    `npx openapi-typescript "${OPENAPI_JSON}" --output "${SCHEMA_TS}"`,
    { stdio: 'inherit', cwd: ROOT }
  )
  const lines = fs.readFileSync(SCHEMA_TS, 'utf-8').split('\n').length
  console.log(`✅ 类型已生成: ${SCHEMA_TS} (${lines} 行)`)

  console.log('\n▶ SDK 入口: frontend/src/api/sdk.ts')
  console.log('   用法: import { sdk } from "@/api/sdk"')
  console.log('   强类型调用: await sdk.contracts.list({ page: 1, pageSize: 20 })')

  console.log('\n🎉 完成')
}

main().catch(e => {
  console.error('生成失败:', e.message)
  process.exit(1)
})
