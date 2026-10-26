# 导入分析学习应用 openKylin 技能仓库与跨平台直传（v0.6.64）

> 来源：`https://mp.weixin.qq.com/s/IGQR8pkaMZJeEfnbFJXJlA`（openKylin 公众号：WorkBuddy × 桌面小插件教程）、
> `https://mp.weixin.qq.com/s/HdiFDAWpIBCkRyc5X7k2kA`（电脑报：国行安卓 Quick Share ↔ AirDrop 互通）、
> `https://gitee.com/openkylin/openkylin-skills`（68 技能仓库，目标 skill：`create-peony-desktop-manager-widget`）。
> 落点：netsys / comp / apilab，与既有「克隆→审查→安装→分析→回灌」纪律一致。
> 纪律红线：只登记可核实的事实；无法核实的标 `needs_verify`，不臆造；桥接目标必须真实存在（构建期 `--check` 校验无悬空）。

## 一、安装过程与安全审查（先于一切分析）

用户给定的一键安装命令是 `curl -fsSL ... | bash -s -- --agent workbuddy --skill create-peony-desktop-manager-widget`。
按「绝不盲跑管道」纪律，先取证再安装：

| 步骤 | 动作 | 结论 |
|---|---|---|
| 1 | `git clone --depth 1` 全仓到临时区 | 504 文件、6 大分类（ukui/ai/devops/community/domain/linux-generic），peony 插件组 7 个 skill |
| 2 | 逐行审阅 install.sh 全文（1167 行，v1.2.0） | **P2 级（可安装）**：仅从 Gitee 下载 skill 文件（API contents / 仓库 zip archive / raw CDN）并拷贝到目标目录；无 `eval`、无 curl↑bash 嵌套、无外传数据、无系统级写入；唯一删除动作是目标 skill 目录的 `rm -rf` 后重装（幂等设计） |
| 3 | 下载远程 master 的 install.sh 与本地 clone `diff` | **逐字节一致**——管道实际执行的就是已审阅版本，消除供应链疑点 |
| 4 | 用 install.sh 原生 `--offline` 模式从本地 checkout 安装 | 与线上安装产物逐字节等价（同走 frontmatter 归一化、平铺布局流程），但不经 curl 管道 |
| 5 | 验证安装树 | `~/.workbuddy/skills/create-peony-desktop-manager-widget/` 5 文件：SKILL.md、agents/openai.yaml、references/{templates,implementations,external-projects}.md |

安装位置遵循文章指引：用户级 `~/.workbuddy/skills/`（所有项目可用；`--agent workbuddy-project` 则是项目级 `.workbuddy/skills/`）。
安装器对 WorkBuddy 的两项自动处理值得登记：SKILL.md 缺 frontmatter 时从「## 技能描述」段合成 name/description（本 skill 自带完整 frontmatter，未触发）；平铺布局下目录名对齐 `name:` 字段。

## 二、资源概览与可复用点

| 资源 | 性质 | 可复用工程纪律 / 概念 | 回灌目标系统 |
|---|---|---|---|
| openkylin-skills 仓库 + `create-peony-desktop-manager-widget` skill | openKylin 社区 AI 技能库（MulanPSL-2.0） | 安装器多 agent 平台适配（nested/flat 布局、frontmatter 自动补全、Gitee API→zip archive 降级）；技能契约 = SKILL.md frontmatter + references 按需读；UKUI 桌面小插件完整契约：`ShowInManager`/`ManagerVariants` 三档、`WidgetItem` 顶层 + `Loader` 延迟右键菜单 + `Menu.popup(host,x,y)`、`z:100000` MouseArea 捕获右键、桌面 shell API 五件套（removeWidgetInstance/showWidgetManager/canResizeWidgetTo/clampWidgetPositionToScreen/getScreenAvailableGeometry）、`/usr/share/ukui/widgets/<Id>/` 扁平安装 | netsys（ukui-desktop-widget）、comp（plugin-install-layout）、apilab（dbus-iface） |
| 文章一（openKylin 公众号） | WorkBuddy × openKylin 桌面小插件教程 | 六步流程范式（说需求→对规范→生成→安装→重启桌面→使用）；插件三种显示尺寸、系统卡片样式、深色主题适配、本地持久化不联网；需求收集先问缺失关键信息、不拿猜测值生成 | netsys（ukui-desktop-widget 的 redline 与应用场景） |
| 文章二（电脑报） | Quick Share ↔ AirDrop 跨平台直传 | 2025-11 谷歌宣布 Quick Share 兼容 AirDrop；小米澎湃 OS 4 全面兼容苹果生态（18 Pro 系列 4.0.24 起新增「与 Apple 设备互传」）；前提：安卓开蓝牙+Wi-Fi、苹果端隔空投送设「所有人（10 分钟）」；机型覆盖：三星 S26/S25/S24、Pixel 8a–10、小米 17T Pro、OPPO Find X9、vivo X300、荣耀 Magic V6、一加 15；隐私限制：跨平台仍须临时放开可见范围 | netsys（quickshare-airdrop） |

