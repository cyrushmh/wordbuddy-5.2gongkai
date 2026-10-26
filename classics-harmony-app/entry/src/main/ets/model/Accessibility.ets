// 无障碍与适老化中枢。
//
// 由「系统使用无障碍 / 组网无障碍」需求驱动，集中处理：
//  - 适老化（长辈模式）：一键放大字号与行距、提升对比度；
//  - 系统使用无障碍：跟随系统字体、高对比配色、读屏播报（announce）；
//  - 计算「有效字号 / 有效行距 / 有效配色」，供各阅读页统一调用。
//
// 设计：本文件只做「计算与播报」，不持有状态；状态仍存于 ReaderPrefs（AppStorage）。
// 任何读屏 / API 异常都静默降级，绝不阻断主流程。

import { AccessibilityLevel } from '@kit.ArkUI';
import { accessibility } from '@kit.AccessibilityKit';
import { ThemeColors, themeColors } from './ReaderPrefs';

/** 长辈模式字号倍率（在手动字号之上再放大，面向弱视与长辈）。 */
export const ELDER_FONT_SCALE: number = 1.5;
/** 长辈模式行距倍率（疏朗排版，减轻阅读压迫感）。 */
export const ELDER_LINE_SCALE: number = 1.4;

/** 高对比配色：纯黑底、纯白字、亮黄强调，对比度拉满，便于弱视与强光环境。 */
export const HIGH_CONTRAST: ThemeColors = {
  bg: '#000000',
  text: '#ffffff',
  sub: '#e6e6e6',
  accent: '#ffd400'
};

/**
 * 有效字号：长辈模式优先于手动；开启「跟随系统字体」时再乘系统缩放。
 * @param manual 手动字号倍率
 * @param elder 是否长辈模式
 * @param systemScale 系统字体缩放（由 UIContext.getFontScale 取得）
 * @param followSystem 是否跟随系统字体
 */
export function effectiveFontScale(manual: number, elder: boolean, systemScale: number, followSystem: boolean): number {
  const base: number = elder ? ELDER_FONT_SCALE : manual;
  return base * (followSystem ? systemScale : 1.0);
}

/**
 * 有效行距：长辈模式优先于手动。
 */
export function effectiveLineScale(manual: number, elder: boolean): number {
  return elder ? ELDER_LINE_SCALE : manual;
}

/**
 * 有效配色：高对比优先于主题。
 */
export function effectiveColors(theme: string, highContrast: boolean): ThemeColors {
  if (highContrast) {
    return HIGH_CONTRAST;
  }
  return themeColors(theme);
}

/**
 * 读屏播报（无障碍核心 API）：把状态变化念给视障用户听。
 * 任何异常静默降级，绝不阻断主流程。
 * @param ctx 当前 UIAbility 上下文（可为 undefined，此时跳过播报）
 * @param text 播报文本
 */
export function announce(ctx: Context | undefined, text: string): void {
  if (!ctx) {
    return;
  }
  try {
    accessibility.announce(ctx, { text: text, holdTime: 3000 }).catch(() => {});
  } catch (e) {
    // 读屏不可用或当前平台不支持 announce：忽略。
  }
}

export { AccessibilityLevel };
