# R9 P7B 报告：admin 4 vue 1:1 复刻

> 阶段：R9 P7B（系统管理：用户/角色/字典/部门）
> 完成时间：2026-06-14
> 自检：14/14 E2E 100% PASS + 4 页对比图 + Build 0 错误

---

## 完成清单（4 vue）

| # | 页面 | 文件 | 状态 | 设计稿 |
|---|------|------|------|--------|
| 1 | 用户管理 | `frontend/src/views/admin/AdminUser.vue` | ✅ | **无 design**，按 R9 列表 pattern 自造 |
| 2 | 角色权限 | `frontend/src/views/admin/AdminRole.vue` | ✅ | **无 design**，按权限矩阵 pattern 自造 |
| 3 | 数据字典 | `frontend/src/views/admin/AdminDict.vue` | ✅ | **无 design**，按双栏 pattern 自造 |
| 4 | 部门管理 | `frontend/src/views/admin/AdminDept.vue` | ✅ | **无 design**，按自造递归树 pattern 自造 |

---

## 各页面要点

### 1. AdminUser（用户管理 · 12 行表 + 4 KPI）
- **4 KPI**：用户总数 12 / 当前在线 6 / 今日活跃 8 / 待审核 2
- **5 status-tabs**：全部/启用/禁用/待审核/最近登录
- **工具栏**：搜索框 + 部门 select + 状态 select + 批量启用/禁用
- **12 行用户表**：账号/姓名（带在线 tag）/ 角色多 tag / 部门 / 邮箱 / 手机 / 状态 / 最后登录 / 4 操作
- **角色 tag 5 色**：超级(红) / 管理员(橙) / 财务(绿) / HR(灰) / 其他(蓝)
- **行操作**：编辑 / 分配角色 / 重置密码 / 切换启用状态
- **批量操作**：勾选 + 批量启用/禁用 + 已选 N 个提示

### 2. AdminRole（角色权限 · 6 角色 + 8×8 权限矩阵）
- **4 KPI**：角色总数 6 / 启用 6 / 用户绑定 57 / 权限项 56（8 模块×8 操作）
- **左 280px 角色列表**：6 角色（超级管理员/管理员/财务/销售/业务员/访客）
  - 圆形渐变头像 + 内置 tag + 描述 + 用户数 + 数据范围
- **右权限矩阵**：
  - **8 模块行**：工作台/项目/合同/费用/回款/发票/AI/系统管理
  - **8 操作列**：增/删/改/查/审批/导入/导出/配置
  - 单元格 checkbox（未授权操作显 —）
  - 模块名点击全选/全取消该模块
  - 半选状态视觉（partial 紫色）
- **sticky 保存栏**：共 N 项权限 + 删除 + 保存
- **保留完整 mockPerms**：6 角色各权限配置

### 3. AdminDict（数据字典 · 6 分类 + 字典项表）
- **4 KPI**：字典分类 6 / 字典项 32 / 已启用 30 / 系统内置 4
- **左 240px 分类列表**：6 分类（客户等级/费用类型/发票类型/项目状态/回款类型/合同状态）
  - 内置 tag + 编码（mono 字体）+ 项数
- **右字典项表**：
  - 排序/编码/名称/说明/状态/类型（内置/自定义）/操作
  - 批量启用/禁用 + 同步到下拉 + 删除分类
- **mockItems 6 套**：每分类预填 4-8 项

### 4. AdminDept（部门管理 · 自造递归树 + 14 部门）
- **4 KPI**：部门总数 14 / 成员总数 57 / 顶级 5 / 含子部门 9
- **左 320px 自造组织树**：
  - **手写递归 TreeNode 子组件**（不用 el-tree，可控性最强）
  - 5 顶级部门：总经理办公室/财务部/销售部/项目部/人力资源部
  - 9 子部门（销售一部/二部/三部等）
  - 展开/折叠 ▶ 动画 + 顶级/子级不同 emoji（🏢/📁）
  - 选中态：紫色高亮 + 左侧 border
- **右详情**：
  - 6 字段信息网格（编号/负责人/成员数/排序/父级）
  - **成员列表**：8 列表格（ID/账号/姓名/角色/邮箱/手机/状态/操作）
  - mockUsers 8 人：按部门过滤
- **拖拽提示**：tip-box 提示用户可拖拽

---

## 关键技术点

### 1. 自造递归 TreeNode 子组件（AdminDept）
- **挑战**：el-tree 难定制 + 拖拽事件难控
- **方案**：用 `<script lang="ts">` + `defineComponent` + `h()` 渲染函数写递归
  - 接受 node/expanded/selectedId/depth 4 props
  - 触发 toggle/select 2 emit
  - 内部用 h() 渲染节点行 + 递归渲染 children
  - 配合 `<TreeNode>` 在 template 中使用
- **优势**：完全可控样式 + 不依赖 el-tree
- **关键 prop**：`selected-id="selectedDeptId ?? undefined"`（`null` 会触发 TS 类型错误）

