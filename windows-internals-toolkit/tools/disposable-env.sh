#!/usr/bin/env bash
# disposable-env.sh —— 一次性隔离环境（手动版 chroot，零 mount 依赖）
#
# 为什么是「手动版 chroot」：真正的 chroot 要重配动态链接器、挂 /proc、/dev，
# 多数还要 root。这里换一条路达到同等隔离效果——不 chroot、不 mount、不 root：
#
#   ① 私有 HOME / TMPDIR / XDG_*：全部指向 mktemp 出的私有区，
#      工具在里面怎么折腾（缓存、配置、临时文件）都可整体抛弃；
#   ② --guard FILE：进入前整文件备份，退出时原样还原，
#      命令对真实配置的涂改全部回滚；
#   ③ --ro PATH：进入前算 sha256 清单，退出时复算比对，
#      被改动立刻报警（只报不改，改不改你说了算）。
#
# 全程只用 bash 内建 + coreutils（mktemp / cp / sha256sum / find / diff），
# 不需要 Docker、不需要 mount 权限、不需要 root。
#
# 用法：
#   disposable-env.sh CMD [ARGS...]                 # 在一次性环境里跑命令，退出即还原
#   disposable-env.sh                               # 不带命令：进交互 bash（需终端）
#   disposable-env.sh -s FOO=bar -c env.conf CMD    # 注入变量
#   disposable-env.sh -g ~/.gitconfig git ...       # 真实配置进入备份、退出还原
#   disposable-env.sh -r /etc/hosts cat /etc/hosts  # 只读校验区，改动即报警
#   disposable-env.sh --no-restore CMD              # 调试：退出不还原，保留现场
#
# 退出码：透传所跑命令的退出码；被 Ctrl-C / kill 时分别为 130 / 143。

set -uo pipefail

PROG=$(basename "$0")

usage() {  # 剥掉本脚本头部的 '# ' 注释作为用法
    awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
}

die() { echo "$PROG: $*" >&2; exit 2; }

# ---------------------------------------------------------------- 参数解析
# （此阶段的 die 尚未创建任何临时目录，直接退出即可）

SETS=()          # -s KEY=VALUE（可重复）
CONFIGS=()       # -c FILE（可重复）
GUARDS=()        # -g FILE（可重复）
ROS=()           # -r PATH（可重复）
NO_RESTORE=0

while [ $# -gt 0 ]; do
    case "$1" in
        -s|--set)
            [ $# -ge 2 ] || die "-s/--set 需要 KEY=VALUE 参数"
            SETS+=("$2"); shift 2 ;;
        --set=*)   SETS+=("${1#*=}"); shift ;;
        -c|--config)
            [ $# -ge 2 ] || die "-c/--config 需要文件参数"
            CONFIGS+=("$2"); shift 2 ;;
        --config=*) CONFIGS+=("${1#*=}"); shift ;;
        -g|--guard)
            [ $# -ge 2 ] || die "-g/--guard 需要文件参数"
            GUARDS+=("$2"); shift 2 ;;
        --guard=*) GUARDS+=("${1#*=}"); shift ;;
        -r|--ro)
            [ $# -ge 2 ] || die "-r/--ro 需要路径参数"
            ROS+=("$2"); shift 2 ;;
        --ro=*)    ROS+=("${1#*=}"); shift ;;
        -n|--no-restore) NO_RESTORE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) die "未知选项: $1（-h 看用法）" ;;
        *)  break ;;
    esac
done

# ---------------------------------------------------------------- 私有区

PRIV=$(mktemp -d "${TMPDIR:-/tmp}/disposable-env.XXXXXX") || die "mktemp 失败"
chmod 700 "$PRIV"
mkdir -p "$PRIV/home" "$PRIV/tmp" "$PRIV/run" \
         "$PRIV/xdg/cache" "$PRIV/xdg/config" "$PRIV/xdg/data" "$PRIV/xdg/state"

# ---------------------------------------------------------------- 状态初始化
# 全部先声明再装 trap：此后任何位置 die/中断，cleanup 都能安全跑完

EXPORT_SNAPSHOT="$PRIV/export-before.env"
export -p > "$EXPORT_SNAPSHOT"
NEW_KEYS=""                    # 进入前不存在的 key，退出时 unset

INJECT_KEYS=()                 # 注入报告用（去重）
GUARD_SRC=() GUARD_BAK=() GUARD_STAT=()
GUARD_DIR="$PRIV/guards" GUARD_N=0
RO_SRC=() RO_CHANGED=() RO_DIFF=()
RO_DIR="$PRIV/ro"
RC=0

# ---------------------------------------------------------------- 函数定义

