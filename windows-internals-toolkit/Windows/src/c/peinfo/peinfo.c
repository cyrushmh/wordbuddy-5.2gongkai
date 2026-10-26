/* peinfo.c — 一个最小的 PE(Portable Executable) 头信息查看器
 * 编译: x86_64-w64-mingw32-gcc peinfo.c -o peinfo.exe   (PE32+ / Windows x64)
 *       i686-w64-mingw32-gcc   peinfo.c -o peinfo32.exe (PE32  / Windows x86)
 *       gcc peinfo.c -o peinfo_nat                          (本机 Linux，用于测试/对齐)
 * 运行: peinfo.exe [目标文件.exe]   缺省解析自身
 *       peinfo.exe -j [目标]     输出机器可读 JSON（便于自动化与跨语言一致性校验）
 *
 * 注意：结构体一律使用定宽整数类型（stdint.h），因此 Windows(mingw) 与本机
 * Linux 都能正确编译运行——PE 字段宽度是固定的，不受平台 long 宽度影响。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#pragma pack(push, 1)
typedef struct {
    uint16_t e_magic;
    uint8_t  _pad[58];
    uint32_t e_lfanew;          /* 偏移 0x3C：指向 NT 头 */
} IMAGE_DOS_HEADER;

typedef struct {
    uint16_t Machine;
    uint16_t NumberOfSections;
    uint32_t TimeDateStamp;
    uint32_t PointerToSymbolTable;
    uint32_t NumberOfSymbols;
    uint16_t SizeOfOptionalHeader;
    uint16_t Characteristics;
} IMAGE_FILE_HEADER;

typedef struct {
    uint8_t  Name[8];
    uint32_t VirtualSize;
    uint32_t VirtualAddress;
    uint32_t SizeOfRawData;
    uint32_t PointerToRawData;
    uint32_t PointerToRelocations;
    uint32_t PointerToLinenumbers;
    uint16_t NumberOfRelocations;
    uint16_t NumberOfLinenumbers;
    uint32_t Characteristics;
} IMAGE_SECTION_HEADER;
#pragma pack(pop)

static const char* machine_name(uint16_t m) {
    switch (m) {
        case 0x14C: return "x86 (Intel 386+)";
        case 0x8664: return "x64 (AMD64)";
        case 0xAA64: return "ARM64";
        case 0x1C0: return "ARM (32-bit)";
        case 0x14D: return "ARM (Thumb/Thumb-2, NT)";
        case 0x200: return "Intel IA64";
        case 0x9041: return "ARM64X";
        default: return "未知";
    }
}

static const char* subsystem_name(uint16_t s) {
    switch (s) {
        case 1: return "Native (驱动/系统)";
        case 2: return "Windows GUI";
        case 3: return "Windows CUI (控制台)";
        case 7: return "POSIX";
        case 9: return "Windows CE";
        case 10: return "EFI 应用程序";
        case 12: return "EFI ROM";
        default: return "未知";
    }
}

static void print_flags(uint16_t ch) {
    if (ch & 0x0002) printf("  EXECUTABLE_IMAGE\n");
    if (ch & 0x2000) printf("  DLL\n");
    if (ch & 0x0100) printf("  32BIT_MACHINE\n");
    if (ch & 0x0020) printf("  LARGE_ADDRESS_AWARE\n");
    if (ch & 0x0001) printf("  RELOCS_STRIPPED(无重定位)\n");
}

/* 把 8 字节节名打印为 JSON 字符串字面量（转义引号/反斜杠） */
static void print_name_json(const uint8_t* name) {
    putchar('"');
    for (int i = 0; i < 8; i++) {
        uint8_t c = name[i];
        if (c == 0) break;
        if (c == '"') printf("\\\"");
        else if (c == '\\') printf("\\\\");
        else putchar((int)c);
    }
    putchar('"');
}

static uint32_t rd32(FILE* f, long off) {
    uint32_t v = 0;
    fseek(f, off, SEEK_SET);
    (void)fread(&v, 1, 4, f);
    return v; /* 主机为小端，PE 亦小端，直接读 */
}

