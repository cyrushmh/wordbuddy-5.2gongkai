#!/usr/bin/env bash
# 一键构建道家经典文库 App 的 HAP（调试签名）。
#
# 前置（任选其一，二者都会把 HarmonyOS 工具链暴露到 PATH）：
#   A. DevEco Studio 已打开本工程并完成「自动生成签名」（会在本目录生成 material/ 与 hvigorw）；
#   B. 已安装 HarmonyOS Command Line Tools：把其下的 ohpm、hvigor、sdkmgr 加入 PATH，
#      并 export OHOS_SDK_HOME=/path/to/OpenHarmony/Sdk（或 HarmonyOS Sdk）。
#
# 说明：本脚本不负责安装 SDK；SDK 体积大且需授权下载，请在本机 / CI 自托管 runner 准备好。
# 产物：entry/build/default/outputs/default/entry-default-signed.hap

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> 检查 node"
command -v node >/dev/null 2>&1 || { echo "缺少 node，请先安装"; exit 1; }

echo "==> 安装依赖（ohpm install）"
if command -v ohpm >/dev/null 2>&1; then
  ohpm install
else
  echo "未找到 ohpm，请先配置 HarmonyOS Command Line Tools 到 PATH"
  exit 1
fi

echo "==> 构建 HAP（调试签名，--mode debug）"
if [ -f hvigorw ]; then
  ./hvigorw assembleHap --mode debug
else
  command -v hvigor >/dev/null 2>&1 || { echo "未找到 hvigor/hvigorw，请配置工具链"; exit 1; }
  hvigor assembleHap --mode debug
fi

echo "==> 构建完成，HAP 产物："
ls -lh entry/build/default/outputs/default/*.hap 2>/dev/null || echo "（未找到 hap，请检查构建日志）"
