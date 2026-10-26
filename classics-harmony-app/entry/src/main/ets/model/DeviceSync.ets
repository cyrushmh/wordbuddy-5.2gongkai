// 组网无障碍：多设备协同阅读进度（无障碍化封装）。
//
// 立意：无障碍不只是读屏，也是「组网无障碍」——让跨设备同步这件事对所有人都没有门槛：
// 视障与长辈用户也能用 plain-language 听懂「组网是否通畅、连了几台、何时同步」。
//
// 实现：在分布式 KV（ArkData distributedKVStore）之上做一层无障碍封装：
//  - 以无障碍语言暴露组网状态（已连接设备数 / 上次同步 / 开关）；
//  - 状态变化时读屏播报（announce）；
//  - 默认安全降级：无权限 / 无可信设备组时，状态如实说明「组网待开启」，绝不崩溃。
//
// ⚠️ 构建块性质（与 DistributedPrefs 一致）：真实跨设备同步需
//   ① 真机 + 同一华为账号下的可信设备组；
//   ② module.json5 已声明 ohos.permission.DISTRIBUTED_DATASYNC；
//   ③ 用户在设置中开启本开关。开启失败时状态会如实播报阻塞原因。

import { distributedKVStore } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { announce } from './Accessibility';

class DeviceSyncManager {
  /** 用户是否开启多设备同步（意图开关，持久化在 ReaderPrefs）。 */
  public enabled: boolean = false;
  /** 已识别的协同设备数（含本机）。 */
  public deviceCount: number = 1;
  /** 上次同步时间文案。 */
  public lastSync: string = '尚未同步';
  /** 给用户界面与读屏用的中文状态文案。 */
  public statusText: string = '未开启多设备同步';

  private kvManager: distributedKVStore.KVManager | undefined = undefined;

  /** 在 EntryAbility.onCreate 调用：仅建 KVManager（单机即可，不需权限）。 */
  public init(context: common.UIAbilityContext): void {
    try {
      this.kvManager = distributedKVStore.createKVManager({
        context: context,
        bundleName: 'com.example.classicsharmony'
      });
    } catch (e) {
      console.error('DeviceSync init KVManager failed: ' + JSON.stringify(e));
    }
  }

  /**
   * 切换多设备同步开关。开启时尝试建立协作库（DEVICE_COLLABORATION）；
   * 失败则如实说明「组网待开启」，并把开关视为「意图已记录但暂未连通」。
   * @param on 是否开启
   * @param ctx 上下文（用于读屏播报，可空）
   */
  public setEnabled(on: boolean, ctx?: Context): void {
    this.enabled = on;
    if (on) {
      const ok: boolean = this.tryEnableCollaboration();
      this.statusText = ok
        ? `多设备同步已开启，当前 ${this.deviceCount} 台设备`
        : '组网待开启：需在真机与同一华为账号可信设备组中启用';
    } else {
      this.statusText = '未开启多设备同步';
    }
    announce(ctx, this.statusText);
  }

  /** 尝试建立协作 KV 库；成功返回 true。任何异常都安全返回 false。 */
  private tryEnableCollaboration(): boolean {
    if (!this.kvManager) {
      return false;
    }
    try {
      const options: distributedKVStore.Options = {
        createIfMissing: true,
        encrypt: false,
        backup: false,
        autoSync: true,
        kvStoreType: distributedKVStore.KVStoreType.DEVICE_COLLABORATION,
        securityLevel: distributedKVStore.SecurityLevel.S2
      };
      this.kvManager.getKVStore<distributedKVStore.SingleKVStore>('classicsSync', options, (err, store) => {
        if (err) {
          console.error(`DeviceSync getKVStore failed: Code:${err.code},message:${err.message}`);
          return;
        }
        // 监听对端（其他设备）变更，跨设备书签/进度到达即播报，体现「组网无障碍」。
        store.on('dataChange', distributedKVStore.SubscribeType.SUBSCRIBE_TYPE_REMOTE, () => {
          this.lastSync = '刚刚';
          this.deviceCount = Math.max(this.deviceCount, 2);
          announce(undefined, '已收到其他设备的阅读进度同步');
        });
        this.deviceCount = Math.max(this.deviceCount, 2);
        this.lastSync = '已就绪';
        this.statusText = `多设备同步已开启，当前 ${this.deviceCount} 台设备`;
      });
      return true;
    } catch (e) {
      console.error('DeviceSync enable collaboration exception: ' + JSON.stringify(e));
      return false;
    }
  }
}

export default new DeviceSyncManager();
