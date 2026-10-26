"""容器运行时（Docker / Podman / containerd / BuildKit / OCI / LXC-LXD / CRI）
的原生接口与文档引用。

「触类旁通、举一反三」：在系统软件、鸿蒙、小程序端、包管理器之后，本层把同一模式
推广到**容器运行时**。它们同样是接口彼此完全不同的领域，逐个按**自身的协议与接口**
核对，绝不套用同一套路径：

- Docker       : OCI runtime-spec + Docker 镜像 manifest(v2+json) + Engine API(/var/run/docker.sock)
                 docker system df / image prune / container prune / volume prune / builder prune
- Podman       : OCI + 兼容 docker CLI + rootless(crun/slirp4netns/fuse-overlayfs)
                 podman system df / image prune / volume prune（数据根 ~/.local/share/containers）
- containerd   : OCI + 插件架构(images/tasks/snapshots) + Content Store(内容寻址) + Snapshotter
                 nerdctl system prune / ctr images ls（无 docker 那套系统级 prune）
- BuildKit     : LLB 构建图 + 内容寻址 build cache（/var/lib/docker/buildkit）
                 docker builder prune -a / docker buildx prune -a
- OCI          : Image Spec(manifest/index/descriptor) + Runtime Spec(config.json) + digest 内容寻址
                 skopeo / umoci / runc
- LXC/LXD      : liblxc + LXD REST(/1.0) + 存储池(ZFS/Btrfs/LVM/dir)
                 lxc image delete / lxc storage volume rm
- CRI          : CRI gRPC(RuntimeService/ImageService) + Pod 沙箱(pause)
                 crictl images / rmi / ps / rm

所有探测只读：仅统计磁盘占用与可清理项数量，不做任何删除/安装。未安装该运行时或守护
进程未运行时返回 (False, 说明)，由上层降级为指引。参考文档见 data/container_docs.json。
"""

from __future__ import annotations

import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "container_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(rt_id: str) -> dict:
    """返回某容器运行时的文档参考（含协议 protocols 与接口 interfaces）。"""
    return REFS.get(rt_id, {})


def reference_all() -> dict:
    """返回全部容器运行时文档参考。"""
    return REFS


def _common_run(cmd: str, timeout: int = 30):
    from . import common
    return common.run(cmd, timeout=timeout)


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024 / 1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MiB"
    if n >= 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n} B"


def _dir_size(path: str) -> int:
    """递归统计目录字节数（只读）。不存在或不可读返回 0。"""
    total = 0
    if not path or not os.path.isdir(path):
        return 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _indent(text: str, prefix: str = "   ") -> str:
    return "\n".join(prefix + l if l else l for l in (text or "").splitlines())


def detect_container() -> dict:
    """探测本机可用的容器运行时（按各自官方 CLI 是否可用判断，只读 which 查询）。"""
    return {
        "docker": bool(shutil.which("docker")),
        "podman": bool(shutil.which("podman")),
        "containerd": bool(shutil.which("nerdctl") or shutil.which("ctr")),
        "buildkit": bool(shutil.which("docker")),
        "oci": bool(shutil.which("skopeo")),
        "lxc": bool(shutil.which("lxc")),
        "cri": bool(shutil.which("crictl")),
    }


# --------------------------------------------------------------------------- #
# 各运行时只读探测：返回 (ok: bool, msg: str)。ok 表示该运行时可用且探测成功。  #
# --------------------------------------------------------------------------- #

def docker_report() -> tuple:
    if not shutil.which("docker"):
        return False, "未安装 Docker（dockerd / CLI），跳过"
    rc, out = _common_run("docker system df 2>/dev/null", timeout=45)
    if rc != 0 or not (out or "").strip():
        return False, ("Docker 守护进程未运行或无权限（docker system df 失败；"
                       "需 dockerd 运行且当前用户在 docker 组）")
    lines = ["Docker 磁盘占用（docker system df）：", _indent(out)]
    rc2, dangling = _common_run(
        "docker images -f dangling=true -q 2>/dev/null | wc -l", timeout=30)
    if rc2 == 0 and (dangling or "").strip():
        lines.append(f"   · 悬空镜像: {dangling.strip()} 个 → docker image prune -f")
    return True, "\n".join(lines)


def podman_report() -> tuple:
    if not shutil.which("podman"):
        return False, "未安装 Podman（CLI），跳过"
    rc, out = _common_run("podman system df 2>/dev/null", timeout=45)
    if rc != 0 or not (out or "").strip():
        return False, ("Podman 存储未就绪（podman system df 失败；"
                       "检查 /var/lib/containers/storage 权限或 rootless 用户命名空间）")
    lines = ["Podman 磁盘占用（podman system df）：", _indent(out)]
    rc2, dangling = _common_run(
        "podman images -f dangling=true -q 2>/dev/null | wc -l", timeout=30)
    if rc2 == 0 and (dangling or "").strip():
        lines.append(f"   · 悬空镜像: {dangling.strip()} 个 → podman image prune -a -f")
    return True, "\n".join(lines)


def containerd_report() -> tuple:
    if shutil.which("nerdctl"):
        rc, out = _common_run("nerdctl system df 2>/dev/null", timeout=45)
        if rc == 0 and (out or "").strip():
            return True, "containerd 磁盘占用（nerdctl system df）：\n" + _indent(out)
    if shutil.which("ctr"):
        rc, out = _common_run("ctr images ls 2>/dev/null", timeout=45)
        if rc == 0 and (out or "").strip():
            rows = [l for l in out.splitlines()
                    if l.strip() and not l.startswith("REF")]
            n = max(len(rows) - 1, 0) if rows else 0
            lines = [f"containerd 镜像（ctr images ls）：{n} 个",
                     "   · 回收: nerdctl system prune，或 ctr images rm <ref> + ctr snapshots rm",
                     "   · 孤儿 blob: ctr content prune / ctr snapshots prune（仅删无 lease 引用）"]
            return True, "\n".join(lines)
        return False, ("containerd 守护进程未运行或无权限（ctr images ls 失败；"
                       "需 containerd 服务运行，且当前用户在 containerd 组或 root）")
    return False, "未安装 containerd（nerdctl / ctr 均不可用），跳过"


