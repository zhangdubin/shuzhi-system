# 数智化管理系统 · E2E 测试（Playwright）

> 基于 Playwright（推荐）+ 纯 HTML 设计稿。**前端联调前可以独立跑**，联调后切到真实地址即可。

---

## 1. 快速开始

```bash
# 安装
npm init -y
npm install -D @playwright/test
npx playwright install chromium

# 跑测试
npx playwright test

# UI 模式（推荐开发时用）
npx playwright test --ui

# 生成报告
npx playwright test --reporter=html
```

---

## 2. 配置：`playwright.config.ts`

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8080',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
    { name: 'mobile',   use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'python3 -m http.server 8080',
    cwd: './design',
    port: 8080,
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 3. 公共 fixtures：`e2e/fixtures.ts`

```ts
import { test as base, Page } from '@playwright/test';

export const test = base.extend({
  // 已登录的页面（绕过登录）
  loggedInPage: async ({ page }, use) => {
    // 实际接入后端时改为真实登录
    // await page.goto('/login.html');
    // await page.fill('input[type="text"]', 'admin');
    // await page.fill('input[type="password"]', 'password');
    // await page.click('button:has-text("登 录")');
    // await page.waitForURL('**/dashboard.html');

    // 设计稿阶段直接跳 dashboard
    await page.goto('/dashboard.html');
    await use(page);
  },
});

export const expect = base.expect;
```

---

## 4. 测试用例

### 4.1 登录流程：`e2e/auth.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('登录流程', () => {
  test('登录页所有元素可见', async ({ page }) => {
    await page.goto('/login.html');
    await expect(page.locator('h1, h2, h3').filter({ hasText: '欢迎回来' })).toBeVisible();
    await expect(page.locator('input[placeholder*="手机号"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button:has-text("登 录")')).toBeVisible();
  });

  test('显示密码切换', async ({ page }) => {
    await page.goto('/login.html');
    const pwd = page.locator('input[type="password"]');
    await pwd.fill('123456');
    await page.locator('.eye').click();
    await expect(page.locator('input[type="text"]')).toHaveValue('123456');
  });

  test('记住我勾选状态', async ({ page }) => {
    await page.goto('/login.html');
    const checkbox = page.locator('input[type="checkbox"]');
    await expect(checkbox).toBeChecked();  // 默认勾选
    await checkbox.uncheck();
    await expect(checkbox).not.toBeChecked();
  });

  test('三种 SSO 按钮存在', async ({ page }) => {
    await page.goto('/login.html');
    await expect(page.locator('button:has-text("微信扫码")')).toBeVisible();
    await expect(page.locator('button:has-text("钉钉扫码")')).toBeVisible();
    await expect(page.locator('button:has-text("飞书扫码")')).toBeVisible();
  });

  test('忘记密码链接可点击', async ({ page }) => {
    await page.goto('/login.html');
    await page.click('a:has-text("忘记密码")');
    // 此处可断言跳转到忘记密码页（待开发）
  });
});
```

### 4.2 Dashboard：`e2e/dashboard.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('Dashboard 总览', () => {
  test('所有模块入口可见且可点击', async ({ loggedInPage: page }) => {
    await page.goto('/dashboard.html');
    const modules = ['发票识别', '发票模板', '销售费用', '项目管理', '合同管理', '回款管理'];
    for (const m of modules) {
      const link = page.locator(`.module-card:has-text("${m}")`);
      await expect(link).toBeVisible();
    }
  });

  test('4 个数据卡渲染正确', async ({ loggedInPage: page }) => {
    await page.goto('/dashboard.html');
    const stats = page.locator('.stat-value');
    await expect(stats).toHaveCount(4);
  });

  test('点击发票识别跳转到正确页面', async ({ loggedInPage: page }) => {
    await page.goto('/dashboard.html');
    await page.click('a[href="invoice-ocr.html"]');
    await expect(page).toHaveURL(/invoice-ocr\.html/);
  });
});
```

### 4.3 发票识别：`e2e/invoice-ocr.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('发票识别 - 主页', () => {
  test('子标签切换', async ({ page }) => {
    await page.goto('/invoice-ocr.html');
    await expect(page.locator('.sub-tabs a.active')).toContainText('智能识别');
    await page.click('.sub-tabs a:has-text("批量上传")');
    // 注：当前设计稿是同页 tab，未跳转，后续可能是路由
  });

  test('父菜单"发票识别"可展开/折叠', async ({ page }) => {
    await page.goto('/dashboard.html');
    const parent = page.locator('.nav-parent:has-text("发票识别")');
    await expect(parent).toBeVisible();
    await page.click('text=发票识别 >> nth=0');
    // 展开/折叠状态
  });
});

