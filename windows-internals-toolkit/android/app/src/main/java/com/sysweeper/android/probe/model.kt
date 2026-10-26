package com.sysweeper.android.probe

/**
 * 单条只读探针结果。
 *
 * 设计对齐 system-optimizer 的「只读安全底线」：本 App 只读取系统设置用于诊断与适老化建议，
 * 绝不修改、不 root、不写系统属性。severity 仅用于 UI 提示分级，不改变只读性质。
 */
data class ProbeResult(
    val key: String,
    val label: String,
    val value: String,
    val advice: String,
    val severity: Severity,
)

enum class Severity {
    /** 普通信息 */
    INFO,
    /** 适老化 / 护眼等可选优化建议 */
    TIP,
    /** 需要注意（如开发者选项常开），但不强制 */
    WARN,
}