def buildkit_report() -> tuple:
    if not shutil.which("docker"):
        return False, "未安装 Docker（BuildKit 随 dockerd 提供），跳过"
    p = "/var/lib/docker/buildkit"
    if not os.path.isdir(p):
        return False, "未发现 BuildKit 缓存目录 /var/lib/docker/buildkit"
    size = _dir_size(p)
    lines = [f"BuildKit 构建缓存: {p}",
             f"   · 占用: {_fmt_size(size)}",
             "   · 回收: docker builder prune -a -f（或 docker buildx prune -a -f）"]
    return True, "\n".join(lines)


def oci_report() -> tuple:
    if not shutil.which("skopeo"):
        return False, "未安装 skopeo（OCI 镜像复制/检查工具），跳过"
    rc, out = _common_run("skopeo --version 2>/dev/null", timeout=20)
    ver = (out or "").strip().splitlines()[0] if (out or "").strip() else ""
    lines = ["OCI 镜像工具:",
             f"   · skopeo: {ver or '已安装'}",
             "   · 操作: skopeo inspect / delete <oci 或 docker 格式仓库>",
             "   · 规范: Image Spec（manifest/config/layer，digest 内容寻址，共享层按引用计数）"]
    return True, "\n".join(lines)


def lxc_report() -> tuple:
    if not shutil.which("lxc"):
        return False, "未安装 LXC/LXD（lxc CLI），跳过"
    rc, out = _common_run("lxc image list 2>/dev/null", timeout=30)
    if rc != 0:
        return False, "LXD 守护进程未运行（lxc image list 失败；需 lxd 启动）"
    n = len([l for l in out.splitlines()
             if "|" in l and "ALIAS" not in l and "---" not in l])
    lines = [f"LXC/LXD 镜像（lxc image list）：{n} 个",
             "   · 回收未使用: lxc image delete <fingerprint>",
             "   · 孤儿卷: lxc storage volume rm <pool> <type/vol>"]
    return True, "\n".join(lines)


def cri_report() -> tuple:
    if not shutil.which("crictl"):
        return False, "未安装 crictl（CRI 调试 CLI），跳过"
    rc, out = _common_run("crictl images 2>/dev/null", timeout=30)
    if rc != 0 or not (out or "").strip():
        return False, ("CRI 运行时未就绪（crictl images 失败；"
                       "检查 /etc/crictl.yaml 的 runtime-endpoint，如 unix:///run/containerd/containerd.sock）")
    n = len([l for l in out.splitlines()
             if l.strip() and not l.startswith("IMAGE") and "---" not in l])
    lines = [f"CRI 镜像（crictl images）：{max(n - 1, 0)} 个",
             "   · 回收未用: crictl rmi <image>@<digest>",
             "   · 退出容器: crictl rm <id>（默认不碰运行中的 pause 沙箱）"]
    return True, "\n".join(lines)


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("docker_report", "Docker 磁盘占用（system df + 悬空镜像数）"),
    ("podman_report", "Podman 磁盘占用（system df + 悬空镜像数）"),
    ("containerd_report", "containerd 镜像/快照占用（nerdctl system df / ctr images ls）"),
    ("buildkit_report", "BuildKit 构建缓存占用（/var/lib/docker/buildkit）"),
    ("oci_report", "OCI 镜像工具（skopeo 版本与布局能力）"),
    ("lxc_report", "LXC/LXD 镜像与卷占用（lxc image list）"),
    ("cri_report", "CRI 镜像与容器（crictl images）"),
)


def environment_report() -> list:
    """返回本机容器运行时环境概览行（✓ 已装 / ✗ 未装）。"""
    det = detect_container()
    lines = [f"容器运行时可用性："]
    for key, label in (
        ("docker", "Docker"), ("podman", "Podman"), ("containerd", "containerd"),
        ("buildkit", "BuildKit"), ("oci", "OCI(skopeo)"), ("lxc", "LXC/LXD"),
        ("cri", "CRI(crictl)"),
    ):
        mark = "✓" if det.get(key) else "✗"
        lines.append(f"   {mark} {label}")
    return lines


def container_doc_list() -> list:
    """返回文档参考清单文本行（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    协议:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append("    接口:")
        for i in ref.get("interfaces", []):
            lines.append(f"      - {i}")
        lines.append(f"    建议: {ref.get('summary', '')}")
    return lines


def _agg_norm(r):
    """归一化报告返回：tuple→(ok,msg)；list→(True,拼接)；其它→(True,str)。"""
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
        return ok, msg
    if isinstance(r, list):
        return True, "\n".join(str(x) for x in r)
    return True, str(r)


def container_report() -> tuple:
    """容器运行时只读聚合：串联 Docker/Podman/containerd/BuildKit/OCI/LXC-LXD/CRI + 环境探测。"""
    parts = []
    ok_any = False
    for fn in (docker_report, podman_report, containerd_report, buildkit_report,
               oci_report, lxc_report, cri_report, environment_report):
        try:
            ok, msg = _agg_norm(fn())
        except Exception:  # noqa: BLE001
            continue
        ok_any = ok_any or ok
        if msg.strip():
            parts.append(msg.strip())
    if not parts:
        return False, "未检测到任何容器运行时（Docker/Podman/containerd/...）"
    return ok_any, "\n".join(parts)
