# 量子架构 XFCE 桌面基座（xfce4-quantum）

XFCE 会话/守护进程/面板小程序/主题，接线量子架构内核的诚实接口
（`/proc/quantum-energy`、`/proc/quantum-net`、`/dev/qpu0`）。源包可在任意拥有 `gcc` 与 XFCE 的目标架构
（含 `ARCH=quantum`）上构建，证明「桌面系统基座可为目标架构构建」。

## 目录布局

```
desktop/
  quantum-core/         C 守护进程（读接口、写 state.json、可选 DBus）
  debian/               debhelper 源包（双二进制包：quantum-core + xfce4-quantum）
  xsessions/            quantum.desktop 会话 + autostart 桌面文件
  session/              quantum-session 包装 + 面板小程序注入脚本
  genmon/               三个 Genmon 面板小程序（能级 / QPU 链路 / 量子组网）
  theme/                量子色系 GTK 主题 + 壁纸
  quantum-settings/     桌面设置入口（状态与诚实边界）
  build_deb.sh          轻量打包（dpkg-deb -b，无需 debhelper）
```

## 构建

### 方式一：debhelper（标准，建议在 chroot/CI）

```sh
cd quantum-kernel/desktop
dpkg-buildpackage -us -uc -b
# 产出 ../quantum-core_<ver>_<arch>.deb 与 ../xfce4-quantum_<ver>_all.deb
```

### 方式二：build_deb.sh（轻量，最小环境可用）

```sh
cd quantum-kernel/desktop
./build_deb.sh
# 产出 ../quantum-core_<ver>_<arch>.deb 与 ../xfce4-quantum_<ver>_all.deb
```

## 安装与使用

```sh
dpkg -i quantum-core_<ver>_<arch>.deb xfce4-quantum_<ver>_all.deb
# 显示管理器选择 "Quantum XFCE Session" 登录即可。
# 首次进入后，在面板右键「+ 添加小程序」选 Genmon，命令填：
#   /usr/lib/quantum-core/genmon/quantum-energy-genmon.sh
#   /usr/lib/quantum-core/genmon/quantum-qpu-genmon.sh
#   /usr/lib/quantum-core/genmon/quantum-net-genmon.sh
# 或运行：quantum-panel-add-genmon.sh（需在 XFCE 会话内）
```

## 诚实边界

- 量子架构是宿主模拟架构（与 `arch/um` 同型）；以上接口读写的是**模拟/记账模型**，
  不是真实量子硬件。
- 本适配不声称 XFCE 能在「已引导的量子处理器」上运行（无 bzImage/Image 引导协议）。
- `quantum-core` 在宿主缺 `/dev/qpu0`、`/proc/quantum-energy` 与 `/proc/quantum-net` 时优雅降级：
  接口标记为 `available=false`，不崩溃、不伪造数据。
- 详见 `../../windows-internals-toolkit/system-optimizer/docs/48_XFCE量子架构适配.md`，及同目录 `44_量子架构内核.md` §8 / `47_量子架构测试床与initrd.md`。
