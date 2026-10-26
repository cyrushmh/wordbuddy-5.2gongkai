#!/usr/bin/env python3
"""z80core — self-contained Z80 CPU core for the 8-bit run layer of the
DOS/8-16-32-64-128 bit-width ladder (research/comp batch-8 closure).

Scope (honest coverage statement):
  * full unprefixed base opcode set (all 256 slots, incl. undocumented
    SLL and the IXH/IXL register aliases in the H/L slot)
  * full CB-prefixed block (rotates / shifts / BIT / RES / SET)
  * ED-prefixed documented block instructions (LDI/LDD/LDIR/LDDR,
    CPI/CPD/CPIR/CPDR, INI/IND/INIR/INDR, OUTI/OUTD/OTIR/OTDR,
    NEG, RETN/RETI, IM 0/1/2, LD I/R and LD A,I/R, RRD/RLD,
    ADC/SBC HL,rr, LD (nn),rr / LD rr,(nn), IN/OUT (C))
  * DDCB/FDCB (IX/IY + displacement + CB op) — decoded and executed
  * undocumented ED slots decode as 8T NOPs (per Zilog convention)

What is deliberately NOT modelled (documented gaps):
  * interrupt acceptance / daisy chain (IFF is tracked, not acted on)
  * memory contention / exact T-state accuracy (T counts are the
    documented nominal values, labelled "approx")
  * R register increments follow the documented +1/+2 pattern only

Run:
    python3 z80core.py --selftest        # known-answer instruction tests
    from z80core import Z80               # embeddable use

Evidence discipline: this core was written for the repo's own bit-width
ladder closure. Its instruction decode is cross-checked against the
independent `d52` Z80 disassembler (see z80_runner.py --xcheck).
"""
from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------- registers
# 8-bit register file: A F B C D E H L  (r-index per Zilog r[] table)
# r = 6 means (HL) memory operand; r = 4/5 alias IXH/IXL when prefixed.

C, N_, P, H_, Z, S = 0x01, 0x02, 0x04, 0x10, 0x40, 0x80
F5, F3 = 0x20, 0x08


class Halt(Exception):
    pass


