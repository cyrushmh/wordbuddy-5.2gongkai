# 参数阈值与多来源导入（图形界面可控可调）· v0.6.24

> 对应需求：**「图形界面也应该必须能够调控参数，还有阈值，甚至能够导入剪贴板、本地文件、二维码的扫码和读取（支持通过文件读取图片）」**

v0.6.22 做的是「哪些诊断项嵌入总览」（子系统开关）。这一版补的是另一半：
**这些诊断怎么跑**（参数与阈值），以及**外部内容怎么进来**（多来源导入）。
两件事 GUI 与 CLI 都能做，改完立即生效。

---

## 一、参数与阈值：13 项，全部真实生效

单一事实源在 `src/python/sysweeper/native/settings.py`，配置落在
`~/.config/sysweeper/settings.json`。**没有一项是只显示不生效的装饰参数**——
每一项都登记了生效点，并在代码里被真实消费。

### 数值阈值（5 项）

| KEY | 名称 | 默认 | 范围 | 生效点 |
|---|---|---|---|---|
| `cmd.timeout` | 命令执行超时 | 120 秒 | 1 ~ 3600 | `common.run()` 的默认 timeout |
| `cmd.tail` | 输出截断长度 | 2000 字符 | 0 ~ 200000（0=不截断） | `common.run()` 的默认 tail |
| `scan.limit` | 扫描条数上限 | 10 条 | 1 ~ 1000 | `large_dirs_report` / `find_large_subdirs` |
| `import.max_bytes` | 导入读入上限 | 1048576 字节 | 1024 ~ 52428800 | 导入层四种来源的统一上限 |
| `qr.camera_timeout` | 摄像头扫码超时 | 20 秒 | 1 ~ 120 | 摄像头扫码循环上限 |

### 运行参数（5 项）

| KEY | 名称 | 默认 | 生效点 |
|---|---|---|---|
| `scan.root` | 大目录扫描根目录 | `~` | `large_dirs_report` 的默认根目录（支持 `~` 展开） |
| `arch` | 架构/指令集档位 | `auto` | CLI `--arch` 的默认值（`build_parser` 时读取） |
| `profile` | 任务档位 | 空 | CLI `--profile` 的默认值 |
| `locale` | 界面语言(i18n) | 空（跟随环境） | CLI `--locale` 的默认值 |
| `report.path` | 报告默认落点 | 空 | CLI `--report` 的默认值 |

> 这四项改成什么，命令行不显式给参数时就按配置走；**命令行显式给出仍优先**。
> 实测：`settings --set arch=riscv` 后 `sysweeper list` 默认按 riscv 过滤，
> 而 `sysweeper list --arch x86` 仍按 x86。

### 导入/二维码（3 项）

| KEY | 名称 | 默认 | 生效点 |
|---|---|---|---|
| `qr.backend` | 二维码解码后端 | `auto`（OpenCV → pyzbar 降级） | 图片二维码解码 |
| `qr.camera_index` | 摄像头编号 | 0 | 摄像头扫码 `VideoCapture` 索引 |
| `clipboard.backend` | 剪贴板后端 | `auto`（按平台自动挑） | 剪贴板读取 |

### 校验口径

- **越界/类型错/未知 key 一律拒绝**，回退默认值并逐项报告原因，**不静默接受**。
- **配置损坏**（JSON 写坏）安全回退全默认，绝不因配置问题阻断诊断。
- **显式传参始终优先**：`common.run(cmd, 120, 3)` 这类既有调用行为完全不变，
  配置值只在参数未传时兜底——向后兼容。

---

## 二、多来源导入：剪贴板 / 本地文件 / 图片二维码 / 摄像头

实现在 `src/python/sysweeper/native/importio.py`，四种来源统一返回
`(是否成功, 文本, 说明)`。

| 来源 | 说明 | 依赖 |
|---|---|---|
| **剪贴板** | Linux `wl-copy`/`xclip`/`xsel` → macOS `osascript` → Windows `powershell` → 都不行回退 `tkinter`；**取不到纯文本时自动再试剪贴板截图里的二维码**（截图即导入，不必先存文件）。只读，**不写回剪贴板** | 标准库 + 平台命令；截图扫码另需 `pillow` |
| **本地文件** | 文本文件按 UTF-8 读入（失败回退 Latin-1），受 `import.max_bytes` 限制，超限截断并说明 | 标准库 |
| **图片二维码** | **从 PNG/JPG/BMP/GIF/WebP/TIFF 图片文件解码二维码**（需求点名的「通过文件读取图片」） | `opencv-python` 或 `pyzbar` |
| **摄像头扫码** | 实时取画面解码，识别到即返回，受 `qr.camera_timeout` 限制，超时即停 | `opencv-python` |

### 后端降级与安装指引

- 二维码后端顺序：`auto` = OpenCV → pyzbar 依次尝试；都没有时**给安装指引，绝不自动安装**。
- 缺少的库按提示自行安装：
  - `pip install opencv-python-headless`
  - `pip install pyzbar pillow`（pyzbar 还需系统库 `apt install libzbar0`）
- 无摄像头 / 无权限 / 被占用 都只返回说明，**不抛错、不死等**。

---

## 三、图形界面怎么用

主窗口顶部按钮栏与底部按钮栏各新增两个入口：

- **参数/阈值** —— 打开参数窗口
- **导入（剪贴板/文件/二维码）** —— 打开导入窗口

### 参数窗口

- 按类型自动生成控件：数值 → Spinbox（带上下界）、枚举 → 下拉、路径 → 输入框 + 浏览、布尔 → 勾选。
- 每行标出**生效点**，改之前就知道这一项管什么、作用在哪里。
- 按钮：**保存（立即生效）** / 恢复默认 / 导出 JSON / 导入 / 关闭。
- 越界的取值会被拒绝并弹窗列出「哪项因为什么原因回退」，不会写出非法配置。

