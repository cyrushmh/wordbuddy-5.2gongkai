/*
 * classics — Linux 原生典籍阅读 / 乱码安全解码 CLI
 *
 * 复用本仓库 TextEncoding 设计哲学：
 *   严格 UTF-8  →  严格 GB18030  →  标注乱码，绝不假装成功。
 * 这是"编码防护落到用户路径"在 Linux 端的落地（对应 iOS/macOS 的
 * TextEncoding.decodeSafe 与 HarmonyOS 的 decodeTextSafe）。
 *
 * 子命令：
 *   classics                        显示用法
 *   classics list                   列出 /usr/share/classics 下的典籍
 *   classics show <book>            输出整本（book 为文件名，可省略 .txt）
 *   classics decode <file>          读取字节，判定编码并安全解码输出
 *   classics lint <file>            扫描乱码指纹与非法 UTF-8 区段
 *
 * 编译（交叉安全，由 debian/rules 注入 host 前缀 CC 与 dpkg-buildflags）：
 *   make
 * 安装：
 *   make install DESTDIR=...
 *
 * 仅依赖 glibc（iconv 提供 GB18030），无第三方库；C99 可移植。
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <iconv.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>

#ifndef DATADIR
#define DATADIR "/usr/share/classics"
#endif

/* 数据目录：默认 DATADIR，可用环境变量 CLASSICS_DATADIR 覆盖（便于测试/便携）*/
static const char *data_dir(void)
{
    const char *e = getenv("CLASSICS_DATADIR");
    return e && *e ? e : DATADIR;
}

/* ---- 字节读取：整文件读入内存 ---- */
static unsigned char *read_all(const char *path, size_t *out_len)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "classics: 无法打开 %s: %s\n", path, strerror(errno));
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long sz = ftell(f);
    if (sz < 0) { fclose(f); return NULL; }
    rewind(f);
    unsigned char *buf = malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return NULL; }
    size_t got = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[got] = 0;
    *out_len = got;
    return buf;
}

/* ---- 严格 UTF-8 校验（拒绝过长的 4 字节序列与代理区）---- */
static int utf8_valid(const unsigned char *s, size_t n)
{
    size_t i = 0;
    while (i < n) {
        unsigned char c = s[i];
        if (c < 0x80) { i++; continue; }
        size_t need; uint32_t cp;         uint32_t lo, hi;
        if ((c & 0xE0) == 0xC0) { need = 2; cp = c & 0x1F; lo = 0x80; hi = 0x7FF; }
        else if ((c & 0xF0) == 0xE0) { need = 3; cp = c & 0x0F; lo = 0x800; hi = 0xFFFF; }
        else if ((c & 0xF8) == 0xF0) { need = 4; cp = c & 0x07; lo = 0x10000; hi = 0x10FFFF; }
        else return 0; /* 非法首字节 */
        if (i + need > n) return 0;
        for (size_t j = 1; j < need; j++) {
            if ((s[i + j] & 0xC0) != 0x80) return 0;
            cp = (cp << 6) | (s[i + j] & 0x3F);
        }
        if (cp < lo) return 0;                       /* 过度编码 */
        if (cp > hi) return 0;
        if (cp >= 0xD800 && cp <= 0xDFFF) return 0;  /* 代理区 */
        if (cp > 0x10FFFF) return 0;
        i += need;
    }
    return 1;
}

/* ---- 用 iconv 把 GB18030 字节转 UTF-8；成功返回新缓冲区 ---- */
static unsigned char *gb18030_to_utf8(const unsigned char *in, size_t inlen, size_t *outlen)
{
    iconv_t cd = iconv_open("UTF-8", "GB18030");
    if (cd == (iconv_t)-1) return NULL;
    size_t outcap = inlen * 2 + 16;
    unsigned char *out = malloc(outcap);
    if (!out) { iconv_close(cd); return NULL; }
    char *ip = (char *)in;
    size_t ileft = inlen;
    char *op = (char *)out;
    size_t oleft = outcap;
    size_t r = iconv(cd, &ip, &ileft, &op, &oleft);
    iconv_close(cd);
    if (r == (size_t)-1 || ileft != 0) { free(out); return NULL; }
    *outlen = outcap - oleft;
    out[*outlen] = 0;
    return out;
}

/* ---- 乱码指纹（命中即说明编码已损坏/错判）---- */
static const char *const FINGERPRINTS[] = {
    "\xE2\xEF\xBF\xBD",          /* 锟斤拷：U+FFFD 的 GBK 双重编码 */
    "\xE7\x83\xAB\xE7\x83\xAB\xE7\x83\xAB", /* 烫烫烫 */
    "\xE5\xB1\xAF\xE5\xB1\xAF\xE5\xB1\xAF", /* 屯屯屯 */
    "\xEF\xBF\xBD",              /* 裸 U+FFFD 替换符（信息已丢失） */
    NULL
};

static int count_fingerprint(const unsigned char *buf, size_t n)
{
    int hits = 0;
    for (int k = 0; FINGERPRINTS[k]; k++) {
        size_t fl = strlen(FINGERPRINTS[k]);
        if (fl == 0) continue;
        for (size_t i = 0; i + fl <= n; i++) {
            if (memcmp(buf + i, FINGERPRINTS[k], fl) == 0) {
                hits++;
                i += fl - 1;
            }
        }
    }
    return hits;
}

