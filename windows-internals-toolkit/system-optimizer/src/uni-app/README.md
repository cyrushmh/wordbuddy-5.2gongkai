# sysweeper · uni-app 移动端（Vue 3）

本目录是 sysweeper 的 **uni-app 跨平台前端**，与现有「Deno 本机 Web 控制台」和「单文件静态报告查看器」同源、同协议、同只读承诺。

- 技术栈：uni-app（Vue 3 `<script setup>`），零额外运行时依赖
- 覆盖端：H5（浏览器）/ App（iOS·Android）/ 微信小程序（mp-weixin）一套代码
- 文档参照：[uni-app 官方文档](https://hx.dcloud.net.cn/)

## 三个页面

| 页面 | 路径 | 作用 |
|------|------|------|
| 总览 | `pages/cockpit/cockpit` | 实时拉取本机只读诊断：宿主信息、诊断状态计数、量化评分、系统统筹总览 |
| 报告 | `pages/report/report` | 粘贴 / 载入 sysweeper 快照 JSON，渲染全部段落（含内核 / OpenJDK 只读体检） |
| 档位 | `pages/profiles/profiles` | 任务档位清单 + 量化评分 + 一键跑内核 / OpenJDK 只读体检 |

## 怎么跑

**方式一：HBuilderX（推荐）**
1. 用 HBuilderX 打开本目录（`src/uni-app`）作为 uni-app 项目；
2. 顶部菜单「运行」→ 选 H5 / 手机真机 / 微信开发者工具；
3. 手机真机调试需手机与电脑同一局域网。

**方式二：命令行（cli）**
```bash
npm i -g @vue/cli @dcloudio/uvm  # 首次
cd src/uni-app
npm i
npm run dev:h5          # H5
npm run dev:app-plus    # App（需 HBuilderX 或云端打包）
npm run dev:mp-weixin   # 微信小程序（需微信开发者工具 + 填 appid）
```

## 对接本机控制台

所有实时数据来自 `sysweeper web` 控制台（Deno 外壳 + Python 逻辑层），协议是
`POST {BASE_URL}/api` → `{ action, params, source }` → `{ ok, data }`。

- 默认地址 `http://127.0.0.1:8787`（见 `common/config.js`）。
- **手机真机**要访问时，把 `BASE_URL` 改成电脑局域网 IP（如 `http://192.168.1.20:8787`），
  并让控制台监听外部网卡：
  ```bash
  deno run --allow-net --allow-read --allow-run src/deno/console.ts --host 0.0.0.0
  ```
  （控制台默认只监听 `127.0.0.1`，外部访问不到。）

## 只读承诺（与控制台一致）

- 本前端**只读取**本机 `sysweeper web` 产出的诊断结果，**不触发任何写系统动作**；
- 「报告」页用粘贴 JSON 模式，数据不出机器也能看，**全端通用**；
- 实时模式的可用范围：App / 小程序端正常；**H5（浏览器）跨域访问会被 CORS 拦截**
  （控制台 `/api` 未开 CORS），H5 请用「报告」页的粘贴 JSON 模式，或把页面托管到
  控制台同源地址。

## 目录

```
src/uni-app/
├── manifest.json        # 应用配置（名称/版本/各端开关）
├── pages.json           # 路由
├── main.js / App.vue    # 入口
├── uni.scss             # 深色主题与通用类
├── common/
│   ├── config.js        # BASE_URL 等可改配置
│   ├── api.js           # /api 调用封装（串行化，与控制台桥一致）
│   ├── format.js        # 状态配色 / 百分比 / 数值格式化
│   └── report.js        # 快照 JSON → 可渲染结构（对齐 report_viewer.ts）
├── components/TopNav.vue# 三页通用顶栏
└── pages/{cockpit,report,profiles}/
```
