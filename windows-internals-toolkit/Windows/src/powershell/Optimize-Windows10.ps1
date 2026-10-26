<#
.SYNOPSIS
    Windows 10 整体优化脚本：检测 / 应用 / 回退
.DESCRIPTION
    将《Windows 10 整体优化方案》与《磁盘优化方案》落地为可执行动作。
    -WhatIf  仅检测并打印当前状态（默认）
    -Apply   应用优化，自动把原始值写入 rollback.json
    -Rollback 读取 rollback.json 还原到优化前状态
    每条动作遵循“一次只改一项、可回退优先”原则。
.NOTES
    必须以管理员身份运行（脚本已用 #Requires 强制）。
    风险分级见每条目注释；标注 [红线] 的系统组件请勿关闭。
#>
[CmdletBinding(DefaultParameterSetName='WhatIf')]
param(
    [switch]$WhatIf,
    [switch]$Apply,
    [switch]$Rollback,
    [string]$LogPath = "$PSScriptRoot\optimize-log.txt"
)

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$rollbackFile = Join-Path $PSScriptRoot 'rollback.json'

function Write-Log {
    param([string]$Msg, [string]$Color = 'White')
    $line = "[$timestamp] $Msg"
    $line | Tee-Object -FilePath $LogPath -Append | Write-Host -ForegroundColor $Color
}

function Load-Rollback { if (Test-Path $rollbackFile) { return (Get-Content $rollbackFile -Raw | ConvertFrom-Json) } return $null }
function Save-Rollback($data) { $data | ConvertTo-Json -Depth 5 | Set-Content $rollbackFile -Encoding UTF8 }

# ---------------- 各项优化 ----------------

# 1) 电源计划：高性能 / 卓越性能（CPU 不降频，延迟更低）  风险：低
function PowerPlan {
    $plans = powercfg /list
    Write-Log "== 电源计划 ==" Cyan
    Write-Log ($plans -join "`n")
    $high = (powercfg /list) -match '高性能' | Select-Object -First 1
    if ($high -match '(\{[\w-]+\})') { $guid = $Matches[1] }
    else { $guid = (powercfg /list | Select-String '\{[\w-]+\}' | Select-Object -First 1).Matches[0].Value }
    if ($Apply) {
        # 卓越性能（若已隐藏则先解锁）
        $ultra = powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61 2>$null
        if ($ultra -match '(\{[\w-]+\})') { powercfg /setactive $Matches[1]; Write-Log "已激活 卓越性能" Green }
        else { powercfg /setactive $guid; Write-Log "已激活 高性能 ($guid)" Green }
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PowerPlan) { powercfg /setactive $rb.PowerPlan; Write-Log "回退电源计划 -> $($rb.PowerPlan)" Yellow } }
}

# 2) 视觉效果：调整为最佳性能（关闭动画/阴影，降低 DWM 开销）  风险：低（仅视觉）
function VisualFX {
    Write-Log "== 视觉效果 ==" Cyan
    $path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects'
    $cur = (Get-ItemProperty $path -ErrorAction SilentlyContinue).VisualFXSetting
    Write-Log "当前 VisualFXSetting = $cur (2=最佳外观, 3=最佳性能)"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($null -ne $cur) { $rb | Add-Member -NotePropertyName 'VisualFX' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        Set-ItemProperty $path -Name VisualFXSetting -Value 3 -Force
        Write-Log "已设为 最佳性能" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['VisualFX']) { Set-ItemProperty $path -Name VisualFXSetting -Value $rb.VisualFX -Force; Write-Log "回退 VisualFX -> $($rb.VisualFX)" Yellow } }
}

# 3) 传递优化（DoSvc）：限制为仅局域网，减少后台 P2P 带宽占用  风险：低
function DeliveryOpt {
    Write-Log "== 传递优化（DoSvc）==" Cyan
    $key = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization'
    $cur = (Get-ItemProperty $key -ErrorAction SilentlyContinue).DODownloadMode
    Write-Log "当前 DODownloadMode = $cur (0=HTTP直连,1=局域网+Internet,99=简单)"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($null -ne $cur) { $rb | Add-Member -NotePropertyName 'DODownloadMode' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty $key -Name DODownloadMode -Value 99 -Force   # 99 = 简易模式（仅局域网）
        Write-Log "已设为 仅局域网简易模式(99)" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['DODownloadMode']) { Set-ItemProperty $key -Name DODownloadMode -Value $rb.DODownloadMode -Force; Write-Log "回退 DODownloadMode -> $($rb.DODownloadMode)" Yellow } }
}