/* ---- decode 子命令 ---- */
static int cmd_decode(const char *path)
{
    size_t len;
    unsigned char *raw = read_all(path, &len);
    if (!raw) return 1;

    if (utf8_valid(raw, len)) {
        printf("# 判定：UTF-8（严格通过，可安全使用）\n");
        fwrite(raw, 1, len, stdout);
        free(raw);
        return 0;
    }

    int fp = count_fingerprint(raw, len);
    unsigned char *conv = gb18030_to_utf8(raw, len, &len);
    if (conv) {
        printf("# 判定：GB18030（原始非 UTF-8，已安全转 UTF-8）\n");
        if (fp) printf("# 注意：含 %d 处乱码指纹，原文件可能已损坏\n", fp);
        fwrite(conv, 1, len, stdout);
        free(conv);
        free(raw);
        return 0;
    }

    printf("# 判定：无法安全解码（既非 UTF-8 也非合法 GB18030）\n");
    if (fp) printf("# 乱码指纹命中：%d 处\n", fp);
    printf("# 原始字节（前 256，十六进制）仅作诊断：\n");
    for (size_t i = 0; i < len && i < 256; i++)
        printf("%02X ", raw[i]);
    printf("\n");
    free(raw);
    return 2;
}

/* ---- lint 子命令 ---- */
static int cmd_lint(const char *path)
{
    size_t len;
    unsigned char *raw = read_all(path, &len);
    if (!raw) return 1;

    int bad = 0;
    /* 非法 UTF-8 区段 */
    if (!utf8_valid(raw, len)) {
        size_t i = 0;
        while (i < len) {
            if (!utf8_valid(raw + i, 1)) {
                printf("[非法字节] @%zu: %02X\n", i, raw[i]);
                bad++;
                if (bad > 50) { printf("... 截断（>50 处）\n"); break; }
            }
            i++;
        }
    }
    int fp = count_fingerprint(raw, len);
    if (fp) { printf("[乱码指纹] 命中 %d 处（锟斤拷/烫烫烫/屯屯屯/裸U+FFFD）\n", fp); bad += fp; }
    if (bad == 0) printf("OK：未发现乱码指纹，UTF-8 合法\n");
    else printf("总计 %d 处可疑\n", bad);
    free(raw);
    return bad ? 2 : 0;
}

/* ---- list 子命令 ---- */
static int cmd_list(void)
{
    const char *dd = data_dir();
    DIR *d = opendir(dd);
    if (!d) {
        fprintf(stderr, "classics: 数据目录缺失 %s（请确认包已安装）\n", dd);
        return 1;
    }
    struct dirent *e;
    printf("已安装典籍（%s）：\n", dd);
    int n = 0;
    while ((e = readdir(d))) {
        size_t l = strlen(e->d_name);
        if (l > 4 && strcmp(e->d_name + l - 4, ".txt") == 0) {
            printf("  - %.*s\n", (int)(l - 4), e->d_name);
            n++;
        }
    }
    closedir(d);
    if (n == 0) printf("  （空）\n");
    return 0;
}

/* ---- show 子命令 ---- */
static int cmd_show(const char *book)
{
    const char *dd = data_dir();
    char path[4096];
    if (strchr(book, '/') || strstr(book, "..")) {
        snprintf(path, sizeof(path), "%s", book);
    } else {
        snprintf(path, sizeof(path), "%s/%s", dd, book);
        if (access(path, R_OK) != 0)
            snprintf(path, sizeof(path), "%s/%s.txt", dd, book);
    }
    size_t len;
    unsigned char *raw = read_all(path, &len);
    if (!raw) return 1;
    if (utf8_valid(raw, len)) {
        fwrite(raw, 1, len, stdout);
    } else {
        unsigned char *conv = gb18030_to_utf8(raw, len, &len);
        if (conv) { fwrite(conv, 1, len, stdout); free(conv); }
        else { fwrite(raw, 1, len, stdout); }
    }
    free(raw);
    return 0;
}

static void usage(void)
{
    printf(
        "classics — 典籍阅读 / 乱码安全解码 (0001.0000.0000.0000.20261024)\n"
        "用法：\n"
        "  classics                        显示本帮助\n"
        "  classics list                   列出已安装典籍\n"
        "  classics show <book>            输出整本（可省略 .txt）\n"
        "  classics decode <file>          安全解码：UTF-8→GB18030→标注\n"
        "  classics lint <file>            扫描乱码指纹与非法 UTF-8\n");
}

int main(int argc, char **argv)
{
    if (argc < 2) { usage(); return 0; }
    if (strcmp(argv[1], "list") == 0)   return cmd_list();
    if (strcmp(argv[1], "show") == 0) {
        if (argc < 3) { fprintf(stderr, "classics: show 需要 <book>\n"); return 1; }
        return cmd_show(argv[2]);
    }
    if (strcmp(argv[1], "decode") == 0) {
        if (argc < 3) { fprintf(stderr, "classics: decode 需要 <file>\n"); return 1; }
        return cmd_decode(argv[2]);
    }
    if (strcmp(argv[1], "lint") == 0) {
        if (argc < 3) { fprintf(stderr, "classics: lint 需要 <file>\n"); return 1; }
        return cmd_lint(argv[2]);
    }
    usage();
    return 0;
}
