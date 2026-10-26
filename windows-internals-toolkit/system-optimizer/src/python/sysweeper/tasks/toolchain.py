"""工具链全景任务（platform=any，跨平台）。

只读盘点宿主工具链与仓库工具软件（catalog 数据层 + 本机实采），给出分类别、
仓库目录、配置逻辑顺序与命令序列——与 docs/57 工具链全景 README 同源。

红线：只读探测与编目；安装/卸载/构建/下载一律只给指引，不代执行。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="toolchain_catalog",
        platform="any",
        title="工具链全景编目（只读）",
        category="maintenance",
        risk="low",
        desc="按「类别 × 目标架构 × 仓库目录」三维编目宿主工具链（10 类别 42 条：交叉编译/原生构建/"
             "仿真/打包/质量/安全检测/版本控制与网络/容器/媒体/编辑器与浏览器）与仓库工具软件"
             "（14 条：PE 查看器家族/classics 三端/sysweeper/syspkg/novel-website/Docker 支持/"
             "CI 工作流/repo guard），每条带 setup_steps（配置逻辑顺序）与 commands（命令序列）。"
             "绝不安装、绝不构建。",
        actions=[
            N("toolchain.catalog_report", "编目全景（类别×工具链×仓库工具×目标矩阵）"),
        ],
        notes=["catalog 的 setup_steps/commands 是 README 性质的逻辑顺序，不是自动执行队列。"],
        standards=["[国际] GNU 目标三元组（Target Triple）规范",
                  "[国际] MinGW-w64 / Android NDK / OpenHarmony SDK 工具链约定"],
    ),
    Task(
        id="toolchain_host_probe",
        platform="any",
        title="本机工具链实采（只读）",
        category="maintenance",
        risk="low",
        desc="对 catalog 42 条宿主工具链全覆盖实采（which + 首行版本；版本旗标按上游口径："
             "openssl/go 用 version、ssh/tmux 用 -V、perl 用 -v、ffmpeg 用 -version、tclsh 走 "
             "stdin 读 $tcl_version；NDK/OHOS/libiconv 按绝对路径回退），缺席如实标注。",
        actions=[
            N("toolchain.host_probe_report", "本机实采（which + 版本实读，不装不卸）"),
        ],
        notes=["缺席≠异常：交叉链按需安装；msf 只检测存在性（secdetect 口径）。"],
        standards=["[国际] 各工具链 --version 输出约定（实读为凭）"],
    ),
    Task(
        id="toolchain_target_matrix",
        platform="any",
        title="目标架构矩阵（只读）",
        category="maintenance",
        risk="low",
        desc="三元组 → OS → 工具链 → 验证口径一览：x86_64/i686-linux-gnu、PE32/PE32+（mingw）、"
             "Android bionic×3（API 21）、aarch64-unknown-linux-ohos（musl）、deb 矩阵。",
        actions=[
            N("toolchain.target_matrix_report", "目标架构矩阵报告"),
        ],
        notes=["bionic qemu 三连坎如实记录：Android 运行级验证不可行，构建级完整。"],
        standards=["[国际] Android NDK ABI / OpenHarmony musl 工具链口径"],
    ),
    Task(
        id="toolchain_freshness",
        platform="any",
        title="工具链上游新鲜度（只读）",
        category="maintenance",
        risk="low",
        desc="上游新鲜度两栏：needs_action（27 条，安全相关优先：openssl 3.0.13/curl 8.5.0/"
             "Chrome 144/Docker 27.5.1/git 2.43.0/Perl 5.38.2/jq 1.7 等，均带上游版本与发布日期）"
             "与 fresh（4 条当前线）。",
        actions=[
            N("toolchain.freshness_report", "上游新鲜度报告"),
        ],
        notes=["来源：官网与安全公告；补丁响应时钟口径见 comp bringup 域。"],
        standards=["[国际] CVE/NVD 补丁响应口径（docs/52 九项评估表）"],
    ),
]