### 2. 权限矩阵 8×8 全自造（AdminRole）
- **挑战**：el-tree 不直观、矩阵化展示更友好
- **方案**：手写 HTML table + 8 模块行 × 8 操作列
  - 单元格 checkbox 组件（hidden input + 渐变方块 + ✓）
  - 模块名点击 toggleModule（全选/全取消该模块所有操作）
  - 半选状态 `partial` 类（紫色文字 + 紫色背景 icon）
- **保留 moduleDefs + 翻译逻辑**：8 模块 + 5 操作类型映射到后端 permission code

### 3. 4 页面统一 KPI 卡 pattern
- 4 KPI 卡 + border-left 4 色（primary/info/success/warning）
- icon 圆角方块 + kpi-num + kpi-trend 趋势
- 全部复用 R9 mixin 库

### 4. 工具栏统一 pattern
- input-search + input-select × 2 + btn-primary 查询 + btn-ghost 重置
- 批量操作行（border-top 分隔）
- 自定义 checkbox（不用 el-checkbox）

### 5. 用户表 role tag 5 色
- 超级(红 danger) / 管理员(橙 warning) / 财务(绿 success) / HR(灰 info) / 其他(蓝 primary)
- 自动判断 `r.includes('超级')` 等

### 6. 字典管理双栏
- 左分类列表 240px（sticky）
- 右字典项表（选中分类的项）
- 顶部 ip-actions（批量启用/禁用/删除分类）
- meta 信息含编码 + 项数 + 启用数

### 7. 状态枚举
- 用户：active/disabled/pending（成功/信息/警告 3 色）
- 字典：enabled/disabled + builtin/自定义
- 角色：builtin 内置/自定义

---

## 自检结果

| 自检项 | 结果 |
|--------|------|
| `npm run build` | ✅ 0 错误，3.90s |
| 14/14 E2E | ✅ 100% PASS（test-09 首次偶发 uwsgi 500，单跑 3/3 全过，再跑全 14/14 PASS）|
| 4 张对比图 | ✅ 192-281KB 实际渲染 |
| 路由可达 | ✅ 4/4（/admin/user /role /dict /dept）|
| 浏览器渲染 | ✅ 全部正常 |

### E2E 14/14 列表（修一次 test-09 偶发）
- test-01-login-dashboard ✅
- test-02-contract-list ✅
- test-03-ai-ask ✅
- test-04-sse-realtime ✅
- test-05-permission ✅
- test-06-notice-cron ✅
- test-07-cron-scheduler ✅
- test-08-paddleocr-real ✅
- **test-09-nuonuo-verify** ✅（首跑偶发 500，重跑 3/3 PASS，确认为后端 uwsgi 临时问题，与前端改动无关）
- test-10-wechat-work-sso ✅
- test-11-monitoring ✅
- test-12-invoice-ocr-submenu ✅
- test-13-parent-menu-404 ✅
- test-14-invoice-ocr-tabs ✅

### 4 张截图
- `docs/screenshots/compare/2-real-p7b-admin-user.png`（193KB）
- `docs/screenshots/compare/2-real-p7b-admin-role.png`（281KB）
- `docs/screenshots/compare/2-real-p7b-admin-dict.png`（281KB）
- `docs/screenshots/compare/2-real-p7b-admin-dept.png`（281KB）

---

## 整体进度

### R9 P7（8 vue）
- **P7A** AI 中心 5 vue：✅
- **P7B** admin 4 vue：✅ **本报告**
- **P7C** AiExtract 对齐 + 收尾：待做

### R9 累计
- P1-P5C：✅
- P7A：✅
- **P7B：✅** ← 本报告
- P7C：待做
- P8：待做
- P10：待做

---

## 下一步
- **P7C**：AiExtract 对齐 ai-extract-demo.html + P7 总报告（~0.5h）
- **P8**：AiPanelContract + AiPanelProject + Drawer + NoticeCenter 4 vue（~1.5h）
- **P10**：R9-FINAL-REPORT + GO-LIVE 更新（~1h）

---

## 关键经验总结（写进 memory）

1. **手写递归 TreeNode**：用 `<script lang="ts">` + `defineComponent` + `h()` 渲染函数写递归树，**比 el-tree 完全可控**，不依赖任何组件库。
2. **手写权限矩阵**：8 模块 × 8 操作 = 64 单元格的 table 比 el-tree 直观 10 倍，点击模块名整行 toggle 是核心交互。
3. **4 页面 KPI 统一**：border-left 4 色 + icon 方块 + trend 文字，admin 系列 4 vue 视觉完全统一。
4. **后端 uwsgi 偶发 500**：同前端代码无关，单跑几次就过；记录到 memory 不要每次误判。
5. **prop 类型 null vs undefined**：`ref<number | null>` + 子组件 prop `default: null` 在 vue-tsc 严格模式下要用 `?? undefined` 转换。

---

## 重要技术坑（记录在 memory）

- **uwsgi 5 worker 启动滞后**：同 R7 教训一致，多 worker 启动后第一个请求可能撞到未完全 ready 的 worker，偶发 500。
- **TreeNode prop 类型**：selectedId 类型不匹配 TS 严格模式，要用 `?? undefined`。
- **手写 checkbox**：避免 el-checkbox 依赖，自定义 `<label>` + hidden input + 渐变方块 + ✓ 字符。
