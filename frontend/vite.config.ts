import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
// import { VitePWA } from 'vite-plugin-pwa' // PWA 已禁用，避免更新需清缓存
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia'],
        resolvers: [ElementPlusResolver()],
        dts: 'src/auto-imports.d.ts',
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: 'src/components.d.ts',
      }),

    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        // 开发代理：所有 /api/* 转到后端容器
        '/api': {
          target: env.VITE_API_PROXY || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      target: 'es2018',
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          // R11A 性能优化：按 domain 拆 chunk（function 形式按模块路径匹配）
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('element-plus') || id.includes('@element-plus/icons-vue')) return 'element-plus'
              return 'vendor'
            }
            // AI 组件单独切
            if (id.includes('/src/components/ai/')) return 'ai-components'
            // 业务 domain 按目录切
            if (id.includes('/src/views/auth/')) return 'domain-auth'
            if (id.includes('/src/views/project/')) return 'domain-project'
            if (id.includes('/src/views/contract/')) return 'domain-contract'
            if (id.includes('/src/views/expense/')) return 'domain-expense'
            if (id.includes('/src/views/receivable/')) return 'domain-receivable'
            if (id.includes('/src/views/client/')) return 'domain-client'
            if (id.includes('/src/views/invoice/')) return 'domain-invoice'
            if (id.includes('/src/views/ai/')) return 'domain-ai'
            if (id.includes('/src/views/admin/')) return 'domain-admin'
            if (id.includes('/src/views/error/')) return 'domain-error'
            if (id.includes('/src/views/notice/')) return 'domain-notice'
            if (id.includes('/src/views/dashboard/')) return 'domain-dashboard'
            return undefined
          },
        },
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: `@use "@/assets/styles/variables.scss" as *;`,
        },
      },
    },
  }
})
