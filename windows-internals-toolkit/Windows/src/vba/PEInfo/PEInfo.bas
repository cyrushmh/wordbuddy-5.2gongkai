Attribute VB_Name = "PEInfo"
'==============================================================================
' PEInfo —— Microsoft Office VBA 版 PE 头查看器（标准模块）
'
' 同源同义实现：与 C / Rust / Python / .NET 版解析口径、JSON 字段完全对齐。
' 可导入任意 Office VBA 工程（Excel / Word / Access / PowerPoint 的 VBA 编辑器
' → 文件 → 导入文件），无需引用任何外部库，纯 VBA 实现。
'
' 提供：
'   PeInfoJson(path)        —— 核心：解析 PE，返回与 parity_test 同 schema 的 JSON 字符串
'   ShowPeInfo()            —— 弹文件框，把 JSON 输出到"立即窗口"(Ctrl+G 可见)
'   DumpPeInfoJsonFile()    —— 弹文件框，把 JSON 写到 <原名>.pe.json 旁，便于人工比对
'
' 说明：VBA 运行于 Office（Windows/Mac），无命令行/标准输出，故以"字符串"承载
'       机器可读结果；字段命名与数据类型与 Python 版 pe_inspect.py 的 --json 一致：
'       machine / number_of_sections / timestamp / optional{magic,entry_point,
'       image_base,subsystem,number_of_rva_and_sizes} / data_directories / sections[]。
'
' 所属子项目：Windows/ （wordbuddy-github 总仓库）。Windows-only，沙箱内不自动验证。
'==============================================================================

Option Explicit

'------------------------------------------------------------------------------
' 公共入口：解析 PE 文件，返回 JSON 字符串
'------------------------------------------------------------------------------
Public Function PeInfoJson(ByVal path As String) As String
    On Error GoTo Fail
    PeInfoJson = ParsePeToJson(path)
    Exit Function
Fail:
    PeInfoJson = "{" & vbCrLf & _
                 "  ""error"": " & JsonStr(Err.Description) & "," & vbCrLf & _
                 "  ""source"": " & JsonStr(path) & vbCrLf & _
                 "}"
End Function

'------------------------------------------------------------------------------
' 展示用：选择文件并把 JSON 打印到立即窗口
'------------------------------------------------------------------------------
Public Sub ShowPeInfo()
    Dim p As String
    p = PickFile()
    If Len(p) = 0 Then Exit Sub
    Debug.Print PeInfoJson(p)
End Sub

'------------------------------------------------------------------------------
' 落地用：选择文件，把 JSON 写成 <原名>.pe.json（Windows 上可对照 parity）
'------------------------------------------------------------------------------
Public Sub DumpPeInfoJsonFile()
    Dim p As String
    p = PickFile()
    If Len(p) = 0 Then Exit Sub
    Dim out As String
    out = p & ".pe.json"
    Dim ff As Integer
    ff = FreeFile
    Open out For Output As #ff
    Print #ff, PeInfoJson(p)
    Close #ff
    Debug.Print "已写出: " & out
End Sub

'==============================================================================
' 以下是解析实现
'==============================================================================