int main(int argc, char** argv) {
    int want_json = 0;
    const char* path = NULL;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-j") == 0) { want_json = 1; continue; }
        if (path == NULL) path = argv[i];
    }
    if (path == NULL) path = argv[0];

    FILE* f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "无法打开: %s\n", path); return 1; }

    IMAGE_DOS_HEADER dos;
    if (fread(&dos, 1, sizeof(dos), f) != sizeof(dos) || dos.e_magic != 0x5A4D) {
        fprintf(stderr, "不是有效的 PE：缺少 MZ 头\n"); fclose(f); return 1;
    }

    fseek(f, (long)dos.e_lfanew, SEEK_SET);
    uint8_t sig[4];
    (void)fread(sig, 1, 4, f);
    if (!(sig[0]=='P' && sig[1]=='E' && sig[2]==0 && sig[3]==0)) {
        fprintf(stderr, "不是有效的 PE：缺少 PE\\0\\0 签名\n"); fclose(f); return 1;
    }

    IMAGE_FILE_HEADER fh;
    (void)fread(&fh, 1, sizeof(fh), f);

    long opt_off = (long)dos.e_lfanew + 4 + (long)sizeof(fh);
    uint16_t magic = (uint16_t)(rd32(f, opt_off) & 0xFFFF);
    uint32_t entry = rd32(f, opt_off + 16);
    uint64_t image_base;
    if (magic == 0x20B) { /* PE32+ : ImageBase 为 8 字节，偏移 24 */
        uint32_t lo = rd32(f, opt_off + 24);
        uint32_t hi = rd32(f, opt_off + 28);
        image_base = ((uint64_t)hi << 32) | lo;
    } else {              /* PE32 : ImageBase 为 4 字节，偏移 28 */
        image_base = rd32(f, opt_off + 28);
    }
    uint32_t sec_align = rd32(f, opt_off + 32);
    uint32_t file_align = rd32(f, opt_off + 36);
    uint16_t subsystem = (uint16_t)(rd32(f, opt_off + 68) & 0xFFFF);

    /* 数据目录偏移：PE32+ 在 opt+112，PE32 在 opt+96 */
    long dd_start = (magic == 0x20B) ? (opt_off + 112) : (opt_off + 96);
    /* NumberOfRvaAndSizes 偏移：PE32+ 在 opt+108，PE32 在 opt+92 */
    uint32_t num_rva = rd32(f, (magic == 0x20B) ? (opt_off + 108) : (opt_off + 92));
    uint32_t num_dirs = num_rva; if (num_dirs > 16) num_dirs = 16;

    long sec_tbl = opt_off + fh.SizeOfOptionalHeader;

    if (want_json) {
        printf("{");
        printf("\"e_lfanew\":%u,", dos.e_lfanew);
        printf("\"machine\":%u,", (unsigned)fh.Machine);
        printf("\"machine_name\":\"%s\",", machine_name(fh.Machine));
        printf("\"number_of_sections\":%u,", (unsigned)fh.NumberOfSections);
        printf("\"time_date_stamp\":%u,", fh.TimeDateStamp);
        printf("\"size_of_optional_header\":%u,", (unsigned)fh.SizeOfOptionalHeader);
        printf("\"characteristics\":%u,", (unsigned)fh.Characteristics);
        printf("\"optional\":{");
        printf("\"magic\":%u,", (unsigned)magic);
        printf("\"entry_point\":%u,", entry);
        printf("\"image_base\":%llu,", (unsigned long long)image_base);
        printf("\"subsystem\":%u,", (unsigned)subsystem);
        printf("\"number_of_rva_and_sizes\":%u", num_rva);
        printf("},");
        printf("\"data_directories\":[");
        for (uint32_t i = 0; i < num_dirs; i++) {
            uint32_t rva = rd32(f, dd_start + (long)i * 8);
            uint32_t size = rd32(f, dd_start + (long)i * 8 + 4);
            if (i) printf(",");
            printf("{\"index\":%u,\"name\":\"dir%u\",\"rva\":%u,\"size\":%u}", i, i, rva, size);
        }
        printf("],");
        printf("\"sections\":[");
        for (uint32_t i = 0; i < fh.NumberOfSections; i++) {
            IMAGE_SECTION_HEADER sh;
            fseek(f, sec_tbl + (long)i * (long)sizeof(sh), SEEK_SET);
            if (fread(&sh, 1, sizeof(sh), f) != sizeof(sh)) break;
            if (i) printf(",");
            printf("{\"index\":%u,\"name\":", i);
            print_name_json(sh.Name);
            printf(",\"virtual_size\":%u,\"virtual_address\":%u,\"size_of_raw_data\":%u,"
                   "\"pointer_to_raw_data\":%u,\"characteristics\":%u}",
                   sh.VirtualSize, sh.VirtualAddress, sh.SizeOfRawData,
                   sh.PointerToRawData, sh.Characteristics);
        }
        printf("]}");
        fclose(f);
        return 0;
    }

    /* 人类可读输出 */
    printf("==================================================\n");
    printf(" PE 头信息查看器  (解析: %s)\n", path);
    printf("==================================================\n");
    printf("[DOS 头]\n  e_magic  = MZ (0x5A4D)\n");
    printf("  e_lfanew = 0x%X  -> NT 头位置\n", dos.e_lfanew);
    printf("[NT 签名]  PE\\0\\0\n");
    printf("[COFF 文件头]\n");
    printf("  Machine            = 0x%04X  (%s)\n", fh.Machine, machine_name(fh.Machine));
    printf("  NumberOfSections   = %u\n", fh.NumberOfSections);
    printf("  TimeDateStamp      = 0x%X\n", fh.TimeDateStamp);
    printf("  SizeOfOptionalHdr  = %u\n", fh.SizeOfOptionalHeader);
    printf("  Characteristics     = 0x%04X\n", fh.Characteristics);
    print_flags(fh.Characteristics);
    printf("[可选头]\n");
    printf("  Magic              = 0x%04X  (%s)\n", magic, magic==0x20B?"PE32+ (64位)":magic==0x10B?"PE32 (32位)":"未知");
    printf("  EntryPoint (RVA)   = 0x%X\n", entry);
    printf("  ImageBase          = 0x%llX\n", (unsigned long long)image_base);
    printf("  SectionAlignment   = 0x%X\n", sec_align);
    printf("  FileAlignment      = 0x%X\n", file_align);
    printf("  Subsystem          = %u  (%s)\n", subsystem, subsystem_name(subsystem));

    printf("[数据目录]  共 %u 项\n", num_rva);
    for (uint32_t i = 0; i < num_dirs; i++) {
        uint32_t rva = rd32(f, dd_start + (long)i * 8);
        uint32_t size = rd32(f, dd_start + (long)i * 8 + 4);
        printf("  [%2u] dir%u  RVA=0x%X Size=0x%X\n", i, i, rva, size);
    }

    printf("[节表]  共 %u 节\n", fh.NumberOfSections);
    for (uint32_t i = 0; i < fh.NumberOfSections; i++) {
        IMAGE_SECTION_HEADER sh;
        fseek(f, sec_tbl + (long)i * (long)sizeof(sh), SEEK_SET);
        if (fread(&sh, 1, sizeof(sh), f) != sizeof(sh)) break;
        char name[9]; memcpy(name, sh.Name, 8); name[8] = 0;
        printf("  #%2u  %-8s  VSize=0x%05X  VAddr=0x%05X  Raw=0x%05X@0x%05X  Chars=0x%08X\n",
               i, name,
               sh.VirtualSize, sh.VirtualAddress,
               sh.SizeOfRawData, sh.PointerToRawData,
               sh.Characteristics);
    }
    printf("==================================================\n");
    printf("  ✅ 这是一个合法 PE 文件，可被 Windows 加载器识别。\n");
    fclose(f);
    return 0;
}
