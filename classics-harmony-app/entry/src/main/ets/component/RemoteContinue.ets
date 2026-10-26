/*
 * RemoteContinue.ets —— 跨设备接续阅读（组网无障碍）
 * 来源：Batch23 ContinueRemoteFA + ContinueRemoteFACollaboration（Java API8：IAbilityContinuation / continueAbilityReversibly / DeviceManager.getDeviceList）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「枚举组网设备 + 保存/恢复阅读状态 + 可回迁流转」概念做成未接线块。
 * NEXT 对应 API（以当前 SDK 为准）：
 *   - 设备枚举：import { distributedDeviceManager } from '@kit.DeviceManager'，getAvailableDeviceListSync()
 *   - 跨端迁移：Ability 的 continuation 接口（@kit.DistributedHardwareKit 的 continuationManager）
 * 用途（组网无障碍）：正在读的书页一键流转到附近可信设备「接着读」——书/章/滚动位置随迁移 save/restore。
 *   与 DeviceSync（后台分布式 KV 静默同步）互补：DeviceSync 是「多端同数据」，本块是「把当前会话搬到另一台设备」。
 *   适老化场景：长辈在手机读，一键流转到平板大屏继续（配合 Batch22 DisplayModeAdapter 双栏放大）。
 * 默认不接线：权限需 ohos.permission.DISTRIBUTED_DATASYNC（已在 module.json5 声明）+ 设备可信组网。
 */
export interface ReadingState {
  bookId: string;       // 当前书
  chapterIndex: number; // 当前章
  scrollOffset: number; // 当前阅读滚动位置（用于续读定位）
}

/** 枚举当前组网内可信设备 id（NEXT: distributedDeviceManager.getAvailableDeviceListSync 之类）。 */
export function listTrustedDevices(): string[] {
  // 接线：const dm = distributedDeviceManager.createDeviceManager(context, bundleName);
  // return dm.getAvailableDeviceListSync().map(d => d.deviceId);
  return [];
}

/** 发起可回迁的接续：把当前阅读状态交给目标设备恢复。 */
export function continueReadingTo(deviceId: string, state: ReadingState): void {
  // 接线：实现 Ability 的 onSaveData 写入 state → continuationManager.continueAbility(deviceId, { reversible: true });
  // 目标端 onRestoreData 内用 state 还原，再 router.replaceUrl 到阅读页定位 scrollOffset。
  void deviceId;
  void state;
}

/*
 * 接线伪代码（阅读页 Ability 实现 IContinuation）：
 *   onSaveData(data) { data.setParam('bookId', this.bookId); data.setParam('chapter', this.idx); data.setParam('offset', this.offset); }
 *   onRestoreData(data) { this.bookId = data.getParam('bookId'); this.idx = data.getParam('chapter'); this.offset = data.getParam('offset'); }
 *   onContinueAbility() { this.router.replaceUrl({ url: 'pages/ChapterDetail', params: {...} }); }
 * 触发按钮「转到平板上读」：continueReadingTo(listTrustedDevices()[0], { bookId, chapterIndex, scrollOffset });
 */
