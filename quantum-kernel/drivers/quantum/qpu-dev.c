// SPDX-License-Identifier: GPL-2.0
/*
 * drivers/quantum/qpu-dev.c — emulated QPU misc character device.
 *
 * /dev/qpu0：用户态经 QPU_ENC/QPU_DEC/QPU_LINK_STATS/QPU_RESET 与模拟
 * 量子核交互。门语义 = Π_k 置换矩阵（对 k 置 1 位复合 X 门）：
 * 从 |0...0> 编码 k 得 |k>；不复位继续编码 j 得 |k XOR j>（翻转语义，
 * 与用户态量子基座一致）。QPU_DEC 模拟真实测量坍缩。
 */
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#include <uapi/linux/quantum.h>
#include <asm/quantum.h>

#define QPU_MAX_QUBITS 20 /* 与用户态量子基座 MAX_QUBITS 对齐 */

struct qpu_state {
	struct mutex lock;
	unsigned int nqubits;
	unsigned long state;      /* 计算基矢（模拟寄存器内容） */
	bool collapsed;
	/* π 链路缓冲（环形，满则覆盖计数）。 */
	unsigned int slots;
	unsigned int buffered;
	u64 total_writes;
	u64 overwrites;
	unsigned long *ring;
};

static struct qpu_state **qpus;
static int qpu_count;

static void qpu_link_push(struct qpu_state *q)
{
	if (q->buffered == q->slots) {
		q->overwrites++;
	} else {
		q->buffered++;
	}
	q->total_writes++;
}

static int qpu_open(struct inode *inode, struct file *filp)
{
	filp->private_data = qpus[iminor(inode) - qpu_count < 0 ?
				  0 : iminor(inode) % qpu_count];
	return 0;
}

static long qpu_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct qpu_state *q = filp->private_data;
	unsigned long k;
	struct qpu_link_stats st;
	int ret = 0;

	mutex_lock(&q->lock);
	switch (cmd) {
	case QPU_ENC:
		if (copy_from_user(&k, (void __user *)arg, sizeof(k))) {
			ret = -EFAULT;
			break;
		}
		if (k >= (1UL << q->nqubits)) {
			ret = -EOVERFLOW;
			break;
		}
		/* Π_k 置换矩阵门：对置 1 位复合 X（模拟核里是异或）。 */
		q->state = quantum_permutation_gate(q->state, k);
		q->collapsed = false;
		qpu_link_push(q);
		break;
	case QPU_DEC:
		/* 真实坍缩模拟：解码后寄存器保持（测量还原）。 */
		k = q->state;
		if (copy_to_user((void __user *)arg, &k, sizeof(k))) {
			ret = -EFAULT;
			break;
		}
		q->collapsed = true;
		qpu_link_push(q);
		break;
	case QPU_LINK_STATS:
		st.slots = q->slots;
		st.buffered = q->buffered;
		st.total_writes = q->total_writes;
		st.overwrites = q->overwrites;
		if (copy_to_user((void __user *)arg, &st, sizeof(st)))
			ret = -EFAULT;
		break;
	case QPU_RESET:
		q->state = 0;
		q->collapsed = false;
		qpu_link_push(q);
		break;
	default:
		ret = -ENOTTY;
	}
	mutex_unlock(&q->lock);
	return ret;
}

static const struct file_operations qpu_fops = {
	.owner		= THIS_MODULE,
	.open		= qpu_open,
	.unlocked_ioctl	= qpu_ioctl,
	.compat_ioctl	= compat_ptr_ioctl,
	.llseek		= noop_llseek,
};

static struct miscdevice *qpu_miscdevs;

static int __init qpu_init(void)
{
	int i, ret;

	qpu_count = CONFIG_QUANTUM_QPU_NR;
	qpus = kcalloc(qpu_count, sizeof(*qpus), GFP_KERNEL);
	qpu_miscdevs = kcalloc(qpu_count, sizeof(*qpu_miscdevs), GFP_KERNEL);
	if (!qpus || !qpu_miscdevs) {
		ret = -ENOMEM;
		goto err_free;
	}

	for (i = 0; i < qpu_count; i++) {
		struct qpu_state *q = kzalloc(sizeof(*q), GFP_KERNEL);

		if (!q) {
			ret = -ENOMEM;
			goto err_free;
		}
		mutex_init(&q->lock);
		q->nqubits = QUANTUM_QUBITS;
		q->slots = QUANTUM_LINK_SLOTS;
		q->ring = kcalloc(q->slots, sizeof(unsigned long), GFP_KERNEL);
		if (!q->ring) {
			kfree(q);
			ret = -ENOMEM;
			goto err_free;
		}
		qpus[i] = q;

		qpu_miscdevs[i].minor = MISC_DYNAMIC_MINOR;
		qpu_miscdevs[i].name = kasprintf(GFP_KERNEL, "qpu%d", i);
		qpu_miscdevs[i].fops = &qpu_fops;
		qpu_miscdevs[i].mode = 0600;
		ret = misc_register(&qpu_miscdevs[i]);
		if (ret)
			goto err_free;
	}

	pr_info("qpu: %d emulated device(s), %d qubits, %d link slots\n",
		qpu_count, QUANTUM_QUBITS, QUANTUM_LINK_SLOTS);
	return 0;

err_free:
	while (--i >= 0) {
		misc_deregister(&qpu_miscdevs[i]);
		kfree(qpus[i]->ring);
		kfree(qpus[i]);
	}
	kfree(qpu_miscdevs);
	kfree(qpus);
	return ret;
}
module_init(qpu_init);

static void __exit qpu_exit(void)
{
	int i;

	for (i = 0; i < qpu_count; i++) {
		misc_deregister(&qpu_miscdevs[i]);
		kfree(qpu_miscdevs[i].name);
		kfree(qpus[i]->ring);
		kfree(qpus[i]);
	}
	kfree(qpu_miscdevs);
	kfree(qpus);
}
module_exit(qpu_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Emulated quantum processing unit (/dev/qpuN)");
MODULE_AUTHOR("quantum-kernel project");
