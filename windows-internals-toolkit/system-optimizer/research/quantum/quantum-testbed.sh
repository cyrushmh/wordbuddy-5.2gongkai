#!/usr/bin/env bash
# quantum-testbed.sh —— 量子架构补丁链的 chroot 测试床（v0.6.81，docs/79）。
#
# 目的：把「量子架构内核补丁」放进一个干净的 Debian bookworm chroot 里复验构建，
# 避免污染 /workspace 工作树，也给补丁链一个可重复的验收环境。
#
# 默认轻量路径（minbase）：
#   stage1  debootstrap --variant=minbase bookworm（ROOTFS 默认 /tmp，绝不落 /workspace）
#   stage2  chroot 内复验量子概念系统构建（python3 build_quantum.py --check）——
#           干净 Debian bookworm + 系统 python3 下重建 quantum_taxonomy.json 并校验，
#           证明构建不依赖宿主环境特殊包
#   stage3  initrd 演示（mkinitramfs；宿主缺 initramfs-tools 时尝试安装，仍缺则
#           如实挂 needs_action，退出码 4，不假装成功）
#
# 诚实边界（与 research/quantum/build_quantum.py 一致）：
#   * chroot 是验收环境，不是量子硬件；宿主工具链产出宿主机器码的边界不变。
#   * stage3 只是 initramfs 生成演示，不启动、不声称引导任何量子架构内核。
#   * 任何阶段缺少工具/网络/磁盘，脚本以非零退出码 + 明确原因结束，不静默跳过。
#
# 用法：
#   quantum-testbed.sh check                # 只读体检：报告 debootstrap/mkinitramfs/网络/磁盘
#   quantum-testbed.sh stage1               # debootstrap minbase（幂等：已存在则跳过）
#   quantum-testbed.sh stage2               # chroot 内构建复验
#   quantum-testbed.sh stage3               # initrd 演示（可失败，失败即 needs_action）
#   quantum-testbed.sh all                  # stage1 → stage2 → stage3
#   quantum-testbed.sh clean                # 删除 ROOTFS（仅限 /tmp 下默认路径）
#
# 环境变量：
#   QUANTUM_TESTBED_ROOT   ROOTFS 路径（默认 /tmp/quantum-testbed/rootfs；拒绝 /workspace）
#   QUANTUM_TESTBED_MIRROR debootstrap 镜像（默认阿里云源；2026-10-25 实测：aliyun/ustc/
#                          tencent 三源 debootstrap 全量 0 失败，清华源偶发 CDN 403 约 10%，
#                          故默认不用清华；可用 QUANTUM_TESTBED_MIRROR 覆盖）
set -euo pipefail

VERSION="0.6.81"
ROOTFS="${QUANTUM_TESTBED_ROOT:-/tmp/quantum-testbed/rootfs}"
MIRROR="${QUANTUM_TESTBED_MIRROR:-https://mirrors.aliyun.com/debian}"
SUITE="bookworm"
VARIANT="minbase"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_TAG="[quantum-testbed]"

log()  { printf '%s %s\n' "$LOG_TAG" "$*"; }
err()  { printf '%s 错误：%s\n' "$LOG_TAG" "$*" >&2; }
die()  { err "$*"; exit 1; }

