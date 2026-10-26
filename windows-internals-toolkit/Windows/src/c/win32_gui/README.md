# PE Viewer（Win32 API / C）

无第三方依赖的原生 Windows GUI，直连 `user32` / `gdi32` / `comdlg32`。

## 编译（交叉编译，无需 Windows）

```bash
x86_64-w64-mingw32-gcc -O2 -s -mwindows peview.c -o peview.exe -lcomdlg32
```

`-mwindows` 将子系统设为 GUI（不弹控制台窗口）。产物 `peview.exe` 本身即合法 PE。

## 特点

- 真正的原生控件，零运行时依赖，体积最小。
- 适合：追求最小体积 / 嵌入式的诊断工具、安装包内自检工具。
- 缺点：手写布局、无现代样式，维护 UI 成本高。
