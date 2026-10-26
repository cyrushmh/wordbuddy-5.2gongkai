// PeInfo.java — 纯 JDK 标准库的 PE(Portable Executable) 结构解析器
//
// 与仓库内 C / Rust / Python / .NET / VBA / Java 六个实现同源同义，机器可读 JSON
// 输出（--json）字段与 tests/parity_test.py 的对比口径完全一致。
// 零第三方依赖，仅需 JDK（源码面向 OpenJDK 17+，建议 25 LTS；tests/parity_test.py
// 的 build_java() 会自适应回退到本机可用版本，无需手动指定 --release）。
//
// 用法:
//   javac PeInfo.java                # 用本机 JDK 编译（或 javac --release 25）
//   java  PeInfo file.exe            # 打印文本头信息
//   java  PeInfo file.exe --json     # 输出机器可读 JSON
//
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public final class PeInfo {

    // ---------- 常量表（与 python pe_inspect.py 保持一致） ----------
    private static final java.util.Map<Integer, String> MACHINES = new java.util.LinkedHashMap<>();
    private static final java.util.Map<Integer, String> SUBSYSTEMS = new java.util.LinkedHashMap<>();
    private static final java.util.Map<Integer, String> CHAR_FLAGS = new java.util.LinkedHashMap<>();
    private static final java.util.Map<Long, String> SEC_FLAGS = new java.util.LinkedHashMap<>();
    private static final String[] DATA_DIR_NAMES = {
        "导出表", "导入表", "资源表", "异常表", "安全表", "重定位表", "调试表",
        "版权表", "全局指针", "TLS 表", "加载配置", "绑定导入", "IAT",
        "延迟导入", "COM 描述符", "保留"
    };

    static {
        MACHINES.put(0x14C, "x86 (Intel 386+)");
        MACHINES.put(0x8664, "x64 (AMD64)");
        MACHINES.put(0xAA64, "ARM64");
        MACHINES.put(0x1C0, "ARM (32-bit)");
        MACHINES.put(0x14D, "ARM (Thumb/Thumb-2)");
        MACHINES.put(0x200, "IA64");
        MACHINES.put(0x9041, "ARM64X");

        SUBSYSTEMS.put(1, "Native (驱动/系统)");
        SUBSYSTEMS.put(2, "Windows GUI");
        SUBSYSTEMS.put(3, "Windows CUI (控制台)");
        SUBSYSTEMS.put(7, "POSIX");
        SUBSYSTEMS.put(9, "Windows CE");
        SUBSYSTEMS.put(10, "EFI 应用程序");
        SUBSYSTEMS.put(12, "EFI ROM");

        CHAR_FLAGS.put(0x0002, "EXECUTABLE_IMAGE");
        CHAR_FLAGS.put(0x2000, "DLL");
        CHAR_FLAGS.put(0x0100, "32BIT_MACHINE");
        CHAR_FLAGS.put(0x0020, "LARGE_ADDRESS_AWARE");
        CHAR_FLAGS.put(0x0001, "RELOCS_STRIPPED");
        CHAR_FLAGS.put(0x0080, "BYTES_REVERSED_LO");
        CHAR_FLAGS.put(0x0200, "DEBUG_STRIPPED");

        SEC_FLAGS.put(0x00000020L, "CNT_CODE");
        SEC_FLAGS.put(0x00000040L, "CNT_INITIALIZED_DATA");
        SEC_FLAGS.put(0x00000080L, "CNT_UNINITIALIZED_DATA");
        SEC_FLAGS.put(0x20000000L, "MEM_EXECUTE");
        SEC_FLAGS.put(0x40000000L, "MEM_READ");
        SEC_FLAGS.put(0x80000000L, "MEM_WRITE");
        SEC_FLAGS.put(0x10000000L, "MEM_SHARED");
    }

    // ---------- 数据模型 ----------
    static final class DataDir {
        int index;
        String name;
        long rva;
        long size;
    }

    static final class Section {
        int index;
        String name;
        long virtualSize;
        long virtualAddress;
        long sizeOfRawData;
        long pointerToRawData;
        long characteristics;
    }

    static final class Pe {
        int eLfanew;
        int machine;
        int numberOfSections;
        long timeDateStamp;
        int sizeOfOptionalHeader;
        int characteristics;
        int magic;
        boolean pe32plus;
        long entryPoint;
        long imageBase;
        long sectionAlignment;
        long fileAlignment;
        long sizeOfImage;
        long sizeOfHeaders;
        int subsystem;
        int numberOfRvaAndSizes;
        List<DataDir> dataDirectories = new ArrayList<>();
        List<Section> sections = new ArrayList<>();
    }

    public static void main(String[] args) {
        if (args.length == 0) {
            System.err.println("用法: java PeInfo <file.exe|self> [--json]");
            System.exit(2);
        }
        boolean json = false;
        String path = null;
        for (String a : args) {
            if ("--json".equals(a)) json = true;
            else if (!a.startsWith("-")) path = a;
        }
        if (path == null) {
            System.err.println("缺少 PE 文件路径");
            System.exit(2);
        }

        byte[] data;
        try {
            data = Files.readAllBytes(Path.of(path));
        } catch (IOException e) {
            System.err.println("无法读取文件: " + e.getMessage());
            System.exit(1);
            return;
        }

        Pe pe;
        try {
            pe = parse(data);
        } catch (RuntimeException e) {
            System.err.println(e.getMessage());
            System.exit(1);
            return;
        }

        if (json) {
            System.out.print(toJson(pe));
        } else {
            System.out.print(toText(pe));
        }
    }

    static Pe parse(byte[] data) {
        if (data.length < 0x40 || data[0] != 'M' || data[1] != 'Z') {
            throw new RuntimeException("不是有效 PE：缺少 MZ 头");
        }
        int eLfanew = (int) u32(data, 0x3C);
        if (eLfanew + 4 > data.length
                || data[eLfanew] != 'P' || data[eLfanew + 1] != 'E'
                || data[eLfanew + 2] != 0 || data[eLfanew + 3] != 0) {
            throw new RuntimeException(String.format("不是有效 PE：偏移 0x%X 处缺少 PE\\0\\0 签名", eLfanew));
        }
        int off = eLfanew + 4;

        Pe pe = new Pe();
        pe.eLfanew = eLfanew;
        pe.machine = u16(data, off);
        pe.numberOfSections = u16(data, off + 2);
        pe.timeDateStamp = u32(data, off + 4);
        // off+8: PointerToSymbolTable(u32), off+12: NumberOfSymbols(u32)
        pe.sizeOfOptionalHeader = u16(data, off + 16);
        pe.characteristics = u16(data, off + 18);

        int optOff = off + 20;
        pe.magic = u16(data, optOff);
        pe.pe32plus = (pe.magic == 0x20B);
        pe.entryPoint = u32(data, optOff + 16);
        int numRvaOff = pe.pe32plus ? optOff + 108 : optOff + 92;
        int ddOff;
        if (pe.pe32plus) {
            pe.imageBase = u64(data, optOff + 24);
            ddOff = optOff + 112;
        } else {
            pe.imageBase = u32(data, optOff + 28);
            ddOff = optOff + 96;
        }
        pe.sectionAlignment = u32(data, optOff + 32);
        pe.fileAlignment = u32(data, optOff + 36);
        pe.subsystem = u16(data, optOff + 68);
        pe.sizeOfImage = u32(data, optOff + 56);
        pe.sizeOfHeaders = u32(data, optOff + 60);
        pe.numberOfRvaAndSizes = (int) u32(data, numRvaOff);

        int ndd = Math.min(pe.numberOfRvaAndSizes, 16);
        for (int i = 0; i < ndd; i++) {
            DataDir d = new DataDir();
            d.index = i;
            d.name = (i < DATA_DIR_NAMES.length) ? DATA_DIR_NAMES[i] : ("#" + i);
            d.rva = u32(data, ddOff + i * 8);
            d.size = u32(data, ddOff + i * 8 + 4);
            pe.dataDirectories.add(d);
        }

        int secTbl = optOff + pe.sizeOfOptionalHeader;
        for (int i = 0; i < pe.numberOfSections; i++) {
            int s = secTbl + i * 40;
            if (s + 40 > data.length) break;
            Section sec = new Section();
            sec.index = i;
            sec.name = readName(data, s);
            sec.virtualSize = u32(data, s + 8);
            sec.virtualAddress = u32(data, s + 12);
            sec.sizeOfRawData = u32(data, s + 16);
            sec.pointerToRawData = u32(data, s + 20);
            sec.characteristics = u32(data, s + 36);
            pe.sections.add(sec);
        }
        return pe;
    }

    private static String readName(byte[] data, int s) {
        int len = 0;
        while (len < 8 && data[s + len] != 0) len++;
        return new String(data, s, len, StandardCharsets.ISO_8859_1);
    }

    private static int u16(byte[] d, int off) {
        return ByteBuffer.wrap(d, off, 2).order(ByteOrder.LITTLE_ENDIAN).getShort() & 0xFFFF;
    }

    private static long u32(byte[] d, int off) {
        return ByteBuffer.wrap(d, off, 4).order(ByteOrder.LITTLE_ENDIAN).getInt() & 0xFFFFFFFFL;
    }

    private static long u64(byte[] d, int off) {
        return ByteBuffer.wrap(d, off, 8).order(ByteOrder.LITTLE_ENDIAN).getLong();
    }

    // ---------- 文本输出 ----------
    static String toText(Pe pe) {
        StringBuilder b = new StringBuilder();
        b.append("====================================================\n");
        b.append(" PE 结构解析 (OpenJDK 版)\n");
        b.append("====================================================\n");
        b.append("[DOS 头]\n");
        b.append("  e_magic  = MZ (0x5A4D)\n");
        b.append(String.format("  e_lfanew = 0x%X  -> NT 头位置%n", pe.eLfanew));
        b.append("[COFF 文件头]\n");
        b.append(String.format("  Machine           = 0x%04X  (%s)%n", pe.machine, MACHINES.getOrDefault(pe.machine, "未知")));
        b.append(String.format("  NumberOfSections  = %d%n", pe.numberOfSections));
        b.append(String.format("  TimeDateStamp      = 0x%X%n", pe.timeDateStamp));
        b.append(String.format("  SizeOfOptionalHdr = %d%n", pe.sizeOfOptionalHeader));
        b.append(String.format("  Characteristics   = 0x%04X%n", pe.characteristics));
        for (var e : CHAR_FLAGS.entrySet()) {
            if ((pe.characteristics & e.getKey()) != 0) b.append("      ").append(e.getValue()).append("\n");
        }
        b.append("[可选头]\n");
        b.append(String.format("  Magic             = 0x%04X  (%s)%n", pe.magic, pe.pe32plus ? "PE32+ (64位)" : "PE32 (32位)"));
        b.append(String.format("  EntryPoint (RVA)  = 0x%X%n", pe.entryPoint));
        b.append(String.format("  ImageBase         = 0x%X%n", pe.imageBase));
        b.append(String.format("  SectionAlignment  = 0x%X%n", pe.sectionAlignment));
        b.append(String.format("  FileAlignment     = 0x%X%n", pe.fileAlignment));
        b.append(String.format("  SizeOfImage       = 0x%X%n", pe.sizeOfImage));
        b.append(String.format("  SizeOfHeaders     = 0x%X%n", pe.sizeOfHeaders));
        b.append(String.format("  Subsystem         = %d  (%s)%n", pe.subsystem, SUBSYSTEMS.getOrDefault(pe.subsystem, "未知")));
        b.append("[数据目录]\n");
        for (DataDir dd : pe.dataDirectories) {
            b.append(String.format("  [%2d] %-12s RVA=0x%X Size=0x%X%n", dd.index, dd.name, dd.rva, dd.size));
        }
        b.append(String.format("[节表]  共 %d 节%n", pe.numberOfSections));
        for (Section sec : pe.sections) {
            b.append(String.format("  #%2d  %-8s  VSize=0x%05X VAddr=0x%05X Raw=0x%05X@%05X%n",
                    sec.index, sec.name, sec.virtualSize, sec.virtualAddress, sec.sizeOfRawData, sec.pointerToRawData));
        }
        b.append("====================================================\n");
        b.append("  ✅ 这是一个结构合法的 PE 文件。\n");
        return b.toString();
    }

    // ---------- JSON 输出（手写，零依赖，字段与 parity_test 对比口径一致） ----------
    static String toJson(Pe pe) {
        StringBuilder b = new StringBuilder();
        b.append("{\n");
        b.append(String.format("  \"e_lfanew\": %d,%n", pe.eLfanew));
        b.append(String.format("  \"machine\": %d,%n", pe.machine));
        b.append(String.format("  \"machine_name\": %s,%n", jstr(MACHINES.getOrDefault(pe.machine, "未知"))));
        b.append(String.format("  \"number_of_sections\": %d,%n", pe.numberOfSections));
        b.append(String.format("  \"time_date_stamp\": %d,%n", pe.timeDateStamp));
        b.append(String.format("  \"size_of_optional_header\": %d,%n", pe.sizeOfOptionalHeader));
        b.append(String.format("  \"characteristics\": %d,%n", pe.characteristics));
        b.append("  \"optional\": {\n");
        b.append(String.format("    \"magic\": %d,%n", pe.magic));
        b.append(String.format("    \"magic_name\": %s,%n", jstr(pe.pe32plus ? "PE32+ (64位)" : "PE32 (32位)")));
        b.append(String.format("    \"entry_point\": %d,%n", pe.entryPoint));
        b.append(String.format("    \"image_base\": %d,%n", pe.imageBase));
        b.append(String.format("    \"section_alignment\": %d,%n", pe.sectionAlignment));
        b.append(String.format("    \"file_alignment\": %d,%n", pe.fileAlignment));
        b.append(String.format("    \"size_of_image\": %d,%n", pe.sizeOfImage));
        b.append(String.format("    \"size_of_headers\": %d,%n", pe.sizeOfHeaders));
        b.append(String.format("    \"subsystem\": %d,%n", pe.subsystem));
        b.append(String.format("    \"subsystem_name\": %s,%n", jstr(SUBSYSTEMS.getOrDefault(pe.subsystem, "未知"))));
        b.append(String.format("    \"number_of_rva_and_sizes\": %d%n", pe.numberOfRvaAndSizes));
        b.append("  },\n");
        b.append("  \"data_directories\": [");
        for (int i = 0; i < pe.dataDirectories.size(); i++) {
            DataDir d = pe.dataDirectories.get(i);
            if (i > 0) b.append(", ");
            b.append(String.format("{\"index\": %d, \"name\": %s, \"rva\": %d, \"size\": %d}",
                    d.index, jstr(d.name), d.rva, d.size));
        }
        b.append("],\n");
        b.append("  \"sections\": [");
        for (int i = 0; i < pe.sections.size(); i++) {
            Section s = pe.sections.get(i);
            if (i > 0) b.append(", ");
            b.append("{");
            b.append(String.format("\"index\": %d, ", s.index));
            b.append(String.format("\"name\": %s, ", jstr(s.name)));
            b.append(String.format("\"virtual_size\": %d, ", s.virtualSize));
            b.append(String.format("\"virtual_address\": %d, ", s.virtualAddress));
            b.append(String.format("\"size_of_raw_data\": %d, ", s.sizeOfRawData));
            b.append(String.format("\"pointer_to_raw_data\": %d, ", s.pointerToRawData));
            b.append(String.format("\"characteristics\": %d", s.characteristics));
            b.append("}");
        }
        b.append("]\n");
        b.append("}");
        return b.toString();
    }

    private static String jstr(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> b.append("\\\"");
                case '\\' -> b.append("\\\\");
                case '\n' -> b.append("\\n");
                case '\r' -> b.append("\\r");
                case '\t' -> b.append("\\t");
                default -> {
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
                }
            }
        }
        b.append("\"");
        return b.toString();
    }
}
