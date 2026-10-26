#!/usr/bin/env bash
# 国学经典 · iOS / macOS 构建尝试脚本
#
# 设计镜像 classics-harmony-app/build_hap.sh：先检查工具链，再尝试构建，
# 缺工具则优雅退出并给出指引——「不能测试的也保留代码规范」。
#
# 沙箱（Ubuntu/Linux）无 swift/xcodebuild，预期在此优雅降级；
# 在 macOS + Xcode 环境方可真正出包。

set -u

echo "===== 国学经典 iOS/macOS 构建检查 ====="

# 1) 检查 swift（共享库 / macOS 可执行编译需要）
if ! command -v swift >/dev/null 2>&1; then
  echo "[缺少] swift —— 当前环境（Linux 沙箱）无法编译 Swift。"
  echo "        请在 macOS 安装 Xcode（含 Command Line Tools）后重试。"
  echo "        源码与 Package.swift 已按规范写就，可离线审阅。"
  exit 1
fi
echo "[通过] swift: $(swift --version 2>/dev/null | head -1)"

# 2) 检查 xcodebuild（出 iOS/macOS .app 包需要）
if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "[缺少] xcodebuild —— 只能编译共享库，无法出 .app 包。"
  echo "        出包步骤：macOS 上 'swift build' 后打包，或用 Xcode 打开本目录 / Apps/iOS。"
else
  echo "[通过] xcodebuild: $(xcodebuild -version 2>/dev/null | head -1)"
fi

# 3) 尝试编译共享库 ClassicsHarmony（仅 macOS/Linux-with-swift 可过）
echo "===== 尝试编译共享库 ClassicsHarmony ====="
if swift build 2>/tmp/swiftbuild.err; then
  echo "[成功] 共享库编译通过"
else
  echo "[失败] 共享库编译未通过（多见于 Linux 缺 SwiftUI/AppKit 平台支持）："
  tail -n 15 /tmp/swiftbuild.err
  echo "        代码规范与 Package.swift 已保留；请在 macOS + Xcode 环境构建。"
  exit 1
fi

# 4) 提示出包（需 xcodebuild）
echo "===== 出包指引 ====="
echo "macOS .app : 在 Mac 上 'swift build' 后打包，或 Xcode 打开本目录选 ClassicsMac scheme。"
echo "iOS .app   : 见 Apps/iOS/README.md，Xcode 引用本 Package 后 Product ▸ Run。"
echo "完成。"