class Z80:
    def __init__(self, memory: bytearray, port_out=None, port_in=None):
        assert len(memory) == 65536
        self.m = memory
        self.port_out = port_out or (lambda p, v: None)
        self.port_in = port_in or (lambda p: 0xFF)
        self.a = self.f = 0
        self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.a_ = self.f_ = self.b_ = self.c_ = self.d_ = self.e_ = self.h_ = self.l_ = 0
        self.ix = self.iy = 0
        self.sp = 0
        self.pc = 0
        self.i = self.r = 0
        self.iff1 = self.iff2 = False
        self.im = 0
        self.halted = False
        self.tstates = 0
        self.trace: list[tuple[int, str, str]] = []
        self._fetch_count = 0
        self._prefix = 0          # 0 / 0xCB / 0xED / 0xDD / 0xFD
        self._xy = 0              # current IX/IY index register
        self._displacement = 0

    # ------------------------------------------------------------ helpers
    def _rd(self, addr: int) -> int:
        return self.m[addr & 0xFFFF]

    def _wr(self, addr: int, val: int) -> None:
        self.m[addr & 0xFFFF] = val & 0xFF

    def _rd16(self, addr: int) -> int:
        return self._rd(addr) | (self._rd(addr + 1) << 8)

    def _wr16(self, addr: int, val: int) -> None:
        self._wr(addr, val & 0xFF)
        self._wr(addr + 1, (val >> 8) & 0xFF)

    def _push(self, val: int) -> None:
        self.sp = (self.sp - 1) & 0xFFFF
        self._wr(self.sp, (val >> 8) & 0xFF)
        self.sp = (self.sp - 1) & 0xFFFF
        self._wr(self.sp, val & 0xFF)

    def _pop(self) -> int:
        lo = self._rd(self.sp)
        hi = self._rd(self.sp + 1)
        self.sp = (self.sp + 2) & 0xFFFF
        return lo | (hi << 8)

    def _fetch(self) -> int:
        v = self._rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        self._fetch_count += 1
        return v

    # register get/set by r-index; prefix 0xDD/0xFD remap 4/5 -> IXH/IXL
    def _get_r(self, r: int) -> int:
        if self._prefix in (0xDD, 0xFD):
            if r == 4:
                return (self._xy >> 8) & 0xFF
            if r == 5:
                return self._xy & 0xFF
        if r == 6:
            return self._rd(self._hl_addr())
        return (self.b, self.c, self.d, self.e, self.h, self.l, 0, self.a)[r]

    def _set_r(self, r: int, v: int) -> None:
        v &= 0xFF
        if self._prefix in (0xDD, 0xFD):
            if r == 4:
                self._xy = (self._xy & 0x00FF) | (v << 8)
                return
            if r == 5:
                self._xy = (self._xy & 0xFF00) | v
                return
        if r == 6:
            self._wr(self._hl_addr(), v)
            return
        if r == 0:
            self.b = v
        elif r == 1:
            self.c = v
        elif r == 2:
            self.d = v
        elif r == 3:
            self.e = v
        elif r == 7:
            self.a = v
        else:  # r == 4/5 unprefixed -> H/L
            if r == 4:
                self.h = v
            else:
                self.l = v

    def _hl_addr(self) -> int:
        if self._prefix in (0xDD, 0xFD):
            return (self._xy + self._displacement) & 0xFFFF
        return (self.h << 8) | self.l

    def _get_rp(self, p: int) -> int:
        if self._prefix in (0xDD, 0xFD) and p == 2:
            return self._xy
        return (self.bc(), self.de(), self._hl16(), self.sp)[p]

    def _set_rp(self, p: int, v: int) -> None:
        v &= 0xFFFF
        if self._prefix in (0xDD, 0xFD) and p == 2:
            self._xy = v
            return
        if p == 0:
            self.b, self.c = v >> 8, v & 0xFF
        elif p == 1:
            self.d, self.e = v >> 8, v & 0xFF
        elif p == 2:
            self.h, self.l = v >> 8, v & 0xFF
        else:
            self.sp = v

    def _get_rp2(self, p: int) -> int:
        if self._prefix in (0xDD, 0xFD) and p == 2:
            return self._xy
        return (self.bc(), self.de(), self._hl16(), self.af())[p]

    def _set_rp2(self, p: int, v: int) -> None:
        v &= 0xFFFF
        if self._prefix in (0xDD, 0xFD) and p == 2:
            self._xy = v
            return
        if p == 0:
            self.b, self.c = v >> 8, v & 0xFF
        elif p == 1:
            self.d, self.e = v >> 8, v & 0xFF
        elif p == 2:
            self.h, self.l = v >> 8, v & 0xFF
        else:
            self.a, self.f = v >> 8, v & 0xFF

    # 16-bit pair views
    def bc(self):
        return (self.b << 8) | self.c

    def de(self):
        return (self.d << 8) | self.e

    def _hl16(self):
        return (self.h << 8) | self.l

    def af(self):
        return (self.a << 8) | self.f

    # ------------------------------------------------------------ flags
    def _sz53(self, v: int) -> None:
        """set S, Z, F5, F3 from 8-bit v; clears H/N/PV/C caller-side."""
        self.f &= ~(S | Z | F5 | F3)
        self.f |= v & (F5 | F3)
        if v == 0:
            self.f |= Z
        if v & 0x80:
            self.f |= S

    def _parity(self, v: int) -> int:
        return P if bin(v & 0xFF).count("1") % 2 == 0 else 0

    # ------------------------------------------------------------ ALU
    def _alu(self, y: int, operand: int) -> None:
        a = self.a
        if y == 0:    # ADD
            r = a + operand
            self.f = (r & (F5 | F3)) | (H_ if (a ^ operand ^ r) & 0x10 else 0)
            if r == 0:
                self.f |= Z
            if r & 0x80:
                self.f |= S
            if r & 0x100:
                self.f |= C
            self.f |= self._parity(((a ^ operand ^ r) >> 8) & 0xFF) & P if False else 0
            # V = carry into bit7 != carry out of bit7
            v = (~(a ^ operand) & (a ^ r) & 0x80)
            if v:
                self.f |= P
            self.a = r & 0xFF
        elif y == 1:  # ADC
            carry = 1 if self.f & C else 0
            r = a + operand + carry
            self.f = (r & (F5 | F3)) | (H_ if (a ^ operand ^ r) & 0x10 else 0)
            if r == 0:
                self.f |= Z
            if r & 0x80:
                self.f |= S
            if r & 0x100:
                self.f |= C
            v = (~(a ^ operand) & (a ^ r) & 0x80)
            if v:
                self.f |= P
            self.a = r & 0xFF
        elif y == 2:  # SUB
            r = a - operand
            self.f = N_ | (r & (F5 | F3))
            if (a ^ operand ^ r) & 0x10:
                self.f |= H_
            if r == 0:
                self.f |= Z
            if r & 0x80:
                self.f |= S
            if r & 0x100:
                self.f |= C
            if (a ^ operand) & (a ^ r) & 0x80:
                self.f |= P
            self.a = r & 0xFF
        elif y == 3:  # SBC
            carry = 1 if self.f & C else 0
            r = a - operand - carry
            self.f = N_ | (r & (F5 | F3))
            if (a ^ operand ^ r) & 0x10:
                self.f |= H_
            if r == 0:
                self.f |= Z
            if r & 0x80:
                self.f |= S
            if r & 0x100:
                self.f |= C
            if (a ^ operand) & (a ^ r) & 0x80:
                self.f |= P
            self.a = r & 0xFF
        elif y == 4:  # AND
            self.a = a & operand
            self.f = self._parity(self.a) | H_ | (self.a & (F5 | F3))
            if self.a == 0:
                self.f |= Z
            if self.a & 0x80:
                self.f |= S
        elif y == 5:  # XOR
            self.a = a ^ operand
            self.f = self._parity(self.a) | (self.a & (F5 | F3))
            if self.a == 0:
                self.f |= Z
            if self.a & 0x80:
                self.f |= S
        elif y == 6:  # OR
            self.a = a | operand
            self.f = self._parity(self.a) | (self.a & (F5 | F3))
            if self.a == 0:
                self.f |= Z
            if self.a & 0x80:
                self.f |= S
        else:         # CP
            r = a - operand
            self.f = N_ | (r & (F5 | F3)) | S if r & 0x80 else N_ | (r & (F5 | F3))
            self.f = N_ | (operand & (F5 | F3))
            if (a ^ operand ^ r) & 0x10:
                self.f |= H_
            if r == 0:
                self.f |= Z
            if r & 0x80:
                self.f |= S
            if r & 0x100:
                self.f |= C
            if (a ^ operand) & (a ^ r) & 0x80:
                self.f |= P

    def _inc8(self, v: int) -> int:
        r = (v + 1) & 0xFF
        self.f = (self.f & C) | (r & (F5 | F3))
        if (v & 0x0F) == 0x0F:
            self.f |= H_
        if r == 0:
            self.f |= Z
        if r & 0x80:
            self.f |= S
        if v == 0x7F:
            self.f |= P
        return r

    def _dec8(self, v: int) -> int:
        r = (v - 1) & 0xFF
        self.f = (self.f & C) | N_ | (r & (F5 | F3))
        if (v & 0x0F) == 0x00:
            self.f |= H_
        if r == 0:
            self.f |= Z
        if r & 0x80:
            self.f |= S
        if v == 0x80:
            self.f |= P
        return r

    def _rot(self, y: int, v: int, use_carry: bool) -> int:
        c = 1 if self.f & C else 0
        if y == 0:    # RLC
            r = ((v << 1) | (v >> 7)) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v >> 7) | (r & (F5 | F3))
            self.f |= self._parity(r) if use_carry else 0
            return r
        if y == 1:    # RRC
            r = ((v >> 1) | (v << 7)) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v & 1) | (r & (F5 | F3))
            return r
        if y == 2:    # RL
            r = ((v << 1) | c) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v >> 7) | (r & (F5 | F3))
            return r
        if y == 3:    # RR
            r = ((v >> 1) | (c << 7)) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v & 1) | (r & (F5 | F3))
            return r
        if y == 4:    # SLA
            r = (v << 1) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v >> 7) | (r & (F5 | F3))
            return r
        if y == 5:    # SRA
            r = ((v >> 1) | (v & 0x80)) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v & 1) | (r & (F5 | F3))
            return r
        if y == 6:    # SLL (undocumented)
            r = ((v << 1) | 1) & 0xFF
            self.f = (self.f & ~(C | F5 | F3)) | (v >> 7) | (r & (F5 | F3))
            return r
        # SRL
        r = v >> 1
        self.f = (self.f & ~(C | F5 | F3)) | (v & 1) | (r & (F5 | F3))
        return r

    def _bit(self, y: int, r: int, v: int) -> None:
        if y == 1:    # BIT
            self.f = (self.f & C) | H_ | (v & (F5 | F3))
            if y == 1 and not (v & (1 << r)):
                self.f |= Z | P
            if r == 7 and v & 0x80:
                self.f |= S
        elif y == 2:  # RES
            self._set_r(r, v & ~(1 << r))
        elif y == 3:  # SET
            self._set_r(r, v | (1 << r))

    # ------------------------------------------------------------ DAA
    def _daa(self) -> None:
        a = self.a
        correction = 0
        carry = self.f & C
        if self.f & H_ or (a & 0x0F) > 9:
            correction |= 0x06
        if carry or a > 0x99:
            correction |= 0x60
            carry = C
        else:
            carry = 0
        if self.f & N_:
            a = (a - correction) & 0xFF
            self.f = (self.f & ~(C | H_)) | carry
            if ((self.a ^ correction ^ a) & 0x10):
                self.f |= H_
        else:
            a = (a + correction) & 0xFF
            self.f = (self.f & ~(C | H_)) | carry
            if ((self.a ^ correction ^ a) & 0x10):
                self.f |= H_
        self.a = a
        self.f = (self.f & ~(S | Z | F5 | F3)) | (a & (F5 | F3))
        if a == 0:
            self.f |= Z
        if a & 0x80:
            self.f |= S
        self.f |= self._parity(a)

    # ------------------------------------------------------------ block ops
    def _block(self, kind: int, repeat_: bool, inc_dec: int) -> None:
        """kind: 0=LDI 1=CPI 2=INI 3=OUTI ; repeat_ adds the R and loop."""
        if kind == 0:
            v = self._rd(self._hl16())
            self._wr(self.de(), v)
            t = (self.bc() - 1) & 0xFFFF
            self._set_rp(0, t)
            n = v + self.a
            self.f &= ~(H_ | N_ | F5 | F3 | P)
            self.f |= F3 if n & 0x08 else 0
            self.f |= F5 if n & 0x02 else 0
            if inc_dec:
                self._set_rp(2, (self._hl16() + 1) & 0xFFFF)
                self._set_rp(1, (self.de() + 1) & 0xFFFF)
            else:
                self._set_rp(2, (self._hl16() - 1) & 0xFFFF)
                self._set_rp(1, (self.de() - 1) & 0xFFFF)
            if t:
                self.f |= P
            self.tstates += 21 if repeat_ else 16
            if repeat_ and t:
                self.pc = (self.pc - 2) & 0xFFFF
                self.tstates += 5
        elif kind == 1:
            v = self._rd(self._hl16())
            r = (self.a - v) & 0xFF
            t = (self.bc() - 1) & 0xFFFF
            self._set_rp(0, t)
            self.f &= ~(F5 | F3 | P | N_)
            self.f |= N_ | (r & (F5 | F3))
            if (self.a ^ v ^ r) & 0x10:
                self.f |= H_
            if r == 0:
                self.f |= Z
            if t:
                self.f |= P
            if inc_dec:
                self._set_rp(2, (self._hl16() + 1) & 0xFFFF)
            else:
                self._set_rp(2, (self._hl16() - 1) & 0xFFFF)
            self.tstates += 21 if repeat_ else 16
            if repeat_ and t and not (self.f & Z):
                self.pc = (self.pc - 2) & 0xFFFF
                self.tstates += 5
        else:
            # INI/IND/OUTI/OUTD (kind 2/3): basic modelled behaviour
            port = (self.b << 8) | ((self.c - 1) & 0xFF if not inc_dec else (self.c + 1) & 0xFF)
            if kind == 2:
                v = self.port_in((self.b << 8) | self.c)
                self._wr(self._hl16(), v)
                self.b = self._dec8(self.b)
            else:
                v = self._rd(self._hl16())
                self.port_out((self.b << 8) | self.c, v)
                self.b = self._dec8(self.b)
            if inc_dec:
                self._set_rp(2, (self._hl16() + 1) & 0xFFFF)
            else:
                self._set_rp(2, (self._hl16() - 1) & 0xFFFF)
            self.tstates += 16
            if repeat_ and self.b:
                self.pc = (self.pc - 2) & 0xFFFF

    # ------------------------------------------------------------ step
    def step(self) -> tuple[int, str, str]:
        """Execute one instruction. Returns (pc, hex_bytes, mnemonic)."""
        start_pc = self.pc
        self._fetch_count = 0
        self.r = (self.r & 0x7F) | ((self.r + 1) & 0x7F)

        op = self._fetch()
        raw = [op]
        self._prefix = 0
        self._xy = 0
        self._displacement = 0
        if op in (0xDD, 0xFD):
            self._prefix = op
            self._xy = self.ix if op == 0xDD else self.iy
            op2 = self._fetch()
            raw.append(op2)
            if op2 == 0xCB:
                self._displacement = self._fetch()
                if self._displacement & 0x80:
                    self._displacement -= 0x100
                op3 = self._fetch()
                raw.append(op3)
                self._exec_cb(op3)
                self._store_xy()
                return self._ret_trace(start_pc, raw, 0)
            op = op2
        elif op == 0xCB:
            op2 = self._fetch()
            raw.append(op2)
            self._exec_cb(op2)
            return self._ret_trace(start_pc, raw, 0)
        elif op == 0xED:
            op2 = self._fetch()
            raw.append(op2)
            self._exec_ed(op2)
            return self._ret_trace(start_pc, raw, 0)

        try:
            self._exec_base(op)
        except Halt:
            self._ret_trace(start_pc, raw, 0)
            raise
        self._store_xy()
        return self._ret_trace(start_pc, raw, 0)

    def _store_xy(self) -> None:
        if self._prefix == 0xDD:
            self.ix = self._xy
        elif self._prefix == 0xFD:
            self.iy = self._xy

    def _ret_trace(self, pc: int, raw: list[int], t0: int) -> tuple[int, str, str]:
        # instruction bytes: exactly what was fetched (jump targets excluded)
        end = (pc + self._fetch_count) & 0xFFFF
        if end >= pc:
            blob = bytes(self.m[pc:end])
        else:  # 16-bit wrap
            blob = bytes(self.m[pc:0x10000]) + bytes(self.m[0:end])
        hexs = "".join(f"{b:02X}" for b in blob)
        mn = self._last_mnemonic
        self.trace.append((pc, hexs, mn))
        # nominal T-states: 4 per byte + 7 for a taken control transfer
        seq_next = end
        self.tstates += 4 * len(blob) + (7 if self.pc != seq_next else 0)
        return pc, hexs, mn

    def _imm8(self) -> int:
        return self._fetch()

    def _imm16(self) -> int:
        lo = self._fetch()
        hi = self._fetch()
        return lo | (hi << 8)

    # ------------------------------------------------------------ base set
    def _exec_base(self, op: int) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        self._last_mnemonic = f"db {op:02X}h"
        if op == 0x76:  # HALT
            self._last_mnemonic = "HALT"
            raise Halt()

        if x == 1:  # LD r,r' / LD r,n / LD (HL),n / HALT handled above
            if z == 6 and y == 6:
                v = self._imm8()
                self._set_r(6, v)
                self._last_mnemonic = f"LD (HL),{v:02X}h"
                return
            v = self._get_r(z)
            self._set_r(y, v)
            self._last_mnemonic = f"LD r{y},r{z}"
            return

        if x == 0:
            if z == 0:
                if y == 0:
                    self._last_mnemonic = "NOP"
                elif y == 1:  # EX AF,AF'
                    self.a, self.a_ = self.a_, self.a
                    self.f, self.f_ = self.f_, self.f
                    self._last_mnemonic = "EX AF,AF'"
                    return
                elif y == 2:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    self.b = (self.b - 1) & 0xFF
                    self._last_mnemonic = "DJNZ"
                    if self.b:
                        self.pc = (self.pc + d) & 0xFFFF
                    return
                elif y == 3:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    self.pc = (self.pc + d) & 0xFFFF
                    self._last_mnemonic = f"JR {d:+d}"
                    return
                elif y == 4:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    if not (self.f & Z):
                        self.pc = (self.pc + d) & 0xFFFF
                    self._last_mnemonic = "JR NZ"
                    return
                elif y == 5:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    if self.f & Z:
                        self.pc = (self.pc + d) & 0xFFFF
                    self._last_mnemonic = "JR Z"
                    return
                elif y == 6:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    if not (self.f & C):
                        self.pc = (self.pc + d) & 0xFFFF
                    self._last_mnemonic = "JR NC"
                    return
                else:
                    d = self._imm8()
                    if d & 0x80:
                        d -= 0x100
                    if self.f & C:
                        self.pc = (self.pc + d) & 0xFFFF
                    self._last_mnemonic = "JR C"
                    return
            elif z == 1:
                if q == 0:  # LD rp,nn
                    self._set_rp(p, self._imm16())
                    self._last_mnemonic = f"LD rp{p},nn"
                    return
                else:      # ADD HL,rp
                    hl = self._hl16()
                    operand = self._get_rp(p)
                    r = hl + operand
                    self.f &= ~(H_ | N_ | C)
                    if (hl ^ operand ^ r) & 0x1000:
                        self.f |= H_
                    if r & 0x10000:
                        self.f |= C
                    self.f |= (r >> 8) & (F5 | F3)
                    self._set_rp(2, r & 0xFFFF)
                    self._last_mnemonic = f"ADD HL,rp{p}"
                    return
            elif z == 2:
                # p=y>>1 selects the operand: p=0 (BC), p=1 (DE), p=2 (nn)+HL, p=3 (nn)+A
                if q == 0:
                    if p < 2:
                        self._wr(self._get_rp(p), self.a)
                        self._last_mnemonic = f"LD (rp{p}),A"
                    elif p == 2:
                        nn = self._imm16()
                        self._wr16(nn, self._hl16())
                        self._last_mnemonic = f"LD ({nn:04X}h),HL"
                    else:
                        nn = self._imm16()
                        self._wr(nn, self.a)
                        self._last_mnemonic = f"LD ({nn:04X}h),A"
                else:
                    if p < 2:
                        self.a = self._rd(self._get_rp(p))
                        self._last_mnemonic = f"LD A,(rp{p})"
                    elif p == 2:
                        nn = self._imm16()
                        self._set_rp(2, self._rd16(nn))
                        self._last_mnemonic = f"LD HL,({nn:04X}h)"
                    else:
                        nn = self._imm16()
                        self.a = self._rd(nn)
                        self._last_mnemonic = f"LD A,({nn:04X}h)"
                return
            elif z == 3:
                self._set_rp(p, self._get_rp(p) + (1 if q == 0 else -1) & 0xFFFF)
                self._last_mnemonic = f"{'INC' if q == 0 else 'DEC'} rp{p}"
                return
            elif z == 4:  # INC r
                self._set_r(y, self._inc8(self._get_r(y)))
                self._last_mnemonic = f"INC r{y}"
                return
            elif z == 5:  # DEC r
                self._set_r(y, self._dec8(self._get_r(y)))
                self._last_mnemonic = f"DEC r{y}"
                return
            elif z == 6:  # LD r,n
                v = self._imm8()
                self._set_r(y, v)
                self._last_mnemonic = f"LD r{y},{v:02X}h"
                return
            else:  # z == 7
                ops = ("RLCA", "RRCA", "RLA", "RRA", "DAA", "CPL", "SCF", "CCF")
                self._last_mnemonic = ops[y]
                if y == 0:
                    self.a = self._rot(0, self.a, False)
                elif y == 1:
                    self.a = self._rot(1, self.a, False)
                elif y == 2:
                    self.a = self._rot(2, self.a, True)
                elif y == 3:
                    self.a = self._rot(3, self.a, True)
                elif y == 4:
                    self._daa()
                elif y == 5:
                    self.a ^= 0xFF
                    self.f = (self.f & ~(F5 | F3 | H_ | N_)) | (self.a & (F5 | F3)) | H_ | N_
                elif y == 6:
                    self.f = (self.f & ~(F5 | F3)) | ((self.a | (self.f & (C | P))) & (F5 | F3)) | C
                else:
                    self.f ^= C
                    self.f = (self.f & ~(F5 | F3)) | ((self.a | (self.f & (C | P))) & (F5 | F3))
                return
            return

        if x == 2:  # ALU A,r
            self._alu(y, self._get_r(z))
            names = ("ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR", "CP")
            self._last_mnemonic = f"{names[y]} A,r{z}"
            return

        # x == 3
        if z == 0:  # RET cc
            cc = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
            cond = self._cc(y)
            if cond:
                self.pc = self._pop()
            self._last_mnemonic = f"RET {cc[y]}"
            return
        if z == 1:
            if q == 0:
                v = self._pop()
                if p == 2:
                    self.h, self.l = v >> 8, v & 0xFF
                elif p == 0:
                    self.b, self.c = v >> 8, v & 0xFF
                elif p == 1:
                    self.d, self.e = v >> 8, v & 0xFF
                else:
                    self.a, self.f = v >> 8, v & 0xFF
                self._last_mnemonic = f"POP rp2{p}"
                return
            else:
                cc = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
                if p == 0:
                    self.pc = self._pop()
                    self._last_mnemonic = "RET"
                    return
                elif p == 1:
                    self._last_mnemonic = "EXX"
                    self.b, self.b_ = self.b_, self.b
                    self.c, self.c_ = self.c_, self.c
                    self.d, self.d_ = self.d_, self.d
                    self.e, self.e_ = self.e_, self.e
                    self.h, self.h_ = self.h_, self.h
                    self.l, self.l_ = self.l_, self.l
                    return
                elif p == 2:
                    self.pc = self._hl16()
                    self._last_mnemonic = "JP (HL)"
                    return
                else:
                    self.sp = self._hl16()
                    self._last_mnemonic = "LD SP,HL"
                    return
        if z == 2:  # JP cc,nn
            nn = self._imm16()
            cc = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
            if self._cc(y):
                self.pc = nn
            self._last_mnemonic = f"JP {cc[y]},{nn:04X}h"
            return
        if z == 3:
            if y == 0:
                self.pc = self._imm16()
                self._last_mnemonic = "JP nn"
                return
            if y == 1:  # CB prefix (handled elsewhere; unreachable here)
                return
            if y == 2:  # OUT (n),A
                n = self._imm8()
                self.port_out((self.a << 8) | n, self.a)
                self._last_mnemonic = f"OUT ({n:02X}h),A"
                return
            if y == 3:  # IN A,(n)
                n = self._imm8()
                self.a = self.port_in((self.a << 8) | n)
                self._last_mnemonic = f"IN A,({n:02X}h)"
                return
            if y == 4:  # EX (SP),HL
                lo = self._rd(self.sp)
                hi = self._rd((self.sp + 1) & 0xFFFF)
                self._wr(self.sp, self.l)
                self._wr((self.sp + 1) & 0xFFFF, self.h)
                self.l, self.h = lo, hi
                self._last_mnemonic = "EX (SP),HL"
                return
            if y == 5:  # EX DE,HL
                self.d, self.e, self.h, self.l = self.h, self.l, self.d, self.e
                self._last_mnemonic = "EX DE,HL"
                return
            if y == 6:
                self.f &= ~H_ if False else self.f  # no-op guard
                self.f &= ~H_
                self.f &= ~N_
                self._last_mnemonic = "DI"
                self.iff1 = self.iff2 = False
                return
            else:
                self.iff1 = self.iff2 = True
                self._last_mnemonic = "EI"
                return
        if z == 4:  # CALL cc,nn
            nn = self._imm16()
            cc = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
            if self._cc(y):
                self._push(self.pc)
                self.pc = nn
            self._last_mnemonic = f"CALL {cc[y]},{nn:04X}h"
            return
        if z == 5:
            if q == 0:
                self._push(self._get_rp(p))
                self._last_mnemonic = f"PUSH rp2{p}"
                return
            if p == 0:
                nn = self._imm16()
                self._push(self.pc)
                self.pc = nn
                self._last_mnemonic = f"CALL {nn:04X}h"
                return
            # DD/ED/FD prefixes are intercepted in step(); here treat as NOP
            self._last_mnemonic = "NOP*"
            return
        if z == 6:  # ALU A,n
            v = self._imm8()
            names = ("ADD", "ADC", "SUB", "SBC", "AND", "XOR", "OR", "CP")
            self._alu(y, v)
            self._last_mnemonic = f"{names[y]} A,{v:02X}h"
            return
        # z == 7: RST
        self._push(self.pc)
        self.pc = y * 8
        self._last_mnemonic = f"RST {y*8:02X}h"
        return

    def _cc(self, y: int) -> bool:
        return (
            y == 0 and not (self.f & Z) or
            y == 1 and (self.f & Z) or
            y == 2 and not (self.f & C) or
            y == 3 and (self.f & C) or
            y == 4 and not (self.f & P) or
            y == 5 and (self.f & P) or
            y == 6 and not (self.f & S) or
            y == 7 and (self.f & S)
        )

    # ------------------------------------------------------------ CB set
    def _exec_cb(self, op: int) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        if x == 0:  # rot/shift
            v = self._get_r(z)
            r = self._rot(y, v, False)
            self._set_r(z, r)
            names = ("RLC", "RRC", "RL", "RR", "SLA", "SRA", "SLL", "SRL")
            self._last_mnemonic = f"{names[y]} r{z}"
            return
        if x == 1:  # BIT
            v = self._get_r(z)
            self.f = (self.f & C) | H_
            if not (v & (1 << y)):
                self.f |= Z | P
            if y == 7 and v & 0x80:
                self.f |= S
            self.f |= v & (F5 | F3)
            self._last_mnemonic = f"BIT {y},r{z}"
            return
        if x == 2:  # RES
            v = self._get_r(z)
            self._set_r(z, v & ~(1 << y))
            self._last_mnemonic = f"RES {y},r{z}"
            return
        # SET
        v = self._get_r(z)
        self._set_r(z, v | (1 << y))
        self._last_mnemonic = f"SET {y},r{z}"

    # ------------------------------------------------------------ ED set
    def _exec_ed(self, op: int) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        self._last_mnemonic = f"ED {op:02X}h"
        if x == 1:
            if z == 0:  # IN r,(C) / OUT (C),r
                v = self.port_in(self.bc())
                if y != 6:
                    self._set_r(y, v)
                    self._last_mnemonic = f"IN r{y},(C)"
                else:
                    self._last_mnemonic = "IN (C)"  # flags only
                self.f = (self.f & C) | (v & (F5 | F3))
                self.f |= self._parity(v)
                if v & 0x80:
                    self.f |= S
                if v == 0:
                    self.f |= Z
                self.f &= ~N_
                return
            if z == 1:
                if q == 0:
                    self.port_out(self.bc(), 0 if y == 6 else self._get_r(y))
                    self._last_mnemonic = "OUT (C),0" if y == 6 else f"OUT (C),r{y}"
                    return
                # SBC/ADC HL,rp
                hl = self._hl16()
                operand = self._get_rp(p)
                if y in (2, 6) or (y >> 1) == 1 and False:
                    pass
                is_sbc = y in (2, 3, 6, 7)
                if is_sbc:
                    carry = 1 if self.f & C else 0
                    r = hl - operand - carry
                    self.f = N_
                    if ((hl ^ operand ^ r) & 0x1000):
                        self.f |= H_
                    if r == 0:
                        self.f |= Z
                    if r & 0x8000:
                        self.f |= S
                    if r & 0x10000:
                        self.f |= C
                    if (hl ^ operand) & (hl ^ r) & 0x8000:
                        self.f |= P
                else:
                    carry = 1 if self.f & C else 0
                    r = hl + operand + carry
                    self.f = 0
                    if ((hl ^ operand ^ r) & 0x1000):
                        self.f |= H_
                    if r == 0:
                        self.f |= Z
                    if r & 0x8000:
                        self.f |= S
                    if r & 0x10000:
                        self.f |= C
                    if (~(hl ^ operand) & (hl ^ r) & 0x8000):
                        self.f |= P
                self.f |= (r >> 8) & (F5 | F3)
                self._set_rp(2, r & 0xFFFF)
                self._last_mnemonic = ("SBC" if is_sbc else "ADC") + f" HL,rp{p}"
                return
            if z == 2:
                nn = self._imm16()
                if q == 0:
                    self._wr16(nn, self._get_rp(p))
                    self._last_mnemonic = f"LD ({nn:04X}h),rp{p}"
                else:
                    self._set_rp(p, self._rd16(nn))
                    self._last_mnemonic = f"LD rp{p},({nn:04X}h)"
                return
            if z == 3:
                if q == 0:
                    self._set_rp(p, self._get_rp(p) + 1 & 0xFFFF)
                    self._last_mnemonic = f"INC rp{p}*"
                else:
                    self._set_rp(p, self._get_rp(p) - 1 & 0xFFFF)
                    self._last_mnemonic = f"DEC rp{p}*"
                return
            if z == 4:  # NEG
                a = self.a
                self._alu(2, self.a)
                self._last_mnemonic = "NEG"
                return
            if z == 5:
                if y == 1:
                    self.pc = self._pop()
                    self.iff1 = self.iff2
                    self._last_mnemonic = "RETN"
                    return
                self._last_mnemonic = "RETI"
                self.pc = self._pop()
                return
            if z == 6:
                im_mode = (0, 0, 1, 2, 0, 0, 1, 2)[y]
                self.im = im_mode
                self._last_mnemonic = f"IM {im_mode}"
                return
            if z == 7:
                ld_map = {0: ("LD I,A", lambda: setattr(self, "i", self.a)),
                          1: ("LD R,A", lambda: setattr(self, "r", self.a)),
                          2: ("LD A,I", None), 3: ("LD A,R", None),
                          4: ("RRD", None), 5: ("RLD", None), 6: ("NOP*", None), 7: ("NOP*", None)}
                if y == 0:
                    self.i = self.a
                    self._last_mnemonic = "LD I,A"
                elif y == 1:
                    self.r = self.a
                    self._last_mnemonic = "LD R,A"
                elif y == 2:
                    self.a = self.i
                    self.f = (self.f & C) | (self.a & (F5 | F3))
                    self.f |= self._parity(self.a)
                    if self.a == 0:
                        self.f |= Z
                    if self.a & 0x80:
                        self.f |= S
                    if self.iff2:
                        self.f |= P
                    self.f &= ~H_ | N_ if False else self.f
                    self.f &= ~(H_ | N_)
                    self._last_mnemonic = "LD A,I"
                elif y == 3:
                    self.a = self.r
                    self.f = (self.f & C) | (self.a & (F5 | F3))
                    self.f |= self._parity(self.a)
                    if self.a == 0:
                        self.f |= Z
                    if self.a & 0x80:
                        self.f |= S
                    if self.iff2:
                        self.f |= P
                    self.f &= ~(H_ | N_)
                    self._last_mnemonic = "LD A,R"
                elif y == 4:  # RRD
                    m = self._rd(self._hl16())
                    lo = self.a & 0x0F
                    self.a = (self.a & 0xF0) | (m & 0x0F)
                    self._wr(self._hl16(), ((m >> 4) | (lo << 4)) & 0xFF)
                    self._sz53(self.a)
                    self.f |= self._parity(self.a)
                    self._last_mnemonic = "RRD"
                elif y == 5:  # RLD
                    m = self._rd(self._hl16())
                    lo = self.a & 0x0F
                    self.a = (self.a & 0xF0) | (m >> 4)
                    self._wr(self._hl16(), ((m << 4) | lo) & 0xFF)
                    self._sz53(self.a)
                    self.f |= self._parity(self.a)
                    self._last_mnemonic = "RLD"
                else:
                    self._last_mnemonic = "NOP*"
                return
            return
        if x == 2 and y >= 4:  # block instructions
            # z selects the instruction: 0=LDI 1=CPI 2=INI 3=OUTI
            # y selects the variant: 4=base 5=decrement 6=repeat 7=repeat+decrement
            kind = z
            repeat_ = bool(y & 2)
            inc_dec = (y & 1) == 0
            self._block(kind, repeat_, inc_dec)
            names = ("LDI", "CPI", "INI", "OUTI")
            self._last_mnemonic = names[kind] + ("R" if repeat_ else "") + ("" if inc_dec else "D")
            return
        # remaining ED slots: modelled as 8T NOPs
        self._last_mnemonic = "NOP*"


