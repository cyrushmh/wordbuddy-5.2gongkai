package com.sysweeper.android.probe

import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.provider.Settings

/**
 * 只读探针引擎：把 system-optimizer 的 Android 只读接口（native/android.py）的核心口径
 * 移植到 Kotlin/Android，适配 Android 8（API 26）下探到 Android 14（API 34）。
 *
 * 所有读取都包在 try/catch 中；某一项读不到（权限/厂商定制）就降级为提示，绝不中断、绝不写入。
 *
 * 版本门控（对齐 PC 侧 android.py 的 API 口径表）：
 *   · 放大镜            API 17 起（minSdk 26 恒可用）
 *   · 色彩校正 daltonizer API 26 起（本工具下探起点）
 *   · 可调字重          API 28 起（Android 9）
 *   · 护眼/夜览         API 28 起（Android 9）
 *   · 高对比度文本       API 29 起（Android 10）
 *   · 深色模式(settings) API 29 起（Android 10）
 * 低于所需 API 时**明说「此版本无此开关」**，绝不伪装成已开启。
 */
object ProbeEngine {

    fun scan(ctx: Context): List<ProbeResult> {
        val r = mutableListOf<ProbeResult>()

        // —— 设备 / 系统（只读） ——
        r += ProbeResult(
            "device.model", "设备型号",
            Build.MODEL ?: "?",
            "适配下限 API 26（Android 8）",
            Severity.INFO,
        )
        r += ProbeResult(
            "android.sdk", "Android API",
            Build.VERSION.SDK_INT.toString(),
            "目标 Android 14（API 34），当前 ${describeSdk(Build.VERSION.SDK_INT)}",
            Severity.INFO,
        )
        r += ProbeResult(
            "android.release", "Android 版本",
            Build.VERSION.RELEASE ?: "?",
            "建议升级到受支持的大版本以获安全补丁",
            Severity.INFO,
        )
        r += ProbeResult(
            "abi", "支持的 ABI",
            Build.SUPPORTED_ABIS?.joinToString() ?: "?",
            "按硬件分发：arm64-v8a / armeabi-v7a / x86_64",
            Severity.INFO,
        )

        // —— 字体缩放（适老化） ——
        val fontScale = readFloat(ctx) { Settings.System.getFloat(it, Settings.System.FONT_SCALE) }
        if (fontScale != null) {
            val lowVision = fontScale < 1.15f
            r += ProbeResult(
                "font.scale", "字体缩放",
                "%.2fx".format(fontScale),
                if (lowVision) "适老化建议：放大到 ≥1.15（设置 → 显示 → 字体大小）" else "字体已放大，适老友好",
                if (lowVision) Severity.TIP else Severity.INFO,
            )
        } else {
            r += ProbeResult(
                "font.scale", "字体缩放",
                "（无读取权限）",
                "无法读取，请在系统设置中手动核对字体大小",
                Severity.INFO,
            )
        }

        // —— 可调字重（适老化，API 28+） ——
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val weight = readInt(ctx) { Settings.System.getInt(it, "font_weight_adjustment") }
            if (weight != null) {
                val adjusted = weight in 101..400
                r += ProbeResult(
                    "font.weight", "字重加粗",
                    if (weight == 0) "默认(0)" else "$weight",
                    when {
                        adjusted -> "字重已加粗（$weight），对低视力老人比放大字号更省版式空间"
                        weight < 0 -> "字重已减细，弱视用户慎用"
                        else -> "低视力用户可在支持此项的 ROM 上加粗，缓解字迹发虚"
                    },
                    if (adjusted) Severity.INFO else Severity.TIP,
                )
            } else {
                r += ProbeResult(
                    "font.weight", "字重加粗",
                    "（此 ROM 未暴露）",
                    "部分 ROM 即便 Android 9+ 也未提供字重键；可用字体缩放 + 高对比度替代",
                    Severity.INFO,
                )
            }
        } else {
            r += ProbeResult(
                "font.weight", "字重加粗",
                "此版本无此开关",
                "可调字重需 Android 9（API 28）以上；当前系统请用字体缩放替代",
                Severity.INFO,
            )
        }

