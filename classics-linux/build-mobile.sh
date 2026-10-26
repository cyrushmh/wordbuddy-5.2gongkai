#!/usr/bin/env bash
# build-mobile.sh — classics 移动/桌面新平台交叉构建（Android NDK + OpenHarmony SDK）
#
# 版本：0001.0000.0000.0000.20261024（与 debian/changelog 对账一致）
#
# Android（NDK r26d，低 API 21/26 × aarch64/armv7a）：
#   - bionic 无 iconv（NDK r15 起移除）→ 自动交叉编译 GNU libiconv 1.17 补齐
#   - qemu-user 对 bionic 三连坎（TLS 对齐 / personality / linker init）→ 仅构建级验证
# HarmonyOS（OpenHarmony SDK 6.0.0.47，clang 15.0.4 / musl）：
#   - musl iconv 原生支持 GB18030 → classics 直编，无需 libiconv
#   - 静态产物 qemu-aarch64-static 实跑通过（musl 与 glibc 同属 qemu 友好目标）
#
# 前置（一次性，由 HANDOFF-arm-deb.md §10 记录）：
#   /opt/android-ndk/android-ndk-r26d/…            NDK r26d
#   /opt/ohos-sdk/linux/native/llvm/bin/…          ohos-sdk 6.0.0.47（native zip 已解压）
#   /opt/ohos-sdk/linux/native/sysroot/lib -> usr/lib   （qemu 动态 linker 解析，可选）
set -euo pipefail

PKG="$(cd "$(dirname "$0")" && pwd)"
OUT="$PKG/build/mobile"
NDK_BIN="${NDK_BIN:-/opt/android-ndk/android-ndk-r26d/toolchains/llvm/prebuilt/linux-x86_64/bin}"
OHOS_BIN="${OHOS_BIN:-/opt/ohos-sdk/linux/native/llvm/bin}"
ICONV_CACHE="${ICONV_CACHE:-/opt/libiconv-android}"
ICONV_SRC="${ICONV_SRC:-/tmp/libiconv-1.17}"

mkdir -p "$OUT"
echo "== classics 移动平台交叉构建（$(date -R)） =="

build_hello() { # $1=CC  $2=out
  printf '#include <stdio.h>\nint main(void){ printf("hello from classics cross build\\n"); return 0; }\n' > "$OUT/hello.c"
  "$1" -O2 -static -o "$2" "$OUT/hello.c"
}

build_iconv() { # $1=CC  $2=prefix  $3=host
  if [ ! -f "$2/lib/libiconv.a" ]; then
    [ -d "$ICONV_SRC" ] || { curl -fL -o /tmp/libiconv-1.17.tar.gz \
      https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.17.tar.gz
      mkdir -p "$ICONV_SRC" && tar -xzf /tmp/libiconv-1.17.tar.gz -C "$ICONV_SRC" --strip-components=1; }
    ( cd "$ICONV_SRC" || exit 1
      make distclean >/dev/null 2>&1 || true
      CC="$1" ./configure --host="$3" --prefix="$2" --enable-static --disable-shared >/dev/null
      make -j"$(nproc)" >/dev/null && make install >/dev/null )
  fi
}

echo "--- Android（NDK r26d，API 21/26 × aarch64/armv7a）---"
build_hello "$NDK_BIN/aarch64-linux-android21-clang"    "$OUT/hello_a64_api21"
build_hello "$NDK_BIN/armv7a-linux-androideabi21-clang" "$OUT/hello_a32_api21"
build_hello "$NDK_BIN/aarch64-linux-android26-clang"    "$OUT/hello_a64_api26"
build_iconv "$NDK_BIN/aarch64-linux-android26-clang" "$ICONV_CACHE-a64" aarch64-linux-android
build_iconv "$NDK_BIN/armv7a-linux-androideabi26-clang" "$ICONV_CACHE-a32" armv7a-linux-android
for spec in "aarch64-linux-android26-clang a64 api26 a64" "armv7a-linux-androideabi26-clang a32 api26 a32"; do
  # shellcheck disable=SC2086  # 有意按空格拆分为位置参数（spec 为受控字面量，不含通配符）
  set -- $spec
  "$NDK_BIN/$1" -O2 -static -o "$OUT/classics_$2_$3" "$PKG/src/classics.c" \
    -I"$ICONV_CACHE-$4/include" \
    "$ICONV_CACHE-$4/lib/libiconv.a" "$ICONV_CACHE-$4/lib/libcharset.a"
done
"$NDK_BIN/aarch64-linux-android21-clang" -O2 -static -o "$OUT/classics_a64_api21" "$PKG/src/classics.c" \
  -I"$ICONV_CACHE-a64/include" \
  "$ICONV_CACHE-a64/lib/libiconv.a" "$ICONV_CACHE-a64/lib/libcharset.a"
echo "Android 产物：hello ×3 + classics ×3（API 21/26，全静态零 NEEDED）"

echo "--- HarmonyOS（OpenHarmony SDK 6.0.0.47，clang 15.0.4 / musl）---"
build_hello "$OHOS_BIN/aarch64-unknown-linux-ohos-clang" "$OUT/hello_ohos_a64_dyn"
build_hello "$OHOS_BIN/armv7-unknown-linux-ohos-clang"   "$OUT/hello_ohos_a32_dyn"
"$OHOS_BIN/aarch64-unknown-linux-ohos-clang" -O2 -static -o "$OUT/hello_ohos_a64_static" "$OUT/hello.c"
"$OHOS_BIN/aarch64-unknown-linux-ohos-clang" -O2 -static -o "$OUT/classics_ohos_a64" "$PKG/src/classics.c"
echo "OHOS 产物：hello ×3 + classics ×1"

echo "--- qemu 实跑（OHOS 静态，musl 友好；Android bionic 三连坎见 HANDOFF §10）---"
qemu-aarch64-static "$OUT/hello_ohos_a64_static"
qemu-aarch64-static "$OUT/classics_ohos_a64" | head -1

echo "--- file 判定汇总 ---"
file "$OUT"/hello_a* "$OUT"/classics_* 2>/dev/null | sed "s|$OUT/||"
echo "== 完成：$OUT =="