# ---------------------------------------------------------------- selftest
def _selftest() -> int:
    """Known-answer tests from documented Z80 semantics (independent of
    any assembler). Each case: (setup, code bytes, expected checks)."""
    failures = []

    def fresh(code: bytes, a=0, f=0, b=0, c=0, d=0, e=0, h=0, l=0, sp=0xF000):
        mem = bytearray(65536)
        mem[0:len(code)] = code
        z = Z80(mem)
        z.a, z.f, z.b, z.c, z.d, z.e, z.h, z.l, z.sp = a, f, b, c, d, e, h, l, sp
        return z

    cases = []

    # 1. LD A,n : 3E 42 -> A=0x42, F unchanged pattern
    z = fresh(b"\x3E\x42")
    z.step()
    cases.append(("LD A,n", z.a == 0x42 and z.pc == 2))

    # 2. ADD A,B : A=0x0F + B=0x01 = 0x10, H set, C clear
    z = fresh(b"\x80", a=0x0F, b=0x01)
    z.step()
    cases.append(("ADD A,B H", z.a == 0x10 and (z.f & H_) and not (z.f & C) and not (z.f & Z)))

    # 3. ADD A,B overflow: 0x7F+0x01=0x80 -> S set, V(P) set, H set
    z = fresh(b"\x80", a=0x7F, b=0x01)
    z.step()
    cases.append(("ADD A,B V", z.a == 0x80 and (z.f & S) and (z.f & P) and (z.f & H_)))

    # 4. SUB: 0x00-0x01 -> N set, H set, C set, Z clear
    z = fresh(b"\x90", a=0x00, b=0x01)
    z.step()
    cases.append(("SUB", z.a == 0xFF and (z.f & N_) and (z.f & H_) and (z.f & C)))

    # 5. INC (HL) on memory 0xFF -> 0x00, Z set, H set
    z = fresh(b"\x34", h=0x12, l=0x34)
    z.m[0x1234] = 0xFF
    z.step()
    cases.append(("INC (HL)", z.m[0x1234] == 0x00 and (z.f & Z) and (z.f & H_)))

    # 6. DJNZ taken/not-taken: B=2 -> B=1, jump taken (PC=0x0005)
    z = fresh(b"\x10\x03\x00\x00\xC9", b=2)
    z.step()
    cases.append(("DJNZ taken", z.b == 1 and z.pc == 5))
    z = fresh(b"\x10\x03\x00\x00\xC9", b=1)
    z.step()
    cases.append(("DJNZ fallthrough", z.b == 0 and z.pc == 2))

    # 7. LD (nn),A / LD A,(nn) roundtrip
    z = fresh(b"\x32\x00\x20\x3A\x00\x20", a=0xA5)
    z.step(); z.step()
    cases.append(("LD (nn),A", z.m[0x2000] == 0xA5 and z.a == 0xA5))

    # 8. OUT (n),A drives port hook
    z = fresh(b"\xD3\x07", a=0x5A)
    seen = []
    z.port_out = lambda p, v: seen.append((p, v))
    z.step()
    cases.append(("OUT (n),A", seen == [((0x5A << 8) | 0x07, 0x5A)]))

    # 9. CB rotate RLC B: B=0x81 -> 0x03, C set
    z = fresh(b"\xCB\x00", b=0x81)
    z.step()
    cases.append(("RLC B", z.b == 0x03 and (z.f & C)))

    # 10. BIT 7,A on A=0x80 -> Z clear
    z = fresh(b"\xCB\x7F", a=0x80)
    z.step()
    cases.append(("BIT 7,A hit", not (z.f & Z)))
    z = fresh(b"\xCB\x7F", a=0x7F)
    z.step()
    cases.append(("BIT 7,A miss", (z.f & Z) and (z.f & P) and (z.f & H_)))

    # 11. CALL/RET: CALL 0x0010 pushes return addr; RET returns
    code = b"\xCD\x10\x00\xC9" + b"\x00" * 12 + b"\xC9"
    z = fresh(code)
    z.step()  # CALL
    cases.append(("CALL push", z.pc == 0x10 and z.sp == 0xEFFE and z._rd(0xEFFE) == 0x03))
    z.step()  # RET
    cases.append(("RET pop", z.pc == 0x03 and z.sp == 0xF000))

    # 12. DAA after ADD: 0x09+0x08=0x11 -> DAA -> 0x11 (no correction)
    z = fresh(b"\x27", a=0x11)
    z.f = 0  # Z clear, H clear, N clear
    z.step()
    cases.append(("DAA bcd", z.a == 0x11 and not (z.f & H_)))
    # 0x0A + 0x03 = 0x0D -> DAA -> 0x13
    z = fresh(b"\x27", a=0x0D)
    z.f = 0
    z.step()
    cases.append(("DAA bcd2", z.a == 0x13))

    # 13. RLCA: A=0x80 -> 0x01, C set, other flags untouched
    z = fresh(b"\x07", a=0x80, f=S)
    z.step()
    cases.append(("RLCA", z.a == 0x01 and (z.f & C) and (z.f & S)))

    # 14. LDIR copies 3 bytes over 3 steps; PC rewinds while BC != 0
    z = fresh(b"\xED\xB0", h=0x10, l=0x00, d=0x20, e=0x00, b=0, c=3)
    z.m[0x1000:0x1003] = b"\xAA\xBB\xCC"
    z.step()
    cases.append(("LDIR step1", z.m[0x2000] == 0xAA and z.bc() == 2 and (z.f & P) and z.pc == 0))
    z.step()
    cases.append(("LDIR step2", z.m[0x2001] == 0xBB and z.bc() == 1 and (z.f & P) and z.pc == 0))
    z.step()
    cases.append(("LDIR step3 done", z.m[0x2000:0x2003] == b"\xAA\xBB\xCC" and z.bc() == 0 and not (z.f & P) and z.pc == 2))

    # 15. SBC A,A with carry set -> 0xFF, C set
    z = fresh(b"\x9F", a=0x00, f=C)
    z.step()
    cases.append(("SBC A,A", z.a == 0xFF and (z.f & C) and (z.f & S)))

    # 16. PUSH/POP BC roundtrip
    z = fresh(b"\xC5\xC1", b=0x12, c=0x34)
    z.step(); z.step()
    cases.append(("PUSH/POP", z.b == 0x12 and z.c == 0x34 and z.sp == 0xF000))

    ok = sum(1 for _, passed in cases if passed)
    for name, passed in cases:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if not passed:
            failures.append(name)
    print(f"selftest: {ok}/{len(cases)} passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="self-contained Z80 core")
    ap.add_argument("--selftest", action="store_true", help="run known-answer tests")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
