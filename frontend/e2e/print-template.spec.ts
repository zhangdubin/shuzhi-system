/**
 * UDPE 打印模板 — E2E 测试
 *
 * 覆盖关键流程：
 *  1. 模板列表页加载
 *  2. 创建模板
 *  3. 模板编辑器
 *  4. 模板预览
 *  5. 模板发布/归档
 *  6. Excel 导入
 *  7. 删除模板
 */
import { test, expect, type Page } from '@playwright/test'

// 登录辅助函数
async function login(page: Page) {
  await page.goto('/login')
  await page.fill('input[placeholder*="账号"]', 'admin')
  await page.fill('input[placeholder*="密码"]', 'admin123')
  await page.click('button:has-text("登录")')
  await page.waitForURL('**/dashboard', { timeout: 10_000 })
}

test.describe('打印模板管理', () => {

  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('模板列表页加载正常', async ({ page }) => {
    await page.goto('/admin/print-template')
    // 等待列表加载
    await expect(page.locator('text=模板总数')).toBeVisible({ timeout: 10_000 })
    // KPI 卡片应该存在
    await expect(page.locator('text=已发布')).toBeVisible()
    await expect(page.locator('text=草稿')).toBeVisible()
    // 列表应该有数据
    await page.waitForTimeout(1000)
    const rows = page.locator('.el-table__row')
    const count = await rows.count()
    expect(count).toBeGreaterThan(0)
  })

  test('搜索过滤模板', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 搜索框输入关键词
    const searchInput = page.locator('input[placeholder*="搜索"]')
    if (await searchInput.isVisible()) {
      await searchInput.fill('合同')
      await page.waitForTimeout(500)
      // 检查过滤结果
      const rows = page.locator('.el-table__row')
      const count = await rows.count()
      expect(count).toBeGreaterThan(0)
    }
  })

  test('创建新模板', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 点击创建按钮
    const createBtn = page.locator('button:has-text("新建模板")')
    if (await createBtn.isVisible()) {
      await createBtn.click()
      // 应弹出对话框或跳转到编辑器
      await page.waitForTimeout(1000)
      const dialog = page.locator('.el-dialog')
      const editorPage = page.url().includes('editor')
      expect(await dialog.isVisible() || editorPage).toBeTruthy()
    }
  })

  test('模板编辑器加载', async ({ page }) => {
    await page.goto('/admin/print-template/editor/1')
    // 等待编辑器加载
    await page.waitForTimeout(2000)
    // 应该有 JSON 编辑区域或可视化设计器
    const hasJsonArea = await page.locator('textarea').isVisible()
    const hasCanvas = await page.locator('.visual-canvas').isVisible()
    const hasEditor = hasJsonArea || hasCanvas
    expect(hasEditor).toBeTruthy()
  })

  test('模板预览功能', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 找到预览按钮并点击
    const previewBtn = page.locator('button:has-text("预览")').first()
    if (await previewBtn.isVisible()) {
      await previewBtn.click()
      await page.waitForTimeout(2000)
      // 应弹出预览对话框
      const dialog = page.locator('.el-dialog')
      await expect(dialog).toBeVisible()
    }
  })

  test('模板发布与归档', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 找到草稿状态的模板
    const draftTag = page.locator('.el-tag:has-text("草稿")').first()
    if (await draftTag.isVisible()) {
      // 找到同行的发布按钮
      const row = draftTag.locator('xpath=ancestor::tr')
      const publishBtn = row.locator('button:has-text("发布")')
      if (await publishBtn.isVisible()) {
        await publishBtn.click()
        // 确认对话框
        const confirmBtn = page.locator('.el-message-box__btns button:has-text("确定")')
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click()
        }
        await page.waitForTimeout(1000)
        // 检查状态变为已发布
        await expect(page.locator('.el-tag:has-text("已发布")').first()).toBeVisible()
      }
    }
  })

  test('打印日志页加载', async ({ page }) => {
    await page.goto('/admin/print-log')
    await page.waitForTimeout(2000)
    // 页面应该有表格或日志数据
    const hasTable = await page.locator('.el-table').isVisible()
    const hasDashboard = await page.locator('text=打印统计').isVisible()
    expect(hasTable || hasDashboard).toBeTruthy()
  })

  test('Excel 导入对话框', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 点击 Excel 导入按钮
    const importBtn = page.locator('button:has-text("Excel")')
    if (await importBtn.isVisible()) {
      await importBtn.click()
      await page.waitForTimeout(500)
      // 应弹出导入对话框
      await expect(page.locator('.el-dialog')).toBeVisible()
    }
  })

  test('模板卡片视图', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 切换到卡片视图
    const gridBtn = page.locator('button[title*="卡片"], button[title*="网格"]')
    if (await gridBtn.isVisible()) {
      await gridBtn.click()
      await page.waitForTimeout(500)
      // 应该显示卡片
      const cards = page.locator('.el-card')
      const count = await cards.count()
      expect(count).toBeGreaterThan(0)
    }
  })

  test('删除草稿模板', async ({ page }) => {
    await page.goto('/admin/print-template')
    await page.waitForTimeout(1000)

    // 找到草稿状态的删除按钮
    const draftTag = page.locator('.el-tag:has-text("草稿")').first()
    if (await draftTag.isVisible()) {
      const row = draftTag.locator('xpath=ancestor::tr')
      const deleteBtn = row.locator('button:has-text("删除")')
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click()
        // 确认删除
        const confirmBtn = page.locator('.el-message-box__btns button:has-text("确定")')
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click()
          await page.waitForTimeout(1000)
          // 应该有成功提示
          await expect(page.locator('.el-message--success')).toBeVisible()
        }
      }
    }
  })
})
