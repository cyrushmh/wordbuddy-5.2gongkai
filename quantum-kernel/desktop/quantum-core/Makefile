# SPDX-License-Identifier: GPL-2.0
#
# quantum-core 守护进程构建。
#
# DBus 为可选依赖：若宿主机有 dbus-1 开发包（pkg-config 可见），则编译进 DBus
# 支持（org.quantum.Core 接口）；否则降级为仅写 /run/quantum-core/state.json。
# 这样在最小构建环境（如沙箱、交叉编译）也能编译通过。

CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra -std=c11
TARGET   = quantum-core

# DBus 为可选依赖：仅当 pkg-config 能定位 dbus-1（含正确的 -I）时启用，
# 否则降级为仅写 /run/quantum-core/state.json。这样最小构建环境也能编译通过。
DBUS_PRESENT = $(shell pkg-config --exists dbus-1 2>/dev/null && echo 1 || echo 0)
ifeq ($(DBUS_PRESENT),1)
  DBUS_DEFS   = -DHAVE_DBUS
  DBUS_CFLAGS = $(shell pkg-config --cflags dbus-1 2>/dev/null)
  DBUS_LIBS   = $(shell pkg-config --libs dbus-1 2>/dev/null)
endif

# 调试：显示 DBus 探测结果（构建无 dbus 时 DBUS_DEFS 为空属正常降级）。
$(info DBUS_PRESENT=$(DBUS_PRESENT) DBUS_DEFS=$(DBUS_DEFS) DBUS_CFLAGS=$(DBUS_CFLAGS))

SRCS = src/quantum_core.c src/quantum_parse.c

all: $(TARGET)

$(TARGET): $(SRCS) src/quantum_parse.h src/quantum_uapi.h
	$(CC) $(CFLAGS) $(DBUS_DEFS) $(DBUS_CFLAGS) -o $@ $(SRCS) $(DBUS_LIBS)

# 单元测试：宿主即可跑，无需量子内核（用内嵌 mock /proc 文本）。
check: test_parse
	./test_parse

test_parse: src/test_parse.c src/quantum_parse.c src/quantum_parse.h
	$(CC) $(CFLAGS) -o $@ src/test_parse.c src/quantum_parse.c

# 单次快照（调试用）：读一次接口写一次 state.json 即退出。
run-once: $(TARGET)
	./$(TARGET) --once

clean:
	rm -f $(TARGET) test_parse

.PHONY: all check clean run-once
