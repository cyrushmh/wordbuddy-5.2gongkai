# PEInfo（Microsoft Office VBA）

用 **VBA（Visual Basic for Applications）** 实现的 PE 头查看器，与 `src/` 下 C / Rust / Python / .NET 版**解析口径、JSON 字段完全对齐**。无需任何外部引用，纯 VBA 实现，可导入任意 Office 宿主（Excel / Word / Access / PowerPoint）的 VBA 工程。

## 导入

1. 打开目标 Office 文档（如 Excel 工作簿），按 `Alt+F11` 打开 VBA 编辑器。
2. 菜单 **文件 → 导入文件**，选择 `PEInfo.bas`（本目录）。
3. 导入后工程资源管理器中出现标准模块 `PEInfo`，即可使用。

## 使用

| 过程 | 作用 |
|---|---|
| `ShowPeInfo` | 弹文件选择框，把 JSON 结果打印到**立即窗口**（Ctrl+G 查看） |
| `DumpPeInfoJsonFile` | 弹文件选择框，把 JSON 写到 `<原名>.pe.json` 旁边 |
| `PeInfoJson(path)` | 核心函数：传入路径，返回与 parity 同 schema 的 JSON 字符串 |

示例（在立即窗口或任意模块里调用）：

```vb
' 直接拿到 JSON 字符串（便于字符串处理 / 写入单元格）
Dim s As String
s = PeInfoJson("C:\Windows\System32\notepad.exe")

' 选文件并导出 JSON 旁挂文件，供 Windows 上与 parity_test 人工比对
Call DumpPeInfoJsonFile
```

## JSON 字段（与一致性测试一致）

```
machine / machine_name / number_of_sections / timestamp / characteristics
optional.magic / optional.entry_point / optional.image_base
optional.subsystem / optional.subsystem_name / optional.number_of_rva_and_sizes
data_directories[] { name, virtual_address, size }
sections[]        { name, virtual_address, virtual_size, size_of_raw_data,
                    pointer_to_raw_data, characteristics }
```

## 与跨语言一致性测试的关系

VBA 运行于 Office（Windows / Mac），无命令行、无标准输出，因此以**字符串**承载机器可读结果；字段命名/数据类型与 `pe_inspect.py --json`、.NET `PeInfo --json` 一致。

- **Windows-only**：沙箱（Linux）无 Office，不自动纳入 `tests/parity_test.py`。
- **人工比对**：在 Windows 上运行 `DumpPeInfoJsonFile` 生成 `<file>.pe.json`，再与 `python3 tests/parity_test.py <file>` 的各语言 JSON 对照即可确认等价。
- 解析偏移已用 Python 复刻并验证：对 `tools/` 下 4 个样本（PE32+ x64 ×3 + PE32 x86），VBA 口径与 Python 实现**核心字段完全一致**。

## 实现要点

- 文件整体读入 `Byte` 数组；小端读取用 `Le16 / Le32 / Le64`（64 位 `ImageBase` 用 `Double` 承载，避免 VBA 有符号 `Long` 溢出）。
- PE32 与 PE32+ 可选头布局不同：`ImageBase` 分别在 `opt+28`(4B) / `opt+24`(8B)；`NumberOfRvaAndSizes` 与数据目录表分别在 `opt+92 / +96` 与 `opt+108 / +112`——已按 `magic` 分支处理（与 Python 版修复后的偏移一致）。
- 无 GUI：结果以文本/JSON 输出，复用 Office 宿主自身的"立即窗口 / 单元格 / 文件"作为承载，不依赖 WinForms。