test.describe('发票识别 - 批量上传', () => {
  test('SSE Demo 进度条自动推进', async ({ page }) => {
    await page.goto('/invoice-ocr-batch.html');

    // 进度条 0.8s/帧递增，等 5 秒
    await page.waitForTimeout(5500);

    // 至少一个进度条 ≥ 100
    const progressBars = page.locator('.progress-mini .fill');
    const count = await progressBars.count();
    expect(count).toBeGreaterThan(0);
  });

  test('批量操作按钮可点击', async ({ page }) => {
    await page.goto('/invoice-ocr-batch.html');
    const bulkSubmit = page.locator('button:has-text("批量提交入账")');
    await expect(bulkSubmit).toBeVisible();
  });
});

test.describe('发票识别 - 识别记录', () => {
  test('8 个状态 tab 全部存在', async ({ page }) => {
    await page.goto('/invoice-ocr-records.html');
    const tabs = ['全部', '待核验', '已识别', '已入账', '已关联合同', '已归档', '已剔除', '识别失败'];
    for (const t of tabs) {
      await expect(page.locator(`.status-tabs a:has-text("${t}")`)).toBeVisible();
    }
  });

  test('高级筛选可展开/折叠', async ({ page }) => {
    await page.goto('/invoice-ocr-records.html');
    await expect(page.locator('.filter-panel')).toBeVisible();
  });
});

test.describe('发票识别 - 查验真伪', () => {
  test('风险告警条显示', async ({ page }) => {
    await page.goto('/invoice-ocr-verify.html');
    await expect(page.locator('.risk-card')).toBeVisible();
  });

  test('查验表单 4 必填字段', async ({ page }) => {
    await page.goto('/invoice-ocr-verify.html');
    const required = page.locator('label:has-text("*")');
    const count = await required.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });
});
```

### 4.4 合同管理：`e2e/contract.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('合同管理', () => {
  test('列表显示 11 行合同', async ({ page }) => {
    await page.goto('/contract.html');
    const rows = page.locator('tbody tr');
    expect(await rows.count()).toBeGreaterThanOrEqual(10);
  });

  test('6 步审批流正确显示', async ({ page }) => {
    await page.goto('/contract-detail.html');
    const steps = page.locator('.fh-step');
    expect(await steps.count()).toBe(6);
  });

  test('合同起草 4 步骤条', async ({ page }) => {
    await page.goto('/contract-create.html');
    const steps = page.locator('.step-item');
    expect(await steps.count()).toBe(4);
  });
});
```

### 4.5 设计系统一致性：`e2e/design-system.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('设计系统', () => {
  test('主色在所有页面一致', async ({ page }) => {
    const pages = ['dashboard.html', 'contract.html', 'project.html'];
    for (const p of pages) {
      await page.goto(`/${p}`);
      const primary = await page.evaluate(() =>
        getComputedStyle(document.documentElement)
          .getPropertyValue('--color-primary').trim()
      );
      expect(primary).toBe('#4F6BFF');
    }
  });

  test('侧栏宽度 248px', async ({ page }) => {
    await page.goto('/dashboard.html');
    const sidebarWidth = await page.locator('.sidebar').evaluate(
      el => getComputedStyle(el).width
    );
    expect(sidebarWidth).toBe('248px');
  });

  test('所有页面都引用 common.css', async ({ page, request }) => {
    const pages = await page.evaluate(() => {
      // 简单实现：扫描所有 link[rel=stylesheet]
      return Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
        .map(l => (l as HTMLLinkElement).href);
    });
    const hasCommon = pages.some(h => h.includes('common.css'));
    expect(hasCommon).toBe(true);
  });
});

test.describe('错误页', () => {
  test('404 页可访问', async ({ page }) => {
    const resp = await page.goto('/error-404.html');
    expect(resp?.status()).toBe(200);
    await expect(page.locator('.err-code')).toContainText('404');
  });

  test('403/500/network 页可访问', async ({ page }) => {
    for (const p of ['error-403', 'error-500', 'error-network']) {
      const resp = await page.goto(`/${p}.html`);
      expect(resp?.status()).toBe(200);
    }
  });
});
```

### 4.6 响应式：`e2e/responsive.spec.ts`

```ts
import { test, expect } from './fixtures';