Private Function ParsePeToJson(ByVal path As String) As String
    ' ---- 读入整个文件到 Byte 数组 ----
    Dim ff As Integer
    ff = FreeFile
    Open path For Binary Access Read As #ff
    Dim n As Long
    n = LOF(ff)
    If n < 64 Then
        Close #ff
        Err.Raise 5, , "文件过小，不是 PE"
    End If
    Dim b() As Byte
    ReDim b(0 To n - 1)
    Get #ff, , b
    Close #ff

    ' ---- DOS 头：e_magic 必须为 'MZ'，e_lfanew 指向 PE 签名 ----
    If Not (b(0) = &H4D And b(1) = &H5A) Then
        Err.Raise 5, , "缺少 MZ 头（不是 PE）"
    End If
    Dim e_lfanew As Long
    e_lfanew = Le32(b, &H3C)   ' e_lfanew 在文件偏移 0x3C，4 字节
    If e_lfanew + 4 > n Then Err.Raise 5, , "e_lfanew 越界"
    If Not (b(e_lfanew) = &H50 And b(e_lfanew + 1) = &H45 And _
            b(e_lfanew + 2) = 0 And b(e_lfanew + 3) = 0) Then
        Err.Raise 5, , "缺少 PE\0\0 签名"
    End If

    ' ---- COFF 文件头（PE 签名后 4 字节起）----
    Dim coff As Long
    coff = e_lfanew + 4
    Dim machine As Long
    machine = Le16(b, coff + 0)
    Dim numSections As Long
    numSections = Le16(b, coff + 2)
    Dim timestamp As Double
    timestamp = Le32(b, coff + 4)
    Dim sizeOpt As Long
    sizeOpt = Le16(b, coff + 16)
    Dim characteristics As Long
    characteristics = Le16(b, coff + 18)

    ' ---- 可选头 ----
    Dim optOff As Long
    optOff = coff + 20
    Dim magic As Long
    magic = Le16(b, optOff + 0)
    Dim isPe32Plus As Boolean
    isPe32Plus = (magic = &H20B)

    Dim entryPoint As Double
    entryPoint = Le32(b, optOff + 16)
    Dim imageBase As Double
    If isPe32Plus Then
        imageBase = Le64(b, optOff + 24)        ' PE32+: ImageBase 为 8 字节
    Else
        imageBase = Le32(b, optOff + 28)        ' PE32 : ImageBase 为 4 字节
    End If
    Dim subsystem As Long
    subsystem = Le16(b, optOff + 68)             ' Subsystem 在两种格式下偏移均为 +68

    Dim numRva As Long
    Dim ddOff As Long
    If isPe32Plus Then
        numRva = Le32(b, optOff + 108)          ' PE32+: NumberOfRvaAndSizes 在 +108
        ddOff = optOff + 112                     ' 数据目录表起始 +112
    Else
        numRva = Le32(b, optOff + 92)            ' PE32 : +92
        ddOff = optOff + 96                      ' 数据目录表起始 +96
    End If

    ' ---- 数据目录 ----
    Dim ddCount As Long
    ddCount = numRva
    If ddCount > 16 Then ddCount = 16
    Dim s As String
    s = s & "  ""data_directories"": ["
    Dim i As Long
    For i = 0 To ddCount - 1
        If i > 0 Then s = s & ","
        Dim eOff As Long
        eOff = ddOff + i * 8
        Dim va As Double, sz As Double
        va = Le32(b, eOff)
        sz = Le32(b, eOff + 4)
        s = s & "{" & _
              """name"": " & JsonStr(DataDirName(i)) & "," & _
              """virtual_address"": " & JNum(va) & "," & _
              """size"": " & JNum(sz) & "}"
    Next i
    s = s & "]" & vbCrLf

    ' ---- 节表 ----
    Dim secOff As Long
    secOff = optOff + sizeOpt
    s = s & "  ," & " ""sections"": ["
    Dim j As Long
    For j = 0 To numSections - 1
        If j > 0 Then s = s & ","
        Dim o As Long
        o = secOff + j * 40
        If o + 40 > n Then Err.Raise 5, , "节表越界"
        Dim nameStr As String
        nameStr = SectionName(b, o)
        Dim vsize As Double, vaddr As Double, rawSize As Double, rawPtr As Double, chars As Double
        vsize = Le32(b, o + 8)
        vaddr = Le32(b, o + 12)
        rawSize = Le32(b, o + 16)
        rawPtr = Le32(b, o + 20)
        chars = Le32(b, o + 36)
        s = s & "{" & _
              """name"": " & JsonStr(nameStr) & "," & _
              """virtual_address"": " & JNum(vaddr) & "," & _
              """virtual_size"": " & JNum(vsize) & "," & _
              """size_of_raw_data"": " & JNum(rawSize) & "," & _
              """pointer_to_raw_data"": " & JNum(rawPtr) & "," & _
              """characteristics"": " & JNum(chars) & "}"
    Next j
    s = s & "]" & vbCrLf

    ' ---- 组装顶层 JSON ----
    ParsePeToJson = "{" & vbCrLf & _
        "  ""machine"": " & JNum(machine) & "," & vbCrLf & _
        "  ""machine_name"": " & JsonStr(MachineName(machine)) & "," & vbCrLf & _
        "  ""number_of_sections"": " & JNum(numSections) & "," & vbCrLf & _
        "  ""timestamp"": " & JNum(timestamp) & "," & vbCrLf & _
        "  ""characteristics"": " & JNum(characteristics) & "," & vbCrLf & _
        "  ""optional"": {" & vbCrLf & _
        "    ""magic"": " & JNum(magic) & "," & vbCrLf & _
        "    ""entry_point"": " & JNum(entryPoint) & "," & vbCrLf & _
        "    ""image_base"": " & JNum(imageBase) & "," & vbCrLf & _
        "    ""subsystem"": " & JNum(subsystem) & "," & vbCrLf & _
        "    ""subsystem_name"": " & JsonStr(SubsystemName(subsystem)) & "," & vbCrLf & _
        "    ""number_of_rva_and_sizes"": " & JNum(numRva) & vbCrLf & _
        "  }," & vbCrLf & _
        s & _
        "}"
End Function

'------------------------------------------------------------------------------
' 小端读取辅助
'------------------------------------------------------------------------------
Private Function Le16(b() As Byte, o As Long) As Long
    Le16 = b(o) + b(o + 1) * 256
End Function

Private Function Le32(b() As Byte, o As Long) As Double
    ' 以 Double 承载，避免 32 位无符号值在 VBA Long（有符号）下溢出
    Le32 = b(o) + b(o + 1) * 256# + b(o + 2) * 65536# + b(o + 3) * 16777216#
End Function

Private Function Le64(b() As Byte, o As Long) As Double
    ' PE32+ 的 ImageBase 为 8 字节；整数部分最多 2^53 仍精确
    Le64 = b(o) + b(o + 1) * 256# + b(o + 2) * 65536# + b(o + 3) * 16777216# _
         + b(o + 4) * 4294967296# + b(o + 5) * 1099511627776# _
         + b(o + 6) * 281474976710656# + b(o + 7) * 72057594037927936#
End Function

Private Function SectionName(b() As Byte, o As Long) As String
    Dim r As String, i As Long, ch As Long
    For i = 0 To 7
        ch = b(o + i)
        If ch = 0 Then Exit For
        If ch >= 32 And ch <= 126 Then r = r & Chr(ch)
    Next i
    SectionName = r
End Function

'------------------------------------------------------------------------------
' JSON 工具
'------------------------------------------------------------------------------
Private Function JNum(v As Double) As String
    ' 整数以无分隔符十进制输出，保证与 Python/Dotnet 的数值一致
    JNum = Format(v, "0")
End Function

Private Function JsonStr(v As String) As String
    Dim r As String, i As Long, c As String
    r = """"
    For i = 1 To Len(v)
        c = Mid(v, i, 1)
        Select Case c
            Case """": r = r & "\"""
            Case "\": r = r & "\\"
            Case vbCr: r = r & "\n"
            Case vbLf: r = r & "\n"
            Case vbTab: r = r & "\t"
            Case Else: r = r & c
        End Select
    Next i
    JsonStr = r & """"