## 三、概念映射与落地明细

### netsys（40 模块，+2）与出边（6→8）

- `ukui-desktop-widget`（UKUI 桌面小插件体系）：`reference` 性质（第三方项目只读引用登记，不打包二进制）、L7/standalone。redline：不生成、不安装、不删除 widget，不写 `/usr/share/ukui/widgets/`，不调用桌面 shell。
- `quickshare-airdrop`（跨平台近场直传）：`reference`、L7/lan，与 `meshchat` 互补（设备间传输同族）；redline：不经手任何文件传输，不安装/调用投送服务。
- 新增 2 条出边（构建顺序：先建 netsys 模块 → comp/apilab 概念 → netsys 补桥接，保证三个 build 的 `--check` 全绿）：

| netsys 出边 | 目标 | 关系 | 含义 |
|---|---|---|---|
| ukui-desktop-widget | comp:plugin-install-layout | 安装契约实例 | 三类产物必须装到运行时发现路径，是「构建终点=被发现」的活样本 |
| ukui-desktop-widget | apilab:dbus-iface | 接口信道同一族 | 插件经 D-Bus 系统服务完成发现与交互；接口可见性即能力面 |

### comp（54 概念，+1）

- `plugin-install-layout`（插件安装布局）：build 轴。gist：构建的终点不是编译成功，而是安装结果被运行时发现——QML 插件库+qmldir / widget 元数据 / QML 运行文件三类产物各有安装路径，漏一项运行时就少一项发现。detail 登记 peony widget 安装契约（扁平目录、metadata.json 只写扁平文件名、TARGET/qmldir/plugin.cpp 三者模块名一致、qmake 的 INSTALLS 与 CMake 等价 install()）。bridges → netsys:module:ukui-desktop-widget（安装契约实例）。

### apilab（36 概念，+1）

- `dbus-iface`（D-Bus 桌面系统接口）：transport 轴。detail 登记三要素（对象路径+接口+信号）、服务发现（知名名↔唯一连接名）、org.ukui.* 服务的能力面语义；engineering：未落地本仓库不监听 D-Bus，但 ACTIONS 白名单与接口可见性同为「显式声明的能力面」。bridges → netsys:module:ukui-desktop-widget（接口消费者）。

## 四、诚实边界

- openKylin 仓库 68 个技能中**只精读目标 skill 全文**（SKILL.md + 三篇 references），其余仅按目录树与 README 登记生态事实（分类、数量、许可证），不逐一分析、不登记其内部细节。
- UKUI D-Bus 接口清单取自仓库内规划文档（`docs/UKUI接口技能规划.md`，已排除「待定义/待移除/二期计划」项）；沙箱无 UKUI 环境，**未在本机实测**任何接口。
- 文章中番茄钟/便签两插件的功能清单为教程口径（三种尺寸、本地持久化、深色适配），**未运行验证**；Quick Share/AirDrop 的机型与版本号为媒体 2026-10-19 报道口径。
- `quickshare-airdrop` 与 `meshchat` 的互补是**同族关系**（设备间文件传输），不是事实等价断言。
- 本轮不新增 plang 语言条目：openKylin 生态未贡献新语言或新标准编号，无 probe 证据不动 plang。

## 五、验证

- 三个 build（netsys/comp/apilab）`--check` 全绿：40 模块 / 54 概念 48 桥 / 36 概念 18 桥，RFC 全命中、无悬空轴。
- `topo()` 实测：`sum(out)==sum(in)==250`（内部桥接 246→250，守恒），外部 llvm×10 + langref×2 不变，总桥接 262。
- 受影响测试子集（netsys/comp/apilab/concepts_center/pkg_layer + GUI 页）全过；新增 `test_imported_okskills_modules` 契约测试（reference 性质 + 只读红线 + 互补端点）。
