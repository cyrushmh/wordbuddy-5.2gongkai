"""容器运行时的清理、核对与优化任务（按各运行时**自身的协议与接口**）。

「触类旁通、举一反三」：在系统软件、鸿蒙、小程序端、包管理器之后，把同一模式推广到
**容器运行时**。它们的接口彼此完全不同，因此逐个按**自身的协议与接口**处理：

- Docker       : docker image/container/volume prune + docker system prune（官方接口，不动 /var/lib/docker 目录）
- Podman       : podman image/volume/system prune（rootless 走 ~/.local/share/containers）
- containerd   : nerdctl system prune，或 ctr content/snapshots prune（回收无 lease 引用的孤儿 blob）
- BuildKit     : docker builder prune -a / docker buildx prune -a（回收内容寻址构建缓存）
- OCI          : 只读核对（skopeo/runc 能力 + digest 共享层引用计数）
- LXC/LXD      : lxc image delete / lxc storage volume rm（按存储池后端 ZFS/Btrfs/LVM/dir）
- CRI          : crictl rmi / crictl rm（Kubernetes 节点上用，不动 pause 沙箱）

删除类动作默认带 `command -v` 守卫：无该运行时自动降级为「跳过」而非报错；中风险（删容器/
卷）还需 --yes。绝不直接 rm -rf 各运行时数据目录——内容寻址/chain_id 一致性一破，守护进程
可能起不来。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

DOCKER = ("[国际] Docker 文档（docker system prune / system df 参考 + OCI runtime-spec "
          "+ Docker Engine API /var/run/docker.sock）")
PODMAN = ("[国际] Podman 文档（podman-system-prune / image-prune / volume-prune + OCI rootless "
          "crun/slirp4netns/fuse-overlayfs）")
CONTAINERD = ("[国际] containerd.io 文档 + nerdctl command-reference（content store 内容寻址 "
              "/ snapshotter / CRI 插件）")
BUILDKIT = ("[国际] moby/buildkit 文档（LLB 构建图 + 内容寻址 build cache "
            "+ docker builder prune / docker buildx prune）")
OCI = ("[国际] OCI image-spec / runtime-spec（manifest/config/layer descriptor + digest 内容寻址 "
       "+ skopeo / umoci / runc）")
LXC = ("[国际] linuxcontainers.org lxc / lxd 文档（liblxc + LXD REST /1.0 "
       "+ 存储池 ZFS/Btrfs/LVM/dir 后端）")
CRI = ("[国际] Kubernetes crictl 文档（CRI gRPC RuntimeService / ImageService "
       "+ Pod 沙箱 pause + kubelet image-gc）")


TASKS = [
    Task(
        id="ct_docker_dangling",
        platform="any",
        title="清 Docker 悬空镜像（docker image prune -f）",
        category="cleanup",
        risk="low",
        desc="删除「无标签且不被任何容器引用」的悬空镜像——典型由构建失败遗留，删了不影响任何运行中的容器。",
        actions=[
            S('if command -v docker >/dev/null; then docker image prune -f 2>/dev/null '
              '&& echo "Docker 悬空镜像已清"; else echo "无 docker，跳过"; fi',
              "删悬空镜像（官方 image prune 接口，不动 /var/lib/docker 目录）", rev=True),
        ],
        standards=[DOCKER],
        notes=["参考 docker image prune：默认只删 dangling（无仓库:标签且未被引用）的镜像；"
               "加 -a 才删「无容器引用」的所有未使用镜像。",
               "悬空层按 digest 共享，只删引用计数归零的层，不影响其他镜像。"],
        caveats=["无数据破坏性（悬空镜像本就不被引用）；离线环境重构建需重新拉取。"],
    ),
    Task(
        id="ct_docker_stopped",
        platform="any",
        title="清 Docker 已停止容器（docker container prune -f）",
        category="cleanup",
        risk="medium",
        desc="删除所有已退出（Exited）状态的容器。容器只读层可重建，但容器内未提交到镜像的改动会丢失。",
        actions=[
            S('if command -v docker >/dev/null; then docker container prune -f 2>/dev/null '
              '&& echo "Docker 已停止容器已清"; else echo "无 docker，跳过"; fi',
              "删所有退出容器（不可恢复，需 --apply 且 --yes）", rev=True),
        ],
        standards=[DOCKER],
        notes=["参考 docker container prune：只针对 status=exited/created 的容器；"
               "运行中的容器不受影响。",
               "若容器是用作临时调试（未 commit），其中改动随之消失——先 docker commit 再清。"],
        caveats=["会真实删除容器元数据与可写层：运行 docker rm 前确认其中无未保存改动。"],
    ),
    Task(
        id="ct_docker_volumes",
        platform="any",
        title="清 Docker 未用卷（docker volume prune -f）",
        category="cleanup",
        risk="medium",
        desc="删除没有任何容器（含已停止）引用的卷。卷常存数据库/持久化数据，删了可能永久丢失。",
        actions=[
            S('if command -v docker >/dev/null; then docker volume prune -f 2>/dev/null '
              '&& echo "Docker 未用卷已清"; else echo "无 docker，跳过"; fi',
              "删无容器引用的卷（数据可能永久丢失，需 --yes）", rev=True),
        ],
        standards=[DOCKER],
        notes=["参考 docker volume prune：默认保留仍被任意容器（哪怕已停止）引用的卷；"
               "-f 才删真正孤儿卷。",
               "匿名卷（未命名）最易被清；命名卷请先 docker volume inspect 确认内容。"],
        caveats=["高风险数据丢失：生产数据库卷务必先备份或 `docker run --rm -v <vol> busybox "
                 "tar` 导出后再清。"],
    ),
    Task(
        id="ct_docker_build",
        platform="any",
        title="清 Docker BuildKit 构建缓存（docker builder prune -f）",
        category="cleanup",
        risk="low",
        desc="回收 /var/lib/docker/buildkit 下内容寻址的构建缓存——随构建次数累积极易膨胀，且不影响已构建镜像。",
        actions=[
            S('if command -v docker >/dev/null; then docker builder prune -f 2>/dev/null '
              '&& echo "BuildKit 构建缓存已清"; else echo "无 docker，跳过"; fi',
              "回收 BuildKit 缓存（官方 builder prune，不影响镜像/容器）", rev=True),
        ],
        standards=[DOCKER, BUILDKIT],
        notes=["参考 docker builder prune：缓存按 diffID 内容寻址，清了下次构建重新计算，"
               "不影响已 push/pull 的镜像。",
               "加 -a 清更彻底（含仍可能被引用的中间层）；--filter until=24h 可按时间保留。"],
        caveats=["清后首次构建变慢（需重算缓存）；不影响运行中的容器。"],
    ),
    Task(
        id="ct_docker_system",
        platform="any",
        title="Docker 系统级组合清理（docker system prune -a -f）",
        category="cleanup",
        risk="medium",
        desc="组合清理：悬空镜像 + 已停止容器 + 未用网络 +（加 -a）所有未使用镜像。一举回收但面较大，需谨慎。",
        actions=[
            S('if command -v docker >/dev/null; then docker system prune -a -f 2>/dev/null '
              '&& echo "Docker 系统级清理完成"; else echo "无 docker，跳过"; fi',
              "组合清理（含全部未使用镜像，需 --yes）", rev=True),
        ],
        standards=[DOCKER],
        notes=["参考 docker system prune：-a 会删所有未容器引用的镜像（不只是悬空），"
               "加 --volumes 才连未用卷一起清（默认不删卷，防误删数据）。",
               "比逐项 prune 省事，但 -a 会让你下次拉镜像重新下载——CI 机常用，个人开发机慎用 -a。"],
        caveats=["面最大：会删你本地所有「当前没在跑」的镜像，下次构建/运行需重新拉取。"],
    ),
    Task(
        id="ct_podman_dangling",
        platform="any",
        title="清 Podman 未使用镜像（podman image prune -a -f）",
        category="cleanup",
        risk="low",
        desc="删除无容器引用的镜像（含有标签但未使用的）。Podman 无 daemon，rootless 下清的是用户命名空间存储。",
        actions=[
            S('if command -v podman >/dev/null; then podman image prune -a -f 2>/dev/null '
              '&& echo "Podman 未使用镜像已清"; else echo "无 podman，跳过"; fi',
              "删未使用镜像（官方 image prune，rootless 走 ~/.local/share/containers）", rev=True),
        ],
        standards=[PODMAN],
        notes=["参考 podman image prune：与 docker 同语义；rootless 模式数据在 "
               "~/.local/share/containers/storage，需用对应用户执行。",
               "不加 -a 只删悬空；加 -a 删所有无容器引用的镜像。"],
        caveats=["rootless 时注意用运行容器的同一用户执行，否则权限不匹配会漏清或报错。"],
    ),
    Task(
        id="ct_podman_volumes",
        platform="any",
        title="清 Podman 未用卷（podman volume prune -f）",
        category="cleanup",
        risk="medium",
        desc="删除无容器引用的 Podman 卷；rootless 下清的是用户命名空间内的卷，数据可能永久丢失。",
        actions=[
            S('if command -v podman >/dev/null; then podman volume prune -f 2>/dev/null '
              '&& echo "Podman 未用卷已清"; else echo "无 podman，跳过"; fi',
              "删无容器引用的卷（需 --yes）", rev=True),
        ],
        standards=[PODMAN],
        notes=["参考 podman volume prune：只删无容器（含停止）引用的卷；"
               "命名卷先 podman volume inspect 确认内容。",
               "rootless 卷路径在 ~/.local/share/containers/storage/volumes。"],
        caveats=["数据丢失风险同 docker volume prune；生产卷先备份。"],
    ),
    Task(
        id="ct_podman_system",
        platform="any",
        title="Podman 系统级组合清理（podman system prune -a -f）",
        category="cleanup",
        risk="medium",
        desc="组合清理：未使用镜像 + 已停止容器 + 未用卷 + 网络。无 daemon 架构，清理与 docker 同语义但命令名不同。",
        actions=[
            S('if command -v podman >/dev/null; then podman system prune -a -f 2>/dev/null '
              '&& echo "Podman 系统清理完成"; else echo "无 podman，跳过"; fi',
              "组合清理（含未使用镜像与卷，需 --yes）", rev=True),
        ],
        standards=[PODMAN],
        notes=["参考 podman system prune：等价于逐项 image/container/volume prune 的组合；"
               "rootless 务必用运行容器的同一用户执行。",
               "Podman 兼容 docker CLI 语义，但 podman.sock 默认也支持 docker API 客户端。"],
        caveats=["面大：会删本地所有未运行镜像与其卷；CI 常用，个人机慎用 -a/-f。"],
    ),
    Task(
        id="ct_containerd_gc",
        platform="any",
        title="回收 containerd 孤儿 blob（nerdctl system prune / ctr prune）",
        category="cleanup",
        risk="medium",
        desc="containerd 无 docker 那套 system prune；借助 nerdctl 组合回收，或直接对 content store 回收无 lease 引用的孤儿 blob。",
        actions=[
            S('if command -v nerdctl >/dev/null; then nerdctl system prune -a 2>/dev/null '
              '&& echo "containerd(nerdctl) 清理完成"; '
              'elif command -v ctr >/dev/null; then ctr content prune 2>/dev/null; '
              'ctr snapshots prune 2>/dev/null; echo "containerd 孤儿 blob 已回收"; '
              'else echo "无 containerd(nerdctl/ctr)，跳过"; fi',
              "nerdctl system prune 组合回收，或 ctr content/snapshots prune 回收无 lease 引用",
              rev=True),
        ],
        standards=[CONTAINERD],
        notes=["参考 containerd 架构：content store 按 digest 存 blob，snapshotter 管可写层；"
               "「孤儿」指不再被任何 lease（镜像/容器引用）指向的 blob。",
               "ctr content prune / ctr snapshots prune 只删无 lease 引用的孤儿，比直接 rm 目录安全。"],
        caveats=["直接删 /var/lib/containerd/io.containerd.content.v1.content 下文件会破坏内容寻址，"
                 "导致镜像 digest 校验失败——务必走 GC 接口。"],
    ),
    Task(
        id="ct_buildx",
        platform="any",
        title="清 Docker Buildx 缓存（docker buildx prune -a -f）",
        category="cleanup",
        risk="low",
        desc="回收 buildx 多驱动（docker-container/kubernetes/remote）下的构建缓存；与 builder prune 同源但覆盖 buildx 专属缓存。",
        actions=[
            S('if command -v docker >/dev/null; then docker buildx prune -a -f 2>/dev/null '
              '&& echo "buildx 缓存已清"; else echo "无 docker，跳过"; fi',
              "回收 buildx 构建缓存（官方 buildx prune，不影响镜像/容器）", rev=True),
        ],
        standards=[BUILDKIT],
        notes=["参考 docker buildx prune：覆盖 buildx 各驱动缓存；--filter until=24h 按时间保留，"
               "-a 清更彻底。",
               "与 docker builder prune 同属 BuildKit，但分属不同缓存命名空间。"],
        caveats=["清后首次 buildx 构建变慢；不影响运行中的容器。"],
    ),
    Task(
        id="ct_lxc_unused",
        platform="any",
        title="回收 LXC/LXD 未使用镜像与孤儿卷",
        category="maintenance",
        risk="medium",
        desc="LXC 是系统容器（每容器独立可写层/存储池卷），不作镜像分层共享；清理须按 LXD 各自存储后端接口，而非删目录。",
        actions=[
            N("container.lxc_report",
              "列出 LXC/LXD 镜像与卷占用（只读，lxc image list）"),
            M("用 lxc image delete <fingerprint> 删未使用镜像；用 lxc storage volume rm <pool> <vol> "
              "删孤儿卷；存储池缩容走 zfs destroy / btrfs 等对应后端，勿直接删 /var/lib/lxd。",
              "按 LXC/LXD 各自后端接口清理（需人工确认容器/卷确属废弃）"),
        ],
        standards=[LXC],
        notes=["参考 LXD 存储：卷是存储池（ZFS/Btrfs/LVM/dir）内对象，删除须走 "
               "lxc storage volume rm，直接删 /var/lib/lxd 会破坏池元数据。",
               "停止容器用 lxc delete（默认保留可写层 12 天，可加 --force 立即删）。"],
        caveats=["系统容器可能存有重要状态；删前确认容器/镜像确属废弃，且存储池无需缩容。"],
    ),
    Task(
        id="ct_oci_report",
        platform="any",
        title="OCI 规范核对（镜像分层与 digest 内容寻址）",
        category="maintenance",
        risk="low",
        desc="只读核对 OCI 工具能力与规范要点：所有运行时镜像分层、digest、diff_id 都遵循 Image Spec，删共享层须看引用计数。",
        actions=[
            N("container.oci_report",
              "列出 OCI 镜像工具（skopeo 等）能力与规范要点（只读）"),
        ],
        standards=[OCI],
        notes=["参考 OCI image-spec：manifest 指向 config 与各 layer，descriptor 用 digest 内容寻址，"
               "同一层被多镜像共享。",
               "清理共享层依赖各运行时 GC，不要按文件名手动删层（误删会让其他镜像失效）。"],
        caveats=["只读任务：仅核对接口能力，不做任何修改。"],
    ),
    Task(
        id="ct_disk_report",
        platform="any",
        title="容器运行时磁盘占用总览（各运行时 system df）",
        category="maintenance",
        risk="low",
        desc="只读汇总本机各容器运行时（Docker/Podman/containerd/BuildKit/LXC/CRI）的可用性与磁盘占用，定位空间杀手。",
        actions=[
            N("container.environment_report",
              "汇总本机各容器运行时可用性与磁盘占用概览（只读）"),
        ],
        standards=[DOCKER, PODMAN, CONTAINERD, BUILDKIT, OCI, LXC, CRI],
        notes=["各运行时的磁盘占用口径不同：docker/podman system df 四项（镜像/容器/卷/构建缓存），"
               "containerd 靠 nerdctl/ctr，LXC 靠 lxc image list。",
               "定位到具体运行时后，再用对应的 prune 接口回收，而非直接删数据目录。"],
        caveats=["只读任务：仅汇总，不修改系统。"],
    ),
]
