#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# Quantum 能级 Genmon：展示量子架构内核接口 /proc/quantum-energy 的快照。
# 数据来自 quantum-core 守护进程写入的 /run/quantum-core/state.json。
# XFCE Genmon 插件会把本脚本 stdout 首行作为面板文本，`^tooltip(...)` 作为悬停提示。
STATE=/run/quantum-core/state.json

if [ ! -r "$STATE" ]; then
	echo "Q·E: 未运行"
	echo "^tooltip(quantum-core 守护进程未运行；启动后此处显示能级快照)"
	exit 0
fi

if command -v jq >/dev/null 2>&1; then
	avail=$(jq -r '.energy.available'        "$STATE")
	coh=$(jq -r '.energy.coherence'          "$STATE")
	exc=$(jq -r '.energy.excited'            "$STATE")
	mode=$(jq -r '.energy.idle_mode'         "$STATE")
	bell=$(jq -r '.energy.bell_events'       "$STATE")
	ent=$(jq -r '.energy.entanglements'      "$STATE")
elif command -v python3 >/dev/null 2>&1; then
	read avail coh exc mode bell ent < <(python3 - "$STATE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
e=d.get('energy',{})
print(e.get('available'), e.get('coherence','-'), e.get('excited',0),
      e.get('idle_mode','-'), e.get('bell_events',0), e.get('entanglements',0))
PY
)
else
	avail=$(grep -m1 -o '"available": [a-z]*' "$STATE" | awk '{print $2}')
	coh="-"; exc="-"; mode="-"; bell="-"; ent="-"
fi

if [ "$avail" = "false" ]; then
	echo "Q·E: host(模拟)"
	echo "^tooltip(量子架构接口不可用：host 模拟/记账模型，非真实量子硬件)"
else
	echo "Q·E: 相干 $coh | 激发 $exc | 模式 $mode"
	echo "^tooltip(Bell=$bell 纠缠=$ent — 量子架构能级快照)"
fi
