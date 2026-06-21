# 设计 Token 文档

> **数智化管理系统** 完整设计 Token 速查表。**前端工程师的字典**。
> 所有值都对应 `assets/common.css` 中的 CSS 变量，可直接引用或迁移到 Tailwind / CSS-in-JS。

---

## 1. 颜色（Color Tokens）

### 1.1 品牌色

| Token | HEX | RGB | 用途 |
|-------|-----|-----|------|
| `--color-primary` | `#4F6BFF` | 79, 107, 255 | 品牌主色（蓝），用于按钮/链接/激活态 |
| `--color-primary-hover` | `#3D58E8` | 61, 88, 232 | 主色悬停 |
| `--color-primary-light` | `#E0E6FF` | 224, 230, 255 | 主色背景块（浅） |
| `--color-primary-bg` | `rgba(79,107,255,0.08)` | — | 主色最浅底色（hover/选中背景） |

### 1.2 品牌渐变

| Token | 值 | 用途 |
|-------|-----|------|
| `--gradient-brand` | `linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%)` | 主按钮 / 标题渐变 / 激活指示 |
| `--gradient-brand-soft` | `linear-gradient(135deg, rgba(79,107,255,0.12) 0%, rgba(124,58,237,0.12) 100%)` | 软渐变背景 |
| `--gradient-hero` | `linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #312E81 100%)` | 深色 hero（登录/Dashboard/项目详情） |

### 1.3 功能色

| Token | HEX | 用途 |
|-------|-----|------|
| `--color-success` | `#10B981` | 成功 / 已通过 / 已完成 |
| `--color-success-bg` | `#D1FAE5` | 成功状态底色 |
| `--color-warning` | `#F59E0B` | 警告 / 待处理 / 即将到期 |
| `--color-warning-bg` | `#FEF3C7` | 警告状态底色 |
| `--color-danger` | `#EF4444` | 错误 / 已逾期 / 失败 / 驳回 |
| `--color-danger-bg` | `#FEE2E2` | 危险状态底色 |
| `--color-info` | `#06B6D4` | 信息 / 进行中 / 已关联 |
| `--color-info-bg` | `#CFFAFE` | 信息状态底色 |

### 1.4 文字色（4 级）

| Token | HEX | 用途 | 对比度（白底） |
|-------|-----|------|---------------|
| `--color-text-primary` | `#0F172A` | 主要文字（标题、按钮） | 18.7:1 ✅ AAA |
| `--color-text-secondary` | `#475569` | 次要文字（描述、辅助） | 7.5:1 ✅ AAA |
| `--color-text-tertiary` | `#94A3B8` | 辅助文字（提示、placeholder） | 3.0:1 — 大字 OK |
| `--color-text-inverse` | `#F8FAFC` | 反色文字（深色背景上） | 16.2:1 ✅ AAA |

### 1.5 背景色

| Token | HEX | 用途 |
|-------|-----|------|
| `--color-bg` | `#F1F5F9` | 页面背景（浅灰） |
| `--color-bg-card` | `#FFFFFF` | 卡片背景 |
| `--color-bg-elevated` | `#FFFFFF` | 顶栏背景（带模糊） |
| `#F8FAFC` | — | 子层背景（表头、hover） |
| `#F1F5F9` | — | 骨架屏底色 / 表头更深 |

### 1.6 边框

| Token | HEX | 用途 |
|-------|-----|------|
| `--color-border` | `#E2E8F0` | 默认边框 |
| `--color-border-strong` | `#CBD5E1` | 加强边框（强调） |

### 1.7 深色侧栏（科技金融）

| Token | HEX | 用途 |
|-------|-----|------|
| `--color-sidebar-bg` | `#0B1220` | 侧栏底色（深） |
| `--color-sidebar-bg-2` | `#111A2E` | 备用深色 |
| `--color-sidebar-text` | `#94A3B8` | 侧栏普通文字 |
| `--color-sidebar-text-active` | `#FFFFFF` | 激活态文字 |
| `--color-sidebar-active-bg` | `rgba(79,107,255,0.18)` | 激活态底色 |

### 1.8 阴影

| Token | 值 | 用途 |
|-------|-----|------|
| `--shadow-sm` | `0 1px 2px 0 rgb(15 23 42 / 0.05)` | 默认卡片 |
| `--shadow-md` | `0 4px 12px -2px rgb(15 23 42 / 0.08)` | 浮起卡片 |
| `--shadow-lg` | `0 12px 32px -8px rgb(15 23 42 / 0.12)` | 弹窗、抽屉 |
| `--shadow-glow` | `0 8px 32px -4px rgba(79, 107, 255, 0.35)` | 品牌光晕（主按钮） |

---

## 2. 圆角（Radius Tokens）

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | `6px` | 小元素（tag、input） |
| `--radius-md` | `10px` | 按钮、input、表格行 |
| `--radius-lg` | `14px` | 卡片、弹窗、面板 |
| `--radius-xl` | `20px` | 大型弹窗、登录页 |
| `--radius-full` | `9999px` | 胶囊（avatar、tag、按钮） |

