#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# 量子桌面设置入口：展示 quantum-core 守护进程接口状态与诚实边界。
# 优先用 zenity 弹出图形窗口；无 zenity 时退化为终端输出。
STATE=/run/quantum-core/state.json

if [ -r "$STATE" ]; then
	if command -v jq >/dev/null 2>&1; then
		body=$(jq -r '
			"模型: \(.model)\n" +
			"能级接口可用: \(.energy.available)\n" +
			"  cpu=\(.energy.cpu) 模式=\(.energy.idle_mode) 激发=\(.energy.excited)\n" +
			"  相干=\(.energy.coherence) Bell=\(.energy.bell_events) 纠缠=\(.energy.entanglements)\n" +
			"QPU 接口可用: \(.qpu.available)\n" +
			"  slots=\(.qpu.slots) buffered=\(.qpu.buffered) 覆盖=\(.qpu.overwrites)\n" +
			"组网接口可用: \(.net.available)\n" +
			"  QNIC=\(.net.nics) 模式=\(.net.mode) 链路=\(.net.links) 对等=\(.net.peers)\n" +
			"  纠缠=\(.net.entanglements) 拓扑变化=\(.net.topology_changes) 盖亚层=\(.net.gaia_level)\n" +
			"说明: \(.note)"
		' "$STATE")
	else
		body=$(cat "$STATE")
	fi
else
	body="quantum-core 守护进程未运行（/run/quantum-core/state.json 不存在）。
启动会话后 autostart 会自动拉起 quantum-core；或在终端运行 quantum-core --once 生成快照。"
fi

header="Quantum Desktop (ARCH=quantum)"
if command -v zenity >/dev/null 2>&1; then
	zenity --info --title "$header" --width 480 --text "$body" 2>/dev/null || \
		printf '%s\n\n%s\n' "$header" "$body"
else
	printf '%s\n\n%s\n' "$header" "$body"
fi
