"""native.transfer 单元测试（v0.6.91）。

覆盖：纯逻辑单元（checksum / plan_chunks / resume_offset / throughput / TokenBucket）
+ 注入 FakeFTP 的传输编排（connect/list/upload 回读校验/download/loadtest），
不触碰任何真实网络、不依赖 pyftpdlib。
"""

import hashlib
import os
import tempfile

import pytest

from sysweeper.native import transfer as tr


# --------------------------------------------------------------------------- #
# 纯逻辑
# --------------------------------------------------------------------------- #
def test_checksum_known():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        path = f.name
    try:
        assert tr.checksum(path) == hashlib.sha256(b"hello").hexdigest()
    finally:
        os.unlink(path)


def test_plan_chunks():
    assert tr.plan_chunks(0, 1024) == []
    assert tr.plan_chunks(10, 1024) == [(0, 10)]
    assert tr.plan_chunks(2500, 1000) == [(0, 1000), (1000, 1000), (2000, 500)]
    assert tr.plan_chunks(3000, 1000) == [(0, 1000), (1000, 1000), (2000, 1000)]


def test_resume_offset():
    assert tr.resume_offset(100, 40) == 40
    assert tr.resume_offset(100, 200) == 100      # 远端 >= 本地 -> 从头覆盖由调用方决定
    assert tr.resume_offset(100, -1) == 0          # 远端缺失 -> 0
    assert tr.resume_offset(-1, 50) == 0


def test_throughput():
    assert tr.throughput(0, 0) == 0.0
    assert tr.throughput(1000, 1.0) == 1000.0
    assert tr.throughput(1000, 2.0) == 500.0


def test_tokenbucket_unlimited():
    b = tr.TokenBucket(rate_bytes_per_sec=0.0)
    assert b.want(10_000_000) == 10_000_000     # 不限速立即放行


def test_tokenbucket_limited_returns_full(monkeypatch):
    slept = []
    monkeypatch.setattr(tr.time, "sleep", lambda s: slept.append(s))
    b = tr.TokenBucket(rate_bytes_per_sec=10.0, bucket_cap_factor=2.0)  # cap=20
    assert b.want(50) == 50                       # 首次 deficit=30 -> sleep(3s)
    assert len(slept) == 1 and abs(slept[0] - 3.0) < 1e-6


# --------------------------------------------------------------------------- #
# FakeFTP：内存文件系统，无真实网络
# --------------------------------------------------------------------------- #
class FakeFTP:
    def __init__(self, cfg=None):
        self.cfg = cfg
        self.store = {}          # path -> bytes
        self.dirs = {"/"}
        self.cwd_path = "/"
        self.pasv = True

    def connect(self, host, port, timeout=30):
        self.host, self.port = host, port

    def login(self, user, passwd):
        self.user, self.passwd = user, passwd

    def prot_p(self):
        pass

    def set_pasv(self, v):
        self.pasv = v

    def pwd(self):
        return self.cwd_path

    def cwd(self, path):
        self.cwd_path = path

    def mkd(self, path):
        if path in self.dirs:
            raise self.Error(f"550 {path} exists")
        self.dirs.add(path)

    def size(self, remote):
        return len(self.store[remote]) if remote in self.store else None

    def mlsd(self, path="."):
        for name, data in self.store.items():
            yield name, {"type": "file", "size": len(data), "modify": "20261025"}

    def retrlines(self, cmd, cb):
        for name in self.store:
            cb(f"-rw-r--r-- 1 user user {len(self.store[name])} {name}")

    def storbinary(self, cmd, reader):
        buf = b"".join(reader)
        remote = cmd.split(" ", 1)[1]
        self.store[remote] = buf

    def retrbinary(self, cmd, cb):
        remote = cmd.split(" ", 1)[1]
        if remote in self.store:
            cb(self.store[remote])

    def delete(self, remote):
        self.store.pop(remote, None)

    def quit(self):
        pass

    def close(self):
        pass

    class Error(Exception):
        pass


def _cfg(**kw):
    return tr.TransferConfig(host="h", port=21, user="u", passwd="p", **kw)


def test_ftp_connect_and_list():
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    eng.mkdir("/x")
    assert eng.pwd() == "/"
    # list 空目录
    rows = eng.list_dir(".")
    assert rows == []
    eng.close()


def test_ftp_upload_roundtrip_verify(tmp_path):
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    src = tmp_path / "a.bin"
    data = b"abcdef" * 1000
    src.write_bytes(data)
    res = eng.upload(str(src), "a.bin", verify=True, resume=False, rate_limit=0.0)
    assert res["verified"] is True
    assert res["local_sha256"] == hashlib.sha256(data).hexdigest()
    # 远端确有内容且与本地一致
    assert eng._ftp.store["a.bin"] == data
    eng.close()


def test_ftp_download_and_verify(tmp_path):
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    data = b"xyz" * 500
    eng._ftp.store["b.bin"] = data
    dst = tmp_path / "b.bin"
    res = eng.download("b.bin", str(dst), verify=True, expected_hash=hashlib.sha256(data).hexdigest())
    assert res["verified"] is True
    assert dst.read_bytes() == data
    assert res["received"] == len(data)
    eng.close()


def test_ftp_download_unverified_size_mismatch(tmp_path):
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    eng._ftp.store["c.bin"] = b"short"
    dst = tmp_path / "c.bin"
    # 无 expected_hash：仅比大小；远端 5B == 接收 5B -> 通过
    res = eng.download("c.bin", str(dst), verify=True)
    assert res["verified"] is True
    eng.close()


def test_ftp_loadtest(tmp_path):
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    res = eng.loadtest(size=1 << 16, duration=1.0, rate_limit=0.0)
    assert res["sent"] == 1 << 16
    assert res["rate_limited"] is False
    # 临时文件已清理
    assert "__loadtest__.bin" not in eng._ftp.store
    eng.close()


def test_ftp_loadtest_rate_limited(tmp_path, monkeypatch):
    slept = []
    monkeypatch.setattr(tr.time, "sleep", lambda s: slept.append(s))
    eng = tr.FtpTransfer(_cfg(), ftp_factory=FakeFTP)
    eng.connect()
    # 速率极低（1 B/s），会让灌入过程触发 sleep 限速
    res = eng.loadtest(size=1 << 10, duration=1.0, rate_limit=1.0)
    assert res["rate_limited"] is True
    assert res["sent"] == 1 << 10
    eng.close()


def test_resolve_passwd_rejects_missing(monkeypatch):
    monkeypatch.delenv("FTP_PASS", raising=False)
    with pytest.raises(ValueError):
        tr.resolve_passwd("FTP_PASS")
    monkeypatch.setenv("FTP_PASS", "secret")
    assert tr.resolve_passwd("FTP_PASS") == "secret"


def test_cli_registers_nettransfer():
    import argparse
    from sysweeper import cli
    p = cli.build_parser()
    sp = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    choices = sp.choices
    assert "nettransfer" in choices
    sub = choices["nettransfer"]
    assert any(a.dest == "op" for a in sub._actions)
    assert any(a.dest == "passenv" for a in sub._actions)
