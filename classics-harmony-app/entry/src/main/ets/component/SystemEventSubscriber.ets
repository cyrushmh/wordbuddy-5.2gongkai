/*
 * SystemEventSubscriber.ets —— 系统公共事件订阅（与 Batch22 SystemEventHub 配对）
 * 来源：Batch23 CommonEventSubscriber（Java API8：CommonEventSubscriber.onReceiveEvent + CommonEventSubscribeInfo）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「订阅系统级公共事件」概念，补全 SystemEventHub 的订阅侧。
 * NEXT 对应：import { commonEventManager } from '@kit.NotificationKit'；subscribe(subscribeInfo, subscriber)；subscriber 覆写 onReceiveEvent。
 * 用途（系统使用无障碍）：订阅系统配置变更/电量低/屏幕开关/时区等公共事件，桥接适老化（与 SystemEventHub.applySystemAccessibility 协同）；
 *       也可是组网无障碍的「设备上线」轻量通知通道（DeviceSync 之外的事件总线）。
 * 默认不接线。
 */
import { applySystemAccessibility } from './SystemEventHub';

/*
 * 接线伪代码（以系统配置变更为例，事件名以 NEXT 当前常量/字符串为准）：
 * import { commonEventManager, CommonEventSubscribeInfo, CommonEventSubscriber } from '@kit.NotificationKit';
 *
 * class CfgSubscriber extends CommonEventSubscriber {
 *   constructor(info: CommonEventSubscribeInfo) { super(info); }
 *   onReceiveEvent(data: CommonEventData): void {
 *     // 解析 data 中系统新配置（字号/深色/无障碍），调用：
 *     applySystemAccessibility(systemElder, systemHighContrast);
 *   }
 * }
 *
 * const info = new CommonEventSubscribeInfo();
 * info.events = ['usual.event.configuration_changed']; // 以 NEXT 当前事件名常量为准
 * commonEventManager.subscribe(info, new CfgSubscriber(info));
 *
 * 权限：订阅公开系统事件通常无需额外权限；具体以 NEXT SDK 文档为准。
 */
