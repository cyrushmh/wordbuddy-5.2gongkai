"""量子存储交换任务（v0.6.77 新建）。

把「保持量子架构 + ext4 默认 4K 对齐 + GPU/NPU/TPU/CAN 异构端点缓冲交互 +
按程序要求做储存读取扫描索引 + 量子数字逻辑矩阵做进制转换」落成只读诊断任务。
端点/对齐类归 category="hardware"，转换/管线类归 category="arch"，
全部 platform="any" / risk="low"。

红线：绝不执行写盘/格式化/分区命令（mkfs/dd/wipefs/sgdisk/parted 只作文本建议），
绝不加载驱动或提交计算任务，CAN 绝不开套接字不发帧；量子层纯软件仿真。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="qstore_endpoints",
        platform="any",
        title="GPU/NPU/TPU/CAN 异构端点存在性只读盘点",
        category="hardware",
        risk="low",
        standards=[
            "[标准] PCI-SIG · PCI Express 基规范（配置空间类别码：0x03 显示/0x12 加速器）",
            "[标准] kernel.org · accel 加速器子系统与 /dev/accel 节点",
            "[标准] ISO 11898 · CAN 数据链路层（SocketCAN 接口形态）",
        ],
        desc="只读盘点四类交互端点的存在性：GPU（/sys/class/drm + lspci 显示控制器）、"
             "NPU（/dev/accel/* + PCI 处理加速器类别）、TPU（/dev/apex_* + Coral 厂商 ID）、"
             "CAN（/sys/class/net/can* SocketCAN 接口）。端点角色互补：GPU/NPU/TPU 承担"
             "数据面吞吐与变换，CAN 承担控制面确定性握手。缺失端点按「未检出」降级，不报错。",
        actions=[N("qstore.endpoint_probe_report", "逐端点收集存在性证据（绝不触碰设备）")],
        notes=[
            "类别码是「这是哪类端点」的权威判据：0x03 显示控制器、0x12 处理加速器，来自 PCI 配置空间。",
            "NPU/TPU 的节点名与 PCI ID 落地节奏随内核版本变化，只记存在性不固化版本。",
            "端点在量子基座上各占 2 个经典位（req/ack 握手）：4 端点 × 2 位恰好占满 8 位寄存器。",
        ],
        caveats=["绝不加载厂商内核模块、绝不提交计算任务、绝不打开 CAN 套接字发帧；"
                 "只读 sysfs/dev 节点与 lspci 配置空间。"],
    ),
    Task(
        id="qstore_alignment",
        platform="any",
        title="ext4 / 4K 对齐逐设备核验（sysfs→lsblk→statvfs 降级链）",
        category="hardware",
        risk="low",
        standards=[
            "[标准] kernel.org · ext4 文档（默认 4KiB 块）与 queue-sysfs 参数语义",
            "[标准] UEFI Forum · GPT 分区表规范（Partition Starting LBA）",
            "[开源] e2fsprogs（GPL-2.0，tune2fs/dumpe2fs 只读面）",
        ],
        desc="三级降级核验每个块设备的 4K 对齐：sysfs 读 logical/physical_block_size 与"
             "分区 start（字段缺失按 0 降级）→ lsblk 交叉核对 → statvfs 文件系统视角兜底。"
             "判定公式：(start·逻辑扇区)%4096==0 且逻辑扇区≤4096 且 (对齐偏移+起始偏移)"
             "%max(物理扇区,4096)==0。未对齐只给文本建议（parted/gdisk 重排起点、"
             "mkfs.ext4 -b 4096），绝不代跑。",
        actions=[N("qstore.alignment_report", "逐设备输出 4K 对齐判定表")],
        notes=[
            "对齐只取决于分区起始偏移与底层扇区尺寸，与文件系统自身无关；GPT 1MiB 惯例（2048 扇区）天然满足 4K。",
            "alignment_offset 在 virtio/容器下常缺失——必须按 0 降级，不能当错误。",
            "容器内常无块设备节点，tune2fs 系只作可选增强；sysfs 永远可用。",
        ],
        caveats=["只读读取：不改分区表、不格式化、不挂载卸载、不刷写任何扇区。"],
    ),
    Task(
        id="qstore_radix",
        platform="any",
        title="量子数字逻辑矩阵进制转换（Π_k 编码门保真往返）",
        category="arch",
        risk="low",
        standards=[
            "[本仓] quantum 子系统（v0.6.69 建）· enc k 置换矩阵 Π_k = ∏ X_i",
            "[概念] quantum 概念系统 · 数字逻辑矩阵与进制表示",
        ],
        desc="复用量子架构基座做进制转换：每个数字先 load() 复位（enc 是翻转语义，"
             "不复位会得到旧值 XOR k）、encode_number 经 Π_k 置换矩阵编码、decode_number "
             "测量解码并逐一校验相等。再演示「硬盘可接受数列」：字节流按 12 位重组为 "
             "4096 进制（4K 粒度）数列，每项 0..4095 与 4K 块对齐。",
        actions=[N("qstore.radix_report", "保真往返演示 + 翻转语义陷阱对照 + 4K 数列打包")],
        notes=[
            "诚实边界：量子层做的是可逆编码与校验，不是提速；进位/取模由经典层完成，中间数字过量子寄存器校验。",
            "翻转语义陷阱：从 |0…0> 编码 k 得 |k>，但紧接着编码 j 会得到 |k⊕j>——复位契约由 _quantum_roundtrip 内建。",
            "decode_number() 会真实坍缩态矢量，解码后同样依赖下次 load() 复位。",
        ],
        caveats=["纯软件仿真：不改 quantum.py 任何语义、不接量子硬件/云量子服务。"],
    ),
    Task(
        id="qstore_pipeline",
        platform="any",
        title="储存读取扫描索引管线仿真（分块→端点缓冲→量子转换→4K 打包）",
        category="arch",
        risk="low",
        standards=[
            "[标准] kernel.org · 块层与页缓存（CPU 侧默认缓冲通路）",
            "[本仓] quantum 子系统 · PiLink 圆周率环形缓冲与针脚握手",
        ],
        desc="把「按程序要求进行储存读取扫描索引」跑成量子基座上的完整管线：样本字节流"
             "轮流分配给 GPU/NPU/TPU 数据端点（req/ack 针脚握手）→ Π_k 门量子进制转换 → "
             "累计打包成 4096 对齐块（块完成时 CAN 控制面确认）。全量链路历史由本模块自累积"
             "（PiLink snapshot 只回最近 7 槽），用 total_writes/overwrites 算链路利用率与覆盖浪费率。",
        actions=[N("qstore.pipeline_report", "端到端管线仿真与链路统计")],
        notes=[
            "真实通路对应：CPU 页缓存命中→块层合并→调度器下发；仿真把「缓存」映射为 PiLink、「握手」映射为针脚、「进制转换」映射为 Π_k 门。",
            "snapshot() 只保留最近 size 条（deque maxlen 丢旧记录）——全量历史必须自己累积 step 级返回值。",
            "尾部不足整块按一块计，尾部填充不写盘（只读仿真的诚实口径）。",
        ],
        caveats=["纯仿真：不写盘、不读真实数据面、不调度任何真实 I/O。"],
    ),
]
