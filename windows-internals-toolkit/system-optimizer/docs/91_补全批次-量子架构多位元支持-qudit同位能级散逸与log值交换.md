# 91_补全批次——量子架构多位元支持：qudit 同位能级散逸与 log 值交换

> 批次定位：接用户显式请求「量子架构的多位元支持也要进行，用量子同位能级散逸，进行 log 值交换」。
> 此前量子架构内核（qkern 域）只有 qubit 二进制位（d=2）建模，无多位元（qudit）。本批按
> 与 `native/quantum.py` 同一红线（纯软件模拟、零依赖、不接硬件）真正给出 **d 级 qudit** 的
> 经典数值实现，并把「同位能级散逸（T1/T2 耗散）」与「log 值交换（log₂(d) 比特/符号承载
> 经典值）」落成可实跑、可审计的模块与概念条目。

## 一、缺口定位与路线选择（先探测再决策，不臆造）

量子架构内核此前只把「量子位」当作 d=2 的 qubit 处理，缺 d 级多位元（qudit）这一层：

| 维度 | 此前现状 | 用户要求 | 本批决策 |
|---|---|---|---|
| 多能级建模 | 仅 qubit（d=2） | 多位元（qudit，d≥3） | **实现 d 级密度矩阵 + 门 + 通道** |
| 耗散 | 概念层 decoherence | 「量子同位能级散逸」 | **Kraus 振幅/相位阻尼（T1/T2）实跑** |
| 值承载 | 无 | 「进行 log 值交换」 | **log₂(d) 比特/符号编码经典值 + 散逸下漂量化** |

路线对比（探测后决策）：

1. **接真量子硬件 / 云量子服务**：违反本仓红线（不接硬件、不联网），且 qudit 硬件（俘获离子、
   超导 qutrit）并非随手可得。**排除**。
2. **第三方量子库（qutip / cirq）**：引入重依赖，与「零依赖 native」基调冲突，且掩盖物理模型
   本身。**不必要**。
3. **纯标准库经典数值模拟**（采用）：用 Python 复数矩阵实现 d 级 ρ + DFT 酉门 + 广义 X/Z 门 +
   Kraus 通道，复用 Nielsen & Chuang 标准模型（§4/§8），**不新写轮子、不造假**。

## 二、qudit 物理模型与实现（native/qudit.py，新建）

信息容量真实事实：`capacity_bits(d) = log2(d)`——d=3→1.585 bit、d=5→2.322 bit、d=8→3.0 bit。
这是标准量子信息结论，非臆造；模块内 `MAX_D=8`（d×d 复矩阵，纯 Python 足够）。

门与通道（均为标准开放量子系统模型，经典数值实现）：

- **DFT_d 酉门**：离散傅里叶 酉矩阵，Σ|U|²=1（酉性自测）。
- **广义 X_d（shift）/ Z_d（phase）**：d 级循环移位与相位门。
- **振幅阻尼 amplitude_damping(d, γ)**（T1 能量弛豫）：|k>→|k-1> 逐级衰减，耗散**非酉**，
  纯态→混态，故必须用密度矩阵 ρ 而非态矢量。
- **相位阻尼 dephasing(d, λ)**（T2 退相干）：非对角元按 |i−j| 衰减。
- **CPTP 验证**：`apply_kraus` 要求 Kraus 完备性 ΣE†E=I、迹保持（trace=1），
  这是「物理合法通道」的底线，模块自测钉死。

log 值交换（把经典值编进能级分布再经散逸「传输」解码）：

- `encode_log_amplitudes(value, d)`：中心 μ=log₂(value)，把值编码成能级对数幅度分布。
- `decode_log_value(rho, d)`：从散逸后的 ρ 反解值。
- `dissipation_sweep`：量化 γ 对解码值的下漂。
- `exchange_integer(d, n, value)`：多 qudit 无损整数交换（d**n 值域内精确往返）。

## 三、数值实证（qudit_report d=5, value=6.0）

散逸侵蚀编码值（能量向低能级泄漏 → 解码值下漂），本模块**诚实量化**损失：

| γ(T1) | 解码值 | 保真度 | 纯度 |
|---:|---:|---:|---:|
| 0.00 | 6.1459 | 1.0000 | 1.0000 |
| 0.05 | 5.9366 | 0.9619 | 0.9263 |
| 0.10 | 5.7343 | 0.9237 | 0.8579 |
| 0.20 | 5.3503 | 0.8474 | 0.7367 |
| 0.35 | 4.8220 | 0.7330 | 0.5943 |
| 0.50 | 4.3458 | 0.6185 | 0.4990 |
| 0.75 | 3.6544 | 0.4278 | 0.4450 |
| 1.00 | 3.0730 | 0.2370 | 0.5219 |