### 导入窗口

- 四个来源单选；选「本地文件」或「图片二维码」时出现路径行与「选择文件」按钮。
- **读取** 后内容显示在文本区（二维码解出来的就是码里的文本）。
- **载入为参数（需确认）**：仅当内容是可识别的设置 JSON 时可用，
  弹窗列出将写入哪些键，**确认后才写**；不确认就只是查看。

### 已改动项高亮 + 单项复位

参数窗口会**把与默认值不同的项标成蓝色并加 `●`**，状态行同步显示
「已改动 N 项：cmd.timeout、scan.limit」，一眼看出动过什么。
每项右侧有**「复位」按钮**（没改动时置灰），点一下把**这一项**恢复默认——
不必为了改回一项而整体恢复默认。

### 实时联动：一处改，处处跟着变

参数变更会广播给所有订阅方，**不用关掉窗口重开**：

- 参数窗口自身：值变化后立即刷新高亮与状态；
- 系统控制台：输出区实时追加一行
  `[参数已变更] cmd.timeout: 120 → 300`；
- 导入窗口载入参数后，已打开的参数窗口同步跟上。

实现上是 `settings.on_change()` 订阅 + 队列轮询回到主线程，
订阅方抛异常也不会影响参数写入本身。

### 摄像头扫码不卡界面

扫码最长跑 `qr.camera_timeout` 秒，如果放在界面线程里跑，整个窗口会假死。
实现上：**工作线程只负责把结果放进队列**，界面线程每 100ms 轮询一次取结果并刷新
——tkinter 不允许从工作线程直接碰控件（跨线程 `after` 会抛
`RuntimeError: main thread is not in main loop`），所以一律走队列 + 主线程轮询。
扫码期间「读取」按钮置灰并显示「后台进行，界面不卡」，完成后自动恢复。

---

## 四、命令行怎么用

```bash
# 列出全部参数与阈值
python -m sysweeper settings --list

# 查一个 / 改多个
python -m sysweeper settings --get cmd.timeout
python -m sysweeper settings --set cmd.timeout=300 scan.limit=20 arch=any

# 全部恢复默认
python -m sysweeper settings --reset

# 变更留痕：什么时候、从哪来、改了什么
python -m sysweeper settings --history

# 导入：剪贴板 / 本地文件 / 图片二维码 / 摄像头
python -m sysweeper import --from clipboard
python -m sysweeper import --from file --path ./notes.md
python -m sysweeper import --from qr --path ./qrcode.png
python -m sysweeper import --from camera

# 只有显式加 --as-settings 才把 JSON 载入为参数
python -m sysweeper import --from file --path ./settings.json --as-settings
```

---

## 五、变更留痕：这项是谁改的？

每一次参数变更都会记一笔，落点 `~/.config/sysweeper/settings-history.json`
（**上限 200 条**，超出丢弃最旧的）。

```
· 2026-10-10T02:25:48  [gui]
    cmd.timeout: 120 → 300
· 2026-10-10T02:25:48  [import · ./settings.json]
    scan.limit: 10 → 5
    arch: auto → riscv
```

- `source` 记来源：`gui` / `cli` / `clipboard` / `file` / `qr` / `camera` / `reset`
- `origin` 记具体出处：文件路径、摄像头编号、剪贴板等
- **只记参数键与旧/新值，绝不记录导入的整篇文本** —— 导入内容可能含敏感信息，
  留痕只需能回答「这项是谁改的」，不需要把别人的全文留在本地。
- **值没真的变化不记**（重复保存同一个值不产生噪音记录）

查看方式：参数窗口 **「变更历史」** 按钮，或命令行 `sysweeper settings --history`。

## 六、红线（这一版新增能力的边界）

1. **只读**：导入层不写剪贴板、不改被导入的文件、不联网。
2. **绝不自动安装依赖**：二维码/剪贴板后端缺失时只给指引，不碰 pip、不改系统。
3. **导入内容绝不自动执行**：JSON 只做结构校验；命令行要 `--as-settings`、
   GUI 要二次确认，才会写入配置。中间任何一步不确认，就是纯查看。
4. **参数为真实参数**：不引入「显示了但不生效」的假旋钮；新增参数必须同时登记生效点。
5. **配置异常不致命**：损坏/越界/未知键都回退，不阻断诊断。

---

## 七、测试

`tests/test_settings_import.py`（48 项）覆盖五类断言：

1. **注册表自洽** —— key/label 唯一、默认值自身合法、越界与非法枚举被拒、
   损坏配置回退、未知键忽略、**每条参数都有生效点**（反装饰参数）。
2. **阈值真实生效** —— 改 `cmd.tail` 后 `common.run` 输出真的被截断、
   改 `cmd.timeout` 后长命令真的超时、改 `scan.limit` 后大目录榜真的只列 N 条；
   **显式传参仍优先**。
3. **运行参数真实接入 CLI** —— 设 `arch`/`profile`/`locale`/`report.path` 后
   `parse_args` 的默认值真的跟着变，命令行显式给出仍然优先。
4. **导入层只读安全** —— 文本文件与上限截断、二维码生成→图片解码往返（含
   **内存 PIL 图像**，模拟剪贴板截图）、剪贴板无文本时自动兜底截图扫码、
   缺文件/非图片/未知来源都不抛错、**导入动作本身绝不写配置**。
5. **变更留痕与联动** —— 来源与旧/新值记录正确、值未变不记、**导入全文不进留痕**、
   上限截断与清空、订阅方抛错不影响保存、CLI `--history` 可查。