# 4) 遥测降级：Diagnostic Data 设为安全/必需（不关闭，[红线]不能禁用相关服务）  风险：中（仅限企业合规场景）
function Telemetry {
    Write-Log "== 诊断数据（遥测）==" Cyan
    $key = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection'
    $cur = (Get-ItemProperty $key -ErrorAction SilentlyContinue).AllowTelemetry
    Write-Log "当前 AllowTelemetry = $cur (0=安全,1=基础,3=完整)"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($null -ne $cur) { $rb | Add-Member -NotePropertyName 'AllowTelemetry' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty $key -Name AllowTelemetry -Value 0 -Force   # 0 = 安全（仅必要）
        Write-Log "已降级为 安全(0)。注意：Defender/Update 等[红线]服务不关闭" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['AllowTelemetry']) { Set-ItemProperty $key -Name AllowTelemetry -Value $rb.AllowTelemetry -Force; Write-Log "回退 AllowTelemetry -> $($rb.AllowTelemetry)" Yellow } }
}

# 5) SysMain（原 SuperFetch）：HDD 建议保留，SSD 可禁用以减少后台预读  风险：中（依赖介质）
function SysMain {
    Write-Log "== SysMain（SuperFetch）==" Cyan
    $svc = Get-Service -Name SysMain -ErrorAction SilentlyContinue
    $cur = $svc.StartType
    Write-Log "当前 SysMain StartType = $cur（SSD 可设 Disabled，HDD 建议 Automatic）"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($cur) { $rb | Add-Member -NotePropertyName 'SysMain' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        Set-Service -Name SysMain -StartupType Disabled
        Write-Log "已禁用 SysMain（适合 SSD）。HDD 用户请回退为 Automatic" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['SysMain']) { Set-Service -Name SysMain -StartupType $rb.SysMain; Write-Log "回退 SysMain -> $($rb.SysMain)" Yellow } }
}

# 6) 存储感知：启用自动释放空间  风险：低
function StorageSense {
    Write-Log "== 存储感知 ==" Cyan
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy'
    $cur = (Get-ItemProperty $key -ErrorAction SilentlyContinue).01
    Write-Log "当前 StorageSense(01) = $cur (1=开)"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($null -ne $cur) { $rb | Add-Member -NotePropertyName 'StorageSense' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty $key -Name '01' -Value 1 -Force
        Write-Log "已启用 存储感知" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['StorageSense']) { Set-ItemProperty $key -Name '01' -Value $rb.StorageSense -Force; Write-Log "回退 StorageSense -> $($rb.StorageSense)" Yellow } }
}

# 7) 游戏模式：启用，让前台游戏优先拿资源  风险：低
function GameMode {
    Write-Log "== 游戏模式 ==" Cyan
    $key = 'HKCU:\Software\Microsoft\GameBar'
    $cur = (Get-ItemProperty $key -ErrorAction SilentlyContinue).AllowAutoGameMode
    Write-Log "当前 AllowAutoGameMode = $cur (1=开)"
    if ($Apply) {
        $rb = Load-Rollback
        if (-not $rb) { $rb = [pscustomobject]@{} }
        if ($null -ne $cur) { $rb | Add-Member -NotePropertyName 'GameMode' -NotePropertyValue $cur -Force }
        Save-Rollback $rb
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty $key -Name AllowAutoGameMode -Value 1 -Force
        Write-Log "已启用 游戏模式" Green
    }
    if ($Rollback) { $rb = Load-Rollback; if ($rb -and $rb.PSObject.Properties['GameMode']) { Set-ItemProperty $key -Name AllowAutoGameMode -Value $rb.GameMode -Force; Write-Log "回退 GameMode -> $($rb.GameMode)" Yellow } }
}

# ---------------- 主流程 ----------------
Write-Log "==== Windows 10 优化脚本 ====" Magenta
if ($Rollback) { Write-Log "模式: 回退 (Rollback)" Yellow }
elseif ($Apply) { Write-Log "模式: 应用 (Apply)，回退点将写入 $rollbackFile" Green }
else { Write-Log "模式: 检测 (WhatIf)" Cyan }

PowerPlan
VisualFX
DeliveryOpt
Telemetry
SysMain
StorageSense
GameMode

Write-Log "==== 完成 ====" Magenta
if ($WhatIf -or (-not $Apply -and -not $Rollback)) {
    Write-Log "提示: 加 -Apply 应用优化；加 -Rollback 还原。" DarkGray
}
