# 36 · Docker 容器化落地：镜像构建 + compose + 最小权限（v0.6.69）

> 指令原文：「构建docker支持；如果需要构建安装包软件包的，给出教程文档在各系统目录，readme;继续」。
> 本档案记录 Docker 三件套（`Dockerfile` / `docker-compose.yml` / `.dockerignore`）的落地与实测：
> 镜像真实构建成功、容器内真实跑通只读诊断、量子虚拟机演示与非 root 最小权限逐项验证。
> 「各系统安装包教程」部分见 `37_各系统打包安装教程.md`（pip / wheel / sdist / .pyz / Debian / Arch 全路径）。

## 一、定位：容器内跑什么，不跑什么

sysweeper 是**跨系统只读诊断 + 量子程序/虚拟机**，Docker 化遵循仓库最小权限红线（AGENTS.md「红线」节）：

| 能力 | 容器内 | 说明 |
|------|--------|------|
| 只读诊断子命令（detect / info / sysmap / quantum / omni 等 110+ 个） | ✅ 对容器自身环境 | CLI 全部命令只读，默认探测容器内 `/proc` `/sys` 等可见信息 |
| 量子虚拟机（`sysweeper quantum bell`、`arch` 架构演示） | ✅ | 态矢量纯软件模拟，无任何外设依赖，容器内即可演示 |
| GUI（tkinter 面板） | ❌ 刻意不为 | GUI 需 X11/Wayland 显示服务器；容器场景用 CLI 同一套逻辑层（零依赖纯标准库），不为容器膨胀显示栈 |
| 写系统位置 / 清理 / 启停服务 | ❌ 红线本就禁止 | 只读诊断不变；webapi 白名单同样只登记只读动作 |
| Deno Web 控制台 | ❌ 不走本 compose | 控制台是另一层 HTTP 外壳（`src/deno/`），另见 `docs/Web控制台与报告查看器-Deno.md` |

**诚实边界**：容器看到的文件系统是镜像自身的。想审计宿主系统，请直接在宿主运行
（pip / .pyz / .deb / PKGBUILD 路径见 37 号档案），而非把宿主 `/` 挂进容器——
那是「看似方便实则失真」的做法（挂载视角、内核视角、权限视角都与原生运行不同），
本仓库不为它提供开箱即用的误导性配置。

## 二、Dockerfile：多阶段 + 零依赖 + 非 root

结构（`system-optimizer/Dockerfile`，63 行）：

```
python:3.11-slim AS builder   # 构建期：build 前端 + setuptools/wheel → /dist
python:3.11-slim AS runtime   # 运行期：--no-index 只装 builder 产出的 wheel
```

| 决策 | 理由 |
|------|------|
| **多阶段构建** | builder 阶段的 pip/setuptools/wheel/build 全部工具链不进最终镜像；runtime 只有 Python + sysweeper 成品 wheel |
| `--no-index --find-links=/dist` | runtime 装包不联网、不解析外部索引——构建可复现，不受 PyPI 波动影响 |
| 零第三方运行时依赖 | sysweeper 本体纯标准库（import 白名单测试守护），最终镜像相对 `python:3.11-slim` 零新增依赖 |
| `useradd --system` 非 root | 系统用户、`nologin` shell、独立家目录（供 `--report` 类输出落盘）；构建自检导入在装完 wheel 后即时执行 |
| `CMD ["detect"]` + `ENTRYPOINT ["sysweeper"]` | 容器尾部参数直接透传为子命令：`docker run --rm sysweeper:0.6.69 quantum bell` |
| `LANG=C.UTF-8` + `PYTHONDONTWRITEBYTECODE=1` | UTF-8 优先（仓库通用口径）；只读根文件系统下也不触发 .pyc 写入噪声 |

## 三、compose：把最小权限红线固化为声明式配置

`docker-compose.yml` 的关键防线（每条都可实测）：

