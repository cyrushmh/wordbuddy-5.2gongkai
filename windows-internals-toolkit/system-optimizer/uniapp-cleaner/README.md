# uni-app 端上清理页（uniapp-cleaner）

本目录是 [system-optimizer](../) 中 **uniapp 目标端**「端上 storage 清理」任务的**真实落地页**，
对应 `sysweeper` 里的 `uniapp_storage` / `uniapp_h5_storage` 两项任务。

上一轮这两项任务还是「仅指引（manual）」——告诉你该调哪个 API；这一轮直接给了一份可运行的
`.vue` 页面，把它放进任意 uni-app 工程即可作为「清理缓存」入口使用。

设计原则与整个 system-optimizer 一致：**默认不清理、必须先确认**。

## 页面做了什么

`pages/cleanup/cleanup.vue`：

1. `onMounted` 时调用 `uni.getSystemInfoSync()` 展示运行端（android / ios / h5 / 微信小程序）与系统版本。
2. 调用 `uni.getStorageInfoSync()` 统计「已用 / 上限」与所有 key，并粗略估算每个 key 占用。
3. 用户可**勾选**若干 key，或一键「清空全部」：
   - 清空全部 → `uni.clearStorageSync()`
   - 清理选中 → 逐个 `uni.removeStorageSync(key)`
4. 两种操作都先经 **`uni.showModal` 二次确认**（明确告知会清掉登录态/草稿、不可恢复），确认后才执行。
5. 执行后刷新统计，并展示一份**清理前后对比报告**（KB 级）。
6. 「**清理端上缓存（H5/App）**」按钮：先 `detectRuntime()` 识别运行端，再分支清理**运行期缓存**：
   - **H5**（浏览器）：走 Cache API —— `window.caches.keys()` 列出、`window.caches.delete(k)` 逐个删除 Service Worker 缓存（需 https/localhost 安全上下文）。
   - **App**（5+ 引擎）：走 `plus.cache.clear('/', success, error)` 清应用运行期缓存（图片/离线包等），经 `showModal` 确认，不删登录态。
   - 小程序/未知端：无 Cache API，引导用上方 storage 清理。
   - 注意：这是「应用缓存」，与第 2/3 步的 storage 清理**互相独立**——storage 清键值存储（含登录态），这里只清运行期缓存。

## 用到的 API（与 data/uniapp_api.json 对照）

| 页面内调用 | 所属分组 | 标准出处 |
|---|---|---|
| `uni.getSystemInfoSync()` | system（系统与设备信息） | W3C Device APIs |
| `uni.getStorageInfoSync()` | storage（本地存储） | HTML5 Web Storage（W3C） |
| `uni.clearStorageSync()` | storage | HTML5 Web Storage（W3C） |
| `uni.removeStorageSync(key)` | storage | HTML5 Web Storage（W3C） |
| `uni.showModal()` | ui（界面与交互） | uni-app 官方 API |
| `window.caches.keys/delete`（仅 H5） | fs（运行期缓存） | W3C Cache API / Service Worker |
| `plus.cache.clear`（仅 App） | fs（运行期缓存） | HTML5+ (5+ App) 规范 |

> 各端配额不同：微信小程序 storage 约 10MB，App 受系统配额限制，H5 走浏览器 Web Storage。
> 详见 `../src/python/sysweeper/data/uniapp_api.json`。

## 如何运行

这是一个**最小可运行**的 uni-app 工程，两种方式：

### 方式 A：作为独立工程运行
1. 用 [HBuilderX](https://www.dcloud.io/hbuilderx.html) 打开本目录（或 CLI：`npx @dcloudio/vite-plugin-uni`）
2. 运行到：内置浏览器（H5）/ 微信开发者工具（小程序）/ 真机（App）
3. 默认进入 `pages/cleanup/cleanup`

### 方式 B：并入已有 uni-app 工程
1. 把 `pages/cleanup/cleanup.vue` 复制到你的工程的 `pages/cleanup/` 下
2. 在 `pages.json` 的 `pages` 数组里登记该路由
3. 在需要的地方 `uni.navigateTo({ url: '/pages/cleanup/cleanup' })`

## 与 system-optimizer 的分工

| 层 | 位置 | 作用 |
|---|---|---|
| 工程侧清理（自动） | `sysweeper tasks/uniapp.py` 的 `uniapp_dist` / `uniapp_build_cache` / `uniapp_dep_cache` | 开发机上编译产物 / 构建缓存 / 依赖缓存，可 `clean --apply` 自动执行 |
| 端上清理（需确认） | **本目录页面** | App / 小程序 / H5 端 storage，必须用户点确认才清 |
| API 清单（参考） | `data/uniapp_api.json` | 6 组 API + 各端支持情况 + 标准出处 |

工程侧用 Python 标准库在开发机跑；端上用 uni-app 页面在设备内跑——各司其职，互不耦合。
