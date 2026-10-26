# syntax=docker/dockerfile:1
#
# sysweeper 容器镜像：跨系统只读诊断 + 量子程序/虚拟机。
#
# 定位：在容器内以任意子命令运行只读诊断（对容器自身环境）、
# 量子虚拟机演示与知识库检索。本仓库的镜像遵循最小权限红线：
#   - 多阶段构建：builder 只产出 wheel/sdist，最终镜像只带 sysweeper 成品；
#   - 非 root 用户运行（useradd -r）；
#   - 零第三方运行时依赖（sysweeper 本体纯标准库），最终镜像除 Python 外无新增依赖；
#   - 目录只读化由 compose 的 read_only + cap_drop 完成（见 docker-compose.yml）。
#
# 打包由仓库自带 tools/syspkg.py 完成（手写 PEP 427 wheel / sdist，纯标准库、
# 不经由 setuptools），因此对去中心化版本号 NNNN.NNNN.NNNN.NNNN[.YYYYMMDD]
# 零依赖、不触发任何 PEP 440 校验（避免不同模型为"合规"改动三处活版本）。
#
# 构建上下文 = 仓库根（docker-compose 已设 context: ..）：
#   docker build -t sysweeper:0.6.70 -f system-optimizer/Dockerfile ..
# 运行：
#   docker run --rm sysweeper:0.6.70 detect
#   docker run --rm sysweeper:0.6.70 sysmap

# ---------- 构建阶段：产出 wheel/sdist（syspkg，不依赖 setuptools） ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# 仅取打包必需文件，并保持 system-optimizer/ 前缀以匹配 syspkg 的 ROOT 约定
# （syspkg 从仓库根运行：ROOT = parents[1](tools/)）：
COPY system-optimizer/pyproject.toml system-optimizer/README.md system-optimizer/MANIFEST.in ./system-optimizer/
COPY system-optimizer/src ./system-optimizer/src
COPY tools ./tools

# 手写 wheel（PEP 427）+ sdist，版本串原样写入，无任何 PEP 440 校验
RUN python3 tools/syspkg.py wheel --out /dist \
 && python3 tools/syspkg.py sdist --out /dist

# ---------- 运行阶段：只装成品 wheel ----------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="sysweeper" \
      org.opencontainers.image.description="跨系统/跨语言/跨平台只读诊断 + 量子程序虚拟机（纯标准库零依赖）" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/cyrushmh/wordbuddy-github"

# 语言/缓存环境：UTF-8 优先；不写 .pyc（镜像层保持干净，只读根下也不报错）
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 非 root 运行用户（系统用户，无登录 shell，家目录供 --report 类输出落盘）
RUN groupadd --system sysweeper \
 && useradd --system --gid sysweeper --home-dir /home/sysweeper --create-home --shell /usr/sbin/nologin sysweeper

# 只安装构建阶段产出的 wheel（--no-index：不从公网解析，保证可复现）
COPY --from=builder /dist /dist
RUN pip install --no-cache-dir --no-index --find-links=/dist sysweeper \
 && rm -rf /dist \
 && python -c "import sysweeper, sysweeper.cli; print('sysweeper', sysweeper.__version__, 'OK')"

USER sysweeper
WORKDIR /home/sysweeper

# ENTRYPOINT 固定为 sysweeper 命令本身，CMD 为默认只读诊断子命令
# （docker run 时尾部参数即子命令，如：docker run --rm sysweeper:0.6.70 quantum bell）
ENTRYPOINT ["sysweeper"]
CMD ["detect"]
