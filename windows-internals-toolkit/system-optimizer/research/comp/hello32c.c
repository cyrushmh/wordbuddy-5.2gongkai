/* hello32c.c - 32 位 DOS（DJGPP go32 DPMI）ANSI C 闭环程序
 *
 * 三面证据（参照 16 位档 R7.TXT 文件往返模式）：
 *   1. stdout 流   ：printf 发 "Z32C-RT-OK" + 计数器两位十六进制 + '\n' + 累加值行
 *   2. 文件回读    ：fopen/fwrite/fclose 写 Z32C.TXT，内容 = 上述两行文本，
 *                    宿主机经 dosbox 挂载盘回读一致（int 21h 3Fh/3Ch/40h/3Eh 经 DPMI 反射）
 *   3. 退出码      ：return 0（int 21h AH=4Ch 经 DPMI 反射）
 *
 * ANSI C 纪律（继承 8 位档 sdcc 教训）：不用任何扩展，
 * 编译器 i586-pc-msdosdjgpp-gcc（GCC 12.2.0，DJGPP libc）。
 */

#include <stdio.h>

int main(void)
{
    unsigned char counter = 0x55;
    const char *msg = "Z32C-RT-OK";
    FILE *f;

    /* 计数器与消息字符、换行累加（设计值手算：0x55 + 0x29C(10 字符和) + 0x0A = 0xFB） */
    {
        const char *p;
        for (p = msg; *p; p++)
            counter += (unsigned char)*p;
        counter += 0x0A;
    }

    /* 1. stdout 流 */
    printf("%s%02X\n", msg, (unsigned)0x55);
    printf("%02X\n", (unsigned)counter);

    /* 2. 文件回读证据：与 stdout 同文两行 */
    f = fopen("Z32C.TXT", "wb");
    if (f == NULL) {
        printf("FILE-FAIL\n");
        return 1;
    }
    fprintf(f, "%s%02X\n%02X\n", msg, (unsigned)0x55, (unsigned)counter);
    if (fclose(f) != 0) {
        printf("CLOSE-FAIL\n");
        return 1;
    }

    return 0;
}
