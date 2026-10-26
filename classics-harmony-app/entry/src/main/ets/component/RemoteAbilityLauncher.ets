/*
 * RemoteAbilityLauncher.ets —— 跨设备启动 Ability（构建块，翻 NEXT @kit.DeviceManager）
 * 来源：Batch24 DistributedSchedulingStartRemoteFA（Java API8：DeviceManager.getDeviceList + startAbility 带 deviceId + FLAG_ABILITYSLICE_MULTI_DEVICE）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「枚举可信设备 + 指定 deviceId 跨端拉起 Ability」概念做成未接线块（组网无障碍）。
 * NEXT 对应：import { distributedDeviceManager } from '@kit.DeviceManager'（getAvailableDeviceListSync）
 *          + context.startAbility(want) 在 want 内带 deviceId 即可（旧版 MULTI_DEVICE 标记已废弃，deviceId 即分布式意图）。
 * 用途：在附近可信设备直接拉起同一应用的某页/某 Ability——如把「正在读的道藏图册」一键投到平板大屏打开。
 *       与 Batch23 RemoteContinue（会话迁移）互补：本块是「远程拉起另一个 Ability」，RemoteContinue 是「搬当前会话」。
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

/*
 * 接线伪代码（手机上点「在平板上打开道藏图册」）：
 *   const devices = listTrustedDevices(getContext(this) as common.Context, 'com.classics.hmos');
 *   if (devices.length === 0) { promptAction.showToast({ message: '未发现可信设备' }); return; }
 *   startRemoteAbility(getContext(this) as common.Context, devices[0],
 *     'com.classics.hmos', 'com.classics.hmos.ImageGalleryAbility',
 *     { album: 'daozang' });
 * 旧代对照：原样例 intent.setOperation(withDeviceId(...).withBundleName(...).withAbilityName(...))
 *           + addFlags(FLAG_ABILITYSLICE_MULTI_DEVICE)；NEXT 把 deviceId 直接放进 want，不再需要 MULTI_DEVICE 标记。
 */
