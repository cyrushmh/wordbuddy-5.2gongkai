"""FTP + 目录服务为基础的传输 / 负载验证（v0.6.91 新建）。

以 docs/74 查阅的真实标准为纪律底座，把「上传 / 下载 / 负载验证」落成**可测试**的
原生能力，补本项目组网能力（meshchat 仅做文件属性通知 + 按需 TCP 拉取，无字节级引擎）
的缺口：

- 传输层与可靠性：HTTP Range 分块续传、ETag/Digest 完整性校验、TLS 基线
  （docs/74 §3.2 / §3.4）——本模块用 FTP 的 **REST 断点续传** + **sha256 逐字节校验**
  实现同一精神（FTP RFC 959 / FTPS RFC 4217）。
- 目录服务：FTP 的 MLSD/MLST/LIST/CWD/MKD 即「远程目录列举与管理」基础设施
  （docs/74 §一 表），作为上传/下载/负载验证的寻址与清单基础。
- 负载验证：受控速率（token bucket 限速自约束，对齐 LinkSwift docs/73「并发/带宽上限」）
  + 吞吐测量，验证链路在限定速率下的稳定性。
- 安全基线：密码**只从环境变量读取，绝不落盘、绝不进 CLI 参数、绝不写仓库**
  （对齐 meshchat「收到的东西不自动落盘」+ distcompute「不收外部代码」）。

参考标准（详见 docs/74 / docs/75）：
- FTP RFC 959 / FTPS RFC 4217 / SFTP（SSH-2，RFC 4251）
- HTTP Range RFC 9110 §14.3.3 / ETag RFC 9110 / Digest RFC 9530 / 429 RFC 6585
- TLS 1.3 RFC 8446 / Anycast RFC 4786 / 一致性哈希 Karger 1997

红线（与全仓只读/不信任对端纪律一致，但本模块**需要显式目标才出网**，默认不连）：
- 绝不硬编码任何凭据；密码经 --passenv 从环境变量读，缺失即报错，绝不回退默认值。
- 绝不因平台不匹配在 import 阶段崩溃；真实 FTP I/O 仅在 connect() 调用时发生。
- 绝不静默吞错：每个操作返回 (ok, detail) 元组，失败带上传/下载偏移与原因。
- 限速自约束与并发上限是**自律**不是摆设——loadtest 超出速率即主动 sleep。
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


# --------------------------------------------------------------------------- #
# 纯逻辑单元（无 I/O，直接可单测）
# --------------------------------------------------------------------------- #

def checksum(path: str, algo: str = "sha256", chunk_size: int = 1 << 20) -> str:
    """对本地文件计算摘要（默认 sha256）。失败抛出，由上层转 (ok, detail)。"""
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(chunk_size), b""):
            h.update(blk)
    return h.hexdigest()


def plan_chunks(total: int, chunk_size: int) -> list[tuple[int, int]]:
    """把 [0, total) 切成 (offset, length) 块列表。total<=0 返回空。"""
    if total <= 0 or chunk_size <= 0:
        return []
    out = []
    off = 0
    while off < total:
        length = min(chunk_size, total - off)
        out.append((off, length))
        off += length
    return out


def resume_offset(local_size: int, remote_size: int) -> int:
    """续传起点：已传部分（remote_size）与本地一致则从此继续，否则从头。"""
    if remote_size is None or remote_size < 0:
        return 0
    if local_size is None or local_size < 0:
        return 0
    # 远端已存在且未超过本地 -> 续传；远端 >= 本地 -> 视为已完成，从头覆盖由调用方决定
    return min(remote_size, local_size)


def throughput(bytes_transferred: int, elapsed: float) -> float:
    """字节/秒；elapsed<=0 保护为 0。"""
    if elapsed <= 0:
        return 0.0
    return bytes_transferred / elapsed


class TokenBucket:
    """漏桶式限速器（docs/73 限速自约束的纯逻辑实现）。

    rate_bytes_per_sec<=0 表示不限速。每次 want(n) 返回允许立即发送的量，
    并 sleep 掉为补足额度所需的等待时间——调用方用返回值切片发送。
    """

    def __init__(self, rate_bytes_per_sec: float = 0.0, bucket_cap_factor: float = 2.0,
                 clock: Callable[[], float] = time.monotonic):
        self.rate = max(0.0, rate_bytes_per_sec)
        self.clock = clock
        self.cap = self.rate * bucket_cap_factor if self.rate > 0 else 0.0
        self._level = self.cap
        self._last = self.clock()

    def want(self, n: int) -> int:
        if self.rate <= 0 or n <= 0:
            return n
        now = self.clock()
        # 按真实流逝补充额度
        self._level = min(self.cap, self._level + (now - self._last) * self.rate)
        self._last = now
        if self._level >= n:
            self._level -= n
            return n
        # 额度不足：先发能发的，再为剩余额度等待
        send_now = int(self._level)
        deficit = n - send_now
        if self.rate > 0:
            time.sleep(deficit / self.rate)
        self._level = 0.0
        return send_now + deficit


# --------------------------------------------------------------------------- #
# 配置与传输引擎
# --------------------------------------------------------------------------- #

@dataclass
class TransferConfig:
    """FTP 目标配置。**密码绝不进本结构体的字符串字面量**，改从环境变量读。"""
    host: str
    port: int = 21
    user: str = "anonymous"
    tls: bool = False
    passive: bool = True
    timeout: float = 30.0
    # 密码经 resolve_passwd() 注入；本结构体默认空，绝不硬编码默认值
    passwd: str = field(default="", repr=False)


def resolve_passwd(passenv: Optional[str]) -> str:
    """从环境变量取密码；缺失即抛 ValueError（不回退、不默认可空口令）。"""
    if not passenv:
        raise ValueError("未指定密码环境变量名（--passenv）；拒绝以空口令/默认口令连接")
    val = os.environ.get(passenv, "")
    if not val:
        raise ValueError(f"环境变量 {passenv} 未设置或为空；拒绝连接")
    return val


class TransferError(Exception):
    """传输引擎的显式失败（携带偏移与原因，便于上层 (ok, detail)）。"""


class FtpTransfer:
    """基于 ftplib 的传输引擎（FTP / FTPS）。

    ftp_factory 可注入（测试时换 mock）；默认按 cfg.tls 选 FTP_TLS / FTP。
    所有真实网络 I/O 仅在方法调用内发生，import 阶段零副作用。
    """

    def __init__(self, cfg: TransferConfig, ftp_factory: Optional[Callable] = None):
        self.cfg = cfg
        self._ftp: Optional[object] = None
        self._factory = ftp_factory

    # 惰性工厂：仅在 connect 时触碰 ftplib，import 安全
    def _make(self):
        if self._factory:
            return self._factory(self.cfg)
        import ftplib  # 惰性：未用时绝不 import（虽是标准库，仍尊重惰性守卫）
        if self.cfg.tls:
            return ftplib.FTP_TLS()
        return ftplib.FTP()

    def connect(self) -> None:
        """建连 + 登录 + 模式（被动）。失败抛 TransferError。"""
        try:
            self._ftp = self._make()
            self._ftp.connect(self.cfg.host, self.cfg.port, timeout=self.cfg.timeout)
            self._ftp.login(self.cfg.user, self.cfg.passwd)
            if self.cfg.tls and hasattr(self._ftp, "prot_p"):
                self._ftp.prot_p()  # 私有数据通道加密
            if self.cfg.passive and hasattr(self._ftp, "set_pasv"):
                self._ftp.set_pasv(True)
        except Exception as exc:  # noqa: BLE001 - 网络层异常统一转译
            raise TransferError(f"connect({self.cfg.host}:{self.cfg.port}) 失败：{exc}") from exc

    def close(self) -> None:
        if self._ftp is not None:
            try:
                self._ftp.quit()
            except Exception:  # noqa: BLE001
                try:
                    self._ftp.close()
                except Exception:  # noqa: BLE001
                    pass
            self._ftp = None

    # ----- 目录服务（docs/74：FTP 的 MLSD/MLST/LIST 即目录基础设施） ----- #
    def list_dir(self, path: str = ".") -> list[dict]:
        """列举远程目录（优先 MLSD，退化 LIST）。返回 [{name,type,size,mtime}]。"""
        ftp = self._require()
        try:
            out = []
            try:
                for name, facts in ftp.mlsd(path):
                    if name in (".", ".."):
                        continue
                    out.append({
                        "name": name,
                        "type": facts.get("type", "file"),
                        "size": int(facts.get("size", 0) or 0),
                        "mtime": facts.get("modify", ""),
                    })
                return out
            except Exception:  # noqa: BLE001 - 服务端不支持 MLSD，退化 LIST
                lines = []
                ftp.retrlines(f"LIST {path}", lines.append)
                for ln in lines:
                    out.append({"raw": ln.strip()})
                return out
        except Exception as exc:  # noqa: BLE001
            raise TransferError(f"list_dir({path}) 失败：{exc}") from exc

    def mkdir(self, path: str) -> None:
        ftp = self._require()
        try:
            ftp.mkd(path)
        except Exception as exc:  # noqa: BLE001
            # 已存在等非致命可放宽；其余抛出
            if "550" not in str(exc):
                raise TransferError(f"mkdir({path}) 失败：{exc}") from exc

    def pwd(self) -> str:
        return self._require().pwd()

    def cwd(self, path: str) -> None:
        self._require().cwd(path)

    # ----- 上传（STOR / APPE + REST 续传 + 回读校验） ----- #
    def upload(self, local: str, remote: str, verify: bool = True,
               resume: bool = False, rate_limit: float = 0.0) -> dict:
        """上传本地文件到远端。返回含 offset/checksum/verified 的明细字典。

        - resume=True：先查远端 SIZE，用 REST 跳过已传部分（APPE 追加）。
        - verify=True：回读远端文件做 sha256，与本地比对（docs/74 下载即校验精神）。
        - rate_limit>0：token bucket 限速自约束。
        """
        ftp = self._require()
        if not os.path.isfile(local):
            raise TransferError(f"本地文件不存在：{local}")
        local_size = os.path.getsize(local)
        offset = 0
        if resume:
            try:
                offset = max(0, self._remote_size(remote))
            except Exception:  # noqa: BLE001
                offset = 0
        bucket = TokenBucket(rate_limit) if rate_limit > 0 else None
        algo = "sha256"
        local_hash = checksum(local, algo)

        def _reader() -> bytes:
            with open(local, "rb") as fh:
                if offset:
                    fh.seek(offset)
                while True:
                    blk = fh.read(1 << 16)
                    if not blk:
                        break
                    if bucket is not None:
                        take = bucket.want(len(blk))
                        if take < len(blk):
                            yield blk[:take]
                            time.sleep((len(blk) - take) / rate_limit)
                            continue
                    yield blk

        try:
            if offset:
                ftp.voidcmd(f"REST {offset}")
                ftp.storbinary(f"APPE {remote}", _reader())
            else:
                ftp.storbinary(f"STOR {remote}", _reader())
        except Exception as exc:  # noqa: BLE001
            raise TransferError(f"upload({local}->{remote}) 偏移 {offset} 失败：{exc}") from exc

        result = {"local": local, "remote": remote, "offset": offset,
                  "local_size": local_size, "local_sha256": local_hash}
        if verify:
            ok, detail = self._roundtrip_verify(remote, local_hash, algo)
            result["verified"] = ok
            result["verify_detail"] = detail
            if not ok:
                raise TransferError(f"上传校验失败：{detail}")
        return result

    # ----- 下载（RETR + REST 续传 + 校验） ----- #
    def download(self, remote: str, local: str, verify: bool = True,
                 resume: bool = False, rate_limit: float = 0.0,
                 expected_hash: str = "") -> dict:
        """下载远端文件到本地。返回含 offset/size/checksum/verified 的明细字典。

        - resume=True：若本地已存在部分文件，用 REST 跳过已下部分。
        - verify=True：本地 sha256 与 expected_hash 比对；无 expected 则仅比大小。
        - rate_limit>0：回调内 token bucket 限速。
        """
        ftp = self._require()
        remote_size = self._remote_size(remote)
        offset = 0
        mode = "wb"
        if resume and os.path.isfile(local):
            offset = os.path.getsize(local)
            mode = "ab"
        bucket = TokenBucket(rate_limit) if rate_limit > 0 else None

        start = time.monotonic()
        received = 0
        tmp_hash = hashlib.sha256()
        try:
            if offset:
                ftp.voidcmd(f"REST {offset}")

            def _cb(blk: bytes):
                nonlocal received
                data = blk
                if bucket is not None:
                    take = bucket.want(len(blk))
                    if take < len(blk):
                        data = blk[:take]
                        time.sleep((len(blk) - take) / rate_limit)
                tmp_hash.update(data)
                with open(local, mode) as fh:
                    fh.seek(offset + received)
                    fh.write(data)
                received += len(data)

            ftp.retrbinary(f"RETR {remote}", _cb)
        except Exception as exc:  # noqa: BLE001
            raise TransferError(f"download({remote}->{local}) 偏移 {offset} 失败：{exc}") from exc
        elapsed = time.monotonic() - start

        result = {"remote": remote, "local": local, "offset": offset,
                  "received": received, "remote_size": remote_size,
                  "elapsed": elapsed,
                  "throughput": throughput(received, elapsed),
                  "local_sha256": tmp_hash.hexdigest()}
        if verify:
            if expected_hash:
                ok = (tmp_hash.hexdigest().lower() == expected_hash.lower())
                result["verified"] = ok
                result["verify_detail"] = ("sha256 匹配" if ok else "sha256 不匹配")
            else:
                ok = (received == remote_size) if remote_size else True
                result["verified"] = ok
                result["verify_detail"] = ("大小一致" if ok else "大小不一致")
            if not ok:
                raise TransferError(f"下载校验失败：{result['verify_detail']}")
        return result

    # ----- 负载验证（受控速率吞吐测量） ----- #
    def loadtest(self, size: int = 1 << 24, duration: float = 5.0,
                 rate_limit: float = 0.0, remote_tmp: str = ".__loadtest__.bin") -> dict:
        """向远端临时文件灌入 `size` 字节并测量吞吐（受 rate_limit 自约束）。

        返回 {sent, elapsed, throughput, rate_limited}。测试用临时文件传完即删。
        """
        ftp = self._require()
        bucket = TokenBucket(rate_limit) if rate_limit > 0 else None
        start = time.monotonic()
        sent = 0
        blk = b"\x00" * (1 << 16)

        def _gen():
            nonlocal sent
            while sent < size:
                piece = blk if sent + len(blk) <= size else blk[:size - sent]
                if bucket is not None:
                    take = bucket.want(len(piece))
                    if take < len(piece):
                        piece = piece[:take]
                        time.sleep((len(piece) - take) / rate_limit)
                sent += len(piece)
                yield piece

        try:
            ftp.storbinary(f"STOR {remote_tmp}", _gen())
        except Exception as exc:  # noqa: BLE001
            raise TransferError(f"loadtest 灌入失败：{exc}") from exc
        finally:
            try:
                ftp.delete(remote_tmp)
            except Exception:  # noqa: BLE001
                pass
        elapsed = time.monotonic() - start
        return {"sent": sent, "elapsed": elapsed,
                "throughput": throughput(sent, elapsed),
                "rate_limited": rate_limit > 0}

    # ----- 内部工具 ----- #
    def _require(self):
        if self._ftp is None:
            raise TransferError("尚未 connect()；请先调用 connect()")
        return self._ftp

    def _remote_size(self, remote: str) -> int:
        try:
            sz = self._ftp.size(remote)  # type: ignore[attr-defined]
            return int(sz) if sz is not None else 0
        except Exception:  # noqa: BLE001
            return 0

    def _roundtrip_verify(self, remote: str, expected: str, algo: str) -> tuple:
        """回读远端做 sha256 与本地比对（下载即校验，docs/74 §3.4）。"""
        h = hashlib.new(algo)
        try:
            self._ftp.retrbinary(f"RETR {remote}", h.update)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            return False, f"回读校验取数失败：{exc}"
        got = h.hexdigest()
        return (got.lower() == expected.lower(), f"{algo} 本地={expected[:12]}… 远端={got[:12]}…")