valid_key() { printf '%s' "$1" | grep -q '^[A-Za-z_][A-Za-z0-9_]*$'; }

key_preexisted() {
    grep -q "^declare -x $1=" "$EXPORT_SNAPSHOT" 2>/dev/null
}

set_env() {  # set_env KEY VALUE —— 安全导出（值整体传参，不再二次展开）
    local key=$1 val=$2
    if ! key_preexisted "$key"; then
        NEW_KEYS="${NEW_KEYS:+$NEW_KEYS }$key"
    fi
    export "$key=$val"
}

inject_pair() {
    local pair=$1 key val
    case "$pair" in
        *=*) ;;
        *) die "注入项需为 KEY=VALUE 形式: $pair" ;;
    esac
    key=${pair%%=*}
    val=${pair#*=}
    valid_key "$key" || die "非法变量名: $key"
    set_env "$key" "$val"
    # 报告里去重：同一 key 重复注入只记一次
    case " ${INJECT_KEYS[*]-} " in *" $key "*) ;; *) INJECT_KEYS+=("$key") ;; esac
}

make_manifest() {  # make_manifest PATH OUTFILE —— 输出「sha256  相对路径」清单
    local p=$1 out=$2
    if [ -d "$p" ]; then
        ( cd "$p" && find . -type f -print0 | LC_ALL=C sort -z \
            | xargs -0 -r sha256sum ) > "$out" 2>/dev/null
    elif [ -f "$p" ]; then
        ( cd "$(dirname "$p")" && sha256sum "$(basename "$p")" ) > "$out" 2>/dev/null
    else
        echo "__MISSING__" > "$out"
    fi
}

# shellcheck disable=SC2317  # 由 cleanup 经 trap 间接调用
restore_guards() {
    local i
    for i in "${!GUARD_SRC[@]}"; do
        [ -n "${GUARD_STAT[$i]}" ] && continue
        if cp -a "${GUARD_BAK[$i]}" "${GUARD_SRC[$i]}" 2>/dev/null; then
            GUARD_STAT[i]="restored"
        else
            GUARD_STAT[i]="FAILED"
        fi
    done
}

# shellcheck disable=SC2317  # 由 cleanup 经 trap 间接调用
check_ro() {
    local i d
    for i in "${!RO_SRC[@]}"; do
        make_manifest "${RO_SRC[$i]}" "$RO_DIR/$i.after"
        # 结果先固化进内存：cleanup 末尾会删掉 $PRIV，届时文件已不可读
        if d=$(diff -u --label "进入前" --label "退出时" \
                "$RO_DIR/$i.before" "$RO_DIR/$i.after" 2>/dev/null); then
            RO_CHANGED[i]=0
            RO_DIFF[i]=""
        else
            RO_CHANGED[i]=1
            RO_DIFF[i]=$d
        fi
    done
}

# shellcheck disable=SC2317  # 由 cleanup 经 trap 间接调用
restore_exports() {
    eval "$(cat "$EXPORT_SNAPSHOT")" 2>/dev/null || true
    local k
    for k in $NEW_KEYS; do
        unset "$k" 2>/dev/null || true
    done
    NEW_KEYS=""
}

