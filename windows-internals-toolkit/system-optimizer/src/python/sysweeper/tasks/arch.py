"""架构 / 指令集（ISA）相关任务：龙芯 LoongArch、MIPS、RISC-V、开源硬件。

架构是「跨平台之上」的另一维度：同一条清理/优化在不同指令集上的做法与
工具链并不相同。本模块的任务全部 platform="any"，按当前运行架构自动给出
对应报告与指引（本机非该架构时优雅降级为「非该平台」说明，不报错）。

覆盖：
- 龙芯 LoongArch（国产自主指令集，含向量 LSX/LASX、虚拟化 LVZ、二进制翻译 LBT）
- MIPS（MIPS32/64 Release 6，含龙芯早期 Godson 授权机型与嵌入式设备）
- RISC-V（开源指令集，RVA20/22/23 profiles）
- 开源硬件（OSHWA 认证、CERN OHL 许可、DIN SPEC 3105 地区标准、CHIPS Alliance）
- 交叉工具链与 Go GOARCH 构建映射（呼应 Go 构建支持）

标准引用按三层（国家优先 / 国际给外人 / 地区按需），详见 models.CATEGORY_STANDARDS
的 arch 分类与 data/arch.json。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    Task(
        id="arch_report",
        platform="any",
        title="架构/指令集探测报告",
        category="arch",
        risk="low",
        desc="探测当前 CPU 架构（龙芯 LoongArch / MIPS / RISC-V / x86 / ARM …），"
             "给出对应标准出处与建议。",
        actions=[N("arch.arch_report", "探测架构并引用标准（native/arch 原生接口）")],
        standards=[
            "[国标] 龙芯 LoongArch 指令集架构（国产自主，国家平台 std.samr.gov.cn）",
            "[国际] RISC-V ISA Specification（RISC-V International）",
            "[国际] MIPS Architecture for Programmers（MIPS32/MIPS64 Release 6）",
        ],
        notes=[
            "探测接口：uname -m / /proc/cpuinfo / sysctl hw.machine / %PROCESSOR_ARCHITECTURE%。",
            "未收录的架构会提示可在 data/arch.json 补充，不会报错。",
        ],
    ),
    Task(
        id="arch_loongarch",
        platform="any",
        arch="loongarch",
        title="龙芯 LoongArch 专项报告与调优指引",
        category="arch",
        risk="low",
        desc="识别龙芯平台（LoongArch 或早期 Godson/MIPS 授权机型），"
             "报告向量/虚拟化/二进制翻译扩展并给出工具链与调优建议。",
        actions=[N("arch.loongarch_report", "龙芯平台专项报告（native/arch 原生接口）")],
        standards=[
            "[国标] 龙芯 LoongArch 指令集架构（国产自主架构，国家标准见国家平台 std.samr.gov.cn）",
            "[国际] LoongArch Reference Manual（基础架构 / 向量 / 虚拟化卷，龙芯中科发布）",
        ],
        notes=[
            "LoongArch 是国产自主指令集（2021 年随 3A5000 发布），由 MIPS 授权演进而来。",
            "扩展含义：LSX/LASX 向量、LVZ 虚拟化、LBT 二进制翻译（可跑 x86/ARM 程序但有损耗）。",
            "优先取龙芯/系统厂商提供的源与原生包；交叉工具链为 loongarch64-linux-gnu-*。",
        ],
        caveats=["二进制翻译（LBT）运行非原生程序有性能损耗，生产环境建议原生编译。"],
    ),
    Task(
        id="arch_mips",
        platform="any",
        arch="mips",
        title="MIPS 架构专项报告（含龙芯早期授权机型）",
        category="arch",
        risk="low",
        desc="识别 MIPS 平台，报告位数、端序与 ABI，并区分是否为龙芯早期 Godson 机型。",
        actions=[N("arch.mips_report", "MIPS 平台专项报告（native/arch 原生接口）")],
        standards=[
            "[国际] MIPS Architecture for Programmers（MIPS32 / MIPS64 Release 6）",
            "[国际] MIPS Open（开源指令集计划，2019）",
            "[国标] 国产化替代：龙芯/MIPS 平台适配相关国家标准（国家平台 std.samr.gov.cn）",
        ],
        notes=[
            "MIPS 常见于路由器/嵌入式设备与龙芯早期机型；大端 mips 与小端 mipsel ABI 不通用。",
            "装包须与端序匹配，混用会直接报格式错误。",
        ],
    ),
    Task(
        id="arch_riscv",
        platform="any",
        arch="riscv",
        title="RISC-V 开源架构专项报告",
        category="arch",
        risk="low",
        desc="识别 RISC-V 平台，读取 isa 扩展字符串并引用 RVA20/22/23 profiles 规范。",
        actions=[N("arch.riscv_report", "RISC-V 平台专项报告（native/arch 原生接口）")],
        standards=[
            "[国际] RISC-V Unprivileged / Privileged ISA Specification（RISC-V International）",
            "[国际] RISC-V Profiles（RVA20 / RVA22 / RVA23，ratified 兼容性规范）",
            "[国标] 中国 RISC-V 产业联盟（CRVA）开放指令生态规范",
        ],
        notes=[
            "RISC-V 为开源、免授权费指令集；常用编译参数 -march=rv64gc -mabi=lp64d。",
            "不同扩展组合（如缺 V 向量）影响软件可用性，装包前先核对 isa 字符串。",
        ],
    ),
    Task(
        id="arch_open_hardware",
        platform="any",
        title="开源硬件认证与许可核对（OSHWA / CERN OHL）",
        category="arch",
        risk="low",
        desc="列出开源硬件的定义、认证（OSHWA UID）与许可（CERN OHL v2 / DIN SPEC 3105），"
             "供复用硬件设计前核对。",
        actions=[N("arch.open_hardware_report",
                   "开源硬件认证与许可指引（native/arch 原生接口）")],
        standards=[
            "[国际] OSHWA 开源硬件定义 1.0 + 认证 UID（oshwa.org）",
            "[国际] CERN Open Hardware Licence（OHL v2，强 copyleft 硬件许可）",
            "[国际] CHIPS Alliance（开放芯片设计与互连标准）",
            "[地区] DIN SPEC 3105（德国：开放硬件标准化要求）",
        ],
        notes=[
            "开源硬件 = 设计文件（原理图/PCB/HDL/机械图纸）在开放许可下发布。",
            "企业复用需留意 copyleft 义务：CERN OHL 衍生设计同样需开放。",
        ],
    ),
    Task(
        id="arch_toolchain",
        platform="any",
        title="交叉工具链与构建目标提示",
        category="arch",
        risk="low",
        desc="按当前架构给出交叉工具链三元组与 Go 的 GOARCH 映射，便于交叉编译。",
        actions=[N("arch.toolchain_report", "工具链与 GOARCH 提示（native/arch 原生接口）")],
        standards=[
            "[国际] RISC-V / MIPS / Power ISA（工具链三元组由各架构规范定义 ABI）",
        ],
        notes=[
            "GOARCH 映射：龙芯 loong64、MIPS mips64le/mipsle、RISC-V riscv64、"
            "OpenPOWER ppc64le、x86 amd64、ARM arm64。",
        ],
    ),
    Task(
        id="arch_go_cross_build",
        platform="any",
        title="按当前架构交叉构建 Go（GOARCH 映射）",
        category="maintenance",
        risk="low",
        requires_lang="go",
        desc="按探测到的架构设置 GOARCH 执行 `go build ./...`，"
             "覆盖龙芯(loong64)/MIPS(mips64le)/RISC-V(riscv64) 等非 x86 目标。",
        actions=[S(
            'if [ -f go.mod ]; then '
            'A=$(uname -m); '
            'case "$A" in loongarch64) GA=loong64;; mips64el|mips64le) GA=mips64le;; '
            'mipsel|mips) GA=mipsle;; riscv64) GA=riscv64;; ppc64le) GA=ppc64le;; '
            'aarch64|arm64) GA=arm64;; x86_64|amd64) GA=amd64;; armv7l|armv6l) GA=arm;; '
            '*) GA="";; esac; '
            'if [ -n "$GA" ]; then echo "GOARCH=$GA"; GOARCH="$GA" go build ./...; '
            'else echo "未识别架构 $A，按默认目标构建"; go build ./...; fi; '
            'else echo "当前目录无 go.mod，跳过构建"; fi',
            "按架构设置 GOARCH 构建全部包（go 原生命令）")],
        notes=[
            "未识别架构时回退默认目标，不报错。",
            "龙芯（loong64）需 Go 1.19+；MIPS 上 Go 官方支持 mips64le/mipsle。",
        ],
        caveats=["交叉构建不产生可运行于本机的二进制（除非架构一致）；仅做构建校验。"],
    ),
    Task(
        id="arch_loongarch_optimize",
        platform="any",
        arch="loongarch",
        title="龙芯平台优化指引（原生优先 / 翻译层取舍）",
        category="optimize",
        risk="low",
        desc="龙芯平台的优化要点：优先原生包、源选择、编译参数与二进制翻译（LBT）取舍。",
        actions=[M(
            "优化要点：\n"
            "1) 优先取龙芯/系统厂商源与原生包（避免 x86/ARM 二进制翻译损耗）；\n"
            "2) 编译加 -march=loongarch64，向量密集场景启用 LSX/LASX；\n"
            "3) 必须运行非原生程序时用 LBT 二进制翻译，但仅作过渡；\n"
            "4) 虚拟化场景确认内核已启用 LVZ。",
            "龙芯平台优化指引（手动核对，不改系统）")],
        standards=[
            "[国标] 龙芯 LoongArch 指令集架构（国产自主，国家平台 std.samr.gov.cn）",
        ],
        notes=["全部为核对型指引，不自动修改系统。"],
    ),
    Task(
        id="arch_mips_embedded_optimize",
        platform="any",
        arch="mips",
        title="MIPS / 嵌入式资源受限优化指引",
        category="optimize",
        risk="low",
        desc="MIPS 路由器与嵌入式设备常见资源受限场景的优化要点："
             "优先清缓存日志、关无用服务、避免重包。",
        actions=[M(
            "优化要点：\n"
            "1) 存储小：先清包缓存与轮转日志（收益最直接）；\n"
            "2) 内存小：关无用常驻服务，避免 swap 抖动；\n"
            "3) 装包须匹配端序（mips 大端 / mipsel 小端）与 ABI（o32/n32/n64）；\n"
            "4) CPU 弱：避免编译重型软件，优先取预编译原生包。",
            "MIPS / 嵌入式优化指引（手动核对，不改系统）")],
        standards=[
            "[国际] MIPS Architecture for Programmers（MIPS32 / MIPS64 Release 6）",
        ],
        notes=["全部为核对型指引，不自动修改系统。"],
    ),
]