        // —— 高对比度 / 色彩校正（低视力） ——
        val daltonizer = readInt(ctx) { Settings.Secure.getInt(it, "accessibility_display_daltonizer_enabled") }
        val daltonizerMode = readInt(ctx) { Settings.Secure.getInt(it, "accessibility_display_daltonizer") }
        val contrastOn = daltonizer == 1
        val modeText = when (daltonizerMode) {
            1 -> "红绿(最常用)"
            2 -> "红蓝"
            3 -> "灰度"
            0 -> "无"
            else -> "自定义"
        }
        r += ProbeResult(
            "contrast", "色彩校正 / 高对比",
            if (contrastOn) "已开启（$modeText）" else "未开启",
            if (!contrastOn) "低视力用户可开启：设置 → 无障碍 → 色彩与对比度" else "已为低视力优化（色盲/色弱校正模式：$modeText）",
            if (!contrastOn) Severity.TIP else Severity.INFO,
        )

        // —— 高对比度文本（低视力，API 29+） ——
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val highContrast = readInt(ctx) { Settings.Secure.getInt(it, "accessibility_high_text_contrast") }
            r += ProbeResult(
                "a11y.high_text_contrast", "高对比度文本",
                if (highContrast == 1) "已开启" else if (highContrast == 0) "未开启" else "（此 ROM 未暴露）",
                if (highContrast == 1) "文字与背景反差已提高，低视力友好" else "低视力用户可开启：设置 → 无障碍 → 高对比度文本",
                if (highContrast == 1) Severity.INFO else Severity.TIP,
            )
        } else {
            r += ProbeResult(
                "a11y.high_text_contrast", "高对比度文本",
                "此版本无此开关",
                "高对比度文本需 Android 10（API 29）以上；老设备请用色彩校正 + 深色模式替代",
                Severity.INFO,
            )
        }

        // —— 深色模式（护眼 / 省电） ——
        val nightMode = ctx.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK
        val dark = nightMode == Configuration.UI_MODE_NIGHT_YES
        val uiNightMode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            readInt(ctx) { Settings.Secure.getInt(it, "ui_night_mode") }
        } else null
        val darkSettingsHint = when (uiNightMode) {
            1 -> "；设置侧：固定开启"
            2 -> "；设置侧：自动（日落切换）"
            0 -> "；设置侧：关闭"
            else -> ""
        }
        r += ProbeResult(
            "dark.mode", "深色模式",
            if (dark) "开启" else "关闭",
            if (!dark) "OLED 设备建议开启以省电护眼$darkSettingsHint" else "已开启$darkSettingsHint",
            if (!dark) Severity.TIP else Severity.INFO,
        )

        // —— 放大镜（低视力，API 17+，minSdk 26 恒可用） ——
        val magnification = readInt(ctx) { Settings.Secure.getInt(it, "accessibility_display_magnification_enabled") }
        r += ProbeResult(
            "a11y.magnification", "放大镜手势",
            if (magnification == 1) "已开启" else if (magnification == 0) "未开启" else "（此 ROM 未暴露）",
            if (magnification == 1) "已开启局部放大手势，低视力友好" else "低视力用户可开启：设置 → 无障碍 → 放大镜（老设备最实用的辅助）",
            if (magnification == 1) Severity.INFO else Severity.TIP,
        )

        // —— 屏幕朗读 TalkBack（视障） ——
        val enabledSvcs = readString(ctx) { Settings.Secure.getString(it, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) }
        val talkback = enabledSvcs?.contains("talkback", ignoreCase = true) == true
        r += ProbeResult(
            "a11y.talkback", "屏幕朗读 (TalkBack)",
            if (talkback) "已启用" else "未启用",
            if (!talkback) "视障用户建议在设置 → 无障碍 → TalkBack 启用" else "已为视障优化",
            if (!talkback) Severity.TIP else Severity.INFO,
        )

        // —— 无障碍服务总闸与清单（只读） ——
        val a11yEnabled = readInt(ctx) { Settings.Secure.getInt(it, "accessibility_enabled") }
        val svcNames = enabledSvcs
            ?.split(":")?.map { it.trim() }?.filter { it.isNotEmpty() }
            ?: emptyList()
        r += ProbeResult(
            "a11y.services", "已启用无障碍服务",
            if (svcNames.isEmpty()) "无" else "${svcNames.size} 项：${svcNames.joinToString("、") { it.substringAfterLast('/') }}",
            when {
                a11yEnabled == 0 && svcNames.isEmpty() -> "无障碍总闸关闭（无任何服务运行）；如无需辅助功能，保持关闭更省电"
                svcNames.isEmpty() -> "总闸已开但无服务在运行；视障用户请启用 TalkBack 等读屏服务"
                else -> "总闸开启，${svcNames.size} 个服务在运行；服务会常驻读取屏幕内容，请核对均为本人所需"
            },
            if (svcNames.isEmpty()) Severity.INFO else Severity.TIP,
        )

        // —— 减弱动画（适老防眩晕，三项动画缩放，global 表） ——
        for ((key, label, tag) in listOf(
            Triple(Settings.Global.WINDOW_ANIMATION_SCALE, "窗口动画", "anim.window"),
            Triple(Settings.Global.TRANSITION_ANIMATION_SCALE, "过渡动画", "anim.transition"),
            Triple(Settings.Global.ANIMATOR_DURATION_SCALE, "Animator 时长", "anim.animator"),
        )) {
            val scale = readFloat(ctx) { Settings.Global.getFloat(it, key) }
            r += if (scale != null) {
                val off = scale <= 0.01f
                ProbeResult(
                    tag, label + "缩放",
                    "%.2f".format(scale),
                    if (off) "动画已移除，界面切换更跟手（防眩晕）" else "前庭敏感 / 高龄用户建议降到 0：设置 → 无障碍 → 移除动画",
                    if (off) Severity.INFO else Severity.TIP,
                )
            } else {
                ProbeResult(
                    tag, label + "缩放",
                    "（无读取权限）",
                    "无法读取，请在设置 → 无障碍 → 移除动画手动核对",
                    Severity.INFO,
                )
            }
        }

        // —— 触感反馈 / 触摸音效（非视觉确认反馈） ——
        val haptic = readInt(ctx) { Settings.System.getInt(it, "haptic_feedback_enabled") }
        r += ProbeResult(
            "haptic.feedback", "触感反馈",
            if (haptic == 1) "已开启" else if (haptic == 0) "未开启" else "（此 ROM 未暴露）",
            if (haptic == 1) "操作有振动确认，弱视/老年用户友好" else "建议保留：触感是「操作是否生效」的非视觉反馈",
            if (haptic == 1) Severity.INFO else Severity.TIP,
        )
        val soundFx = readInt(ctx) { Settings.System.getInt(it, "sound_effects_enabled") }
        r += ProbeResult(
            "sound.effects", "触摸提示音",
            if (soundFx == 1) "已开启" else if (soundFx == 0) "未开启" else "（此 ROM 未暴露）",
            if (soundFx == 1) "操作有提示音反馈，听障用户友好" else "可保留作为操作确认；安静场合可关闭",
            if (soundFx == 1) Severity.INFO else Severity.TIP,
        )

        // —— 护眼与省电：亮度 / 息屏超时 ——
        val brightness = readInt(ctx) { Settings.System.getInt(it, Settings.System.SCREEN_BRIGHTNESS) }
        val brightnessMode = readInt(ctx) { Settings.System.getInt(it, Settings.System.SCREEN_BRIGHTNESS_MODE) }
        r += if (brightness != null) {
            val pct = if (brightness in 0..255) (brightness * 100 / 255) else brightness
            val auto = brightnessMode == 1
            ProbeResult(
                "screen.brightness", "手动亮度",
                "$pct%",
                when {
                    pct < 30 -> "偏暗：室内环境对老花/白内障用户普遍不足，建议调高${if (auto) "（当前为自动亮度，可改手动）" else ""}"
                    auto -> "自动亮度生效，环境明暗变化大时可能忽明忽暗"
                    else -> "亮度适中，弱视用户仍可按需调高"
                },
                if (pct < 30) Severity.TIP else Severity.INFO,
            )
        } else {
            ProbeResult(
                "screen.brightness", "手动亮度",
                "（无读取权限）",
                "无法读取，请在设置 → 显示 → 亮度手动核对",
                Severity.INFO,
            )
        }
        val timeoutMs = readInt(ctx) { Settings.System.getInt(it, Settings.System.SCREEN_OFF_TIMEOUT) }
        r += if (timeoutMs != null) {
            val seconds = timeoutMs / 1000
            ProbeResult(
                "screen.timeout", "息屏超时",
                "$seconds 秒",
                if (seconds < 30) "偏短：老年用户阅读/操作节奏较慢，建议调长到 1–2 分钟减少反复点亮" else "息屏时间适中",
                if (seconds < 30) Severity.TIP else Severity.INFO,
            )
        } else {
            ProbeResult(
                "screen.timeout", "息屏超时",
                "（无读取权限）",
                "无法读取，请在设置 → 显示 → 息屏时间手动核对",
                Severity.INFO,
            )
        }

        // —— 护眼 / 夜览（API 28+，冷暖色温） ——
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val nightDisplay = readInt(ctx) { Settings.Secure.getInt(it, "night_display_activated") }
            val nightModeSetting = readInt(ctx) { Settings.Secure.getInt(it, "night_mode") }
            val on = nightDisplay == 1 || nightModeSetting == 1
            val known = nightDisplay != null || nightModeSetting != null
            r += ProbeResult(
                "eyecare.night", "护眼 / 夜览",
                when {
                    on -> "已开启"
                    known -> "未开启"
                    else -> "（此 ROM 未暴露）"
                },
                if (on) "夜览已开启（暖色温护眼）" else "睡前阅读用户建议开启：设置 → 显示 → 护眼模式 / 夜间模式",
                if (on) Severity.INFO else Severity.TIP,
            )
        } else {
            r += ProbeResult(
                "eyecare.night", "护眼 / 夜览",
                "此版本无此开关",
                "护眼夜览需 Android 9（API 28）以上；Android 8 请用厂商显示设置里的护眼开关或深色模式",
                Severity.INFO,
            )
        }

        // —— 开发者选项（普通用户建议关闭） ——
        val dev = readInt(ctx) { Settings.Global.getInt(it, Settings.Global.DEVELOPMENT_SETTINGS_ENABLED) }
        val devOn = dev == 1
        r += ProbeResult(
            "dev.options", "开发者选项",
            if (devOn) "已开启" else "关闭",
            if (devOn) "普通用户建议关闭，避免误改系统参数" else "保持关闭",
            if (devOn) Severity.WARN else Severity.INFO,
        )

        return r
    }

    private fun describeSdk(sdk: Int): String = when (sdk) {
        26 -> "Android 8.0"
        27 -> "Android 8.1"
        28 -> "Android 9"
        29 -> "Android 10"
        30 -> "Android 11"
        31 -> "Android 12"
        32 -> "Android 12L"
        33 -> "Android 13"
        34 -> "Android 14"
        35 -> "Android 15"
        36 -> "Android 16"
        else -> "未知"
    }

    private inline fun readFloat(ctx: Context, block: (android.content.ContentResolver) -> Float): Float? =
        try {
            block(ctx.contentResolver)
        } catch (_: Exception) {
            null
        }

    private inline fun readInt(ctx: Context, block: (android.content.ContentResolver) -> Int): Int? =
        try {
            block(ctx.contentResolver)
        } catch (_: Exception) {
            null
        }

    private inline fun readString(ctx: Context, block: (android.content.ContentResolver) -> String?): String? =
        try {
            block(ctx.contentResolver)
        } catch (_: Exception) {
            null
        }
}
