# peinfo (C)

最小 PE 头信息查看器，纯标准 C 文件 I/O，跨平台可编译。本程序自身即合法 PE。

## 编译（交叉编译，无需 Windows）
```bash
x86_64-w64-mingw32-gcc -O2 -s peinfo.c -o peinfo.exe    # PE32+ / x64
i686-w64-mingw32-gcc   -O2 -s peinfo.c -o peinfo32.exe  # PE32  / x86
```
预编译产物见仓库 `tools/` 目录。
