// PeInfo — .NET 无头控制台版 PE 头解析器（可与 C/Rust/Python 做跨语言一致性验证）。
// 编译（任意平台）: dotnet build -c Release
// 运行: dotnet bin/Release/net10.0/PeInfo.dll <文件> [--json]   缺省解析自身
//
// JSON 字段与本项目其它语言实现对齐：
//   machine, number_of_sections, time_date_stamp, size_of_optional_header, characteristics,
//   optional { magic, entry_point, image_base, subsystem, number_of_rva_and_sizes },
//   data_directories [ {index,name,rva,size} ], sections [ {name,virtual_size,virtual_address,
//     size_of_raw_data,pointer_to_raw_data,characteristics} ]
using System;
using System.IO;
using System.Text;

namespace PeInfo;

internal static class Program
{
    private static int Main(string[] args)
    {
        bool json = false;
        string? path = null;
        foreach (var a in args)
        {
            if (a == "--json") { json = true; continue; }
            if (path == null) path = a;
        }
        if (path == null) path = Environment.GetCommandLineArgs()[0];

        try
        {
            Console.Out.Write(json ? ToJson(path!) : ToText(path!));
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }

    private static ushort RU16(byte[] d, int o) => (ushort)(d[o] | (d[o + 1] << 8));
    private static uint RU32(byte[] d, int o) =>
        (uint)(d[o] | (d[o + 1] << 8) | (d[o + 2] << 16) | (d[o + 3] << 24));
    private static ulong RU64(byte[] d, int o) => RU32(d, o) | ((ulong)RU32(d, o + 4) << 32);

    private static string MachineName(ushort m) => m switch
    {
        0x14C => "x86 (Intel 386+)",
        0x8664 => "x64 (AMD64)",
        0xAA64 => "ARM64",
        0x1C0 => "ARM (32-bit)",
        0x14D => "ARM (Thumb/Thumb-2, NT)",
        0x200 => "Intel IA64",
        0x9041 => "ARM64X",
        _ => "未知"
    };

    private static string SubsystemName(ushort s) => s switch
    {
        1 => "Native (驱动/系统)",
        2 => "Windows GUI",
        3 => "Windows CUI (控制台)",
        7 => "POSIX",
        9 => "Windows CE",
        10 => "EFI 应用程序",
        12 => "EFI ROM",
        _ => "未知"
    };

    private static string JsonName(byte[] d, int off)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < 8; i++)
        {
            byte c = d[off + i];
            if (c == 0) break;
            if (c == (byte)'"') sb.Append("\\\"");
            else if (c == (byte)'\\') sb.Append("\\\\");
            else sb.Append((char)c);
        }
        return sb.ToString();
    }

    private static string ToJson(string path)
    {
        var d = File.ReadAllBytes(path);
        if (d.Length < 0x40 || d[0] != 0x4D || d[1] != 0x5A)
            throw new InvalidDataException("不是有效的 PE：缺少 MZ 头");
        int e = (int)RU32(d, 0x3C);
        if (Encoding.ASCII.GetString(d, e, 4) != "PE\0\0")
            throw new InvalidDataException("不是有效的 PE：缺少 PE 签名");
        int coff = e + 4;
        ushort machine = RU16(d, coff);
        ushort nsec = RU16(d, coff + 2);
        ushort optsize = RU16(d, coff + 16);
        int opt = coff + 20;
        ushort magic = RU16(d, opt);
        bool pe32p = magic == 0x20B;
        uint entry = RU32(d, opt + 16);
        ulong imageBase = pe32p ? RU64(d, opt + 24) : RU32(d, opt + 28);
        ushort subsys = RU16(d, opt + 68);
        long ddStart = opt + (pe32p ? 112 : 96);
        uint numRva = RU32(d, opt + (pe32p ? 108 : 92));
        uint numDirs = numRva > 16 ? 16 : numRva;
        int secTbl = opt + optsize;

        var sb = new StringBuilder();
        sb.Append('{');
        sb.Append("\"e_lfanew\":").Append(e).Append(',');
        sb.Append("\"machine\":").Append(machine).Append(',');
        sb.Append("\"machine_name\":\"").Append(MachineName(machine)).Append("\",");
        sb.Append("\"number_of_sections\":").Append(nsec).Append(',');
        sb.Append("\"time_date_stamp\":").Append(RU32(d, coff + 4)).Append(',');
        sb.Append("\"size_of_optional_header\":").Append(optsize).Append(',');
        sb.Append("\"characteristics\":").Append(RU16(d, coff + 18)).Append(',');
        sb.Append("\"optional\":{");
        sb.Append("\"magic\":").Append(magic).Append(',');
        sb.Append("\"entry_point\":").Append(entry).Append(',');
        sb.Append("\"image_base\":").Append(imageBase).Append(',');
        sb.Append("\"subsystem\":").Append(subsys).Append(',');
        sb.Append("\"number_of_rva_and_sizes\":").Append(numRva);
        sb.Append("},");
        sb.Append("\"data_directories\":[");
        for (uint i = 0; i < numDirs; i++)
        {
            if (i > 0) sb.Append(',');
            uint rva = RU32(d, (int)(ddStart + i * 8));
            uint size = RU32(d, (int)(ddStart + i * 8 + 4));
            sb.Append("{\"index\":").Append(i)
              .Append(",\"name\":\"dir").Append(i)
              .Append("\",\"rva\":").Append(rva)
              .Append(",\"size\":").Append(size).Append('}');
        }
        sb.Append("],");
        sb.Append("\"sections\":[");
        for (uint i = 0; i < nsec; i++)
        {
            if (i > 0) sb.Append(',');
            int s = secTbl + (int)(i * 40);
            sb.Append("{\"index\":").Append(i)
              .Append(",\"name\":\"").Append(JsonName(d, s)).Append('"')
              .Append(",\"virtual_size\":").Append(RU32(d, s + 8))
              .Append(",\"virtual_address\":").Append(RU32(d, s + 12))
              .Append(",\"size_of_raw_data\":").Append(RU32(d, s + 16))
              .Append(",\"pointer_to_raw_data\":").Append(RU32(d, s + 20))
              .Append(",\"characteristics\":").Append(RU32(d, s + 36)).Append('}');
        }
        sb.Append("]}");
        return sb.ToString();
    }

    private static string ToText(string path)
    {
        var d = File.ReadAllBytes(path);
        if (d.Length < 0x40 || d[0] != 0x4D || d[1] != 0x5A)
            return "不是有效的 PE（缺少 MZ 头）";
        int e = (int)RU32(d, 0x3C);
        if (Encoding.ASCII.GetString(d, e, 4) != "PE\0\0") return "缺少 PE 签名";
        int coff = e + 4;
        ushort machine = RU16(d, coff);
        ushort nsec = RU16(d, coff + 2);
        ushort optsize = RU16(d, coff + 16);
        int opt = coff + 20;
        ushort magic = RU16(d, opt);
        bool pe32p = magic == 0x20B;
        uint entry = RU32(d, opt + 16);
        ulong imageBase = pe32p ? RU64(d, opt + 24) : RU32(d, opt + 28);
        ushort subsys = RU16(d, opt + 68);
        int secTbl = opt + optsize;

        var sb = new StringBuilder();
        sb.AppendLine($"文件: {path}");
        sb.AppendLine($"架构: {(machine == 0x8664 ? "x64" : machine == 0x14C ? "x86" : "其它")} (machine={machine:X4})");
        sb.AppendLine($"节数: {nsec}");
        sb.AppendLine($"Magic: {(pe32p ? "PE32+" : "PE32")}");
        sb.AppendLine($"入口点: {entry:X8}");
        sb.AppendLine($"ImageBase: {imageBase:X8}");
        sb.AppendLine($"子系统: {subsys} ({SubsystemName(subsys)})");
        for (uint i = 0; i < nsec; i++)
        {
            int s = secTbl + (int)(i * 40);
            string name = JsonName(d, s);
            sb.AppendLine($"  节 {i}: {name} VA={RU32(d, s + 12):X8} VSize={RU32(d, s + 8):X}");
        }
        return sb.ToString();
    }
}
