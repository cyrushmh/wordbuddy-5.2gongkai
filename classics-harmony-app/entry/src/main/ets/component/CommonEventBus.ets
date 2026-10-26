/*
 * CommonEventBus.ets —— 公共事件发布/订阅（构建块，翻 NEXT @ohos.commonEventManager）
 * 来源：Batch29 JavaCommonEventPublisher / JavaCommonEventSubscriber 两个样本。
 *   ⚠ 重要：这两个 7z 解压后仅含 .gradle / .idea 构建缓存，无 entry/src 源码，
 *       **无法从源码抽取概念**。本块按 NEXT 标准 commonEventManager API 补全发布/订阅范式，
 *       代际与精确字段以真机/重投完整包核验为准（不视为已核验源码）。
 * 代际：NEXT 翻写；旧代 CommonEventPublisher/Subscriber 用
 *   ohos.event.commonEvent.CommonEventManager.publish/subscribe，NEXT 同名语义，
 *   仅模块路径改为 @ohos.commonEventManager（或 @kit.NotificationKit 的 commonEventManager）。
 * NEXT 对应：import { commonEventManager } from '@kit.BasicServicesKit'
 *   - publish(publishData: CommonEventPublishData, callback?)
 *   - subscribe(subscribeInfo: CommonEventSubscribeInfo, subscriber)
 *   - unsubscribe(subscriber)
 * 适老化/组网无障碍：全局事件总线——「长辈触发紧急呼叫」广播给同端监听方；「读书进度变更」
 *   通知 ServiceWidget（Batch27）刷新桌面卡片；与 Batch23 DeviceSync（跨设备 KV 同步）互补：
 *   本块是本地进程/跨 Ability 广播，DeviceSync 是跨设备同步。
 * 权限：自定义事件（event 非系统保留名）一般无需额外权限；订阅系统保留事件才需对应权限。默认不接线。
 */
import { commonEventManager } from '@kit.BasicServicesKit';

export interface CommonEventBusOptions {
  /** 订阅/发布的事件名（自定义建议用反向域名，如 'com.classics.hmos.emergency'）。 */
  event: string;
  /** 发布时携带的业务码与数据。 */
  code?: number;
  data?: string;
}

/** 发布一个公共事件（对应旧代 CommonEventPublisher）。 */
export function publishEvent(opts: CommonEventBusOptions): void {
  // 接线：
  // const publishData: commonEventManager.CommonEventPublishData = {
  //   event: opts.event,
  //   bundleName: 'com.classics.hmos',
  //   data: { code: opts.code ?? 0, data: opts.data ?? '' }
  // };
  // commonEventManager.publish(publishData, (err) => { if (err) { /* 处理发布失败 */ } });
  void opts;
}

/**
 * 订阅一个公共事件（对应旧代 CommonEventSubscriber）。
 * @param opts       事件名等
 * @param onReceive  收到事件回调，回传业务码与数据
 * @returns 订阅句柄；接线后用于 unsubscribeEvent 注销
 */
export function subscribeEvent(
  opts: CommonEventBusOptions,
  onReceive: (code: number, data: string) => void
): commonEventManager.CommonEventSubscriber {
  // 接线：
  // const subscribeInfo: commonEventManager.CommonEventSubscribeInfo = {
  //   events: [opts.event]
  // };
  // const subscriber = commonEventManager.createSubscriber(subscribeInfo);
  // commonEventManager.subscribe(subscriber, (err, data) => {
  //   if (!err && data) { onReceive(data.code ?? 0, data.data ?? ''); }
  // });
  // return subscriber;
  void opts;
  void onReceive;
  return {} as commonEventManager.CommonEventSubscriber;
}

/** 注销订阅（避免泄漏）。 */
export function unsubscribeEvent(subscriber: commonEventManager.CommonEventSubscriber): void {
  // 接线：
  // commonEventManager.unsubscribe(subscriber);
  void subscriber;
}

/*
 * 接线伪代码（长辈端「一键紧急呼叫」广播给同端监听）：
 *   // 发布方（大字按钮）
 *   Button('紧急呼叫').onClick(() => publishEvent({ event: 'com.classics.hmos.emergency', data: '客厅' }));
 *   // 订阅方（守护 Ability 启动时）
 *   const sub = subscribeEvent({ event: 'com.classics.hmos.emergency' }, (code, data) => {
 *     // 弹通知 / 联动 Batch23 DeviceSync 跨设备同步给子女端
 *   });
 *   // 退出时
 *   unsubscribeEvent(sub);
 * 旧代对照：原样例 CommonEventManager.publish(helper, intent) / subscribe(subscriber)；
 *   NEXT 改为 publishData（含 event/bundleName/data）对象 + callback，订阅用 createSubscriber + subscribe。
 */
