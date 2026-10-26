@echo off
setlocal enableextensions
set "MODE=%~1"
if "%MODE%"=="" set "MODE=analyze"

echo ============================================================
echo  Sysweeper Windows 优化脚本  (目标 Windows 11, 风险上限 medium)
echo   无参数        分析模式：仅显示命令，不修改系统
echo   apply         执行：低风险直接跑，中/高风险逐一确认
echo   schedule      注册为每周一 09:00 的计划任务（最高权限）
echo ============================================================

if /i "%MODE%"=="schedule" (
  echo 正在注册计划任务 Sysweeper.Optimize ...
  schtasks /create /tn "Sysweeper.Optimize" /tr "\"%~f0\" apply" /sc weekly /d MON /st 09:00 /rl HIGHEST /f
  echo 完成。可用「任务计划程序」或 schtasks /delete /tn "Sysweeper.Optimize" 移除。
  goto :eof
)

echo 适用任务共 8 项（分析模式）：

echo [任务] 清理系统与用户临时文件  [cleanup/low]
echo   删除 %TEMP% 与 C:\Windows\Temp 下的临时文件。
echo   [注意] 建议每月执行一次；不影响已安装软件。
echo   (分析) powershell -NoProfile -Command "Remove-Item -Path $env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Remove-Item -Path $env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue"
echo   (分析) powershell -NoProfile -Command "Remove-Item -Path C:\Windows\Temp\* -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Remove-Item -Path C:\Windows\Temp\* -Recurse -Force -ErrorAction SilentlyContinue"

echo [任务] 清空回收站  [cleanup/low]
echo   永久删除回收站内容（不可恢复）。用 Shell32 原生 API（SHEmptyRecycleBinW）实现。
echo   [风险] 清空后文件不可恢复，请确认无需要保留的内容。
echo   (分析) powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"

echo [任务] 清理浏览器缓存（Chrome/Edge/Firefox）  [cleanup/low]
echo   删除常见浏览器的缓存与临时文件。
echo   [注意] 仅清理缓存，不删除书签/密码/历史记录。
echo   (分析) powershell -NoProfile -Command "Get-ChildItem \"$env:LOCALAPPDATA\Google\Chrome\User Data\*\Cache\" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Get-ChildItem \"$env:LOCALAPPDATA\Google\Chrome\User Data\*\Cache\" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
echo   (分析) powershell -NoProfile -Command "Get-ChildItem \"$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Cache\" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Get-ChildItem \"$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Cache\" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
echo   (分析) powershell -NoProfile -Command "Remove-Item -Path \"$env:LOCALAPPDATA\Mozilla\Firefox\Profiles\*\cache2\" -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Remove-Item -Path \"$env:LOCALAPPDATA\Mozilla\Firefox\Profiles\*\cache2\" -Recurse -Force -ErrorAction SilentlyContinue"

echo [任务] 清理传递优化缓存（Delivery Optimization）  [cleanup/low]
echo   删除 Windows 更新分发用的 P2P 缓存。
echo   [注意] 不影响已安装更新；下次更新会重新生成。
echo   (分析) powershell -NoProfile -Command "Remove-Item -Path \"$env:SystemRoot\SoftwareDistribution\DeliveryOptimization\Cache\*\" -Recurse -Force -ErrorAction SilentlyContinue"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "Remove-Item -Path \"$env:SystemRoot\SoftwareDistribution\DeliveryOptimization\Cache\*\" -Recurse -Force -ErrorAction SilentlyContinue"

echo [任务] 清理 Prefetch（预读取）  [cleanup/medium]
echo   清空 Prefetch 以释放空间；下次开机略慢。
echo   [风险] 清空后首次启动常用程序会变慢，属正常现象。
echo   (分析) powershell -NoProfile -Command "Remove-Item -Path C:\Windows\Prefetch\* -Force -ErrorAction SilentlyContinue"
if /i not "%MODE%"=="apply" goto end_win_prefetch_140320131371728
choice /C YN /M "执行「清理 Prefetch（预读取）」? (Y=执行 N=跳过)"
if errorlevel 2 goto end_win_prefetch_140320131371728
powershell -NoProfile -Command "Remove-Item -Path C:\Windows\Prefetch\* -Force -ErrorAction SilentlyContinue"
:end_win_prefetch_140320131371728

echo [任务] 清理 Windows 更新组件（DISM）  [maintenance/medium]
echo   用 DISM 清理 WinSxS 组件存储，可释放数 GB。
echo   [风险] 若加 /ResetBase 将不可卸载已装更新；此处保守不加。
echo   [注意] 耗时较长，建议在插电状态下执行。
echo   (分析) powershell -NoProfile -Command "DISM /Online /Cleanup-Image /StartComponentCleanup"
if /i not "%MODE%"=="apply" goto end_win_update_cleanup_140320131372048
choice /C YN /M "执行「清理 Windows 更新组件（DISM）」? (Y=执行 N=跳过)"
if errorlevel 2 goto end_win_update_cleanup_140320131372048
powershell -NoProfile -Command "DISM /Online /Cleanup-Image /StartComponentCleanup"
:end_win_update_cleanup_140320131372048

echo [任务] 降低诊断与体验数据收集  [privacy/medium]
echo   关闭个性化体验/诊断数据上传。
echo   [风险] 仅影响当前用户；企业域策略可能覆盖此设置。
echo   (分析) powershell -NoProfile -Command "Set-ItemProperty -Path \'HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy\' -Name \'TailoredExperiencesWithDiagnosticDataEnabled\' -Value 0 -ErrorAction SilentlyContinue"
if /i not "%MODE%"=="apply" goto end_win_telemetry_140320131372368
choice /C YN /M "执行「降低诊断与体验数据收集」? (Y=执行 N=跳过)"
if errorlevel 2 goto end_win_telemetry_140320131372368
powershell -NoProfile -Command "Set-ItemProperty -Path \'HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy\' -Name \'TailoredExperiencesWithDiagnosticDataEnabled\' -Value 0 -ErrorAction SilentlyContinue"
:end_win_telemetry_140320131372368

echo [任务] 切换至高性能电源计划  [optimize/low]
echo   笔记本可提升性能但缩短续航。
echo   [风险] 笔记本使用电池时续航明显下降。
echo   (分析) powershell -NoProfile -Command "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
if /i "%MODE%"=="apply" powershell -NoProfile -Command "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

echo.
echo 完成。若需真正执行，请以「管理员」运行：%~nx0 apply
echo （注册定时自动执行：%~nx0 schedule）
endlocal
