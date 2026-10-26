#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
#
# Quantum QPU Genmon：展示量子处理单元 /dev/qpu0 的链路统计（ioctl QPU_LINK_STATS）。
# 数据来自 quantum-core 守护进程写入的 /run/quantum-core/state.json。
STATE=/run/quantum-core/state.json

if [ ! -r "$STATE" ]; then
	echo "Q·QPU: 未运行"
	echo "^tooltip(quantum-core 守护进程未运行；启动后此处显示 QPU 链路统计)"
	exit 0
fi

if command -v jq >/dev/null 2>&1; then
	avail=$(jq -r '.qpu.available'    "$STATE")
	slots=$(jq -r '.qpu.slots'        "$STATE")
	buffered=$(jq -r '.qpu.buffered'  "$STATE")
	writes=$(jq -r '.qpu.total_writes' "$STATE")
	overwrites=$(jq -r '.qpu.overwrites' "$STATE")
elif command -v python3 >/dev/null 2>&1; then
	read avail slots buffered writes overwrites < <(python3 - "$STATE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
q=d.get('qpu',{})
print(q.get('available'), q.get('slots',0), q.get('buffered',0),
      q.get('total_writes',0), q.get('overwrites',0))
PY
)
else
	avail=$(grep -m1 -o '"available": [a-z]*' "$STATE" | awk '{print $2}')
	slots="-"; buffered="-"; writes="-"; overwrites="-"
fi

if [ "$avail" = "false" ]; then
	echo "Q·QPU: host(模拟)"
	echo "^tooltip(量子架构 QPU 接口不可用：host 模拟/记账模型，非真实量子硬件)"
else
	echo "Q·QPU: slots $slots | buf $buffered | 覆盖 $overwrites"
	echo "^tooltip(总写入=$writes 覆盖=$overwrites — 量子处理单元链路统计)"
fi