# shellcheck disable=SC2317  # 由 trap 间接调用
cleanup() {
    local rc=$?
    RC=$rc   # EXIT trap 进入时的 $? 即真实退出码（signal 时为 130/143）

    if [ "$NO_RESTORE" -eq 1 ]; then
        check_ro   # ro 校验只读、无副作用，调试模式下同样给出结论
        echo "================ 一次性环境退出报告（--no-restore：保留现场）================"
        echo "  私有区保留  : $PRIV"
        echo "  HOME/TMPDIR/XDG_* 未还原（进程已退出，不影响后续 shell）"
        if [ ${#RO_SRC[@]} -gt 0 ]; then
            echo "  ro 校验     :"
            for i in "${!RO_SRC[@]}"; do
                if [ "${RO_CHANGED[$i]}" = "1" ]; then
                    echo "    - ${RO_SRC[$i]}（已变更！）"
                else
                    echo "    - ${RO_SRC[$i]}（无变更）"
                fi
            done
        fi
        echo "  退出码      : $RC"
        echo "==========================================================================="
        exit "$RC"
    fi

    check_ro            # 先于 guard 还原：避免回滚动作本身污染 ro 比对
    restore_guards
    restore_exports
    rm -rf "$PRIV"

    echo "================ 一次性环境退出报告 ================"
    [ ${#INJECT_KEYS[@]} -gt 0 ] && echo "  注入变量    : ${INJECT_KEYS[*]}"
    echo "  私有区      : $PRIV（已删除）"
    echo "  HOME/TMPDIR/XDG_* 已还原"
    if [ ${#GUARD_SRC[@]} -gt 0 ]; then
        echo "  guard 还原  :"
        for i in "${!GUARD_SRC[@]}"; do
            case "${GUARD_STAT[$i]}" in
                dup)      echo "    - ${GUARD_SRC[$i]}（重复指定，已跳过）" ;;
                restored) echo "    - ${GUARD_SRC[$i]}（已还原）" ;;
                FAILED)   echo "    - ${GUARD_SRC[$i]}（还原失败！请检查 $GUARD_DIR）" ;;
                *)        echo "    - ${GUARD_SRC[$i]}（未处理）" ;;
            esac
        done
    fi
    if [ ${#RO_SRC[@]} -gt 0 ]; then
        echo "  ro 校验     :"
        for i in "${!RO_SRC[@]}"; do
            if [ "${RO_CHANGED[$i]}" = "1" ]; then
                echo "    - ${RO_SRC[$i]}（已变更！）"
            else
                echo "    - ${RO_SRC[$i]}（无变更）"
            fi
        done
        for i in "${!RO_SRC[@]}"; do
            [ "${RO_CHANGED[$i]}" = "1" ] || continue
            echo "  --- ${RO_SRC[$i]} 变更明细 ---"
            printf '%s\n' "${RO_DIFF[$i]}" | sed 's/^/  /'
        done
    fi
    echo "  退出码      : $RC"
    echo "=================================================="
    exit "$RC"
}

# trap 最后设置：此时私有区、快照、状态、函数全部就绪，
# 此后的任何 die / 信号 / 正常退出，清理与还原都有保障。
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ---------------------------------------------------------------- 变量注入：-c 先行，-s 覆盖

for cfg in "${CONFIGS[@]}"; do
    [ -f "$cfg" ] || die "配置文件不存在: $cfg"
    lineno=0
    while IFS= read -r line || [ -n "$line" ]; do
        lineno=$((lineno + 1))
        line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        case "$line" in ''|\#*) continue ;; esac
        inject_pair "$line" || die "配置 $cfg 第 $lineno 行无效: $line"
    done < "$cfg"
done

for pair in "${SETS[@]}"; do
    inject_pair "$pair"
done

# ---------------------------------------------------------------- 私有 HOME / TMPDIR / XDG_*

set_env HOME            "$PRIV/home"
set_env TMPDIR          "$PRIV/tmp"
set_env XDG_CACHE_HOME  "$PRIV/xdg/cache"
set_env XDG_CONFIG_HOME "$PRIV/xdg/config"
set_env XDG_DATA_HOME   "$PRIV/xdg/data"
set_env XDG_STATE_HOME  "$PRIV/xdg/state"
set_env XDG_RUNTIME_DIR "$PRIV/run"
chmod 700 "$PRIV/run"

# ---------------------------------------------------------------- guard：进入备份 / 退出还原

for g in "${GUARDS[@]}"; do
    [ -f "$g" ] || die "--guard 目标不是已存在的文件: $g"
    src=$(realpath -m "$g")
    dup=0
    for i in "${!GUARD_SRC[@]}"; do
        [ "${GUARD_SRC[$i]}" = "$src" ] && dup=1
    done
    if [ "$dup" -eq 1 ]; then
        GUARD_SRC+=("$src"); GUARD_BAK+=(""); GUARD_STAT+=("dup")
        continue
    fi
    mkdir -p "$GUARD_DIR"
    GUARD_N=$((GUARD_N + 1))
    bak="$GUARD_DIR/$GUARD_N.bak"
    cp -a "$src" "$bak" || die "备份失败: $src"
    GUARD_SRC+=("$src")
    GUARD_BAK+=("$bak")
    GUARD_STAT+=("")
done

# ---------------------------------------------------------------- ro：进入前算 sha256 清单

for r in "${ROS[@]}"; do
    mkdir -p "$RO_DIR"
    make_manifest "$r" "$RO_DIR/${#RO_SRC[@]}.before"
    RO_SRC+=("$(realpath -m "$r")")
done

# ---------------------------------------------------------------- 执行

if [ $# -eq 0 ]; then
    # 交互模式：进隔离 bash，退出后自动还原
    if [ -t 0 ] && [ -t 1 ]; then
        echo "$PROG: 已进入一次性隔离环境（HOME=$HOME，退出自动还原）"
        bash
        RC=$?
    else
        die "未指定命令且标准输入不是终端；请给出要执行的命令"
    fi
else
    "$@"
    RC=$?
fi

exit "$RC"