---

## 3. 间距（Spacing Tokens）

> 基于 8px 网格。`spacing-N = N × 4px`

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `spacing-0` | `0` | 重置 |
| `spacing-1` | `4px` | 极小间距 |
| `spacing-2` | `8px` | 紧凑间距（input padding） |
| `spacing-3` | `12px` | 默认间距 |
| `spacing-4` | `16px` | 卡片内边距 |
| `spacing-5` | `20px` | 中等间距 |
| `spacing-6` | `24px` | 区块间距 |
| `spacing-8` | `32px` | 大间距（页面 padding） |
| `spacing-10` | `40px` | section 间距 |
| `spacing-12` | `48px` | 大 section |
| `spacing-16` | `64px` | 巨大间距（hero） |

> 当前 CSS 中常用值：`4px / 6px / 8px / 10px / 12px / 14px / 16px / 20px / 24px / 28px / 32px / 40px / 48px / 60px / 64px`

---

## 4. 字体（Typography Tokens）

### 4.1 字体家族

```css
--font-sans: -apple-system, BlinkMacSystemFont, "PingFang SC",
             "Microsoft YaHei", "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
--font-mono: "SF Mono", "JetBrains Mono", Consolas,
             "Liberation Mono", monospace;
```

### 4.2 字号与行高

| 用途 | 字号 | 行高 | 字重 | class 示例 |
|------|------|------|------|----------|
| 页面大标题 | `22px` | `1.2` | `700` | `page-title` |
| 区块标题 | `17px` | `1.3` | `600` | `page-title` 默认 |
| 卡片标题 | `15px` | `1.4` | `600` | `card-head h3` |
| 段落 | `13.5px` | `1.5` | `400` | `cell` 默认 |
| 小字 | `12.5px` | `1.5` | `400` | `sub` / `m` |
| 极小 | `11.5px` | `1.4` | `400` | `req` / `t.todo` |
| 数字大字（KPI） | `26px` | `1` | `700` | `stat-value` |
| 巨大数字（金额） | `28px` | `1` | `700` | `rh-amount` |

### 4.3 字重

| Token | 值 | 用途 |
|-------|-----|------|
| normal | `400` | 正文 |
| medium | `500` | 辅助标题 |
| semibold | `600` | 强调 |
| bold | `700` | 大数字、按钮 |

---

## 5. 组件尺寸（Component Sizes）

### 5.1 按钮

| Size | Height | Padding | Font | class |
|------|--------|---------|------|-------|
| sm | `32px` | `0 12px` | `12px` | `btn-sm` |
| md (默认) | `40px` | `0 18px` | `14px` | `btn` |
| lg | `48px` | `0 24px` | `15px` | `btn-lg` |

### 5.2 输入框

| 元素 | Height | Padding | Border |
|------|--------|---------|--------|
| Input | `40px` | `0 12px` | `1.5px var(--color-border)` |
| Select | `40px` | `0 12px` | `1.5px var(--color-border)` |
| Textarea min | `80px` | `10px 12px` | `1.5px` |

### 5.3 侧栏

| 元素 | 宽度 |
|------|------|
| 桌面端 | `248px` |
| 平板端 | `72px`（仅图标） |
| 移动端 | 隐藏为抽屉 |

### 5.4 顶栏

| 元素 | 高度 |
|------|------|
| 顶栏 | `64px` |
| 面包屑 | `12.5px` |
| 页面标题 | `17px` |

### 5.5 内容区

| 元素 | 值 |
|------|-----|
| 页面 padding | `24px 28px 40px` |

---

## 6. 状态色映射

| 场景 | 主色 | 背景 | 文字 | 边框 |
|------|------|------|------|------|
| 成功 / 已通过 | `success` | `success-bg` | `#047857` | — |
| 警告 / 待处理 | `warning` | `warning-bg` | `#B45309` | — |
| 危险 / 失败 | `danger` | `danger-bg` | `#B91C1C` | — |
| 信息 / 进行中 | `info` | `info-bg` | `#0E7490` | — |
| 默认 / 中性 | `#94A3B8` | `#F1F5F9` | `#64748B` | — |

---

## 7. 业务图标（统一用 emoji 字符）

| 模块 | 图标 |
|------|------|
| Dashboard | `▦` |
| 发票识别 | `▤` |
| 发票模板 | `▣` |
| 销售费用 | `◈` |
| 项目管理 | `▥` |
| 合同管理 | `▦` |
| 回款管理 | `▩` |
| 批量上传 | `⇪` |
| 查验真伪 | `✓` |
| 上传 | `⇪` |
| 搜索 | `⌕` |
| 通知 | `🔔` |
| 设置 | `⚙` |
| 用户 | `👤` |
| 文件 | `📄` |
| 金额 | `¥` |
| 时间 | `⏱` |
| 警告 | `⚠` |
| 成功 | `✓` |
| 失败 | `✕` |
| 添加 | `+` |
| 编辑 | `✎` |
| 删除 | `🗑` |
| 复制 | `⎘` |
| 下载 | `⇩` |
| 展开 | `▶` / `▼` |
| 关闭 | `×` |

