.. SPDX-License-Identifier: GPL-2.0

===============================
Quantum energy-level model
===============================

:Author: quantum-kernel project
:Date: 2026-10

Honest framing
==============

The QPU of ``ARCH=quantum`` is **host-emulated** -- there is no quantum
silicon.  The energy model implemented by
``arch/quantum/kernel/quantum-energy.c`` is therefore a
**quantum-mechanics-inspired accounting model**: every number it reports
is a real kernel counter or state evolution, while the quantum concepts
(discrete levels, superposition, phase evolution, interference,
measurement collapse, decoherence, entanglement, selection rules) are
used as the semantic layer that maps CPU idle behaviour onto them.
It is not a claim of physical quantum computation.

Energy levels
=============

Discrete spectrum ``E_n = n × CONFIG_QUANTUM_ENERGY_STEP`` with
``n = 0 .. CONFIG_QUANTUM_EXCITED_LEVELS-1``:

* ``E_0`` -- **ground state** (deepest idle);
* ``E_n`` (n ≥ 1) -- **excited states** (lighter idle / run levels).

The level population weights ``w_n = |α_n|²`` (16.16 fixed point) form
the superposition weights of the idle CPU.  Model prior: ground holds
3/4 of the population, the rest is split evenly over the excited
levels.

Quantum effects modelled
========================

Superposition & unitary evolution
  Each energy eigenstate only accumulates phase:
  ``φ_n(t) = ω_n·t`` with ``ω_n = E_n`` (ℏ = 1, fictitious Planck
  accounting units).  ``quantum_phase_advance()`` advances the phases
  between two observations.

Interference
  ``quantum_interference(a, b)`` returns the cross term
  ``2·w_a·w_b·cos(φ_a − φ_b)`` scaled by the surviving coherence
  (2^30 fixed point, range [−2, +2]), computed from the real phase
  difference with a 256-entry fixed-point sine table.

Measurement & collapse
  An interrupt delivery is a **measurement**: on idle exit the
  superposition collapses to a definite level (argmax of population,
  deterministic -- no RNG dependency), and the coherence/phase baseline
  is rebuilt.

Decoherence
  T1: per decoherence tick, 1/8 of every excited population leaks to
  the ground state (amplitude damping).  T2: the coherence is halved
  every ``CONFIG_QUANTUM_COHERENCE_TICKS`` observations.  Transitions
  partially restore coherence (a new observation rebuilds the phase
  baseline).

Stimulated transition & relaxation
  Waking up absorbs ``ΔE`` (excitation); entering idle relaxes one step
  toward the ground state and **emits ΔE as a virtual photon** which is
  pushed into the PiLink ring buffer (``quantum_link_push``) -- one
  exchange, one link record, matching the existing link semantics.

Selection rules
  Adjacent-level transitions (``|Δn| = 1``) are counted as *allowed*
  (electric-dipole-like); non-adjacent transitions are counted as
  *forbidden* (higher-order processes: they still happen in the model,
  but are counted separately).

Entanglement
  ``quantum_entangle(a, b)`` registers a Bell pair; a collapse of side
  ``a`` at level ``a`` records the correlated collapse of side ``b``
  (``bell_events``).  Up to 8 pairs.

idle= boot parameter
====================

``arch/quantum`` registers ``early_param("idle", ...)`` with the x86
compatible subset:

===========  ==========================================================
idle=poll    Force polling: ``cpu_idle_poll_ctrl(true)`` plus a busy
             ``cpu_relax()`` spin in ``arch_cpu_idle()``.
idle=mwait   Ground-state wait (default): the host-emulated
             monitor/wait semantics -- no busy spin, the wait itself is
             emulated by the host process, so ``arch_cpu_idle()``
             returns immediately.  x86 dropped ``idle=mwait`` from its
             documented values (deprecated), but the parameter still
             works in 6.18.57 and the quantum architecture keeps the
             semantics on purpose.
idle=halt    Deepest halt state (emulated semantics identical to
             mwait; there is no real halt instruction).
===========  ==========================================================

Bootloader usage
================

GRUB (``grub.cfg`` sample in ``arch/quantum/boot/grub.cfg``)::

    menuentry 'Linux/quantum 6.18.57 (host-emulated, idle=mwait)' {
            set root='hd0,msdos1'
            linux /boot/vmlinux-6.18.57-quantum root=/dev/sda1 ro idle=mwait
    }

LILO (``lilo.conf`` sample in ``arch/quantum/boot/lilo.conf``)::

    image = /boot/vmlinux-6.18.57-quantum
            label = quantum
            root = /dev/sda1
            read-only
            append = "idle=mwait"

Honest caveat: the quantum architecture is host-emulated and has no
bootable image format (no bzImage/Image boot protocol); the bootloader
configs are **kernel-command-line contract samples** documenting how
``idle=mwait`` reaches the architecture idle path.

Observation
===========

``/proc/quantum-energy`` dumps the live model::

    quantum energy model: levels=4 step=16 coherence_ticks=8 decohere_steps=64
    cpu0: idle_mode=mwait excited=0 coherence=65536/65536 ticks=128 idle_steps=8192
    level  energy  phase        pop
    0      0       0            49152
    ...
    interference(0,1) = <s64> (2^30 fixed, [-2, +2])
    events: excitations=... relaxations=... allowed=... forbidden=...
    energy: absorbed=... emitted=... (planck units)
    bell_events: ...

Exported API (EXPORT_SYMBOL_GPL, usable from modules such as
``drivers/quantum``)::

    unsigned int quantum_levels(void);
    unsigned int quantum_level_energy(unsigned int n);
    unsigned int quantum_idle_mode_current(void);
    const char *quantum_idle_mode_name(unsigned int mode);
    const struct quantum_cpu *quantum_cpu_state(int cpu);
    void quantum_excite(unsigned int from, unsigned int to);
    void quantum_relax(unsigned int from, unsigned int to);
    void quantum_phase_advance(unsigned int dt);
    void quantum_decohere_tick(void);
    s64 quantum_interference(unsigned int a, unsigned int b);
    unsigned int quantum_measure(void);
    int quantum_entangle(unsigned int a, unsigned int b);
