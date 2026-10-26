#requires -Version 5.1
# PE Viewer —— PowerShell + WinForms 图形界面（原生 Windows，无需编译）。
# 以管理员或普通用户直接运行：powershell -STA -File .\PEInfo-Gui.ps1
#
# 无 GUI 模式（用于与 C/Rust/Python/.NET 做跨语言一致性验证，需 Windows 运行）：
#   powershell -STA -File .\PEInfo-Gui.ps1 -Path .\foo.exe -Json
#
# 说明：-Json 仅在 Windows 上验证（依赖 pwsh + .NET 运行时）；本仓库 parity_test.py
# 在 Linux 上会跳过 PowerShell 实现，仅把 .NET 无头控制台版纳入真实验证。
param(
    [string]$Path,
    [switch]$Json
)

function Get-PeInfo {
    param([string]$Path, [switch]$AsJson)
    $d = [System.IO.File]::ReadAllBytes($Path)
    if ($d.Length -lt 0x40 -or $d[0] -ne 0x4D -or $d[1] -ne 0x5A) {
        if ($AsJson) { return (@{ error = "不是合法 PE（缺少 MZ 头)" } | ConvertTo-Json -Compress) }
        return "不是合法 PE（缺少 MZ 头）"
    }
    $e = [BitConverter]::ToUInt32($d, 0x3C)
    if ([System.Text.Encoding]::ASCII.GetString($d, $e, 4) -ne "PE`0`0") {
        if ($AsJson) { return (@{ error = "缺少 PE 签名" } | ConvertTo-Json -Compress) }
        return "缺少 PE 签名"
    }
    $coff = $e + 4
    $machine = [BitConverter]::ToUInt16($d, $coff)
    $nsec = [BitConverter]::ToUInt16($d, $coff + 2)
    $optsize = [BitConverter]::ToUInt16($d, $coff + 16)
    $opt = $coff + 20
    $magic = [BitConverter]::ToUInt16($d, $opt)
    $pe32p = $magic -eq 0x20B
    $entry = [BitConverter]::ToUInt32($d, $opt + 16)
    if ($pe32p) { $ib = [BitConverter]::ToUInt64($d, $opt + 24) } else { $ib = [BitConverter]::ToUInt32($d, $opt + 28) }
    $subsys = [BitConverter]::ToUInt16($d, $opt + 68)
    $arch = @{0x14c = 'x86'; 0x8664 = 'x64'; 0x1c0 = 'ARM'; 0xaa64 = 'ARM64' }[$machine]
    $ddStart = $opt + $(if ($pe32p) { 112 } else { 96 })
    $numRva = [BitConverter]::ToUInt32($d, $opt + $(if ($pe32p) { 108 } else { 92 }))
    $numDirs = [Math]::Min($numRva, 16)
    $sec = $opt + $optsize

    if ($AsJson) {
        $dirs = @()
        for ($i = 0; $i -lt $numDirs; $i++) {
            $dirs += [ordered]@{
                index = $i
                name  = "dir$i"
                rva   = [BitConverter]::ToUInt32($d, $ddStart + $i * 8)
                size  = [BitConverter]::ToUInt32($d, $ddStart + $i * 8 + 4)
            }
        }
        $secs = @()
        for ($i = 0; $i -lt $nsec; $i++) {
            $s = $sec + $i * 40
            $secs += [ordered]@{
                index               = $i
                name                = [System.Text.Encoding]::ASCII.GetString($d, $s, 8).Trim("`0")
                virtual_size        = [BitConverter]::ToUInt32($d, $s + 8)
                virtual_address     = [BitConverter]::ToUInt32($d, $s + 12)
                size_of_raw_data    = [BitConverter]::ToUInt32($d, $s + 16)
                pointer_to_raw_data = [BitConverter]::ToUInt32($d, $s + 20)
                characteristics     = [BitConverter]::ToUInt32($d, $s + 36)
            }
        }
        $obj = [ordered]@{
            machine               = $machine
            machine_name          = $arch
            number_of_sections    = $nsec
            time_date_stamp       = [BitConverter]::ToUInt32($d, $coff + 4)
            size_of_optional_header = $optsize
            characteristics        = [BitConverter]::ToUInt16($d, $coff + 18)
            optional = [ordered]@{
                magic                   = $magic
                entry_point             = $entry
                image_base              = $ib
                subsystem               = $subsys
                number_of_rva_and_sizes = $numRva
            }
            data_directories = $dirs
            sections         = $secs
        }
        return $obj | ConvertTo-Json -Compress -Depth 4
    }

    $lines = @(
        "文件: $Path",
        "架构: $arch (machine=$('{0:X4}' -f $machine))",
        "节数: $nsec",
        "Magic: $(if ($pe32p) { 'PE32+' } else { 'PE32' })",
        "入口点: $($entry.ToString('X8'))",
        "ImageBase: $($ib.ToString('X8'))",
        "子系统: $subsys"
    )
    for ($i = 0; $i -lt $nsec; $i++) {
        $s = $sec + $i * 40
        $name = [System.Text.Encoding]::ASCII.GetString($d, $s, 8).Trim("`0")
        $vaddr = [BitConverter]::ToUInt32($d, $s + 12)
        $vsize = [BitConverter]::ToUInt32($d, $s + 8)
        $lines += "  节 $i`: $name VA=$($vaddr.ToString('X8')) VSize=$($vsize.ToString('X'))"
    }
    return $lines -join "`n"
}

# 无 GUI 模式：直接输出 JSON 并退出（便于 Windows 上纳入一致性测试）
if ($Json -and $Path) {
    Get-PeInfo -Path $Path -AsJson
    return
}

# GUI 模式
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = "PE Viewer (WinForms)"
$form.Size = New-Object System.Drawing.Size(640, 480)
$txt = New-Object System.Windows.Forms.TextBox
$txt.Multiline = $true; $txt.ScrollBars = 'Both'; $txt.Dock = 'Fill'; $txt.ReadOnly = $true
$form.Controls.Add($txt)
$btn = New-Object System.Windows.Forms.Button
$btn.Text = "打开 PE 文件..."; $btn.Dock = 'Top'
$btn.Add_Click({
        $ofd = New-Object System.Windows.Forms.OpenFileDialog
        $ofd.Filter = "PE 文件|*.exe;*.dll;*.sys;*.ocx|所有文件|*.*"
        if ($ofd.ShowDialog() -eq 'OK') { $txt.Text = Get-PeInfo $ofd.FileName }
    })
$form.Controls.Add($btn)
[System.Windows.Forms.Application]::EnableVisualStyles() | Out-Null
$form.ShowDialog() | Out-Null
