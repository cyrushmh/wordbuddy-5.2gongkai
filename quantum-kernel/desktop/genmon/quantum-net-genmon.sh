#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# Quantum Net Genmon：展示量子网卡（QNIC）组网快照 /proc/quantum-net。
# 数据来自 quantum-core 守护进程写入的 /run/quantum-core/state.json。
# XFCE Genmon 插件会把本脚本 stdout 首行作为面板文本，`^tooltip(...)` 作为悬停提示。
STATE=/run/quantum-core/state.json

if [ ! -r "$STATE" ]; then
	echo "Q·NET: 未运行"
	echo "^tooltip(quantum-core 守护进程未运行；启动后此处显示量子组网快照)"
	exit 0
fi

if command -v jq >/dev/null 2>&1; then
	avail=$(jq -r '.net.available'        "$STATE")
	nics=$(jq -r '.net.nics'              "$STATE")
	mode=$(jq -r '.net.mode'              "$STATE")
	links=$(jq -r '.net.links'            "$STATE")
	peers=$(jq -r '.net.peers'            "$STATE")
	ent=$(jq -r '.net.entanglements'      "$STATE")
	gaia=$(jq -r '.net.gaia_level'        "$STATE")
elif command -v python3 >/dev/null 2>&1; then
	read avail nics mode links peers ent gaia < <(python3 - "$STATE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
n=d.get('net',{})
print(n.get('available'), n.get('nics',0), n.get('mode','-'),
      n.get('links',0), n.get('peers',0), n.get('entanglements',0),
      n.get('gaia_level',0))
PY
)
else
	avail=$(grep -m1 -o '"available": [a-z]*' "$STATE" | awk '{print $2}')
	nics="-"; mode="-"; links="-"; peers="-"; ent="-"; gaia="-"
fi

if [ "$avail" = "false" ]; then
	echo "Q·NET: host(模拟)"
	echo "^tooltip(量子网卡接口不可用：host 模拟/记账模型，非真实量子硬件)"
else
	echo "Q·NET: $mode | QNIC $nics | 链路 $links"
	echo "^tooltip(对等=$peers 纠缠=$ent 盖亚层=$gaia — 量子组网快照)"
fi