解码值随 γ **单调下漂**（6.15→3.07），纯度随 γ 衰减；**不宣称量子优势**——这只是经典
数值对散逸损失的诚实建模。无损整数交换：d=3, n=12 编码整数精确往返（3¹²≈53 万值域内）。

## 四、概念系统整合（research/quantum/build_quantum.py）

新增 3 概念，各自归到合理域：

| 概念 id | 域 | 落点 | 桥接 |
|---|---|---|---|
| `qudit-multi-level` | state | measurement 后 | plang:lang:python（纯 Python 复数矩阵实现）+ daoxue 类比（道生一·二生三·三生万物，d 级推广链同构） |
| `level-dissipation` | error | decoherence 后 | 指向 T1/T2 物理通道 |
| `log-value-exchange` | qsim | six-phase-64 后 | 指向自建经典模拟器值域 |

- 桥接 **51→55**（qudit-multi-level 含 2 条跨系统桥接）；概念 **78→81**；
  quantum taxonomy 版本 **0065→0066**，`_meta` 同步。
- 三概念各补 `engineering` 落法字段（落法指向 `native/qudit.py` 实跑），否则审计判漏。

## 五、CLI 与 task action

- `quantum qudit [d] [value]` 新动作：`d∈[2,8]`，`value∈[1, 2^(d−1)]`（μ=log₂(value) 须落在
  能级 [0, d−1] 内，越界将被截断失真），越界**诚实拒绝**；`try/except QuditError` 兜底，**无 traceback**。
- `native/qudit.py` 注册进 `native/__init__.py`；`tasks/quantum.py` 新增 `qudit.qudit_report` action。

## 六、工程坑实录（本批入账 3 条）

| # | 坑 | 正解 |
|---|---|---|
| 1 | CLI 上限写 `[2,64]`，与模块 `MAX_D=8` 不一致；传 `d>8` 触发未捕获 `QuditError` traceback（违反 0 崩溃纪律） | 边界判定改用 `qd.MAX_D` + 异常兜底，统一为 `[2,8]` |
| 2 | taxonomy 构建拒绝自系统桥接 `{"system":"quantum","target":"concept:qubit"}` | 改跨系统桥接（plang / daoxue），桥接须指向真实外部系统 |
| 3 | 新概念缺 `engineering` 落法字段 → 审计判漏 | 在 `apply_engineering()` 映射表登记 3 条落法描述 |

## 七、诚实边界（不夸大半句）

- **经典数值模拟 qudit，非量子硬件**；不接真量子设备、不联网、不调云量子服务。
- 「多位元」= **log₂(d) 比特容量**，与经典位宽不同轴；**不把 d 级系统硬说成「d 比特」**
  （那会把 d 级当二进制，是对量子信息的误读）。
- 耗散为**简化的单步均匀衰减模型**，不建模真实器件的 T1/T2 频变、串扰与门误差谱；
  数值结果仅作「散逸损失量化」演示，不构成器件结论。

## 八、整合落点

- `src/python/sysweeper/native/qudit.py`（新建，约 16KB）：容量/门/通道/CPTP/log 交换全套。
- `native/__init__.py`：import `qudit` 并加入 `__all__`。
- `tasks/quantum.py`：新增 `qudit.qudit_report` native action。
- `research/quantum/build_quantum.py`：3 概念 + engineering 落法 + `_meta` 版本 0065→0066。
- `cli.py`：quantum `qudit [d] [value]` 动作 + choices 注册 + 帮助文本 + 边界兜底。
- 计数断言同步：`concepts/__init__.py` TAGLINES（78→81）、`test_concepts_center`、
  `test_quantum`（78→81、51→55）、`test_quantum_vm`、`test_gui_quantum`（页1 state 域 7 条、
  桥接 55 条）。新增 `test_qudit.py`。
- 版本同步 **0030→0031**：version.py + pyproject + console.ts + report_viewer.ts + go/main.go +
  cnstd 数据 + 5 系统 taxonomy 重烘焙（`build --check` 防漂移）；concept_gui.html 重生。

## 九、验证与交付

- `tests/test_qudit.py`（新建）：容量真值、DFT 酉性、Kraus CPTP 迹保持、log 交换随 γ 单调
  下漂、无损整数交换精确——全过。
- 全量 pytest：**1776 passed / 6 skipped**（零回归）。
- 静态：`audit_concepts.py --strict` 不一致 **0**；`check_concept_mesh.py --strict` 悬空 **0**；
  `deno check console.ts report_viewer.ts` 通过。
- 提交 **9b353ea**，推送 `dede454..9b353ea`（SYNCED）。
