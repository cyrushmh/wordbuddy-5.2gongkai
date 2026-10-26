"""按语言运行时自动启用的优化/清理功能（跨平台，platform="any"）。

核心思路「不强求用户安装」：
- 每项任务声明 requires_lang（python/ruby/go/node/perl/lua…）。
- registry 在扫描/清理时只保留「当前环境已探测到该语言」的任务；未安装则
  自动隐藏（见 registry.applicable 的 lang 过滤）。用 `langs` 命令可查看开关状态。

这些功能用对应语言的标准库完成，无需额外依赖；未装该语言时完全不出现、不报错。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    Task(
        id="lang_python_large",
        platform="any",
        title="查找家目录大文件（Python）",
        category="cleanup",
        risk="low",
        requires_lang="python",
        desc="用 Python 标准库列出 $HOME 下体积最大的 20 个文件，辅助定位可清理项。",
        actions=[S(
            'python3 -c "import os,sys;'
            'from pathlib import Path;'
            'h=os.path.expanduser(\"~\");'
            'fs=sorted((f.stat().st_size,f) for f in Path(h).rglob(\"*\") if f.is_file());'
            '[print(f\'{s/1e6:.1f} MB  {f}\') for s,f in fs[-20:]]"',
            "列出家目录最大 20 个文件（Python 标准库）")],
        notes=["只读分析，不删除任何文件；据此手动判断是否可清理。"],
    ),
    Task(
        id="lang_ruby_dupes",
        platform="any",
        title="查找重复文件（Ruby）",
        category="cleanup",
        risk="low",
        requires_lang="ruby",
        desc="用 Ruby 标准库按大小初筛潜在重复文件，辅助清理冗余副本。",
        actions=[S(
            'ruby -e \'require "digest";h=Hash.new{|k,v|k[v]=[]};'
            'Dir.glob(File.expand_path("~/*")).each{|f|next unless File.file? f;'
            'h[File.size f]<<f};'
            'h.each{|s,fs|puts "#{s} B: #{fs.join(", ")}" if fs.size>1}\'',
            "按大小初筛重复文件（Ruby 标准库）")],
        notes=["仅按大小初筛，不哈希比对；真正删除前请人工确认。"],
    ),
    Task(
        id="lang_go_modcache",
        platform="any",
        title="清理 Go 模块缓存",
        category="cleanup",
        risk="low",
        requires_lang="go",
        desc="用 go 自带的 `go clean -modcache` 清理已下载的模块缓存。",
        actions=[S("go clean -modcache", "清理 GOPATH 模块缓存（go 原生命令）", rev=True)],
        notes=["可重下载；不影响源码与构建产物。"],
    ),
    Task(
        id="lang_go_build_cache",
        platform="any",
        title="清理 Go 构建缓存（GOCACHE）",
        category="cleanup",
        risk="low",
        requires_lang="go",
        desc="用 `go clean -cache` 清理构建缓存（GOCACHE），释放编译中间产物占用的空间。",
        actions=[S("go clean -cache", "清理 GOCACHE 构建缓存（go 原生命令）", rev=True)],
        notes=[
            "构建缓存可重建：清理后首次编译会重新生成，耗时略增。",
            "不影响模块缓存（GOMODCACHE）与源码；两者独立，可分别清理。",
        ],
        caveats=["CI/离线环境清理后若无法重新编译需留意；本地一般无影响。"],
    ),
    Task(
        id="lang_go_build",
        platform="any",
        title="Go 工程预构建校验（go build）",
        category="maintenance",
        risk="low",
        requires_lang="go",
        desc="在当前 Go 工程执行 `go build ./...`，预编译并校验可构建性，"
             "同时把构建结果写入缓存以加速后续编译。",
        actions=[S(
            'if [ -f go.mod ]; then go build ./...; else echo "当前目录无 go.mod，跳过构建"; fi',
            "构建全部包（go 原生命令，需 go.mod）")],
        notes=[
            "有 go.mod 时才执行；无则跳过，不报错。",
            "构建产物写入 GOCACHE，可让后续 `go build` / `go test` 显著加快。",
            "交叉编译可加 GOOS/GOARCH（如 GOOS=windows GOARCH=amd64 go build ./...）。",
        ],
        caveats=["构建失败通常是代码/依赖问题，属正常反馈，不会修改源码。"],
    ),
    Task(
        id="lang_go_mod_tidy",
        platform="any",
        title="整理 Go 依赖（go mod tidy）",
        category="maintenance",
        risk="medium",
        requires_lang="go",
        desc="执行 `go mod tidy` 移除未使用依赖、补齐缺失依赖，保持 go.mod / go.sum 干净。",
        actions=[S(
            'if [ -f go.mod ]; then go mod tidy; else echo "当前目录无 go.mod，跳过"; fi',
            "整理 go.mod / go.sum（会修改这两个文件）")],
        notes=[
            "会重写 go.mod 与 go.sum，属「结构性」改动，故风险定为 medium。",
            "建议先提交/备份 go.mod、go.sum，再执行以便对比回退。",
        ],
        caveats=["需联网解析模块；离线环境会失败。执行前请确认依赖变更可回退。"],
    ),
    Task(
        id="lang_node_cache",
        platform="any",
        title="校验/清理 Node 缓存",
        category="cleanup",
        risk="low",
        requires_lang="node",
        desc="用 npm 的 `npm cache verify` 整理 Node 依赖缓存（需 npm）。",
        actions=[S('if command -v npm >/dev/null; then npm cache verify; else echo "未安装 npm，跳过"; fi',
                  "校验 Node 缓存（npm 原生命令）", rev=True)],
        notes=["仅整理校验缓存，不删依赖；无 npm 时自动跳过。"],
    ),
    Task(
        id="lang_perl_logs",
        platform="any",
        title="汇总大日志文件（Perl）",
        category="maintenance",
        risk="low",
        requires_lang="perl",
        desc="用 Perl 扫描 /var/log 与家目录日志，列出体积偏大的日志。",
        actions=[S(
            'perl -e \'for my $d ("/var/log", $ENV{HOME}){'
            'next unless -d $d;'
            'for my $f (glob("$d/*.log*")){my $s=(stat$f)[7];'
            'print "$s B  $f\\n" if $s>10*1024*1024}}\'',
            "列出大于 10MB 的日志（Perl 标准库）")],
        notes=["只读列出；压缩/轮转日志请结合系统 logrotate。"],
    ),
    Task(
        id="lang_lua_report",
        platform="any",
        title="环境报告（Lua）",
        category="maintenance",
        risk="low",
        requires_lang="lua",
        desc="用 Lua 输出基础环境信息，演示「有 Lua 才启用」的自动显隐。",
        actions=[S('lua -e \'print("Lua "..(_VERSION or "?");'
                   'print("HOME="..(os.getenv("HOME") or "?"))\'',
                   "打印 Lua 版本与 HOME（Lua 标准库）")],
        notes=["仅展示信息，无副作用。"],
    ),
    Task(
        id="lang_rust_cargo",
        platform="any",
        title="清理 Rust 构建缓存（cargo）",
        category="cleanup",
        risk="low",
        requires_lang="rust",
        desc="用 cargo 自带的 `cargo clean` 清理当前工程 target，必要时清理全局 registry 缓存。",
        actions=[
            S('if command -v cargo >/dev/null; then cargo clean; else echo "未安装 cargo，跳过"; fi',
              "清理当前工程 target（cargo 原生命令）", rev=True),
        ],
        notes=[
            "可重编译；不影响源码与 Cargo.lock。",
            "全局缓存 ~/.cargo/registry、~/.cargo/git 体积较大，可用 `cargo clean`（配合 `--target-dir` 或手动清 registry）释放，但会触发重新下载。",
        ],
        caveats=["清理 registry 缓存后下次构建需重新下载依赖，首次略慢。"],
    ),
    Task(
        id="lang_java_cache",
        platform="any",
        title="清理 Java 构建缓存（Gradle/Maven）",
        category="cleanup",
        risk="low",
        requires_lang="java",
        desc="清理 Gradle 与 Maven 的本地依赖/构建缓存（可从仓库重新拉取，不删源码）。",
        actions=[
            S('rm -rf "$HOME/.gradle/caches" 2>/dev/null; echo "已清理 Gradle caches"',
              "清理 Gradle 缓存（可重新下载）", rev=True),
            S('rm -rf "$HOME/.m2/repository" 2>/dev/null; echo "已清理 Maven 本地仓库"',
              "清理 Maven 本地仓库（可重新下载）", rev=True),
        ],
        notes=[
            "Gradle/Maven 缓存均为可重建的下载产物，清理后下次构建会自动重新解析与下载。",
            "不影响项目源码与构建脚本。",
        ],
        caveats=["清理后首次构建需联网重新下载依赖，耗时增加。"],
    ),
    Task(
        id="lang_dotnet_nuget",
        platform="any",
        title="清理 .NET NuGet 缓存",
        category="cleanup",
        risk="low",
        requires_lang="dotnet",
        desc="用 dotnet CLI 清理 NuGet 全局缓存（http-cache / global-packages / temp）。",
        actions=[
            S('if command -v dotnet >/dev/null; then dotnet nuget locals all --clear; else echo "未安装 dotnet，跳过"; fi',
              "清理 NuGet 全部本地缓存（dotnet 原生命令）", rev=True),
        ],
        notes=["NuGet 缓存可重新还原；不影响项目源码与 .csproj 引用。"],
        caveats=["清理后首次还原需重新下载包，耗时增加。"],
    ),

    Task(
        id="lang_php_composer",
        platform="any",
        title="清理 PHP Composer 缓存",
        category="cleanup",
        risk="low",
        requires_lang="php",
        desc="清理 Composer 的包缓存目录（可重新下载，不影响 vendor 与源码）。",
        actions=[S('if command -v composer >/dev/null; then composer clear-cache; '
                   "else php -r \"echo '未安装 composer，跳过';\"; fi",
                   "清理 Composer 缓存（composer 原生命令）", rev=True)],
        notes=["Composer 缓存可重建；不影响项目 vendor 与 composer.lock。"],
        caveats=["清理后首次安装需重新下载依赖，耗时增加。"],
    ),
    Task(
        id="lang_ruby_gem",
        platform="any",
        title="清理 RubyGems 旧版本包",
        category="cleanup",
        risk="low",
        requires_lang="ruby",
        desc="用 `gem cleanup` 移除已安装 gem 的旧版本，只保留最新版。",
        actions=[S('if command -v gem >/dev/null; then gem cleanup; else echo "未安装 gem，跳过"; fi',
                   "清理旧版 gem（RubyGems 原生命令）")],
        notes=["只清理同一 gem 的历史版本，不影响当前依赖可解析性。"],
        caveats=["个别项目锁定旧版本时需重新 `bundle install`。"],
    ),

]
