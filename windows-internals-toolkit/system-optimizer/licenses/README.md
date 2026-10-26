# 第三方依赖与开源许可证引用来源（Licenses & Citations）

本文件夹集中存放本工具**导入/引用**的第三方开源项目的许可证与引用来源。

设计原则（与工具整体「纯 stdlib、离线、默认非变更、只读探测」一致）：

- 这些仓库**只作为只读引用与可选方案登记**到「网络互联互通共享资源 / 硬件优化 / 开源下载」能力中，
  本工具**不打包、不运行其二进制**，用户需自行按各自许可证与平台安装使用。
- 所有引用均标注 **仓库链接、许可证 SPDX、许可证全文链接、在工具中的用途**。
- **安全护栏（必读）**：同人登录的多设备共享只限于本人**授权**的网络与算力；
  个人数据与关键资产数据一律不共享；**绝不盗用他人网络互联互通能力**（见 `net_reshare` / `any_interop_policy` 任务）。

## 导入的第三方仓库 → 许可证映射

| 仓库 | 用途归类 | 许可证 | 仓库链接 | 许可证全文 |
|------|----------|--------|----------|------------|
| yhan-sun/p2wlan | 网络互联互通：P2P 虚拟局域网（自组网补充） | MIT | https://github.com/yhan-sun/p2wlan | https://opensource.org/licenses/MIT |
| daeuniverse/dae | 网络互联互通：eBPF 高性能透明代理 | AGPL-3.0 | https://github.com/daeuniverse/dae | https://www.gnu.org/licenses/agpl-3.0.txt |
| zhiyi7/gfw-pac | 网络互联互通：PAC 文件生成器（直连/代理分流） | Apache-2.0 | https://github.com/zhiyi7/gfw-pac | https://www.apache.org/licenses/LICENSE-2.0.txt |
| 2dust/v2rayN | 网络互联互通：Xray/sing-box GUI 客户端 | GPL-3.0 | https://github.com/2dust/v2rayN | https://www.gnu.org/licenses/gpl-3.0.txt |
| rakanki911/DLSS5-Swapper | 硬件优化：DLSS5 一键安装/调优/还原（用户选择） | MIT | https://github.com/rakanki911/DLSS5-Swapper | https://opensource.org/licenses/MIT |
| aria2/aria2 | 开源下载软件：多协议多源下载（CDN/P2P 开关） | GPL-2.0 | https://github.com/aria2/aria2 | https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt |

> 说明：gfw-pac 仓库根目录 `LICENSE.txt` 经解码确认为 **Apache License 2.0**（GitHub 自动判定为
> `NOASSERTION`，以仓库内实际 LICENSE 文件为准）。

## 本工具自身许可证

本仓库（windows-internals-toolkit / system-optimizer）的许可证请在仓库根 `LICENSE` 查看；
本文档仅汇总**第三方**引用，不构成对第三方许可证的再授权。

## 许可证文件清单（本文件夹）

- `MIT.txt` — MIT License（p2wlan、DLSS5-Swapper）
- `Apache-2.0.txt` — Apache License 2.0（gfw-pac）
- `GPL-2.0.txt` — GNU GPL v2（aria2）
- `GPL-3.0.txt` — GNU GPL v3（v2rayN）
- `AGPL-3.0.txt` — GNU AGPL v3（dae）

每个文件内含：SPDX 标识、官方全文链接、核心义务摘要。
