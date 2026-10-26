# 导入分析学习应用 · 深开鸿 KaihongOS + storytold/photocraft（v0.6.19）

> 延续「大而全 / 小而全，你中有我、我中有你，系统的看待一切」：把外部生态的吸收
> 落到**既有模块的延伸**与**新能力的补点**，不堆孤岛、不与既有重复。

## 一、来源与判定

| 来源 | 定位 | 落入本工具的视角 |
|---|---|---|
| **developer.kaihong.com**（深开鸿） | KaihongOS：基于 OpenHarmony 的分布式 OS 发行版（Stan/Small/Lite/桌面 x86·ARM）；多内核混合部署（集成 UniProton，时延≤3us）、分布式软总线（响应<50ms）、SELinux+可信应用+端到端加密、HDC/HiLog 工具、ArkTS/NAPI | **并入既有 `harmony` 模块**：KaihongOS 是 OpenHarmony 的具体发行版，鸿蒙通用探测（hdc/HiLog/Stage/SysCap/HAP/分布式）为其上层；本任务只做实锤「是不是 KaihongOS、哪一档」 |
| **storytold/photocraft** | 纯 Rust clean-room 复刻 Adobe Photoshop（30.9k★） | **新 `media` 模块**：吸收其「图像管线」视角——本机编解码/色彩能力是图像优化的前提 |
| **github.com/storytold** | 整套纯 Rust clean-room 复刻 Adobe 全家桶（artcraft/lightcraft/filmcraft/vectorcraft/pdfcraft/effectcraft/cadcraft/soundcraft/deckcraft/gridcraft） | 同上：Rust 创意套件是否就位，决定「本机能否跑起 Adobe 级创作/优化工作流」 |

> 注：storytold 系项目为应用层（创作软件），本身不是系统组件。本工具**只吸收其
> 「图像编解码/色彩管理」的诊断维度**，不引入任何应用运行时；Rust 套件检测仅 `shutil.which`，
> 不下载、不运行、不评测其代码。

## 二、落点清单（v0.6.19）

### A. 延伸既有 `native/harmony.py`（不另起平行模块，避免与 OpenHarmony 生态重复）
- 新增 `detect_kaihong()`：只读 `/etc/os-release`（及 `/etc/os-release.d/*`）、
  `/sys/fs/selinux/enforce`、`shutil.which("hdc")`，判定是否为 KaihongOS 及 variant。
- 新增 `kaihong_report()` → `(ok, msg)`：版本 / variant（Stan/Small/Lite/桌面）/ SELinux 挂载态 /
  HDC·HiLog 工具 / 多内核+分布式软总线说明。非 KaihongOS 主机降级为指引。
- 接入 `PROBES`（`("kaihong_report", ...)`）→ 被 `harmony` 子命令与 GUI「鸿蒙」窗口自动展示；
  并写入 `environment_report()` 的 KaihongOS 行。
- 任务：`tasks/harmony.py::harmony_kaihong_distribution`（platform=any / category=maintenance / risk=low）。

### B. 新增 `native/media.py`（图像/媒体编解码与色彩能力）
- `image_capability_report()` → `(ok, msg)`：
  1. 编解码工具链：ImageMagick / identify / exiftool / ffmpeg / libheif / libavif / libwebp / libjxl；
  2. 格式支持矩阵：JPEG/PNG/WebP/HEIC/AVIF/JPEG XL/JPEG 2000/TIFF/BMP/GIF 的读/写；
  3. 色彩管理：ICC 配置目录（`/usr/share/color/icc`）、colord（`colormgr`）；
  4. Rust 创意套件：storytold 系 11 个二进制是否就位。
- 红线：不解码/不转码/不写任何图像文件；仅 `shutil.which` + 目录存在性。
- 任务：`tasks/media.py::media_image_capability`（platform=any / category=maintenance / risk=low）。

### C. 接入面（一致于既有模式）
- `registry.py`：导入并注册 `media` 模块（harmony 已注册）。
- `cli.py`：新增 `kaihong`、`media` 子命令（cmd_kaihong / cmd_media）。
- `gui.py`：顶栏新增「KaihongOS」「图像能力」按钮 + `show_kaihong` / `show_media` 只读窗口。
- `native/__init__.py`：`__all__` 增补 `media`，docstring 注明 v0.6.19。

### D. 系统统筹总览 `native/sysmap.py`（你中有我）
- 探针新增：`KaihongOS 发行版`（harmony.kaihong_report）、`图像编解码能力`（media.image_capability_report）。
- 关联图新增耦合：
  - `KaihongOS 发行版 → 发行版能力`：KaihongOS 是 OpenHarmony 具体发行版，发行版能力探测涵盖其系统栈；
  - `图像编解码能力 → 浏览器引擎`：WebP/AVIF/HEIC 渲染依赖同一编解码底座，图像优化与网页渲染共享解码链路；
  - `图像编解码能力 → 发行版能力`：libheif/libavif/libwebp/libjxl/ImageMagick 由发行版包管理供给，缺失即链路受限。

## 三、红线复核
- 不启停服务、不改配置、不连控制端口写命令、不解码/转码任何图像文件、不连网。
- KaihongOS 识别无需 hdc（hdc 仅在设备侧调试用）；本机判定只读 os-release / SELinux / which。
- 密钥/业务数据：既不读也不印；`identity.secret` 类私钥在任何报告里绝不出现（沿用 v0.6.17 红线）。

## 四、测试（全量随版本回归）
- `tests/test_media.py`（4）：报告形态 / 格式矩阵经 which 点亮 / 缺引擎给提示 / 只读意图。
- `tests/test_harmony_kaihong.py`（4）：非 Kaihong 主机降级 / 正向识别（Stan）/ 报告正向 /
  已纳入 PROBES 与 environment_report。
- `tests/test_sysmap.py`：补断言 v0.6.19 新探针与新耦合已纳入统筹总览。

## 五、版本
- `__init__.py` / `pyproject.toml` / `src/go/main.go` 三处一致：`0.6.19`。
