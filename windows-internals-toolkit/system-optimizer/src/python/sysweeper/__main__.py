"""`python -m sysweeper` 与 zipapp 单文件（.pyz）共用的入口。"""

import sys

from .cli import main as _cli_main


def main(argv=None):
    """入口。退出码用 ``SystemExit`` 抛，而不是 return。

    为什么要这么绕：zipapp 生成的 shim 内容是写死的两行

        import sysweeper.__main__
        sysweeper.__main__.main()

    它**不会**把返回值交给 sys.exit。也就是说如果这里写成
    ``return _cli_main(argv)``，.pyz 里 main 的退出码会被整个丢掉
    （KeyboardInterrupt 的 130 会变成 0）。抛 SystemExit 才能让
    ``python -m sysweeper`` 和 ``./sysweeper-*.pyz`` 两种入口拿到同一个退出码。
    """
    raise SystemExit(_cli_main(argv))


if __name__ == "__main__":
    sys.exit(main())
