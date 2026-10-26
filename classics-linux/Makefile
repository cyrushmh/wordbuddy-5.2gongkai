# classics 构建文件
#
# 技巧（取自 Debian 官方 dpkg make 片段与 gzip 范式，现代化简化）：
#   1) include architecture.mk 后，用 DEB_HOST_GNU_TYPE 选择编译器——
#      原生 x86_64-linux-gnu-gcc 与交叉 aarch64-linux-gnu-gcc 均存在，
#      故统一用 host 前缀，原生/交叉一套代码。
#   2) include buildflags.mk 自动注入 dpkg-buildflags 的 hardening 默认值
#      （-D_FORTIFY_SOURCE=3 / -fstack-protector-strong / -fcf-protection /
#       -Wl,-z,relro / LTO 等），无需手写。
#   3) 仅在 CC 未由外部环境指定时才覆盖，尊重 CC=clang 等用法。

# 可移植性：Debian/Ubuntu 提供 /usr/share/dpkg/*.mk，Arch/Fedora/其他发行版没有。
# 故用 wildcard 探测后再 include——同一份 Makefile 在 Debian 系走 hardening 默认值，
# 在非 Debian 系（Arch 的 PKGBUILD、手工构建）退化为下面手写的安全默认，行为不崩。
DPKG_MK := $(wildcard /usr/share/dpkg/architecture.mk)

ifneq ($(DPKG_MK),)
include /usr/share/dpkg/architecture.mk
ifneq (,$(filter $(origin CC),default undefined))
  CC = $(DEB_HOST_GNU_TYPE)-gcc
endif
include /usr/share/dpkg/buildflags.mk
# 额外维护标志：明确打开全部 hardening（noble 默认已开，写在此处显式可控）
export DEB_BUILD_MAINT_OPTIONS = hardening=+all
# dpkg-buildflags 对 armel/mips/mipsel/mips64/mips64el/powerpc 六个架构默认
# 不注入 PIE（lintian 报 hardening-no-pie）。实测这些架构的交叉 gcc 均支持
# -fPIE/-pie（产出 Type: DYN），显式补齐，保证全架构 hardening 口径一致。
ifneq (,$(filter $(DEB_HOST_ARCH),armel mips mipsel mips64 mips64el powerpc))
CFLAGS += -fPIE
LDFLAGS += -pie
endif
else
# 非 Debian 系的安全默认值（对齐 dpkg-buildflags 的 hardening 口径）
CC       ?= cc
CPPFLAGS ?= -D_FORTIFY_SOURCE=3
CFLAGS   ?= -O2 -Wall -Wextra -fstack-protector-strong -fstack-clash-protection
LDFLAGS  ?= -Wl,-z,relro -Wl,-z,now
endif

BINDIR  ?= /usr/bin
DATADIR ?= /usr/share/classics
BIN      = classics
SRC      = src/classics.c

# 编译/链接严格按 dpkg-buildflags 顺序：CPPFLAGS → CFLAGS → LDFLAGS
$(BIN): $(SRC)
	$(CC) $(CPPFLAGS) $(CFLAGS) -DDATADIR=\"$(DATADIR)\" -o $@ $< $(LDFLAGS)

all: $(BIN)

# 拆分安装目标：为「架构相关主包」+「arch=any 数据子包」的分包结构服务。
# 借鉴 man-pages-zh_cn（arch=any 纯文档包）：把不随架构变化的内容单独成包，
# 避免在 amd64/arm64/riscv64 上重复打包同一份数据。
install-bin: $(BIN)
	install -d $(DESTDIR)$(BINDIR)
	install -m 0755 $(BIN) $(DESTDIR)$(BINDIR)/$(BIN)

install-data:
	install -d $(DESTDIR)$(DATADIR)
	install -m 0644 data/*.txt $(DESTDIR)$(DATADIR)/

install: install-bin install-data

clean:
	rm -f $(BIN)

.PHONY: all install install-bin install-data clean
