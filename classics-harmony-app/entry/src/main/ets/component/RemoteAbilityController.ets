/*
 * RemoteAbilityController.ets —— 跨设备启动/停止远程 Ability（构建块，翻 NEXT @kit.DeviceManager）
 * 来源：Batch25 DistributedSchedulingStartStopRemotePA（Java API8：DeviceManager.getDeviceList + startAbility/stopAbility 带 deviceId + MULTI_DEVICE 标记）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「枚举可信设备 + 跨端拉起/停止 Ability」概念做成未接线块（组网无障碍）。
 * NEXT 对应：import { distributedDeviceManager } from '@kit.DeviceManager'（getAvailableDeviceListSync）
 *          + context.startAbility(want) / context.stopAbility(want)，want 内带 deviceId（旧版 MULTI_DEVICE 标记已废弃）。
 * 用途：在远端设备拉起/停止一个 Ability——如把「朗读服务」远程拉起在平板上播、用毕停止（比 Batch24
 *      RemoteAbilityLauncher 多了 stop 语义；RemoteAbilityLauncher 仅拉起，本块补「拉起+停止」成对控制）。
 * 权限：需 ohos.permission.DISTRIBUTED_DATASYNC（已在 module.json5 声明）+ 设备可信组网；默认不接线。
 */
import { distributedDeviceManager } from '@kit.DeviceManager';
import { common } from '@kit.AbilityKit';

/** 枚举当前组网内可信设备 id（未接线返回空数组）。 */
export function listTrustedDevices(context: common.Context, bundleName: string): string[] {
  // 接线：
  // const dm = distributedDeviceManager.createDeviceManager(context, bundleName);
  // return dm.getAvailableDeviceListSync().map(d => d.deviceId);
  void context;
  void bundleName;
  return [];
}

/** 在目标设备拉起指定 Ability（deviceId 空则本地拉起）。 */
export function startRemoteAbility(
  context: common.Context,
  deviceId: string,
  bundleName: string,
  abilityName: string,
  params?: Record<string, Object>
): void {
  // 接线：
  // const want = { deviceId, bundleName, abilityName, parameters: params ?? {} };
  // context.startAbility(want);
  void context;
  void deviceId;
  void bundleName;
  void abilityName;
  void params;
}

/** 在目标设备停止指定 Ability（远程 PA 停止范式）。 */
export function stopRemoteAbility(
  context: common.Context,
  deviceId: string,
  bundleName: string,
  abilityName: string
): void {
  // 接线：
  // const want = { deviceId, bundleName, abilityName };
  // context.stopAbility(want);
  void context;
  void deviceId;
  void bundleName;
  void abilityName;
}

/*
 * 接线伪代码（手机上远程拉起/停止平板朗读服务）：
 *   const dev = listTrustedDevices(getContext(this) as common.Context, 'com.classics.hmos')[0];
 *   startRemoteAbility(getContext(this) as common.Context, dev,
 *     'com.classics.hmos', 'com.classics.hmos.ReadAloudAbility', { bookId: 'daodejing' });
 *   // 用毕：
 *   stopRemoteAbility(getContext(this) as common.Context, dev,
 *     'com.classics.hmos', 'com.classics.hmos.ReadAloudAbility');
 * 旧代对照：原样例 start/stop 各构造一次带 deviceId 的 Operation + MULTI_DEVICE 标记；NEXT 把 deviceId 放进 want，
 *          停止用 context.stopAbility(want)，标记不再需要。与 Batch24 RemoteAbilityLauncher 同源，本块补 stop。
 */