End Function

'------------------------------------------------------------------------------
' 名称映射（仅展示用，一致性测试不比对名称字符串）
'------------------------------------------------------------------------------
Private Function MachineName(m As Long) As String
    Select Case m
        Case &H14C: MachineName = "x86 (Intel 386)"
        Case &H14D: MachineName = "x86 (Intel 486)"
        Case &H8664: MachineName = "x86-64 (AMD64)"
        Case &H1C0: MachineName = "ARM (32-bit)"
        Case &HAA64: MachineName = "ARM64 (64-bit)"
        Case &H200: MachineName = "Intel Itanium"
        Case &H9041: MachineName = "MIPS (big-endian)"
        Case &H162: MachineName = "MIPS (little-endian)"
        Case Else: MachineName = "Unknown (0x" & Hex(m) & ")"
    End Select
End Function

Private Function SubsystemName(s As Long) As String
    Select Case s
        Case 1: SubsystemName = "Native"
        Case 2: SubsystemName = "Windows GUI"
        Case 3: SubsystemName = "Windows CUI (console)"
        Case 7: SubsystemName = "Windows CE GUI"
        Case 9: SubsystemName = "Windows CE CUI"
        Case 10: SubsystemName = "EFI application"
        Case 11: SubsystemName = "EFI boot service driver"
        Case 12: SubsystemName = "EFI runtime driver"
        Case 13: SubsystemName = "EFI ROM"
        Case 14: SubsystemName = "Xbox"
        Case Else: SubsystemName = "Unknown (0x" & Hex(s) & ")"
    End Select
End Function

Private Function DataDirName(i As Long) As String
    Select Case i
        Case 0: DataDirName = "Export"
        Case 1: DataDirName = "Import"
        Case 2: DataDirName = "Resource"
        Case 3: DataDirName = "Exception"
        Case 4: DataDirName = "Security"
        Case 5: DataDirName = "Base Relocation"
        Case 6: DataDirName = "Debug"
        Case 7: DataDirName = "Architecture"
        Case 8: DataDirName = "Global Pointer"
        Case 9: DataDirName = "TLS"
        Case 10: DataDirName = "Load Config"
        Case 11: DataDirName = "Bound Import"
        Case 12: DataDirName = "IAT"
        Case 13: DataDirName = "Delay Import"
        Case 14: DataDirName = "COM Descriptor"
        Case 15: DataDirName = "Reserved"
        Case Else: DataDirName = "Unknown"
    End Select
End Function

'------------------------------------------------------------------------------
' 文件选择（Excel/Word/Access/PowerPoint 均可）
'------------------------------------------------------------------------------
Private Function PickFile() As String
    On Error Resume Next
    Dim dlg As Object
    Set dlg = Application.FileDialog(3)   ' msoFileDialogFilePicker = 3
    If Err.Number <> 0 Or dlg Is Nothing Then
        On Error GoTo 0
        PickFile = ""
        Exit Function
    End If
    On Error GoTo 0
    With dlg
        .Title = "选择 PE 文件（.exe/.dll/.sys）"
        .Filters.Clear
        .Filters.Add "PE 文件", "*.exe;*.dll;*.sys;*.ocx;*.scr"
        .AllowMultiSelect = False
        If .Show = -1 Then PickFile = .SelectedItems(1)
    End With
End Function
