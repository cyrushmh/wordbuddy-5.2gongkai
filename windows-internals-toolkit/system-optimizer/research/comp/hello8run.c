/* 8-bit Z80 run-layer closure program: SDCC -> ihx -> Z80 core execution.
 * Emits an ASCII banner on OUT port 0x01 (host-capturable), then the final
 * value of `counter` as two uppercase hex chars, then HALTs.
 * `counter` is also read back from RAM by the runner (memory evidence).
 */
#include <stdint.h>

uint8_t counter;
uint8_t out_byte;

void emit(void)
{
    __asm
    ld a, (_out_byte)
    out (1), a
    __endasm;
}

const char msg[] = "Z80-RT-OK";

const char hexd[] = "0123456789ABCDEF";

void main(void)
{
    const char *p = msg;
    uint8_t v;

    counter = 0x55;
    while (*p) {
        out_byte = *p++;
        emit();
        counter++;
    }
    counter += 0x0A;            /* 0x55 + 11 chars + 0x0A = 0x70 */
    v = counter;
    out_byte = hexd[(v >> 4) & 0x0F];
    emit();
    out_byte = hexd[v & 0x0F];
    emit();
    out_byte = '\n';
    emit();
    __asm
    halt
    __endasm;
    while (1) {
        counter++;              /* unreachable on halt; guard if HALT is NOP-ed */
    }
}
