/*
 * StorageStats.ets —— 存储空间统计（构建块，翻 NEXT @kit.CoreFileKit）
 * 来源：Batch24(中断补) DataUsage（Java API8：ohos.data.usage.DataUsage 查挂载状态/卷列表）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「查询存储卷总容量/剩余容量」概念做成未接线块。
 * NEXT 对应：import { storageStatistics, volumeManager } from '@kit.CoreFileKit'
 *          （getTotalSizeSync / getFreeSizeSync / getVolumeInfo 之类）。
 * 用途：下载离线书目/道藏图册前，先查剩余空间并对长辈提示「存储够不够」——无障碍透明化。
 * 默认不接线：本地存储查询无需额外权限（以 NEXT 当前 SDK 为准）。
 */
import { storageStatistics, volumeManager } from '@kit.CoreFileKit';

/** 默认卷的存储概览（未接线返回 0）。 */
export function getStorageInfo(): { total: number; free: number } {
  // 接线（volumeId 取主存储卷，具体来自 volumeManager.getVolumeInfo()[0].volumeId）：
  // const volumeId = volumeManager.getVolumeInfoSync()[0]?.volumeId ?? '';
  // const total = storageStatistics.getTotalSizeSync(volumeId);
  // const free = storageStatistics.getFreeSizeSync(volumeId);
  // return { total, free };
  void storageStatistics;
  void volumeManager;
  return { total: 0, free: 0 };
}

/** 人类可读的剩余空间提示（字节 → MB/GB）。 */
export function freeSpaceText(): string {
  const { free } = getStorageInfo();
  if (free >= 1073741824) {
    return `${(free / 1073741824).toFixed(1)} GB 可用`;
  }
  return `${(free / 1048576).toFixed(0)} MB 可用`;
}

/*
 * 接线伪代码（离线书目下载前校验）：
 *   const info = getStorageInfo();
 *   if (info.free < 50 * 1048576) {
 *     promptAction.showToast({ message: '存储空间不足，先清理再下载离线书目' });
 *     return;
 *   }
 * 旧代对照：原 DataUsage 查 MountState/Volume 列表（是否可插拔/虚拟卷）；NEXT 收口进 CoreFileKit
 *          的 storageStatistics + volumeManager，日常只需总/剩余容量即可。
 */
