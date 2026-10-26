// 参考实现：.NET 10 LTS（WinForms）GUI。需 Windows + .NET 10 SDK 构建：dotnet build -c Release
// 与 PowerShell/WinForms、C#/WPF 同属「托管 GUI」路线，便于与前述原生/脚本路线对比。
using System;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace PeView;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        var form = new Form { Text = "PE Viewer (.NET 8 WinForms)", Width = 640, Height = 480 };
        var txt = new TextBox { Multiline = true, ScrollBars = ScrollBars.Both, Dock = DockStyle.Fill, ReadOnly = true };
        var btn = new Button { Text = "打开 PE 文件...", Dock = DockStyle.Top };
        btn.Click += (_, _) =>
        {
            var ofd = new OpenFileDialog { Filter = "PE 文件|*.exe;*.dll;*.sys;*.ocx|所有文件|*.*" };
            if (ofd.ShowDialog() == DialogResult.OK) txt.Text = PeInfo(ofd.FileName);
        };
        form.Controls.Add(txt);
        form.Controls.Add(btn);
        Application.Run(form);
    }

    private static string PeInfo(string path)
    {
        var d = File.ReadAllBytes(path);
        if (d.Length < 0x40 || d[0] != 0x4D || d[1] != 0x5A) return "不是合法 PE（缺少 MZ 头）";
        int e = BitConverter.ToInt32(d, 0x3C);
        if (Encoding.ASCII.GetString(d, e, 4) != "PE\0\0") return "缺少 PE 签名";
        int coff = e + 4;
        ushort machine = BitConverter.ToUInt16(d, coff);
        ushort nsec = BitConverter.ToUInt16(d, coff + 2);
        ushort optsize = BitConverter.ToUInt16(d, coff + 16);
        int opt = coff + 20;
        ushort magic = BitConverter.ToUInt16(d, opt);
        bool pe32p = magic == 0x20B;
        uint entry = BitConverter.ToUInt32(d, opt + 16);
        ulong ib = pe32p ? BitConverter.ToUInt64(d, opt + 24) : BitConverter.ToUInt32(d, opt + 28);
        ushort subsys = BitConverter.ToUInt16(d, opt + 68);
        var sb = new StringBuilder();
        sb.AppendLine($"文件: {path}");
        sb.AppendLine($"架构: {(machine == 0x8664 ? "x64" : machine == 0x14c ? "x86" : "其它")} (machine={machine:X4})");
        sb.AppendLine($"节数: {nsec}");
        sb.AppendLine($"Magic: {(pe32p ? "PE32+" : "PE32")}");
        sb.AppendLine($"入口点: {entry:X8}");
        sb.AppendLine($"ImageBase: {ib:X8}");
        sb.AppendLine($"子系统: {subsys}");
        int sec = opt + optsize;
        for (int i = 0; i < nsec; i++)
        {
            int s = sec + i * 40;
            string name = Encoding.ASCII.GetString(d, s, 8).Trim('\0');
            uint vaddr = BitConverter.ToUInt32(d, s + 12);
            uint vsize = BitConverter.ToUInt32(d, s + 8);
            sb.AppendLine($"  节 {i}: {name} VA={vaddr:X8} VSize={vsize:X}");
        }
        return sb.ToString();
    }
}
