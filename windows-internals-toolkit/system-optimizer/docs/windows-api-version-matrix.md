# Windows API 版本差目录（kmod / diagnose 参考）

> 来源：导入分析学习应用 `Somehowfreename/windows-2000-supermium`
> （`compat/*.c` 的 Windows API 版本差 + `manifests/*.json` 声明式补丁链）。
> 本文是把 supermium 的「兼容层思路」**反向**用作 sysweeper 的诊断参考：
> 不是去让老系统跑新程序，而是让 `kmod` / `diagnose` 在扫描一台 Windows 机时，
> 知道「这个 Windows 版本**缺哪些 API**」，从而把对应探针**优雅降级**而非误报「异常」。

---

## 1 · 为什么 diagnose / kmod 需要这份目录

supermium 的核心事实：**同一段 Win32 代码，在不同 Windows 版本上能调到的 API 不同**。
Chromium 144 默认假设一堆 Vista+/Win8+ 的 API 存在；要在 Windows 2000 上跑，
就得在 `compat/*.c` 里逐个 shim。

sysweeper 不做兼容层，但做**只读诊断**。等价的问题是：

> 我在目标机上跑某个探针，它依赖 `Xxx` API；目标机是 Win2000，
> `Xxx` 根本不存在 —— 这时探针该报「不适用 / 降级」，不是「失败」。

所以这份目录是 **diagnose 的「版本门控知识库」**：每条 API 标注
「最小可用 Windows 版本」，diagnose 据此决定降级路径。

**真正的事实源**：Windows SDK 头里的 `_WIN32_WINNT` 守卫。例如：

```c
#if (_WIN32_WINNT >= 0x0600)   // Vista
  // CreateEventEx / RegGetValue / InitializeConditionVariable ...
#endif
```

本文的版本标注已尽量对齐这些守卫；**标「约」的请在对应 SDK 头里二次确认**，
不要直接当编译期事实用。

---

## 2 · 版本门控矩阵（精选，diagnose 常用）

| API / 家族 | 最小 Windows | 目标更老时的降级 |
|---|---|---|
| `SHGetSpecialFolderPath`（shfolder） | Win95 / NT4 | 直接可用；优先 `SHGetKnownFolderPath` |
| `SHGetKnownFolderPath`（KNOWNFOLDERID） | **Vista (6.0)** | 降级 `SHGetFolderPath` / 读 `%USERPROFILE%` |
| `GetDiskFreeSpaceEx` | Win95 / NT4 | 直接可用 |
| `CreateToolhelp32Snapshot` | **Win2000 (5.0)** | 老于 2000 用 PSAPI `EnumProcesses` |
| `GetModuleHandleEx` | **Win2000 (5.0)** | 老于 2000 用 `GetModuleHandle` |
| `InitializeCriticalSectionAndSpinCount` | **Win2000 (5.0)** | 老于 2000 用 `InitializeCriticalSection` |
| `SetupDi*` (Device Information) | **Win2000 (5.0)** | 老于 2000 不可用（kmod 设备枚举降级） |
| `WTS*` (Terminal Services) | **Win2000 (5.0)** | 非终端会话场景忽略 |
| Themes / `UXTheme`（`OpenThemeData`/`DrawThemeBackground`） | **XP (5.1)** | 老于 XP：无主题，走经典控件绘制 |
| `IsThemeActive` / `SetWindowTheme` | **XP (5.1)** | 老于 XP 恒为「未启用」 |
| GDI+（`gdiplus.dll`） | **XP (5.1)** | 老于 XP 用 GDI |
| WLAN API（`WlanOpenHandle`） | **XP SP2 / XP** | 无 Wi-Fi API → 走 NDIS 枚举或报「不适用」 |
| DWM（`DwmIsCompositionEnabled`） | **Vista (6.0)** | 老于 Vista：无合成，窗口管理走 GDI |
| `TaskDialog` / `TaskDialogIndirect` | **Vista (6.0)** | 降级 `MessageBox` |
| `RegGetValue` / `RegSetValueEx` 增强 | **Vista (6.0)** | 降级 `RegQueryValueEx` |
| `CreateEventEx` / `CreateSemaphoreEx` / `CreateMutexEx` | **Vista (6.0)** | 降级无 `Ex` 版本 |
| `GetFileInformationByHandleEx` / `SetFileInformationByHandle` | **Vista (6.0)** | 降级 `GetFileInformationByHandle` |
| `InitializeConditionVariable` / `Sleep/WakeConditionVariable` | **Vista (6.0)** | 降级临界区自旋 / 事件 |
| `InitOnceExecuteOnce` / Threadpool (`CreateThreadpool*`) | **Vista (6.0)** | 降级一次性初始化自管 / 自建线程池 |
| `GetTickCount64` | **Vista (6.0)** | 降级 `GetTickCount`（49.7 天回绕注意） |
| `GetSystemTimePreciseAsFileTime` | **Win8 (6.2)** | 降级 `GetSystemTimeAsFileTime` |
| `WaitOnAddress` / `WakeByAddress*`（Wait-on-Address） | **Win8 (6.2)** | 降级临界区/事件 |
| `SetProcessDpiAwareness`（DPI） | **Win8.1 (6.3)** | 降级 `SetProcessDPIAware`（XP 起） |
| `GetDpiForSystem` / `GetDpiForMonitor` | **Win10 1607 (10.0.14393)** | 降级 `GetDeviceCaps` / 固定 96 DPI |
| `SetProcessDpiAwarenessContext` | **Win10 1703 (10.0.15063)** | 降级 `SetProcessDpiAwareness` |
| `GetThreadDescription` / `SetThreadDescription` | **Win10 1607 (10.0.14393)** | 不可用则线程名留空 |
| `DWMWA_USE_IMMERSIVE_DARK_MODE`（`DwmSetWindowAttribute`） | **Win10 20H1 (10.0.19041，约)** | 不支持则走经典标题栏配色 |
| `DWMWA_SYSTEMBACKDROP_TYPE` / `DWMWA_CAPTION_COLOR` | **Win11 22H2 (约)** | 不支持则无 Mica/标题色 |

