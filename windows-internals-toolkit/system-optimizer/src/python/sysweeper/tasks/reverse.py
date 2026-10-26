"""黑箱逆向与调试工具链任务（reverse，platform=any，跨平台）。

把 UPX/GDB/MinGW 黑箱实战落成任务层：黑箱扫描实操（对指定二进制跑只读
格式/节区/熵分析）+ 加壳识别专项 + GDB 命令模板专项。全部只读——不执行
目标程序、不 patch 内存、不 hook 调用、不生成任何绕过手段；逆向目标限
自己/己方/已授权产物。

与 native/reverse.py 对应：binary_scan 为只读分析入口，检查项每条回链
知识库 key（data/reverse_docs.json），保证「结论有出处」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="reverse_blackbox_scan",
        platform="any",
        title="黑箱只读扫描：PE/ELF 格式 + 节区 + 熵 + UPX 判定",
        category="privacy",
        risk="low",
        desc="对指定二进制（自己的/己方/已授权的产物）做黑箱只读分析：格式识别"
             "（PE32/PE32+/ELF）→ 节区清单（名字/虚拟尺寸/原始尺寸/偏移）→ 逐节"
             "香农熵 → 整体熵 → UPX 三特征判定（UPX! marker / UPX0·1·2 节名 /"
             "节熵>7.5）。实测基准：MinGW GCC 13 产 PE32 237KB/17 节、PE32+ "
             "249KB/19 节；UPX 4.2.2 --best 加壳后 win64 48.5%/win32 53.2% 压缩率、"
             "整体熵 5.898→7.035。",
        actions=[
            N("reverse.binary_scan", "黑箱只读扫描指定二进制（格式/节区/熵/UPX 判定）"),
            M("用法：把待查二进制路径填入上方动作执行（本机文件）。观察要点："
              "①节名是否 UPX0/1/2；②数据节熵是否>7.5；③whole_entropy 是否显著"
              "高于同编译链同类产物。三条全中大概率被加过壳——与发布清单不符就追问来源。",
              "黑箱扫描结果读法指引"),
        ],
        notes=["只读分析不执行目标；符号/节区/熵结论仅是黑箱观察，不是恶意/安全判定。"],
        standards=["[REV] PE Format（Microsoft Learn）",
                   "[REV] UPX 官方站点（upx.github.io）",
                   "[REV] GDB 官方文档（sourceware.org/gdb）"],
    ),
    Task(
        id="reverse_entropy_reading",
        platform="any",
        title="熵判据与符号可见性：黑箱信号的量化读法",
        category="privacy",
        risk="low",
        desc="把黑箱信号从『感觉奇怪』变成量化读数：逐节熵 + 整体熵两级读；"
             "strip 前后对照（实测 16000→14472B、熵 1.522→1.235，本地符号消失、"
             "PLT 动态符号保留）；符号缺失时改用外部面还原（PLT 名 + 导入表倒推）。",
        actions=[
            N("reverse.reverse_checklist", "输出熵判据/符号可见性对照清单（每项回链知识库）"),
            M("读表顺序：①该文件与谁比（同编译链同版本）②逐节 entropy 哪节离群"
              "（>7.5 或≈0）③符号还剩多少。三条读数都记下来再下结论，别拍脑袋。",
              "熵与符号读法指引"),
        ],
        notes=["熵是症状不是病名：高熵节也可能是合法压缩资源，须连节名/格式/上下文合判。"],
        standards=["[REV] strip/objdump/binutils 手册",
                   "[REV] 本仓 reverse_docs.json 熵判据表（沙箱实测口径）"],
    ),
    Task(
        id="reverse_gdb_playbook",
        platform="any",
        title="GDB 黑箱四连与 MinGW 造样本（只读观察）",
        category="privacy",
        risk="low",
        desc="GDB 黑箱四连模板：info functions（符号面）→ disassemble <fn>"
             "（指令面）→ info proc mappings（运行期内存布局，无进程时报错属预期）"
             "→ break/run/bt/info registers（动态观察闭环）。样本供给用 MinGW 交叉"
             "链自造（i686/x86_64-w64-mingw32-gcc，实测 GCC 13-win32）——要分析 PE "
             "先造可控样本，不下载来路不明二进制。沙箱 wine 实测启动 PE 失败，"
             "PE 动态分析需目标环境，本环境以静态路径（objdump/自写扫描器）为主。",
        actions=[
            M("四连命令（batch 模板）：\n"
              "  gdb -batch -ex 'info functions' -ex 'disassemble main' <elf>\n"
              "  gdb -batch -ex 'file <elf>' -ex 'set confirm off' ...\n"
              "观察纪律：只看不改——不 patch、不 hook、不 bypass；目标限自己/己方/已授权。",
              "GDB 四连命令模板（人工执行）"),
            N("reverse.reverse_report", "输出黑箱工具链知识总报告（含只读边界声明）"),
        ],
        notes=["逆向他人受保护软件涉及授权与法律（DMCA 反规避等），先拿授权再动手。"],
        standards=["[REV] MinGW-w64 官方（mingw-w64.org）",
                   "[REV] GDB 官方文档（sourceware.org/gdb/current/onlinedocs/gdb/）"],
    ),
]
