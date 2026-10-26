.. SPDX-License-Identifier: GPL-2.0

=====================
Quantum architecture
=====================

:Author: quantum-kernel project
:Date: 2026-10

The quantum architecture (``ARCH=quantum``) brings a **host-emulated
quantum processing unit (QPU)** into the Linux kernel tree, in the same
spirit as arch/um (User Mode Linux): there is no quantum silicon behind
the port -- the QPU is simulated, and everything else runs on the host
toolchain.

Pure addition
=============

This port is **purely additive**: ``arch/Kconfig`` sources
``arch/$(SRCARCH)/Kconfig`` dynamically and the top-level Makefile maps
``SRCARCH := $(ARCH)`` by default, so no existing architecture was
modified or removed.  The only edits to existing files are two
append-only registrations in ``drivers/Kconfig`` / ``drivers/Makefile``
and one line in the documentation index.

Layout (Linux kernel tree discipline)
=====================================

::

    arch/quantum/
    ├── Kconfig              architecture options (QUANTUM, QPU, link slots,
    │                        energy levels)
    ├── Makefile             KBUILD_DEFCONFIG, core-y paths
    ├── configs/
    │   └── quantum_defconfig
    ├── boot/                grub.cfg / lilo.conf command-line samples
    │                        (idle=mwait and friends)
    ├── include/asm/
    │   ├── Kbuild           generic-y forwarding (asm-generic reuse)
    │   ├── quantum.h        Π_k gate / 8-qubit / pi-link semantics +
    │   │                    energy-level model interface
    │   ├── page.h           4KiB page discipline
    │   └── irq.h            emulated NR_IRQS
    ├── kernel/              setup, head stub, irq, time, qpu-core,
    │                        quantum-energy, module
    ├── mm/                  emulated memory init
    └── lib/                 (empty; generic lib covers it)

    drivers/quantum/         /dev/qpuN misc device (QPU_ENC/DEC/STATS/RESET)
    include/uapi/linux/quantum.h   user API

Semantics (aligned with the userspace quantum base)
===================================================

- **Register width**: ``CONFIG_QUANTUM_QUBITS`` (default 8, byte-wide,
  256 basis states; hard ceiling 20 matching the userspace base).
- **Number gate**: ``enc k`` applies the permutation matrix Π_k --
  composite of X gates on the set bits of ``k``.  From |0...0> encoding
  ``k`` yields ``|k>``; encoding ``j`` again *without reset* yields
  ``|k XOR j>`` (flip semantics -- keep the reset contract).
- **Link buffer**: ring of ``CONFIG_QUANTUM_LINK_SLOTS`` slots
  (default ceil(2π) = 7).  Every exchange is pushed; overflow
  overwrites the oldest record and counts in ``overwrites``.
- **Page discipline**: 4KiB pages, matching the ext4/4K alignment
  discipline of the storage domain.

Energy-level model
==================

See :doc:`energy-model` for the quantum-physics semantics of the idle
CPU: discrete levels, superposition, unitary phase evolution,
interference, measurement collapse, decoherence (T1/T2), selection
rules, virtual photons into the PiLink buffer, entanglement -- and the
``idle=mwait`` boot parameter (x86 deprecated it, but it still works;
GRUB/LILO samples in ``arch/quantum/boot/``).

Build
=====

::

    make ARCH=quantum O=build quantum_defconfig
    make ARCH=quantum O=build -j$(nproc)

The build produces a real ``vmlinux`` on the host toolchain (there is
no gcc backend for a quantum processor, so the QPU itself is
host-emulated; see ``quantum-kernel/README.md`` for the honest build
report).
