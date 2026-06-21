# R14C PWA 改造报告

**日期**：2026-06-15  
**父 session 拍板**：R14C PWA（vite-plugin-pwa + manifest + sw + offline + 提示组件）  
**耗时**：~25 分钟  
**当前状态**：✅ 完成

---

## 交付物清单

| 交付物 | 路径 | 大小/行数 | 状态 |
|---|---|---|---|
| 依赖 | `package.json`（vite-plugin-pwa 1.3.0 + workbox-window 7.4.1） | 2 个包 | ✅ |
| Vite PWA plugin 配置 | `vite.config.ts` | +60 行 | ✅ |
| PWA icon SVG | `public/pwa-icon.svg` | 969 B | ✅ |
| PWA icon 192 | `public/pwa-192x192.png` | 8.3 KB | ✅ |
| PWA icon 512 | `public/pwa-512x512.png` | 29.7 KB | ✅ |
| iOS touch icon | `public/apple-touch-icon.png` | 7.7 KB | ✅ |
| favicon | `public/favicon-32x32.png` | 920 B | ✅ |
| 离线降级页 | `public/offline.html` | 4.6 KB | ✅ |
| 安装提示组件 | `src/components/PWAInstallPrompt.vue` | 196 行 | ✅ |
| AppLayout 挂载 | `src/layouts/AppLayout.vue` | +2 行 | ✅ |
| Build 产物（dist） | `sw.js` / `workbox-*.js` / `manifest.webmanifest` | 3 个 | ✅ |

---

## 关键技术细节

### 1. vite.config.ts 改动（VitePWA plugin）

```ts
VitePWA({
  registerType: 'autoUpdate',     // 自动更新
  injectRegister: 'auto',         // 自动注入
  includeAssets: ['favicon-32x32.png', 'apple-touch-icon.png', 'pwa-icon.svg'],
  manifest: {
    name: '数智化管理系统',
    short_name: '数智系统',
    theme_color: '#4F6BFF',
    background_color: '#0F1320',
    display: 'standalone',         // 隐藏浏览器 UI
    start_url: '/',
    scope: '/',
    icons: [192, 512, SVG maskable],
  },
  workbox: {
    maximumFileSizeToCacheInBytes: 5 MB,
    navigateFallback: '/index.html',
    navigateFallbackDenylist: [/^\/api\//],   // API 不走 fallback
    runtimeCaching: [
      // 1. 静态资源 (JS/CSS/字体) — CacheFirst, 1 年
      // 2. 图片 — CacheFirst, 30 天
      // 3. API list — StaleWhileRevalidate, 5 分钟
      // 4. API common/dict/users/ref — CacheFirst, 10 分钟
      // 5. POST/PUT/DELETE — NetworkOnly (永远写)
    ],
  },
})
```

### 2. 缓存策略

| 资源类型 | 策略 | TTL | 容量上限 |
|---|---|---|---|
| JS / CSS / 字体 | CacheFirst | 365 天 | 200 项 |
| 图片 | CacheFirst | 30 天 | 100 项 |
| API `*/list` | StaleWhileRevalidate | 5 分钟 | 50 项 |
| API `common/dict/users/ref` | CacheFirst | 10 分钟 | 50 项 |
| API POST/PUT/DELETE | NetworkOnly | 永不缓存 | — |

### 3. PWAInstallPrompt 组件

- **监听 beforeinstallprompt**：捕获浏览器原生安装提示，5 秒后弹出卡片
- **7 天冷却**：用户点"稍后"后 7 天内不再打扰（localStorage 记录时间戳）
- **离线监听**：网络断开时顶部红色提示条
- **网络恢复自动 reload**：每 10s 探测 `/api/v1/auth/me`，成功就 reload
- **已安装标记**：appinstalled 事件写 localStorage

### 4. offline.html 设计

- 深色背景（`#0F1320 → #312E81` 渐变）+ 毛玻璃卡片
- 移动端友好的"重新连接" + "返回"按钮
- 自动 10s 探测网络恢复
- 友好解释：哪些可用 / 哪些不可用 / 网络恢复会同步

---

## 验证

### 1. Build 验证
```
✓ built in 3.33s
PWA v1.3.0
mode      generateSW
precache  43 entries (2417.05 KiB)
files generated
  dist/sw.js
  dist/workbox-62be624e.js
```

### 2. 资源 200 验证
```
  / : 200
  /manifest.webmanifest : 200
  /sw.js : 200
  /offline.html : 200
  /pwa-192x192.png : 200
  /pwa-512x512.png : 200
  /registerSW.js : 200
  /workbox-62be624e.js : 200
```

### 3. 浏览器真实验证（Playwright）
- ✅ `link[rel=manifest]` 已注入
- ✅ service worker **已注册**（1 个跑起来）
- ✅ manifest 内容正确（name, theme #4F6BFF, display standalone）
- ⚠️ install prompt 元素未显示 = 正确（headless 不触发 beforeinstallprompt）
- ⚠️ offline bar 未显示 = 正确（在线状态）

### 4. 截图归档
- `4-real-r14c-pwa-manifest.png`（manifest 内容）
- `4-real-r14c-pwa-icon.png`（PWA icon 视觉）

---

## R14 整体回顾（A + B + C 全部完成）

| 子项 | 状态 | 关键指标 |
|---|---|---|
| R14A 暗色模式 | ✅ | body #0F1320 + 10 页 E2E 验证 + 49 行 CSS 覆写 |
| R14B 压测基线 | ✅ | 业务核心 20 RPS P95 14ms 0% 错，AI 业务混合 10 RPS P95 26ms |
| R14C PWA | ✅ | vite-plugin-pwa + 43 项 precache + 5 路由缓存策略 + 离线降级 + 安装提示 |

**R14 总耗时**：~75 分钟（30 + 20 + 25）

## R15 候选（等父 session 拍板）

1. **诺诺真接入**（资质 1-3 天到位）
2. **继续性能优化**（扩 worker / 加 Redis 缓存覆盖）
3. **PWA 上线验证**（生产 HTTPS + 真机测试）
4. **整理 R1-R14 全流程文档**（GO-LIVE-REPORT 完整收尾）

---

**报告版本**：R14C v1.0 | 2026-06-15
**状态**：R14 三件套（暗色 + 压测 + PWA）全部完成