test.describe('响应式', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('平板端：侧栏收起为 72px', async ({ page }) => {
    await page.goto('/dashboard.html');
    const width = await page.locator('.sidebar').evaluate(
      el => getComputedStyle(el).width
    );
    expect(width).toBe('72px');
  });

  test('平板端：菜单按钮可见', async ({ page }) => {
    await page.goto('/dashboard.html');
    await expect(page.locator('.menu-toggle')).toBeVisible();
  });
});
```

---

## 5. Mock Server（联调前必备）

用 MSW（Mock Service Worker）拦截 API 请求，让测试不依赖后端：

```bash
npm install -D msw
npx msw init public/ --save
```

`e2e/mocks/handlers.ts`：

```ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  // 登录
  http.post('/v1/auth/login', async ({ request }) => {
    const body = await request.json();
    if (body.account === 'admin' && body.password === 'admin') {
      return HttpResponse.json({
        code: 0,
        data: {
          token: 'mock-token-' + Date.now(),
          userInfo: { userId: 'U-001', name: '张明', role: '财务总监' }
        }
      });
    }
    return HttpResponse.json({ code: 1001, message: '账号或密码错误' }, { status: 401 });
  }),

  // Dashboard
  http.post('/v1/dashboard/summary', () => HttpResponse.json({
    code: 0,
    data: {
      greeting: { name: '张明', time: 'afternoon' },
      moduleStats: [
        { module: 'invoice_ocr', name: '发票识别', value: 328, unit: '张' },
        // ...
      ],
      kpi: [
        { key: 'monthRevenue', label: '本月收入', value: 2864000, unit: '元', delta: 12.4 },
        // ...
      ],
      trendChart: { /* ... */ },
      todos: [],
      teamMembers: [],
    }
  })),

  // 发票列表
  http.post('/v1/invoice/ocr/list', () => HttpResponse.json({
    code: 0,
    data: { list: [], total: 0, page: 1, pageSize: 20 }
  })),
];
```

`e2e/mocks/browser.ts`：

```ts
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
```

在每个测试启动前启用：

```ts
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (typeof window !== 'undefined') {
      // 启用 MSW
      import('./mocks/browser').then(({ worker }) => worker.start());
    }
  });
});
```

---

## 6. 跑测试的 npm scripts

```json
{
  "scripts": {
    "test": "playwright test",
    "test:ui": "playwright test --ui",
    "test:chromium": "playwright test --project=chromium",
    "test:mobile": "playwright test --project=mobile",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:report": "playwright show-report",
    "test:update": "playwright test --update-snapshots"
  }
}
```

---

## 7. CI 集成（GitLab CI 示例）

```yaml
e2e:
  stage: test
  image: mcr.microsoft.com/playwright:v1.40.0-jammy
  script:
    - npm ci
    - npx playwright test --project=chromium
  artifacts:
    when: always
    paths:
      - playwright-report/
    expire_in: 30 days
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

---

## 8. 截图基线（视觉回归）

```ts
test('Dashboard 视觉基线', async ({ loggedInPage: page }) => {
  await page.goto('/dashboard.html');
  await expect(page).toHaveScreenshot('dashboard.png', {
    fullPage: true,
    maxDiffPixelRatio: 0.02,
  });
});
```

第一次跑会生成基线图，之后的跑会做差异对比。

---

## 9. 接入真实后端后的改动

```ts
// playwright.config.ts
use: {
  baseURL: process.env.BASE_URL || 'http://localhost:8080',  // ← 改这里
}
```

或运行时指定：
```bash
BASE_URL=https://staging.shuzhi.com npx playwright test
```

---

## 10. 测试覆盖率目标

| 阶段 | 目标 |
|------|------|
| 设计稿阶段（M0） | 元素可见性 + 关键流程可点 |
| 后端联调（M2） | 真实数据流 + 状态流转 |
| 上线前（M4） | 边界 + 错误 + 性能 + 视觉回归 |

建议覆盖率：
- 关键路径（登录、CRUD、审批）= 100%
- 一般页面 = ≥ 70%
- 错误页 = 100%

---

## 11. 常见问题

**Q: 跑测试时页面加载太慢？**
A: `await page.waitForLoadState('networkidle')`，或者用 `page.waitForSelector('h1')` 等待关键元素。

**Q: 跨域导致 API 失败？**
A: 启动 dev server 时加 `--cors` 标志，或在 `page.route()` 拦截。

**Q: 怎么调试单个测试？**
A: `npx playwright test --debug --grep "登录"`，会自动开 inspector。

**Q: 测试数据怎么管理？**
A: 每个测试用 `test.beforeEach` 创建独立数据，测试结束清理。**不要共享数据**。