# ---- 安全护栏：ROOTFS 绝不落 /workspace ----
guard_rootfs() {
    case "$ROOTFS" in
        /workspace|/workspace/*)
            die "ROOTFS 拒绝指向 /workspace（$ROOTFS）；测试床是临时环境，不得污染工作树" ;;
        /tmp|/tmp/*)
            : # 允许
            ;;
        *)
            die "ROOTFS 只接受 /tmp 下的路径（当前：$ROOTFS）；如需他处请显式设 QUANTUM_TESTBED_ROOT" ;;
    esac
}

# ---- check：只读体检 ----
cmd_check() {
    log "体检（v$VERSION）"
    local ok=0
    if command -v debootstrap >/dev/null 2>&1; then
        log "  debootstrap: $(command -v debootstrap)"
    else
        log "  debootstrap: 缺失（Debian/Ubuntu: apt-get install debootstrap）"; ok=1
    fi
    if command -v mkinitramfs >/dev/null 2>&1; then
        log "  mkinitramfs: $(command -v mkinitramfs)"
    else
        log "  mkinitramfs: 缺失（Debian/Ubuntu: apt-get install initramfs-tools）→ stage3 将挂 needs_action"
    fi
    if [ "$(id -u)" -eq 0 ]; then
        log "  权限: root（debootstrap/chroot 需要）"
    else
        log "  权限: 非 root（debootstrap/chroot 需要 root 或 fakeroot）"; ok=1
    fi
    if curl -fsS --max-time 8 -o /dev/null "$MIRROR/dists/$SUITE/Release" 2>/dev/null; then
        log "  镜像: $MIRROR 可达"
    else
        log "  镜像: $MIRROR 不可达（stage1 需要网络）"; ok=1
    fi
    local avail_kib
    avail_kib=$(df -Pk /tmp | awk 'NR==2{print $4}')
    log "  /tmp 可用: $((avail_kib / 1024)) MiB（minbase 约需 300MiB + 构建缓存）"
    log "  ROOTFS: $ROOTFS"
    if [ -d "$ROOTFS" ] && [ -d "$ROOTFS/bin" ]; then
        log "  ROOTFS 状态: 已stage1（stage2 可跑）"
    else
        log "  ROOTFS 状态: 未初始化（先 stage1）"
    fi
    return $ok
}

# ---- stage1：debootstrap minbase ----
# 镜像 CDN 对同一 IP 偶发 403/限流（实测清华源 20 连发约 10% 失败率，重试即恢复），
# debootstrap 本身无重试，这里用外层有限重试吸收；apt 走 Acquire::Retries。
cmd_stage1() {
    guard_rootfs
    command -v debootstrap >/dev/null 2>&1 || die "缺 debootstrap，先 apt-get install debootstrap"
    [ "$(id -u)" -eq 0 ] || die "debootstrap 需要 root"
    mkdir -p "$(dirname "$ROOTFS")"
    if [ -d "$ROOTFS/bin" ] && [ -x "$ROOTFS/bin/bash" ]; then
        log "stage1: ROOTFS 已存在且可用，跳过（幂等）"
        return 0
    fi
    local attempt=1 max=3
    while [ "$attempt" -le "$max" ]; do
        log "stage1: debootstrap $VARIANT $SUITE → $ROOTFS（镜像 $MIRROR，第 $attempt/$max 次）"
        rm -rf "$ROOTFS"
        if debootstrap --variant="$VARIANT" "$SUITE" "$ROOTFS" "$MIRROR"; then
            break
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -le "$max" ]; then
            log "stage1: 本次失败（镜像偶发限流），10s 后重试"
            sleep 10
        else
            die "stage1 三次均失败——镜像限流/网络问题；稍后重跑，或 QUANTUM_TESTBED_MIRROR 换源"
        fi
    done
    # minbase 无 python3；stage2 需要，装进来（apt 在 chroot 内跑，不动宿主）
    log "stage1: chroot 内安装 python3（minbase 默认不含）"
    chroot "$ROOTFS" /bin/true 2>/dev/null || die "chroot 冒烟失败"
    cp /etc/resolv.conf "$ROOTFS/etc/resolv.conf" 2>/dev/null || true
    chroot "$ROOTFS" apt-get -o Acquire::Retries=3 update -qq
    chroot "$ROOTFS" apt-get -o Acquire::Retries=3 install -y -qq --no-install-recommends python3 ca-certificates
    log "stage1: 完成（python3 $(chroot "$ROOTFS" python3 -V 2>&1)）"
}

# ---- stage2：chroot 内构建复验 ----
cmd_stage2() {
    guard_rootfs
    [ -x "$ROOTFS/bin/bash" ] || die "ROOTFS 未初始化，先跑 stage1"
    local stage="$ROOTFS/tmp/testbed"
    log "stage2: 布置构建源（$stage）"
    rm -rf "$stage"
    mkdir -p "$stage/research/quantum" \
             "$stage/src/python/sysweeper/concepts" \
             "$stage/src/python/sysweeper/data/concepts"
    cp "$REPO_ROOT/research/quantum/build_quantum.py" "$stage/research/quantum/"
    # build_quantum.py --check 需要 sysweeper.concepts._common（跨系统桥接校验），
    # 且 load_other 读 data/concepts/ 下全部 taxonomy——按真实相对结构布置。
    # 注意：不拷 sysweeper/__init__.py——它会 import _zipres/version/registry 全家，
    # 与概念桥接校验无关；缺 __init__.py 时 sysweeper 退化为 namespace package，
    # `from sysweeper.concepts import _common` 照常工作（concepts/ 有真 __init__.py）。
    cp "$REPO_ROOT/src/python/sysweeper/concepts/__init__.py" \
       "$REPO_ROOT/src/python/sysweeper/concepts/_common.py" \
       "$stage/src/python/sysweeper/concepts/"
    cp "$REPO_ROOT"/src/python/sysweeper/data/concepts/*_taxonomy.json \
       "$stage/src/python/sysweeper/data/concepts/"
    log "stage2: chroot 内 python3 build_quantum.py --check（干净 bookworm 复验）"
    chroot "$ROOTFS" /usr/bin/python3 /tmp/testbed/research/quantum/build_quantum.py --check
    log "stage2: 通过——磁盘 JSON 与构建脚本一致，且不依赖宿主环境特殊包"
}

# ---- stage3：initrd 演示（可失败：失败即 needs_action） ----
cmd_stage3() {
    guard_rootfs
    [ -x "$ROOTFS/bin/bash" ] || die "ROOTFS 未初始化，先跑 stage1"
    if ! command -v mkinitramfs >/dev/null 2>&1; then
        log "stage3: 宿主缺 mkinitramfs，尝试 apt-get install initramfs-tools（需网络）"
        if ! apt-get install -y -qq initramfs-tools; then
            err "stage3 needs_action：宿主仍无 mkinitramfs（initramfs-tools 不可得）。"
            err "  initrd 演示未实跑；不假装成功。补齐后重跑 stage3 即可。"
            exit 4
        fi
    fi
    log "stage3: chroot 内安装 initramfs-tools + zstd"
    chroot "$ROOTFS" apt-get -o Acquire::Retries=3 install -y -qq --no-install-recommends initramfs-tools zstd
    # initrd 演示：用宿主当前内核的模块树喂给 chroot（无 /boot 内核的 minbase）
    local kver modules_src
    kver="$(uname -r)"
    if [ -d "/lib/modules/$kver" ]; then
        modules_src="/lib/modules/$kver"
        log "stage3: 复用宿主内核模块 $kver（仅演示 initramfs 生成，不声称可引导）"
    else
        log "stage3: 宿主无 /lib/modules/$kver，用 linux-base 的空模块树演示打包流程"
        modules_src=""
        chroot "$ROOTFS" apt-get -o Acquire::Retries=3 install -y -qq --no-install-recommends linux-base
    fi
    # mkinitramfs 按 /boot/config-<kver> 选压缩器（缺 config 报 RD_GZIP not supported）；
    # 宿主 config 在 /lib/modules/<kver>/config，拷过去
    local out="$ROOTFS/tmp/initrd-demo.img"
    if [ -n "$modules_src" ]; then
        mkdir -p "$ROOTFS/lib/modules" "$ROOTFS/boot"
        rm -rf "$ROOTFS/lib/modules/$kver"
        cp -a "$modules_src" "$ROOTFS/lib/modules/$kver"
        if [ -f "$modules_src/config" ]; then
            cp "$modules_src/config" "$ROOTFS/boot/config-$kver"
        fi
        chroot "$ROOTFS" mkinitramfs -o /tmp/initrd-demo.img "$kver" || {
            err "stage3 needs_action：chroot 内 mkinitramfs 失败（见上）。"
            err "  initrd 演示未完成；这是演示环境限制，不影响 stage1/stage2 结论。"
            exit 4
        }
    else
        # 无内核模块：depmod 空跑后 mkinitramfs 仍可产出一个最小 initramfs
        chroot "$ROOTFS" sh -c 'mkdir -p /lib/modules /boot && depmod -a 2>/dev/null || true'
        chroot "$ROOTFS" mkinitramfs -o /tmp/initrd-demo.img || {
            err "stage3 needs_action：chroot 内 mkinitramfs 失败（无可用内核模块树）。"
            err "  initrd 演示未完成；这是演示环境限制，不影响 stage1/stage2 结论。"
            exit 4
        }
    fi
    log "stage3: initrd 演示产物 $(du -h "$out" | cut -f1) → $out"
    log "stage3: 注意——仅为 initramfs 生成演示；不启动、不引导、不声称量子硬件"
}

# ---- clean：仅清理 /tmp 下 ROOTFS ----
cmd_clean() {
    guard_rootfs
    log "clean: 删除 $ROOTFS"
    rm -rf "$ROOTFS"
    log "clean: 完成"
}

usage() {
    sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

main() {
    local cmd="${1:-check}"
    case "$cmd" in
        check)  cmd_check ;;
        stage1) cmd_stage1 ;;
        stage2) cmd_stage2 ;;
        stage3) cmd_stage3 ;;
        all)    cmd_stage1; cmd_stage2; cmd_stage3 ;;
        clean)  cmd_clean ;;
        -h|--help|help) usage ;;
        *) err "未知子命令：$cmd"; usage; exit 2 ;;
    esac
}

main "$@"
