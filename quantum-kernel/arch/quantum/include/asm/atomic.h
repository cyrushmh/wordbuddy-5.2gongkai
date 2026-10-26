/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/asm/atomic.h — atomic operations for the emulated arch.
 * 模拟架构（单核、无真实并发）：READ_ONCE/WRITE_ONCE 足够，诚实口径。
 * atomic64_t 由 linux/types.h 在 CONFIG_64BIT 下定义，这里只补原生实现。
 */
#ifndef _ASM_QUANTUM_ATOMIC_H
#define _ASM_QUANTUM_ATOMIC_H

#include <linux/compiler.h>
#include <linux/types.h>
#include <asm/barrier.h>
#include <asm/cmpxchg.h>

/* ── atomic_t（32 位族）──────────────────────────────────────────── */

#define arch_atomic_read(v)	READ_ONCE((v)->counter)
#define arch_atomic_set(v, i)	WRITE_ONCE((v)->counter, (i))
#define arch_atomic_set_release(v, i) arch_atomic_set((v), (i))

#define __ATOMIC_OP(op, c_op)						\
static __always_inline void arch_atomic_##op(int i, atomic_t *v)	\
{									\
	WRITE_ONCE((v)->counter, READ_ONCE((v)->counter) c_op i);	\
}

#define __ATOMIC_OP_RETURN(op, c_op)					\
static __always_inline int arch_atomic_##op##_return(int i, atomic_t *v) \
{									\
	WRITE_ONCE((v)->counter, READ_ONCE((v)->counter) c_op i);	\
	return i;							\
}

#define __ATOMIC_FETCH_OP(op, c_op)					\
static __always_inline int arch_atomic_fetch_##op(int i, atomic_t *v)	\
{									\
	int old = READ_ONCE((v)->counter);				\
	WRITE_ONCE((v)->counter, old c_op i);				\
	return old;							\
}

#define ATOMIC_OPS(op, c_op)						\
	__ATOMIC_OP(op, c_op)						\
	__ATOMIC_OP_RETURN(op, c_op)					\
	__ATOMIC_FETCH_OP(op, c_op)

ATOMIC_OPS(add, +)
ATOMIC_OPS(sub, -)
ATOMIC_OPS(and, &)
ATOMIC_OPS(or, |)
ATOMIC_OPS(xor, ^)

#define arch_atomic_add_return			arch_atomic_add_return
#define arch_atomic_sub_return			arch_atomic_sub_return
#define arch_atomic_fetch_add			arch_atomic_fetch_add
#define arch_atomic_fetch_sub			arch_atomic_fetch_sub
#define arch_atomic_fetch_and			arch_atomic_fetch_and
#define arch_atomic_fetch_or			arch_atomic_fetch_or
#define arch_atomic_fetch_xor			arch_atomic_fetch_xor

static __always_inline int arch_atomic_inc_return(atomic_t *v)
{
	return arch_atomic_add_return(1, v);
}

static __always_inline int arch_atomic_dec_return(atomic_t *v)
{
	return arch_atomic_sub_return(1, v);
}

/* ── atomic64_t（64 位原生族）────────────────────────────────────── */

#define ATOMIC64_INIT(i)	{ (i) }

#define arch_atomic64_read(v)	READ_ONCE((v)->counter)
#define arch_atomic64_set(v, i)	WRITE_ONCE((v)->counter, (i))

#define __ATOMIC64_OP(op, c_op)						\
static __always_inline void arch_atomic64_##op(s64 i, atomic64_t *v)	\
{									\
	WRITE_ONCE((v)->counter, READ_ONCE((v)->counter) c_op i);	\
}

#define __ATOMIC64_OP_RETURN(op, c_op)					\
static __always_inline s64 arch_atomic64_##op##_return(s64 i, atomic64_t *v) \
{									\
	WRITE_ONCE((v)->counter, READ_ONCE((v)->counter) c_op i);	\
	return i;							\
}

#define __ATOMIC64_FETCH_OP(op, c_op)					\
static __always_inline s64 arch_atomic64_fetch_##op(s64 i, atomic64_t *v) \
{									\
	s64 old = READ_ONCE((v)->counter);				\
	WRITE_ONCE((v)->counter, old c_op i);				\
	return old;							\
}

#define ATOMIC64_OPS(op, c_op)						\
	__ATOMIC64_OP(op, c_op)						\
	__ATOMIC64_OP_RETURN(op, c_op)					\
	__ATOMIC64_FETCH_OP(op, c_op)

ATOMIC64_OPS(add, +)
ATOMIC64_OPS(sub, -)
ATOMIC64_OPS(and, &)
ATOMIC64_OPS(or, |)
ATOMIC64_OPS(xor, ^)

#define arch_atomic64_add_return		arch_atomic64_add_return
#define arch_atomic64_sub_return		arch_atomic64_sub_return
#define arch_atomic64_fetch_add			arch_atomic64_fetch_add
#define arch_atomic64_fetch_sub			arch_atomic64_fetch_sub
#define arch_atomic64_fetch_and			arch_atomic64_fetch_and
#define arch_atomic64_fetch_or			arch_atomic64_fetch_or
#define arch_atomic64_fetch_xor			arch_atomic64_fetch_xor

static __always_inline s64 arch_atomic64_read_acquire(const atomic64_t *v)
{
	return smp_load_acquire(&(v)->counter);
}

static __always_inline void arch_atomic64_set_release(atomic64_t *v, s64 i)
{
	smp_store_release(&(v)->counter, i);
}

static __always_inline s64 arch_atomic64_inc_return(atomic64_t *v)
{
	return arch_atomic64_add_return(1, v);
}

static __always_inline s64 arch_atomic64_dec_return(atomic64_t *v)
{
	return arch_atomic64_sub_return(1, v);
}

#endif /* _ASM_QUANTUM_ATOMIC_H */
