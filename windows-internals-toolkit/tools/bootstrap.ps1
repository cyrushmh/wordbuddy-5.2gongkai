# sysweeper 引导脚本（Windows / PowerShell 5.1+，系统自带）
#
#   powershell -ExecutionPolicy Bypass -File .\tools\bootstrap.ps1 detect
#   powershell -ExecutionPolicy Bypass -File .\tools\bootstrap.ps1 windows
#
# Windows 默认不带 Python，这里按顺序尝试 python / python3 / py（Python 启动器），
# 找不到就给出安装命令（winget 一行搞定），不会静默下载任何东西。

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here

$py = $null
foreach ($c in @('python', 'python3', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source; break }
}

if (-not $py) {
    Write-Host '未找到 Python 3（sysweeper 的语言底层）。请先安装，任选其一：'
    Write-Host '  winget install Python.Python.3.12          # Windows 11/10 自带 winget'
    Write-Host '  choco install python                       # 或 Chocolatey'
    Write-Host '  https://www.python.org/downloads/windows/  # 或官网安装包（记得勾 Add to PATH）'
    exit 1
}

$app = $null
$candidates = @()
$candidates += (Join-Path $root 'dist') | ForEach-Object { Join-Path $_ 'sysweeper-*.pyz' }
$candidates += Join-Path $root 'sysweeper-*.pyz'
foreach ($p in $candidates) {
    $hit = Get-Item $p -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { $app = $hit.FullName; break }
}

if ($app) {
    & $py $app @args
    exit $LASTEXITCODE
}

$src = Join-Path $root 'system-optimizer\src\python'
if (Test-Path $src) {
    $env:PYTHONPATH = $src
    & $py -m sysweeper @args
    exit $LASTEXITCODE
}

Write-Host '未找到可运行入口：请把 sysweeper-*.pyz 放到 dist\，或保留仓库源码目录。'
exit 1
