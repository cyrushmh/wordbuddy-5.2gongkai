"""鸿蒙（HarmonyOS / OpenHarmony）与 uni-app 鸿蒙端的核对、清理与优化任务。

「触类旁通、举一反三」：与内核、桌面、其余系统软件同一模式——**按鸿蒙自身的协议与接口**
核对与优化，每一项的标准依据指向鸿蒙（或 uni-app）官方文档（见 data/harmony_docs.json）：

- Stage 模型      : UIAbility / ExtensionAbility 生命周期 + Want 意图
- SystemCapability: @ohos.* 分层 API + canIUse() 运行期判定
- HiLog           : 域(domain) / 标签(tag) / 级别(level)
- hdc             : HarmonyOS Device Connector（对标 adb，命令不兼容）
- 应用包          : HAP / HSP / HAR + ohpm / Hvigor 构建
- 分布式          : @ohos.rpc + 分布式软总线
- uni-app 鸿蒙端  : HBuilderX 4.27+ 起支持，仅 vue3（DCloud 官方文档）

未装 hdc / 非鸿蒙工程目录时，原生探测自动降级为「指引」，不强求安装。
清理类动作默认需 --apply 才落地，且只清「可重建的生成目录」。

注：鸿蒙无 systemd 那样的 `journalctl --vacuum` 官方回收接口（日志由系统按配额轮转，
且 /data/log/hilog 为编码 gz），故日志项一律只读核对，不提供删除动作。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

STAGE = "[国际] 鸿蒙 Stage 应用模型文档（UIAbility / ExtensionAbility / Want / module.json5）"
SYSCAP = "[国际] 鸿蒙 SystemCapability 文档（@ohos.* 分层 API + canIUse() 能力判定）"
HILOG = "[国际] 鸿蒙 HiLog 文档（域/标签/级别 + hilogtool 解析，developer.huawei.com / device.harmonyos.com）"
HDC = "[国际] 鸿蒙 hdc 工具文档（HarmonyOS Device Connector：list targets / shell / file / install）"
PKG = "[国际] 鸿蒙应用包文档（HAP / HSP / HAR 结构 + ohpm / Hvigor 构建）"
IPC = "[国际] 鸿蒙 IPC/RPC 与分布式软总线文档（@ohos.rpc / @ohos.distributedDeviceManager）"
UNIAPP = "[国际] uni-app 鸿蒙端文档（uniapp.dcloud.net.cn/tutorial/harmony/：HBuilderX 4.27+，仅 vue3）"


TASKS = [
    Task(
        id="harmony_hdc_report",
        platform="harmony",
        title="鸿蒙设备连接核对（hdc list targets）",
        category="maintenance",
        risk="low",
        desc="用 hdc 官方接口核对已连接的鸿蒙设备，作为后续设备侧操作的前提。",
        actions=[
            N("harmony.hdc_report", "列出已连接鸿蒙设备（只读，hdc list targets）"),
        ],
        standards=[HDC],
        notes=["参考 hdc（HarmonyOS Device Connector）文档：hdc 为 client-server-daemon "
               "三端架构，支持 Windows/Linux/macOS。",
               "hdc 与 adb 命令不通用（adb devices → hdc list targets），勿混用两套工具。"],
        caveats=["仅读取设备列表，不安装/不卸载应用；未装 hdc 时自动降级为指引。"],
    ),
    Task(
        id="harmony_device_report",
        platform="harmony",
        title="鸿蒙设备信息核对（型号 / 版本 / 存储）",
        category="maintenance",
        risk="low",
        desc="经 hdc 官方接口读取设备型号、系统/API 版本与 /data 存储占用，作为优化前基线。",
        actions=[
            N("harmony.device_report", "读取设备型号/版本/存储（只读，param get + df）"),
        ],
        standards=[HDC],
        notes=["参考 hdc 文档：设备侧参数经 `hdc shell param get <name>` 只读查询；"
               "型号 const.product.model、API 版本 const.ohos.apiversion。",
               "存储占用用 `hdc shell df -h /data`；与 Android 的 getprop 不同，勿混用。"],
        caveats=["仅读取，不改任何设备参数；无设备或未装 hdc 时降级为指引。"],
    ),
    Task(
        id="harmony_app_report",
        platform="harmony",
        title="鸿蒙已安装应用核对（bm dump -a）",
        category="maintenance",
        risk="low",
        desc="用 Bundle Manager 列出设备已安装应用，便于核对冗余应用与空间占用。",
        actions=[
            N("harmony.app_report", "列出设备已安装应用（只读 bm dump -a，不卸载）"),
        ],
        standards=[PKG],
        notes=["参考应用包文档：鸿蒙以 Bundle Manager（bm）管理已安装 HAP；"
               "`bm dump -a` 可列出全部 bundleName。",
               "列出的应用仅供核对，卸载需走 `bm uninstall` 或系统设置（本任务不执行）。"],
        caveats=["仅只读列出；部分系统版本需授权否则 bm dump 无返回，此时降级为指引。"],
    ),
    Task(
        id="harmony_hilog_report",
        platform="harmony",
        title="HiLog 日志核对（域 / 标签 / 级别）",
        category="maintenance",
        risk="low",
        desc="按 HiLog 三维协议核对设备日志；只读，且明确不做删除（鸿蒙无官方 vacuum 接口）。",
        actions=[
            N("harmony.hilog_report", "核对设备 /data/log/hilog 日志（只读，不删除）"),
        ],
        standards=[HILOG],
        notes=["参考 HiLog 文档：级别 D/I/W/E/F、域（应用层常用 0xD000）、标签 tag；"
               "排障用 `hdc shell hilog -L E`（只看 Error 及以上）或 `-T <tag>` 过滤。",
               "设备持久日志为编码后的 gz 二进制，直接解压看不到明文，须用 hilogtool 解析。"],
        caveats=["鸿蒙未提供类似 journalctl --vacuum 的官方回收接口（日志由系统按配额轮转），"
                 "直接删 /data/log/hilog 会破坏轮转——本任务只读，绝不删除。"],
    ),
    Task(
        id="harmony_stage_model",
        platform="harmony",
        title="Stage 应用模型核对（UIAbility / module.json5）",
        category="maintenance",
        risk="low",
        desc="核对鸿蒙工程的 Stage 模型配置（AppScope / module.json5），确认组件声明规范。",
        actions=[
            N("harmony.stage_model_report", "核对 Stage 模型工程配置（只读）"),
        ],
        standards=[STAGE],
        notes=["参考 Stage 模型文档：一个 HAP 对应一个 AbilityStage 进程容器；"
               "UIAbility 承载界面、ExtensionAbility 承载无界面扩展，声明于 module.json5。",
               "组件间经 Want（显式/隐式）调度；生命周期走官方 UIAbility 接口。"],
        caveats=["仅读取工程配置；勿在 UIAbility 之外自管进程（系统按 Stage 模型统一调度）。"],
    ),
    Task(
        id="harmony_syscap_report",
        platform="harmony",
        title="系统能力核对（SysCap / canIUse）",
        category="optimize",
        risk="low",
        desc="核对 SysCap 能力声明，并提示用 canIUse() 做运行期判定，避免低能力设备崩溃。",
        actions=[
            N("harmony.syscap_report", "核对 SysCap 声明与 canIUse 判定（只读）"),
        ],
        standards=[SYSCAP],
        notes=["参考 SystemCapability 文档：构建期在 syscap.json / module.json5 声明依赖能力，"
               "运行期用 canIUse() 判定后再调用 @ohos.* API。",
               "低能力设备（如穿戴）上缺失能力要能优雅降级，而不是 try/catch 兜底。"],
        caveats=["仅核对声明与提示，不改工程配置；能力声明过宽会导致应用商店分发范围受限。"],
    ),
    Task(
        id="harmony_package_report",
        platform="harmony",
        title="应用包与构建产物占用核对（HAP / Hvigor）",
        category="maintenance",
        risk="low",
        desc="估算鸿蒙工程可重建生成目录（build / .hvigor / oh_modules）的占用，生成清理前依据。",
        actions=[
            N("harmony.package_report", "估算构建产物占用（只读，不删除）"),
        ],
        standards=[PKG],
        notes=["参考应用包文档：HAP 为部署单元，HSP/HAR 复用代码；三方库由 ohpm 管理、"
               "产物由 Hvigor 构建，生成目录均可重建。"],
        caveats=["仅估算占用，不删除任何文件；真正回收请用 harmony_package_cache（需 --apply）。"],
    ),
    Task(
        id="harmony_package_cache",
        platform="harmony",
        title="清理鸿蒙工程构建产物（可重建生成目录）",
        category="cleanup",
        risk="low",
        desc="清理鸿蒙工程下可重建的生成目录（build/、.hvigor/、.preview/），回收磁盘空间。",
        actions=[
            S('rm -rf ./build ./.hvigor ./.preview 2>/dev/null; '
              'if [ -d ./oh_modules ]; then echo "oh_modules 保留（由 ohpm 管理，'
              '如需重装请手动执行 ohpm install）"; fi; true',
              "清理可重建的生成目录（build/.hvigor/.preview），保留 oh_modules", rev=True),
        ],
        standards=[PKG],
        notes=["参考 ohpm / Hvigor 文档：build、.hvigor、.preview 均为构建生成目录，"
               "删除后重新构建即可恢复。",
               "需在鸿蒙工程根目录执行；oh_modules 由 ohpm 管理，本任务保留不删。"],
        caveats=["切勿删除 AppScope/app.json5、module.json5 与签名文件（p12/cer/p7b）——"
                 "删了无法打包发布。删除前建议先提交版本库。"],
    ),
    Task(
        id="harmony_ipc_distributed",
        platform="harmony",
        title="IPC/RPC 与分布式软总线核对",
        category="maintenance",
        risk="low",
        desc="核对鸿蒙 IPC/RPC（@ohos.rpc）与分布式软总线的能力与前提（设备需先组网认证）。",
        actions=[
            N("harmony.ipc_distributed_report", "核对 IPC/RPC 与分布式能力（只读）"),
        ],
        standards=[IPC],
        notes=["参考 @ohos.rpc 文档：MessageSequence / RemoteObject 提供统一 IPC/RPC；"
               "跨设备还需 @ohos.distributedDeviceManager 完成发现与认证组网。",
               "分布式调用耗电与延迟高于本地 IPC，非必要不要高频跨设备 RPC。"],
        caveats=["仅核对能力；未装 hdc 或未连设备时降级为指引，不做任何设备侧变更。"],
    ),
    Task(
        id="harmony_uniapp_check",
        platform="harmony",
        title="uni-app 鸿蒙端核对（Harmony Next / vue3）",
        category="optimize",
        risk="low",
        desc="按 uni-app 鸿蒙文档核对工程：HBuilderX 4.27+ 支持、仅 vue3、条件编译隔离差异。",
        actions=[
            N("harmony.uniapp_harmony_report", "核对 uni-app 鸿蒙端工程与配置（只读）"),
        ],
        standards=[UNIAPP],
        notes=["参考 uni-app 鸿蒙篇（uniapp.dcloud.net.cn/tutorial/harmony/）："
               "自 HBuilderX 4.27 起支持 Harmony Next 平台 App 开发，**仅支持 vue3 项目**，"
               "vue2 需先迁移（migration-to-vue3）。",
               "调用鸿蒙原生 API 与嵌入原生组件见官方对应章节；uni.* 内置模块在鸿蒙端的"
               "支持度以「内置模块说明」为准。"],
        caveats=["仅核对工程，不改配置/不发起编译；不要假设鸿蒙端 API 与 Android/iOS 端一致，"
                 "差异请用条件编译隔离。"],
    ),
    Task(
        id="harmony_kaihong_distribution",
        platform="any",
        title="KaihongOS 发行版识别（深开鸿 / 基于 OpenHarmony）",
        category="maintenance",
        risk="low",
        desc="只读识别本机是否为 KaihongOS（深开鸿基于 OpenHarmony 的发行版）：版本、variant"
             "（Stan/Small/Lite/桌面）、安全基座（SELinux/可信应用）、调试工具（hdc/HiLog）。"
             "非 KaihongOS 主机降级为指引。",
        standards=["深开鸿开发服务平台 developer.kaihong.com：KaihongOS 发行版"
                     "（Stan/Small/Lite/桌面 x86·ARM）与 OpenHarmony 基座、"
                     "多内核混合部署（集成 UniProton，时延≤3us）、分布式软总线（响应<50ms）"],
        actions=[
            N("harmony.kaihong_report", "只读识别 KaihongOS 发行版（os-release / SELinux / hdc）"),
        ],
        notes=["KaihongOS 是 OpenHarmony 的具体发行版；鸿蒙通用探测（hdc/HiLog/Stage/SysCap/"
               "HAP/分布式）为其上层能力，本任务只做实锤「是不是 KaihongOS、哪一档」。",
               "安全基座含 SELinux 策略配置 + 仅可信应用可安装 + 端到端加密；只读核验 SELinux"
               "挂载态，不读业务数据。"],
        caveats=["绝不连设备、绝不改配置；hdc 仅在设备侧调试时使用，本机识别无需 hdc。"],
    ),
]