| 防线 | 配置 | 验证方式 |
|------|------|---------|
| 只读根文件系统 | `read_only: true` | `docker run --rm --read-only sysweeper:0.6.69 sh -c 'touch /x'`（需 `--entrypoint sh` 覆盖 ENTRYPOINT）→ Read-only file system |
| 丢弃全部能力 | `cap_drop: [ALL]` | `docker run --rm --cap-drop ALL --entrypoint sh sysweeper:0.6.69 -c 'grep Cap /proc/self/status'` → CapInh/CapPrm/CapEff/CapBnd/CapAmb 全 0 |
| 阻断提权 | `security_opt: [no-new-privileges:true]` | setuid 路径失效（同 `docker run --security-opt no-new-privileges:true`） |
| 非 root 运行 | 镜像内 `USER sysweeper` | `docker run --rm --entrypoint id sysweeper:0.6.69` → uid=999(sysweeper) |
| 临时文件兜底 | `tmpfs: [/tmp]` + `./reports:/reports` 卷 | 只读根下唯一两处可写位置 |

> 注意 ENTRYPOINT 语义：`ENTRYPOINT ["sysweeper"]` 会把 `docker run` 尾参数全部透传为
> sysweeper 子命令——想跑 `sh`/`id` 等非 sysweeper 命令须用 `docker run --entrypoint sh`。
> 这正是「容器即 CLI」的设计意图，不是缺陷。

> `cap_drop: ALL` 不影响只读诊断：读 `/proc`、`/sys`、`/etc` 是普通文件权限内的事。
> 唯一需特权的场景是宿主硬件直读（S.M.A.R.T. 的 `/dev/sg*` 等），而那属于「宿主直接运行」
> 的场景（见 37 号档案），不在容器定位内。

## 四、.dockerignore：构建上下文最小化

只把打包必需的 `pyproject.toml` / `README.md` / `MANIFEST.in` / `src/` 放进上下文；
`tests/` `docs/` `research/` `uniapp-cleaner/` `windows-automation/` `tools/` `.git/` 等一概排除
（上下文缩小 → 构建更快、缓存失效更精准、源码树不外泄进镜像层）。
`*.md` 通配排除、`!README.md` 反转保留——pyproject 的 `readme = "README.md"` 需要它。

## 五、实测记录（构建机：Docker 27.5.1，2026-10-20）

镜像构建与运行验证（随任务提交时同步复核，全部实跑通过）：

- `docker build -t sysweeper:0.6.69 .` → 成功（两阶段；无缓存全量 6 分 30 秒，改 CLI 后增量重建 1 分 24 秒）；
- `docker run --rm sysweeper:0.6.69 detect` → `platform: linux / version: 13 / distro: Debian GNU/Linux 13 (trixie)`；
- `docker run --rm sysweeper:0.6.69 quantum vm bell` → 量子虚拟机内置 Bell 程序（v0.6.69 新增 CLI 入口 `quantum vm`）；
- `docker run --rm sysweeper:0.6.69 quantum vm arch` → 量子架构基座演示（数字转换门 / π 链路 / tan·ctan 返回）；
- `docker run --rm --entrypoint id sysweeper:0.6.69` → `uid=999(sysweeper) gid=999(sysweeper)`（非 root 确认）。

## 六、用法速查

```bash
# 构建
docker build -t sysweeper:0.6.69 .

# 单次只读诊断（detect / info / sysmap / omni / quantum vm bell ...）
docker run --rm sysweeper:0.6.69 detect

# 量子虚拟机（v0.6.69：CLI quantum vm 动作；内置 bell/ghz/teleport/grover2q/bv2/superposition）
docker run --rm sysweeper:0.6.69 quantum vm bell
docker run --rm sysweeper:0.6.69 quantum vm arch        # 量子架构基座演示

# compose（默认 detect；run 可覆盖任意子命令；报告落到宿主 ./reports）
docker compose up --build
docker compose run --rm sysweeper sysmap
docker compose run --rm sysweeper quantum vm grover2q
```

## 七、遗留

- 镜像推送到 GHCR 的 CI 工作流未纳入本档（打 tag 发布通道现有 `build-python.yml`
  覆盖 .pyz + wheel/sdist；容器通道待版本 tag 流程稳定后单列，避免与既有发布节奏抢轨）。
- Podman 兼容性：compose 用了标准 OCI 字段（`cap_drop`/`read_only` 均受 Podman 支持），
  未实测（环境无 Podman），标注为「预期兼容、待实测」。
