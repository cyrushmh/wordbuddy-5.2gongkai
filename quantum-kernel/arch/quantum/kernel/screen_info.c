// SPDX-License-Identifier: GPL-2.0
/*
 * arch/quantum/kernel/screen_info.c — screen_info 全局量定义。
 *
 * 模拟架构没有真实 VGA/EFI 显示硬件，screen_info 恒为全零（BSS）。
 * ≤6.11 分支的 drivers/video/console/Kconfig 对 VGA_CONSOLE 采用旧式
 * 负向依赖表（default y），quantum 不在排除名单内，vgacon.o 会被纳入
 * 构建并引用本符号；6.12+ 起 VGA_CONSOLE 改为白名单依赖，本文件按
 * hexagon 同型口径仅在 CONFIG_VGA_CONSOLE 下编译。
 */
#include <linux/screen_info.h>

struct screen_info screen_info;
