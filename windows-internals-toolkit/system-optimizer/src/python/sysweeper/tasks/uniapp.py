"""uni-app（跨端框架）目标端的清理与优化任务。

uni-app 不是操作系统，而是「一套代码编译到 App / H5 / 各小程序」的跨端框架，
因此它作为一个**目标端（platform="uniapp"）**存在，需手动指定：

    python -m sysweeper list --platform uniapp --version 4
    python -m sysweeper uniapp            # 查看 uni-app 需要的 API 清单 + 任务

任务分两类：
1. 工程侧（开发机）：编译产物、构建缓存、依赖缓存、HBuilderX 缓存 —— 可自动执行
2. 端上（App/小程序/H5）：storage、应用缓存 —— 属隐私/中风险，仅给指引 + 需确认

API 清单见 data/uniapp_api.json（含各端支持情况与标准出处）。
"""

from __future__ import annotations

from ..models import Action, Task

TASKS = [
    Task(
        id="uniapp_dist",
        platform="uniapp",
        title="清理编译产物（unpackage/dist、build）",
        category="cleanup",
        risk="low",
        actions=[
            Action(
                "shell",
                'rm -rf unpackage/dist unpackage/build dist build 2>/dev/null; echo "已清理编译产物"',
                "删除 uni-app 发行/运行输出目录（可重新生成）",
            )
        ],
        desc="uni-app 发行（发行到 App/H5/小程序）后产生的编译输出目录，删除不影响源码。",
        notes=[
            "删除后需重新点击「发行」或「运行」才会重新生成；CI 环境可安全清理以节省空间。",
            "工程目录约定见 API 清单的 fs 组（unpackage/ dist/ build/）。",
        ],
    ),
    Task(
        id="uniapp_build_cache",
        platform="uniapp",
        title="清理构建缓存（node_modules/.cache、.vite）",
        category="cleanup",
        risk="low",
        actions=[
            Action(
                "shell",
                'rm -rf node_modules/.cache node_modules/.vite .vite 2>/dev/null; echo "已清理构建缓存"',
                "删除 Vite/webpack 构建缓存（下次构建自动重建）",
            )
        ],
        desc="Vite / webpack 的构建缓存，删除后首次构建稍慢，可安全重建。",
        notes=["属于开发机缓存，不影响已发布的包；大规模项目可显著释放空间。"],
    ),
    Task(
        id="uniapp_dep_cache",
        platform="uniapp",
        title="校验/清理依赖缓存（npm / pnpm / yarn）",
        category="cleanup",
        risk="low",
        actions=[
            Action(
                "shell",
                'if command -v npm >/dev/null; then npm cache verify; fi; '
                'if command -v pnpm >/dev/null; then pnpm store prune; fi',
                "用包管理器自带命令校验与瘦身依赖缓存（不强求安装）",
            )
        ],
        desc="uni-app 工程依赖（vue、@dcloudio 等）下载的本地缓存，可校验瘦身。",
        notes=[
            "无 npm/pnpm 时自动跳过——不强求安装任何包管理器。",
            "`pnpm store prune` 会删除未被任何项目引用的包；`npm cache verify` 仅整理校验。",
        ],
    ),
    Task(
        id="uniapp_hbuilderx",
        platform="uniapp",
        title="清理 HBuilderX 编辑器缓存与日志",
        category="maintenance",
        risk="medium",
        actions=[
            Action(
                "manual",
                "在 HBuilderX 中：帮助 → 清理缓存；或手动删除 ~/.HBuilderX/.cache 与 logs 目录",
                "清理 HBuilderX 缓存与日志（需先关闭编辑器）",
            )
        ],
        desc="HBuilderX 的插件缓存、运行日志会随时间增长，影响启动与构建速度。",
        caveats=["请先关闭 HBuilderX 再清理，避免正在写入的文件被删导致配置丢失。"],
        notes=["若使用 CLI（如 @dcloudio/uvm）而非 HBuilderX，可跳过本项。"],
    ),
    Task(
        id="uniapp_storage",
        platform="uniapp",
        title="清理端上 storage（uni.clearStorageSync）",
        category="privacy",
        risk="medium",
        actions=[
            Action(
                "manual",
                "在应用内提供「清理缓存」入口：调用 uni.clearStorageSync() / plus.cache.clear()；"
                "或用 uni.getStorageInfoSync() 先展示占用再让用户确认。"
                "已提供真实落地页：见 uniapp-cleaner/pages/cleanup/cleanup.vue（含 showModal 二次确认）",
                "清空端上键值对存储与应用缓存（需用户确认）",
            )
        ],
        desc="App / 小程序 / H5 端上的本地存储（含登录态、表单草稿、缓存数据）。",
        caveats=[
            "清空 storage 会一并清掉登录态与本地草稿，务必让用户知情并确认后再执行。",
            "各端容量上限不同：微信小程序约 10MB，App 端受系统配额限制。",
        ],
        notes=[
            "推荐做法：先用 uni.getStorageInfoSync() 展示已用/上限，再由用户点「清理」。",
            "API 参考：data/uniapp_api.json 的 storage 组（W3C Web Storage）。",
        ],
    ),
    Task(
        id="uniapp_h5_storage",
        platform="uniapp",
        title="清理 H5 端 localStorage / CacheStorage",
        category="privacy",
        risk="medium",
        actions=[
            Action(
                "manual",
                "H5 端在浏览器设置中清除站点数据；或在应用内调用 "
                "localStorage.clear() 与 caches.keys().then(ks=>ks.forEach(k=>caches.delete(k)))",
                "清理 H5 端 Web 存储与 Cache Storage",
            )
        ],
        desc="H5 端落在浏览器/内核的存储：localStorage、sessionStorage、Service Worker 缓存。",
        caveats=["若启用了 Service Worker 离线缓存，清理后首次访问需重新联网加载。"],
        notes=["API 参考：W3C Web Storage / Service Worker（CacheStorage）。"],
    ),
    Task(
        id="uniapp_deps_report",
        platform="uniapp",
        title="依赖与体积报告（辅助定位可瘦身项）",
        category="maintenance",
        risk="low",
        actions=[
            Action(
                "python",
                "扫描工程目录：统计 node_modules、unpackage、静态资源（static/）体积，"
                "列出体积最大的依赖与未使用资源（只读分析，不删除）",
                "只读分析工程体积构成（Python 标准库实现，零依赖）",
            )
        ],
        desc="uni-app 包体积直接影响 App 安装体积与小程序主包限制，先量化再优化。",
        notes=[
            "小程序主包/分包有体积限制（如微信小程序主包 2MB），建议把大资源放分包或 CDN。",
            "本任务只读分析，不删除任何文件，可放心执行。",
        ],
    ),
    Task(
        id="uniapp_code_split",
        platform="uniapp",
        title="分包与路由级懒加载（跨端优化指引）",
        category="optimize",
        risk="low",
        desc="通过 pages.json 分包（subPackages）与组件按需引入，降低首屏/主包体积，提升各端启动速度。",
        actions=[
            Action(
                "manual",
                "在 pages.json 配置 subPackages 把非首屏页面拆到分包；图片/字体走 CDN；"
                "组件用 easycom 按需或动态 import。参考 uni-app 官方「分包加载」与「性能优化」文档。",
                "按端拆分代码与资源（需开发者实施）",
            )
        ],
        notes=[
            "API 参考：data/uniapp_api.json 的 fs 组（unpackage/dist 可清理）与 system 组。",
            "属工程侧优化指引，不影响已发布包；实施后代重新构建生效。",
        ],
    ),

    Task(
        id="uniapp_image_compress",
        platform="uniapp",
        title="静态图片压缩与 WebP 化",
        category="optimize",
        risk="low",
        desc="压缩工程内静态图片并转 WebP，降低包体与首屏加载体积。",
        actions=[Action("manual",
                        "将 static 下图片批量压缩（tinypng / squoosh），"
                        "并在支持的端（H5、App、微信小程序）改用 webp 格式",
                        "压缩图片并转 WebP（构建前手动处理）")],
        standards=["[国际] W3C WebP / W3C 图片格式规范",
                   "[国际] W3C WCAG 2.2（图片替代文本无障碍）"],
        notes=["小程序端需确认 webp 支持版本；不支持时退回压缩后的 png/jpg。",
               "图片体积通常是 H5 首屏的最大占比，压缩收益明显。"],
        caveats=["转换前保留原图备份，避免透明通道/动画帧丢失。"],
    ),

]
