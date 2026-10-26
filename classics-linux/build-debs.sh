#!/usr/bin/env bash
#
# 按"硬件架构 × 发行版本"矩阵构建 classics Debian 包。
#  架构：amd64（原生）/ arm64（交叉 aarch64-linux-gnu-gcc）
#        / armhf（交叉 arm-linux-gnueabihf-gcc）
#  版本：noble(24.04) / jammy(22.04) / bookworm(Debian 12) / trixie(Debian 13)
#        → 通过 changelog 的 version + distribution 字段区分（3.0 native 无连字符版本）。
#  依赖修正：交叉构建的 libc 下限由 debian/rules 的 override_dh_gencontrol
#        按 objdump 实测符号版本改写（工具链 shlibs 无 .symbols 会钉死过高版本）。
#
set -u
PKG="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$PKG/.." && pwd)"
OUT="$PKG/build"
mkdir -p "$OUT"
MAINT="WordBuddy Authors <noreply@example.com>"

# 发行版 → 版本号（去中心化 odometer：NNNN.NNNN.NNNN.NNNN.YYYYMMDD + 发行版修订后缀；
# 迁移首版 A 段置 1 保证 dpkg 版本序不降级，见 system-optimizer docs/56）
declare -A VER=(
  [noble]="0001.0000.0000.0000.20261024ubuntu1"
  [jammy]="0001.0000.0000.0000.20261024~jammy1"
  [bookworm]="0001.0000.0000.0000.20261024~bpo12+1"
  [trixie]="0001.0000.0000.0000.20261024"
)

gen_changelog() {
  local ver="$1" dist="$2" date
  date="$(date -R)"
  cat > "$PKG/debian/changelog" <<EOF
classics ($ver) $dist; urgency=medium

  * 初始发布：classics CLI（典籍阅读 + 乱码安全解码）。
  * 复用项目 TextEncoding 哲学，严格 UTF-8 → GB18030 → 标注。
  * debhelper 标准流程，含 hardening 与交叉编译支持。

 -- $MAINT  $date
EOF
}

# 全架构矩阵：dpkg 已注册 13 个 foreign 架构，交叉工具链（crossbuild-essential-*）
# 全部安装到位（详见 HANDOFF-arm-deb.md 第 9 节）。
# r6 变体（mips64r6/mips64r6el/mipsr6/mipsr6el）工具链虽在，但 Ubuntu 无对应
# libc 运行索引、dpkg 生态罕见，暂不纳入；如需另列。
ARGS=(amd64 arm64 armel armhf i386 mips mipsel mips64 mips64el powerpc ppc64el riscv64 s390x)
DISTS=(noble jammy bookworm trixie)

# 交叉构建前确保架构已知（dpkg 自带官方表，通常无需 add-architecture；此处防御性补齐）
dpkg --add-architecture arm64 2>/dev/null || true
dpkg --add-architecture armhf 2>/dev/null || true

for arch in "${ARGS[@]}"; do
  for dist in "${DISTS[@]}"; do
    gen_changelog "${VER[$dist]}" "$dist"
    echo "=================================================="
    echo ">>> 构建  arch=$arch  dist=$dist  ver=${VER[$dist]}"
    echo "=================================================="
    ( cd "$PKG" && dpkg-buildpackage -a"$arch" -us -uc -b ) >"$OUT/build_${dist}_${arch}.log" 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "!!! 失败 rc=$rc，详见 $OUT/build_${dist}_${arch}.log"
      tail -15 "$OUT/build_${dist}_${arch}.log"
      continue
    fi
    # 移动产物（.deb / .ddeb）到归档目录并打标签；清理 changes/buildinfo
    #
    # 注意：分包后同一轮会产出 classics_<ver>_<arch>.deb（架构相关）与
    # classics-data_<ver>_all.deb（Architecture: all）。两者都以 classics_ 开头，
    # 若统一按「主包名」重命名会互相覆盖，故按包名分流，数据包固定记为 all。
    # glob 必须用 classics*（而非 classics_）：数据包的文件名是 classics-data_<ver>_all.deb，
    # 在 classics 之后是连字符不是下划线，写 classics_*.deb 会漏掉它、让它滞留在仓库根。
    for f in "$REPO"/classics*.deb "$REPO"/classics*.ddeb; do
      [ -e "$f" ] || continue
      base="$(basename "$f")"
      case "$base" in
        classics-data_*) tgt="$OUT/classics-data_${VER[$dist]}_all.${base##*.}" ;;
        classics-dbgsym_*) rm -f "$f"; continue ;;
        *)               tgt="$OUT/classics_${VER[$dist]}_${arch}.${base##*.}" ;;
      esac
      mv -v "$f" "$tgt"
    done
    rm -f "$REPO"/classics*.changes "$REPO"/classics*.buildinfo
    echo ">>> 完成：$OUT/classics_${VER[$dist]}_${arch}.deb + classics-data_${VER[$dist]}_all.deb"
  done
done

echo ""
echo "=== 产物清单 ==="
ls -1 "$OUT"/*.deb 2>/dev/null