> `约` 标记的是「随补丁/ undocumented 行为变化」的项，请以实际 SDK 头与
> `rtlgen` / `user32` 导出表为准。`DwmSetWindowAttribute` 的属性枚举本身跨多个版本
> 增量扩展，是「同一 API、不同属性随版本出现」的典型。

---

## 3 · 离线采集脚本（对应 supermium 的离线采集）

`tools/collect_windows_api_baseline.py` 是**离线、只读、零网络**的采集器：

- 在一台 Windows 机上跑，逐个尝试 `ctypes.windll.<dll>.<func>`，记录
  `present` / `absent` / `min_version`（对照第 2 节矩阵）。
- 输出一份 JSON 基线，可回传给 diagnose 作为「这台机实际能调哪些 API」的事实表，
  比「靠 `_WIN32_WINNT` 推断」更准（有些 API 虽头里声明，运行期 DLL 未必导出）。
- 非 Windows 平台：只输出 `os` 信息并优雅跳过，绝不崩、绝不出网。

这与 supermium 的 `manifests/*.json`（声明式补丁链 + SHA 校验）思路一致：
**把「版本差」落成可机器消费的数据**，区别是 supermium 用它为老系统打补丁，
sysweeper 用它为诊断做降级决策。

---

## 4 · 给 kmod / diagnose 的接入建议（待选，非本版范围）

1. `kmod` 设备枚举遇到 `SetupDi*` 不可用时（Win<2000），降级到 WMI / 注册表枚举，
   报告标「降级：无 SetupAPI」。
2. `diagnose` 读完目标 `dwMajorVersion` 后，用第 2 节矩阵对每条探针做门控：
   目标版本 < `min_version` → 该探针结论直接写「不适用（目标 < X）」，不计入异常。
3. 版本矩阵本身可作为 `native/windows.py` 的一个只读数据表（`WIN_API_MIN_VERSION`），
   由 `collect_windows_api_baseline.py` 在真实机上校验、回填。

> 红线：本目录与脚本**只读诊断、不写系统、不连外网、不下载任何补丁**——
> 我们借鉴 supermium 的「版本差认知」，但不继承它的「给老系统打兼容补丁」行为。
