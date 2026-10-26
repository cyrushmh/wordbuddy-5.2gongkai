#!/usr/bin/env python3
"""把源码 _() 壳层串的人工英译写回 en.po（v0.6.61）。

口径
----
- 只填 **msgstr 为空** 的条目（已有译文一律保留，绝不覆盖人工成果）。
- 译文为人工翻译（非机翻）：保留 %s/%d/%.2f 等占位符与 Po 所需的转义。
- 本脚本只服务 en.po；其余语言维持「空 msgstr = 回退中文」的仓库既定口径。
- 新壳层串出现时的流程：源码加 _() → extract_task_strings.py 入册 → 本文件补译 →
  make_mo.py 重编译。

用法
----
    python3 tools/en_shell_po_fill.py            # 写入 en.po
    python3 tools/en_shell_po_fill.py --dry-run  # 只看会填多少
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PO = (ROOT / "src" / "python" / "sysweeper" / "locales" / "en"
      / "LC_MESSAGES" / "sysweeper.po")

# msgid（简体中文）→ 人工英译。键集与 extract_task_strings.py 扫出的源码 _() 串对应。
EN_SHELL = {
    # v0.6.61 plang of 补全字段标签（既有命令新增输出，壳层需翻译）
    "首次出现：": "First appeared: ",
    "范式：": "Paradigm: ",
    "类型系统：": "Type system: ",
    "内存管理：": "Memory management: ",
    "一句话定位：": "One-line summary: ",
    "工程落法：": "Engineering practice: ",
    "十进制(可读): %s  (0x%s)": "Decimal (readable): %s  (0x%s)",
    "十进制（人类可读·默认）: %s": "Decimal (human readable, default): %s",
    "\\x 转义    : %s": "\\x escape    : %s",
    "位串 :": "Bit string:",
    "波形 :": "Waveform:",
    "说明 :": "Description:",
    "标记 :": "Tags:",
    "第 %d 轮合并：%s": "Round %d merge: %s",
    "%-2d %-10s %-14s 覆盖 m(%s)%s": "%-2d %-10s %-14s coverage m(%s)%s",
    "第 %d 轮：%s": "Round %d: %s",
    "原子性    : LOCK — 该指令在多核下原子执行": "Atomicity    : LOCK — this instruction executes atomically on multi-core",
    "· 说明：核心格式走标准库，永远可用；7z/rar/zstd 缺库时明确跳过，不强求安装。": "· Note: core formats go through the standard library and are always available; 7z/rar/zstd are explicitly skipped when the library is missing, never force-installed.",
    "· 按「还值不值得再压」分类：": "· Grouped by \"is it still worth re-compressing\":",
    "· 体积最大的可压缩文件（采样前 1 MiB 实测 LZMA 压缩率）：": "· Largest compressible files (LZMA ratio measured on the first 1 MiB sample):",
    "· 大压缩包内部条目（流式读取，不解压、不驻留内存）：": "· Entries inside large archives (streamed read, no extraction, no memory residency):",
    "· 归档建议（只会打印命令，不自动执行）：": "· Archiving suggestions (commands are printed only, never auto-executed):",
    "- 纯文本/日志：tar czf 归档.tar.gz <目录>   （标准库可用，兼容性最好）": "- Plain text/logs: tar czf archive.tar.gz <dir>   (stdlib only, best compatibility)",
    "- 追求高压缩率：7z a -t7z -mx=9 归档.7z <目录>   （需装 7z 或 py7zr）": "- For max ratio: 7z a -t7z -mx=9 archive.7z <dir>   (needs 7z or py7zr)",
    "- 已压过的（zip/7z/rar/mp4/png/pdf）别再压：收益接近 0，白费 CPU。": "- Already compressed (zip/7z/rar/mp4/png/pdf) — do not re-compress: near-zero gain, wasted CPU.",
    "· 本报告只读：未压缩、未解压、未删除任何文件。": "· This report is read-only: nothing was compressed, extracted or deleted.",
    "· 已扫文件 %d 个，合计 %s%s": "· Scanned %d files, totaling %s%s",
    "- 未发现值得压缩的大文件（多数已是已压缩/已编码格式）": "- No large files worth compressing (most are already compressed/encoded formats)",
    "- 未发现归档/压缩包": "- No archives found",
    "· 仅这 %d 个文件归档，预计可回收约 %s": "· Archiving only these %d files is expected to reclaim about %s",
    "哈希原像搜索": "Hash preimage search",
    "给定盐与难度，搜索使哈希前 N 位为零的 nonce": "Given a salt and difficulty, search for a nonce whose hash starts with N zero bits",
    "一次哈希（O(1)），远便宜于搜索": "One hash (O(1)) — far cheaper than searching",
    "分块矩阵乘法": "Blocked matrix multiplication",
    "把大矩阵乘法切成小块并行，结果确定性可校验": "Split large matrix multiplication into blocks and run in parallel; results are deterministic and verifiable",
    "抽一行一列重算（O(n) 而非 O(n²)）": "Recompute one row and one column (O(n) instead of O(n²))",
    "蒙特卡洛求 π": "Monte Carlo estimation of π",
    "固定种子的随机投点估算 π，同种子必得同结果": "Sample random points with a fixed seed to estimate π; the same seed always yields the same result",
    "同种子原样复算一遍": "Recompute once more with the same seed",
    "未知": "Unknown",
    "分布式计算能力（本机画像，只读探测）": "Distributed computing capacity (local profile, read-only probe)",
    "内置可验证算子（白名单，仅此三个）": "Built-in verifiable operators (whitelist, these three only)",
    "为什么只有内置算子：BOINC 让项目方下发可执行程序，信任链是「我信任这个项目方」；本层砍掉这条链——**绝不下载、绝不执行任何外部代码**。": "Why built-in operators only: BOINC lets project owners ship executables, so the trust chain is \"I trust this project owner\"; this layer cuts that chain — **never download and never execute any external code**.",
    "调度计划（只出计划，不真跑）": "Scheduling plan (plan only, nothing actually runs)",
    "节点（按可捐献评分排序）：": "Nodes (sorted by donatable score):",
    "分布式计算共享": "Distributed compute sharing",
    "红线：不执行任意代码 / 不下载可执行程序 / 不主动连外部服务器 / 有 CPU 与时间预算，跑满即停。": "Red lines: never execute arbitrary code / never download executables / never proactively connect to external servers / CPU and time budgets apply; stop when exhausted.",
    "分布式计算看门狗（模式说明，不执行）": "Distributed compute watchdog (pattern description, not executed)",
    "模式来源：mihomo-kubernetes 用「健康检查 + 定时重启」清掉常驻代理里可能泄漏的敏感上游状态，而非去 patch 上游。": "Pattern origin: mihomo-kubernetes uses \"health checks + scheduled restarts\" to clear potentially leaked sensitive upstream state from long-running proxies, instead of patching upstream.",
    "本层映射：distcompute 的本地采集进程若常驻，会在内存里攒结果 / 对端句柄；看门狗周期性重启它，把这些易失状态清零，降低长期驻留风险。": "Layer mapping: if the distcompute local collector stays resident, it accumulates results / peer handles in memory; the watchdog restarts it periodically, zeroing this volatile state to lower long-residency risk.",
    "触发口径：健康检查（进程在 / 心跳新鲜 / 内存占用 / 距上次重启时长）超阈值 → 重启。": "Trigger rule: restart when health checks (process alive / heartbeat fresh / memory usage / time since last restart) exceed thresholds.",
    "红线：sysweeper 绝不自动重启任何进程。只出重启计划（命令文本），由你显式执行。": "Red line: sysweeper never restarts any process automatically. Only a restart plan (command text) is produced, for you to execute explicitly.",
    "健康检查超阈值（进程僵死 / 心跳陈旧 / 内存超基线 / 距上次重启超时）": "Health check over threshold (process hung / stale heartbeat / memory over baseline / time since last restart exceeded)",
    "sysweeper 不执行此命令；仅给出计划。确认无误后由你手动运行。": "sysweeper does not execute this command; only the plan is shown. Run it manually after verifying.",
    "没有可用节点（电量过低或能力为零）": "No available nodes (battery too low or capacity zero)",
    "未知算子，无法校验": "Unknown operator, cannot verify",
    "复算一致，接受该结果": "Recompute consistent; result accepted",
    "复算不一致，结果存疑——需重投该单元": "Recompute inconsistent; result suspect — this unit must be re-dispatched",
    "未知算子，拒绝执行（只跑内置白名单）": "Unknown operator, refused (only the built-in whitelist runs)",
    "CPU 核心：%d；每核负载：%s": "CPU cores: %d; per-core load: %s",
    "内存：可用 %s / 共 %s": "Memory: %s available / %s total",
    "供电：未检测到电池（台式机/服务器或读取受限）": "Power: no battery detected (desktop/server or read restricted)",
    "网络计费：%s": "Network metering: %s",
    "可捐献评分：%.2f（0 = 不派活）": "Donatable score: %.2f (0 = no work assigned)",
    "图形能力（只登记型号，不跑负载）：": "Graphics capability (model recorded only, no load run):",
    "图形能力：未探测到独立 GPU（无 lspci 或无 VGA/3D 设备）": "Graphics: no discrete GPU detected (no lspci or no VGA/3D device)",
    "算子 %s；工作单元 %d 个；冗余双投 k=%d": "Operator %s; %d work units; redundant double-dispatch k=%d",
    "credit 记账（本地记录，不换任何东西）：": "credit ledger (local record only, exchangeable for nothing):",
    "credit 记账：暂无记录": "credit ledger: no records yet",
    "未知算子：%s（白名单内才有）": "Unknown operator: %s (only whitelisted ones exist)",
    "电池：%d%%（%s）": "Battery: %d%% (%s)",
    "非计量网络或未知": "Unmetered network or unknown",
    "校验成本：%s": "Verification cost: %s",
    "节点 %d：评分 %.2f，%d 核": "Node %d: score %.2f, %d cores",
    "首个单元派给节点 %s（冗余 %d 份，各自独立算，结果一致才接受）": "First unit dispatched to node %s (%d redundant copies, each computed independently; accepted only if results agree)",
    "计量网络（按量计费，派活降权 %.0f%%）": "Metered network (pay-per-use; dispatch down-weighted %.0f%%)",
    "%s：完成 %d 个单元": "%s: completed %d units",
    "充电中": "Charging",
    "使用电池": "On battery",
    "其他": "Other",
    "已收一份，等待冗余第二份": "One copy received, waiting for the redundant second copy",
    "跨机派活（经组网文本通道）": "Cross-machine dispatch (via the mesh text channel)",
    "信任模型：只跑白名单算子；结果必须复算校验，不信任任何节点的自述。": "Trust model: whitelisted operators only; results must be recomputed and verified — no node's self-report is trusted.",
    "接活：serve_once() 听一个包，是工作单元就本地算并回发结果（受预算约束）。": "Taking work: serve_once() listens for one packet; if it is a work unit, compute locally and reply with the result (budget-constrained).",
    "跨机派活链路自检（本地回环，不通网）": "Cross-machine dispatch chain self-test (local loopback, no network)",
    "只编码不出网（dry_run）": "Encode only, no network (dry_run)",
    "已发出": "Sent",
    "收到的不是工作单元，已忽略": "Received packet is not a work unit; ignored",
    "（无回发地址）": "(no reply address)",
    "结果格式不对": "Malformed result",
    "无对应任务": "No matching task",
    "单元号不存在": "Unit number does not exist",
    "收到的不是结果消息，已忽略": "Received packet is not a result message; ignored",
    "载荷格式：%s 与 %s，走同一条组网消息通道（UDP 2425）": "Payload formats: %s and %s, over the same mesh message channel (UDP 2425)",
    "当前没有派出的任务。": "No dispatched tasks at the moment.",
    "派法：dispatch('mc_pi', {'samples': 200000}, dry_run=True) 先看计划，确认后再 dry_run=False 真发。": "Usage: dispatch('mc_pi', {'samples': 200000}, dry_run=True) to inspect the plan first; after confirming, use dry_run=False to actually send.",
    "累计：接受 %d 个单元，存疑 %d 个": "Totals: %d units accepted, %d suspect",
    "存疑明细（前 5 条）：": "Suspect details (first 5):",
    "① 编码：%s…": "① Encoding: %s…",
    "② 解码失败": "② Decoding failed",
    "③ 本地计算：耗时 %.3f 秒，自检校验 %s": "③ Local computation: took %.3f seconds, self-check verification %s",
    "④ 结果回传并复算校验：%s": "④ Result returned and recomputed for verification: %s",
    "⑤ 伪造结果能否混过校验：%s": "⑤ Can a forged result pass verification: %s",
    "⑥ 坏包处理：%s": "⑥ Bad-packet handling: %s",
    "⑦ 白名单外的算子：%s": "⑦ Operators outside the whitelist: %s",
    "未知算子 %s：只派白名单内的活": "Unknown operator %s: only whitelisted work is dispatched",
    "无对应任务（可能是别人的任务），已忽略": "No matching task (possibly someone else's); ignored",
    "未知节点": "Unknown node",
    "② 解码：op=%s，单元号 %s": "② Decoding: op=%s, unit number %s",
    "一致，接受": "Consistent; accepted",
    "不一致，存疑": "Inconsistent; suspect",
    "能（这是漏洞！）": "Yes (this is a vulnerability!)",
    "不能，被打回": "No; rejected",
    "忽略，不抛异常": "Ignored, no exception raised",
    "异常": "Exception",
    "被拒（通道里传的是参数不是代码）": "Rejected (the channel carries parameters, not code)",
    "被接受（漏洞！）": "Accepted (vulnerability!)",
    "载荷超长，已跳过": "Payload too long; skipped",
    "任务 %s：算子 %s，%d 个单元（已完成 %d，存疑 %d，冗余 k=%d）": "Task %s: operator %s, %d units (done %d, suspect %d, redundancy k=%d)",
    "通过": "Pass",
    "不通过": "Fail",
    "Extremely severe / 红色": "Extremely severe / red",
    "Severe / 橙色": "Severe / orange",
    "Moderate / 黄色": "Moderate / yellow",
    "Minor / 蓝色": "Minor / blue",
    "Unknown / 未定级": "Unknown / ungraded",
    "地震 P 波": "Earthquake P wave",
    "地震 S 波": "Earthquake S wave",
    "台风移动": "Typhoon movement",
    "洪水推进": "Flood advance",
    "火势蔓延": "Fire spread",
    "该类事件": "Events of this type",
    "饮用水（每人每天 3 升，至少 3 天量）": "Drinking water (3 liters per person per day, at least 3 days)",
    "即食食品（压缩饼干、罐头，3 天量）": "Ready-to-eat food (compressed biscuits, canned food; 3 days)",
    "手电筒 + 备用电池（或手摇发电）": "Flashlight + spare batteries (or hand-crank)",
    "急救包（纱布、止血带、常用药、处方药）": "First-aid kit (gauze, tourniquet, common medicines, prescriptions)",
    "口哨（呼救比喊叫省力且传得远）": "Whistle (calling for help is easier and carries farther than shouting)",
    "充电宝（满电，配短线）": "Power bank (fully charged, with short cables)",
    "收音机（接收官方广播，网络断了还能听）": "Radio (receives official broadcasts; still works when the network is down)",
    "重要证件复印件 + 少量现金（断电时扫码付不了）": "Copies of important documents + a small amount of cash (QR payment fails during outages)",
    "口罩 / 防尘巾（火灾与地震扬尘）": "Masks / dust cloths (for fire and earthquake dust)",
    "救生哨、手套、结实的鞋": "Rescue whistle, gloves, sturdy shoes",
    "启用定位（关掉后只用手动录入的坐标，不探测本机）": "Enable positioning (when off, only manually entered coordinates are used; the local machine is not probed)",
    "以网络 + 基站定位为首选基线（本层核心口径）": "Use network + cell-tower positioning as the preferred baseline (core rule of this layer)",
    "检测到导航定位时，与首选基线共同综合": "When navigation (GNSS) positioning is detected, fuse it with the preferred baseline",
    "启用预警评估（只评估，不自动报警）": "Enable alert assessment (assessment only, no automatic alarming)",
    "联网订阅预警源（默认关闭；开启后只拉你自己填的 URL）": "Online alert-source subscription (off by default; when on, only fetches the URL you provide)",
    "启用应急呼救文本生成（只生成文本，绝不自动发送）": "Enable emergency SOS text generation (text generation only; never auto-sent)",
    "启用避险点距离排序": "Enable shelter distance ranking",
    "启用应急物资清单核对": "Enable emergency supply checklist verification",
    "手动录入": "Manual entry",
    "缺少位置或事件中心点，无法计算距离（只显示事件本身）": "Missing position or event center; distance cannot be computed (showing the event only)",
    "应急呼救文本已关闭（手动开关 sos_enabled=关）": "Emergency SOS text disabled (manual switch sos_enabled=off)",
    "【应急呼救】": "[EMERGENCY SOS]",
    "本文本由 sysweeper 本地生成，未自动发送——请你自己选择发送方式。": "This text was generated locally by sysweeper and was NOT sent automatically — please choose how to send it yourself.",
    "定位与距离综合（口径：先网络 + 基站，检测到导航再共同综合）": "Position and distance fusion (rule: network + cell tower first; fuse with navigation when detected)",
    "可用定位源：": "Available positioning sources:",
    "预警评估（只评估，不自动报警）": "Alert assessment (assessment only, no automatic alarming)",
    "预警应急系统": "Alert and emergency system",
    "—— 手动开关 ——": "—— Manual switches ——",
    "改法：set_switch('开关名', True/False)；例如关掉联网订阅 set_switch('feed_enabled', False)。": "How to change: set_switch('switch_name', True/False); e.g. to turn off online subscription: set_switch('feed_enabled', False).",
    "预警应急能力自检": "Alert/emergency capability self-test",
    "· Android：adb shell dumpsys location（只读，取 fused/gps/network 最后已知位置）": "· Android: adb shell dumpsys location (read-only; takes the last known fused/gps/network position)",
    "· Linux：mmcli / geoclue 只读探测（**没有基站经纬度库就拿不到坐标，绝不凭 IP 编造**）": "· Linux: mmcli / geoclue read-only probing (**without a cell-tower coordinate database no coordinates can be obtained; never fabricate from IP**)",
    "· 兜底：手动录入坐标（set_manual_position）": "· Fallback: manual coordinate entry (set_manual_position)",
    "本层**不做**的事（红线）：自动报警 / 拨号 / 发短信 / 自动发送任何内容；SOS 只生成文本。": "What this layer does **not** do (red lines): automatic alarms / phone calls / SMS / auto-sending anything; SOS only generates text.",
    "未命名事件": "Unnamed event",
    "按%s的典型速度粗估，仅供量级参考，不是预报": "Rough estimate from the typical speed of %s; for magnitude reference only, not a forecast",
    "你已在影响范围内，按指引行动，不要等下一次更新": "You are already within the impact area; follow instructions and act, do not wait for the next update",
    "我的位置：未能确定（请在安全处手动录入坐标，或说明周边标志物）": "My position: undetermined (please manually enter coordinates while safe, or describe nearby landmarks)",
    "订阅源开关是关的（默认关闭）；先打开 feed_enabled 再拉。": "The subscription switch is off (default); turn on feed_enabled first before fetching.",
    "未配置订阅源地址": "No subscription source URL configured",
    "只接受 http(s) 地址，拒绝其他协议（防止本地文件被当源读）": "Only http(s) URLs accepted; other protocols refused (prevents local files from being read as sources)",
    "已获取并登记 %d 条预警": "Fetched and registered %d alerts",
    "本机未取得任何定位源。": "No positioning source was obtained on this machine.",
    "可以做：在有导航的设备上开启定位后重探；或用手动录入坐标兜底。": "You can: re-probe with positioning enabled on a GNSS-capable device, or fall back to manually entered coordinates.",
    "首选基线（网络 + 基站）：无（未取到网络/基站坐标）": "Preferred baseline (network + cell tower): none (no network/cell-tower coordinates obtained)",
    "导航定位（GNSS）：%s": "Navigation positioning (GNSS): %s",
    "最终采用：无法确定（没有可用坐标）": "Final adopted: undetermined (no usable coordinates)",
    "预警评估已关闭（手动开关 alert_enabled=关）": "Alert assessment disabled (manual switch alert_enabled=off)",
    "当前没有登记的预警。": "No registered alerts at the moment.",
    "没有预警就是没有预警——本层不会凭空生成，也不会在未取到数据时猜测。": "No alerts means no alerts — this layer never fabricates them, and never guesses when no data was obtained.",
    "定位源探测：%s": "Positioning-source probe: %s",
    "已登记预警：%d 条（上限 %d）": "Registered alerts: %d (cap %d)",
    "联网订阅：默认关闭（开关 feed_enabled=%s）": "Online subscription: off by default (switch feed_enabled=%s)",
    "GeoClue 服务运行中（需授权应用才有坐标）": "GeoClue service running (coordinates require an authorized application)",
    "我的位置：纬度 %.6f，经度 %.6f（精度约 %.0f 米，解算方式 %s）": "My position: latitude %.6f, longitude %.6f (accuracy about %.0f meters, resolved via %s)",
    "情况：%s": "Status: %s",
    "已通知：%s": "Notified: %s",
    "当前预警：%s": "Current alert: %s",
    "（可见但无坐标）": "(visible but without coordinates)",
    "首选基线（网络 + 基站）：%.5f,%.5f ±%.0f m（源 %d 个，权重 %s）": "Preferred baseline (network + cell tower): %.5f,%.5f ±%.0f m (%d sources, weights %s)",
    "未检测到": "Not detected",
    "最终采用：%.5f,%.5f ±%.0f m（%s）": "Final adopted: %.5f,%.5f ±%.0f m (%s)",
    "未取到（只读命令不可用或不匹配）": "Not obtained (read-only command unavailable or unmatched)",
    "开": "On",
    "关": "Off",
    "手动录入（已保存）": "Manual entry (saved)",
    "最近避险点：%s（约 %s）": "Nearest shelter: %s (about %s)",
    "最近避险点：%s（距离未知）": "Nearest shelter: %s (distance unknown)",
    "未能获取订阅源：%s（没有预警就是没有预警，不编造）": "Failed to fetch subscription source: %s (no alerts means no alerts; nothing is fabricated)",
    "%.5f,%.5f ±%.0f m": "%.5f,%.5f ±%.0f m",
    "导航 + 首选基线共同综合": "Fused: navigation + preferred baseline",
    "仅导航": "Navigation only",
    "仅网络 + 基站基线": "Network + cell-tower baseline only",
    "两源偏差 %.0f m：%s": "Two-source deviation %.0f m: %s",
    "取到 %d 个": "Obtained %d",
    "基站可见（LAC=%s CID=%s），缺基站经纬度库，无坐标": "Cell tower visible (LAC=%s CID=%s) but no coordinate database; no coordinates",
    "避险点 %d": "Shelter %d",
    "距你约 %s（事件未给影响半径，只给距离）": "About %s from you (the event gave no impact radius, only distance)",
    "（你的位置精度约 %.0f m，距离值同量级误差）": "(your position accuracy is about %.0f m; the distance carries error of the same order)",
    "两源一致": "Sources agree",
    "距中心约 %s：在影响范围内。%s": "About %s from the center: within the impact area. %s",
    "，粗估还有约 %.0f 秒到达边界": ", roughly %.0f seconds estimated to reach the boundary",
    "距中心约 %s，影响半径外 %s%s": "About %s from the center, %s%s outside the impact radius",
    "偏差超过 %.0f m，位置存疑——两套结果都在上面，请你判断": "Deviation exceeds %.0f m; position suspect — both results are shown above, please judge",
}


def po_escape(s: str) -> str:
    """Python 普通串 → PO 双引号串内容（\\ 与 \" 转义；换行拆行）。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def po_unescape(s: str) -> str:
    """PO 串内容 → Python 普通串（只反转义 \\\\/\\" 与常见 \\n \\t，中文原样）。"""
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    lines = PO.read_text(encoding="utf-8").splitlines()
    filled = 0
    skipped_have = 0
    i = 0
    out: list[str] = []
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^msgid "((?:[^"\\]|\\.)*)"$', line)
        if m and i + 1 < len(lines):
            msgid = m.group(1)
            # PO 反转义（只处理 \\ 与 \"，中文等非 ASCII 原样保留）
            key = po_unescape(msgid)
            if key in EN_SHELL:
                nxt = lines[i + 1]
                if re.match(r'^msgstr ""$', nxt):
                    val = po_escape(EN_SHELL[key])
                    out.append(line)
                    out.append(f'msgstr "{val}"')
                    filled += 1
                    i += 2
                    continue
                if nxt.startswith("msgstr "):
                    skipped_have += 1  # 已有译文，保留
        out.append(line)
        i += 1

    if not dry and filled:
        PO.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"en.po：填入 {filled} 条，已有译文跳过 {skipped_have} 条"
          f"{'（dry-run，未写）' if dry else ''}")
    # 自检：EN_SHELL 里不应有没有对应 msgid 的死键
    txt = PO.read_text(encoding="utf-8")
    dead = [k for k in EN_SHELL if f'msgid "{po_escape(k)}"' not in txt]
    if dead:
        print(f"警告：{len(dead)} 个译文键在 .po 中无对应 msgid（可能键名写错）：")
        for k in dead[:10]:
            print("  -", k[:60])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