> **注意**：当前用 emoji 字符（unicode 符号），**不是 SVG**。好处：跨平台一致、无需额外资源。坏处：样式定制受限。
> 后续可考虑替换为 Lucide / Heroicons SVG（`unpkg.com/lucide`）。

---

## 8. 动效（Motion Tokens）

| 用途 | 时长 | 缓动 |
|------|------|------|
| 即时反馈（按钮点击、开关） | `100-150ms` | `ease-out` |
| 简单过渡（hover、tab 切换） | `150-200ms` | `ease-out` |
| 中等过渡（弹窗、抽屉） | `200-300ms` | `cubic-bezier(0, 0, 0.2, 1)` |
| 复杂过渡（页面切换、模态） | `300-500ms` | `cubic-bezier(0, 0, 0.2, 1)` |
| 骨架屏 shimmer | `1.5s` 循环 | `linear` |
| 加载 spinner | `0.8s` 循环 | `linear` |
| 脉冲点（状态指示） | `1.2s` 循环 | `ease` |

---

## 9. 响应式断点（Breakpoints）

| 断点 | 触发条件 | 主要变化 |
|------|---------|---------|
| 桌面 | `≥ 1280px` | 默认 |
| 笔记本 | `1024-1279px` | 侧栏 72px、表格密度略紧 |
| 平板 | `768-1023px` | 详情两栏变一栏、表格横向滚动 |
| 手机 | `< 768px` | 侧栏抽屉化、表格转卡片 |

```css
/* 当前实现 */
@media (max-width: 1024px) { .sidebar { width: 72px; } ... }
@media (max-width: 768px)  { .topbar-left .menu-toggle { display: block; } ... }
```

---

## 10. Z-Index 层级

| 层级 | 值 | 用途 |
|------|------|------|
| 基础 | `0-9` | 默认布局 |
| 顶栏 | `30` | 顶部导航（sticky） |
| 侧栏 | `50` | 侧边栏 |
| 全屏加载 | `90` | 页面 loading |
| 抽屉 / 模态 | `100` | 弹层 |
| Toast | `200` | 顶部通知 |

---

## 11. 在 Tailwind 中使用本 Token

如果后续切到 Tailwind，把这些 token 复制到 `tailwind.config.js`：

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#4F6BFF', hover: '#3D58E8', light: '#E0E6FF' },
        success: '#10B981', 'success-bg': '#D1FAE5',
        warning: '#F59E0B', 'warning-bg': '#FEF3C7',
        danger: '#EF4444', 'danger-bg': '#FEE2E2',
        info: '#06B6D4', 'info-bg': '#CFFAFE',
        'text-primary': '#0F172A',
        'text-secondary': '#475569',
        'text-tertiary': '#94A3B8',
      },
      borderRadius: { sm: '6px', md: '10px', lg: '14px', xl: '20px' },
      boxShadow: {
        'sm': '0 1px 2px 0 rgb(15 23 42 / 0.05)',
        'md': '0 4px 12px -2px rgb(15 23 42 / 0.08)',
        'lg': '0 12px 32px -8px rgb(15 23 42 / 0.12)',
        'glow': '0 8px 32px -4px rgba(79, 107, 255, 0.35)',
      },
    }
  }
}
```

---

## 12. 维护原则

1. **改一处全局生效**：所有颜色 / 间距 / 圆角都通过 token，不写死值
2. **新增颜色先想 token**：先在 token 清单里加，再使用
3. **业务色 vs 语义色分开**：业务色（合同状态）尽量复用语义色（success/warning）
4. **WCAG AA 是底线**：文字对比度 ≥ 4.5:1（普通）、≥ 3:1（大字 18px+）
5. **避免 1px 直角**：圆角是品牌基因，最小 6px

---

## 13. 速查卡片

| 我想要 | 用什么 |
|--------|------|
| 蓝紫渐变按钮 | `class="btn btn-primary"` |
| 红色警告 | `class="tag tag-danger"` |
| 表格行 hover | 默认 `tbody tr:hover` |
| 卡片悬浮效果 | `class="card-pad"` + `class="stat-card"` |
| 大数字展示 | `class="stat-value"` |
| 状态指示器（绿点/红点） | `<span class="s-pill success">` |
| 空状态 | `class="empty-state"` + 子元素 `.ico/.t/.m/.actions` |
| 骨架屏 | `class="skeleton skeleton-line"` |
| 全屏加载 | `class="loading-overlay show"` |
| Toast | `function showToast(msg, type)` |

> **最后**：所有上述 token 都在 `assets/common.css` 头部 `:root` 中定义。改 CSS 变量，所有引用页同步生效。
