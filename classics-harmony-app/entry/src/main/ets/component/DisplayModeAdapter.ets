/*
 * DisplayModeAdapter.ets —— 大屏 / 折叠屏 · 版式自适应（适老化 + 折叠屏适配）
 * 来源样例：Batch22 CategoryOrientationAgent（Java API8：ohos.sensor.agent.CategoryOrientationAgent 方向传感器）
 * 代际说明：原样例为旧版鸿蒙 Java 工程，与 NEXT ArkTS 不再互通；本块抽其「感知设备姿态/大屏」概念，
 *           翻写为 NEXT 推荐 API，做成未接线构建块（默认不接入工程，避免引入失效旧 API）。
 *
 * NEXT 对应 API（接线前以当前 SDK 为准，推荐窗口/折叠状态而非原始方向传感器，能耗更低、语义更清）：
 *   - 窗口尺寸/状态：import { window } from '@kit.ArkUI'，windowClass.on('windowSizeChange' / 'windowStatusChange')
 *   - 折叠屏：import { display } from '@kit.ArkUI'，display.on('foldStatusChange') 或 window 折叠回调
 *   - 方向传感器（备选）：import { sensor } from '@kit.SensorKit'，sensor.on(sensor.SensorId.ORIENTATION, ...)
 *
 * 用途（系统使用无障碍）：
 *   折叠屏展开 / 平板横屏 / 大屏设备时，自动切换「长辈大字 + 双栏排版」版式；
 *   竖屏手机时回落单栏。让长辈/视障用户在大屏上获得更大字号与更少滚动，无需手动开长辈模式。
 *   与 ReaderPrefs.elderMode 协同：大屏自动进入放大版式，退出大屏回落（若用户未显式锁定长辈模式）。
 *
 * 默认不接线：本文件仅作能力模板，需在阅读页 @State 初始化处引用。
 */
import { effectiveFontScale, effectiveLineScale, ELDER_FONT_SCALE, ELDER_LINE_SCALE } from '../model/Accessibility';

/** 版式模式。 */
export enum LayoutMode {
  Single = 'single',   // 单栏（手机竖屏）
  Dual = 'dual'        // 双栏（大屏/折叠展开/横屏）
}

/**
 * 依据窗口宽（dp）判定版式模式。阈值以「可读字号 + 双栏不挤」为准，接线时按真机微调。
 * @param widthDp 窗口宽度（dp）
 * @returns 单栏或双栏
 */
export function resolveLayout(widthDp: number): LayoutMode {
  // 平板/折叠展开常见宽度 840dp 起；手机竖屏多在 360~480dp。
  return widthDp >= 840 ? LayoutMode.Dual : LayoutMode.Single;
}

/**
 * 大屏自动适配：返回该模式下的放大字号与行距，桥接到 Accessibility.effective*。
 * @param manual 用户手动字号
 * @param elder 是否长辈模式（大屏可自动视作长辈版式）
 * @param systemScale 系统字号缩放
 * @param followSystem 是否跟随系统字体
 */
export function adaptiveScale(manual: number, elder: boolean, systemScale: number, followSystem: boolean): number {
  // 大屏场景下，即便用户未开长辈模式，也至少给到 ELDER 阈值，保证远距可读。
  const base = effectiveFontScale(manual, elder, systemScale, followSystem);
  return Math.max(base, ELDER_FONT_SCALE);
}

export function adaptiveLineScale(manual: number, elder: boolean): number {
  const base = effectiveLineScale(manual, elder);
  return Math.max(base, ELDER_LINE_SCALE);
}

/*
 * 接线参考（伪代码，需按 NEXT SDK 校准）：
 *
 * // 阅读页 @State
 * @State layout: LayoutMode = LayoutMode.Single;
 *
 * // EntryAbility 获取 windowClass 后
 * windowClass.on('windowSizeChange', (rect: window.Rect) => {
 *   this.layout = resolveLayout(px2dp(rect.width)); // 像素→dp 自行换算
 * });
 * // 折叠屏
 * display.on('foldStatusChange', (status: display.FoldStatus) => {
 *   this.layout = status === display.FoldStatus.FOLD_STATUS_EXPANDED ? LayoutMode.Dual : LayoutMode.Single;
 * });
 *
 * 权限/声明：窗口尺寸、折叠状态回调无需额外权限；若改用方向传感器，则需
 *           ohos.permission.ACCELEROMETER（接线前确认）。本块不预填 module.json5 以免破坏构建。
 */
