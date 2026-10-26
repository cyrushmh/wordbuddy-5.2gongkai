# 小说网站（novel-website）

`wordbuddy-github` 总仓库下的子项目之一：一个**轻量、零依赖**的小说网站骨架，用于浏览 / 阅读小说章节。

## 技术选型（稳定版 / LTS）

- **Node.js LTS（>= 18）** 仅用于本地预览，使用内置 `http` 模块，**不引入任何第三方依赖**，无需 `npm install`。
- 前端为纯 **HTML + CSS + 原生 JS**，章节内容用 **Markdown** 存放，前端实时渲染。
- 零依赖 + 标记语言内容，保证「构建可复现、永不过期」，与总仓库的稳定版策略一致。

## 目录结构

```
novel-website/
├── README.md
├── package.json          # 仅声明 engines 与 start 脚本，无第三方依赖
├── server.js             # 零依赖静态服务器（Node 内置 http）
├── public/               # 前端静态资源
│   ├── index.html        # 书库首页（列出 data/novels.json 中的作品）
│   ├── reader.html       # 章节阅读页（?novel=<id>&chapter=<序号>）
│   └── assets/
│       ├── style.css
│       ├── app.js        # 首页：拉取书库并渲染卡片
│       └── reader.js     # 阅读页：加载章节 Markdown 并渲染 + 翻页
└── data/
    ├── novels.json       # 书库元数据（作品 + 章节清单）
    └── sample/           # 示例作品（Markdown 章节）
```

## 本地运行

```bash
cd novel-website
node server.js            # 默认 http://localhost:3000
```

浏览器打开 http://localhost:3000 即可浏览书库、点开示例作品阅读。

## 如何新增一部小说

1. 在 `data/` 下新建 `<书名>/` 目录，放入若干 `章节名.md`。
2. 在 `data/novels.json` 中登记该作品及其章节顺序（`file` 填相对 `data/` 的路径，如 `sample/绪论.md`）。
3. 刷新首页即可看到。

## 搜索

- 首页顶部搜索框：按**书名 / 作者 / 简介**即时筛选书架。
- 顶部「搜索」进入 `search.html`，做**全文搜索**：拉取所有章节 Markdown，匹配后给出带高亮 `<mark>` 的片段与跳转链接（直达对应章节）。支持 `search.html?q=关键词` 直达。

## 发布 / 导出

`publish.js`（零依赖 Node 脚本）把一部小说编译为**单文件、自包含 HTML**，便于分享或静态托管：

```bash
cd novel-website
node publish.js            # 发布 novels.json 中的第一部
node publish.js <id>       # 发布指定作品（如 node publish.js sample）
```

产物写入 `dist/<id>.html`（含目录与正文，CSS 内联）。`dist/` 已被忽略，不进仓库，属于本地构建产物。

## 同步到 GitHub

本子项目随总仓库一起同步：在仓库根目录运行

```bash
python3 sync_to_github.py <你的 GitHub PAT>
```
