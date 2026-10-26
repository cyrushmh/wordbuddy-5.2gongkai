#!/bin/sh
# SPDX-License-Identifier: GPL-2.0
#
# 向 XFCE 面板（默认 panel-1）添加三个 Quantum Genmon 小程序。
# 需在已运行的 XFCE 会话内执行（依赖 xfconf-query）。幂等：已存在则跳过。
set -eu

if ! command -v xfconf-query >/dev/null 2>&1; then
	echo "xfconf-query 不可用：请在 XFCE 会话内运行此脚本。" >&2
	exit 1
fi

PANEL="/panels/panel-1"
PLUGIN_IDS_KEY="$PANEL/plugin-ids"

# 读取现有插件 id 列表（无则初始化为空数组）。
if ! ids=$(xfconf-query -c xfce4-panel -p "$PLUGIN_IDS_KEY" 2>/dev/null); then
	ids=""
fi

max_id=0
for id in $ids; do
	[ "$id" -gt "$max_id" ] 2>/dev/null && max_id=$id || true
done

add_genmon() {
	name="$1"; cmd="$2"; tooltip="$3"
	# 已存在相同命令的 genmon 则跳过。
	if xfconf-query -c xfce4-panel -p "$PANEL/plugin-ids" >/dev/null 2>&1; then
		for id in $ids; do
			cur=$(xfconf-query -c xfce4-panel -p "$PANEL/plugin-$id/cmd" 2>/dev/null || true)
			[ "$cur" = "$cmd" ] && { echo "已存在：$name ($cmd)"; return 0; }
		done
	fi
	new_id=$((max_id + 1)); max_id=$new_id
	xfconf-query -c xfce4-panel -p "$PANEL/plugin-ids" -t int -s "$new_id" 2>/dev/null || \
		xfconf-query -c xfce4-panel -p "$PANEL/plugin-ids" -t int -s "$new_id" --create 2>/dev/null
	xfconf-query -c xfce4-panel -p "$PANEL/plugin-$new_id" --create -t int -s 15 2>/dev/null
	xfconf-query -c xfce4-panel -p "$PANEL/plugin-$new_id/cmd"       -t string -s "$cmd"     --create 2>/dev/null
	xfconf-query -c xfce4-panel -p "$PANEL/plugin-$new_id/label"     -t string -s "$name"     --create 2>/dev/null
	xfconf-query -c xfce4-panel -p "$PANEL/plugin-$new_id/use-tooltip" -t bool -s true        --create 2>/dev/null
	echo "已添加：$name -> panel plugin #$new_id ($cmd)"
}

add_genmon "Quantum Energy"  "/usr/lib/quantum-core/genmon/quantum-energy-genmon.sh" "量子能级快照"
add_genmon "Quantum QPU"     "/usr/lib/quantum-core/genmon/quantum-qpu-genmon.sh"    "QPU 链路统计"
add_genmon "Quantum Net"     "/usr/lib/quantum-core/genmon/quantum-net-genmon.sh"    "量子组网快照"
