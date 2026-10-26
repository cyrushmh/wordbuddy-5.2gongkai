/*
 * SystemEventHub.ets —— 系统公共事件订阅（适老化·自动跟随）
 * 来源样例：Batch22 CommonEventPublisher（Java API8：ohos.event.commonevent.CommonEventManager.publishCommonEvent）
 * 代际说明：原样例为旧版鸿蒙 Java 工程，与 NEXT ArkTS 不再互通；本块抽其「发布/订阅系统级事件」概念，
 *           翻写为 NEXT 推荐 API，做成未接线构建块（默认不接入工程，避免引入失效旧 API）。
 *
 * NEXT 对应 API（接线前以当前 SDK 为准）：
 *   - 推荐：Ability 生命周期内覆写 onConfigurationUpdate(newConfig)，系统字号/深色/语言变更时回调；
 *   - 或：import { commonEventManager } from '@kit.NotificationKit'，订阅 COMMON_EVENT_CONFIGURATION_UPDATE（需 wantAgent/权限以实际 SDK 为准）。
 *
 * 用途（系统使用无障碍）：
 *   当前阅读偏好（长辈模式/高对比/跟随系统字体）由设置页手动开关。本块订阅「系统配置变更」公共事件，
 *   让应用自动跟随系统级无障碍设置——长辈在系统里放大字号/开启高对比后，阅读器无需进设置即同步生效，
 *   降低长辈手动操作成本。属于适老化自动化的一环（与 ReaderPrefs.followSystemFont 同一脉络的升级）。
 *
 * 默认不接线：本文件仅作能力模板，需在 EntryAbility 或页面 @State 初始化处引用。
 */
import { READER_KEYS } from '../model/ReaderPrefs';
import { AppStorage } from '@kit.ArkUI';

/**
 * 系统配置变更回调的桥接示例：把系统无障碍状态同步进阅读偏好。
 * 真实接线时，把本函数挂到 Ability.onConfigurationUpdate 或 commonEventManager 的订阅回调内。
 * @param systemElder 系统是否处于「放大字号/无障碍」状态（由 newConfig 解析，见下方注释）
 * @param systemHighContrast 系统是否开启高对比/深色无障碍
 */
export function applySystemAccessibility(systemElder: boolean, systemHighContrast: boolean): void {
  // 跟随系统：系统开启无障碍字号 → 应用长辈模式自动开；高对比同理。
  // 注意：仅当 ReaderPrefs.followSystemFont/highContrast 为「跟随」语义时才自动覆盖，
  // 否则尊重用户手动设置（避免覆盖显式关闭）。具体门控在 ReaderPrefs 偏好读取处判定。
  AppStorage.setOrCreate(READER_KEYS.elderMode, systemElder);
  AppStorage.setOrCreate(READER_KEYS.highContrast, systemHighContrast);
}

/*
 * 接线参考（伪代码，需按 NEXT SDK 校准）：
 *
 * // 在 EntryAbility 内
 * onConfigurationUpdate(newConfig: Configuration): void {
 *   const elder = newConfig.fontSizeScale >= ELDER_FONT_SCALE; // 系统字号放大到长辈阈值
 *   const hc = newConfig.colorMode === ConfigurationConstant.ColorMode.COLOR_MODE_DARK; // 仅示意
 *   applySystemAccessibility(elder, hc);
 * }
 *
 * // 或用 commonEventManager（需 import { commonEventManager } from '@kit.NotificationKit'）：
 * const subscriber = {
 *   onReceive(eventData: CommonEventData) {
 *     // 解析 eventData 中的配置字段，调用 applySystemAccessibility(...)
 *   }
 * };
 * commonEventManager.subscribe(subscribeInfo, subscriber);
 *
 * 权限/声明：订阅系统配置变更通常为公开事件，无需额外权限；具体以 NEXT 当前 SDK 文档为准。
 */
