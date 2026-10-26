// 分布式键值存储（多设备协同）构建块 —— 由 ArkTSDistributedData 样例迁移。
//
// 用途：把阅读书签 / 阅读偏好从「单机 Preferences」升级为「多设备协同 KV」，
// 使手机与平板之间的书签、字号主题等可自动漫游。
//
// ⚠️ 默认未接入主流程（ReaderPrefs 仍用单机 Preferences）。本文件是「可复用构建块」：
//    - 多设备同步需真机 + 同一华为账号下的可信设备组；
//    - module.json5 需声明权限 "ohos.permission.DISTRIBUTED_DATASYNC"；
//    - 真正开启跨设备同步时，把下方 kvStoreType 改为 DEVICE_COLLABORATION 并打开 autoSync。
// 接入方式（需要时）：在 EntryAbility 调 initDistributed()，并将 ReaderPrefs 的读写改为走本类。

import { distributedKVStore } from '@kit.ArkData';
import { BusinessError } from '@kit.BasicServicesKit';

class DistributedPrefs {
  private kvManager: distributedKVStore.KVManager | undefined = undefined;
  private kvStore: distributedKVStore.SingleKVStore | undefined = undefined;

  /** 建 KVManager。context 用 UIAbilityContext 或 ApplicationContext 均可。 */
  public initKVManager(context: Context): void {
    try {
      const cfg: distributedKVStore.KVManagerConfig = {
        context: context,
        bundleName: 'com.example.classicsharmony'
      };
      this.kvManager = distributedKVStore.createKVManager(cfg);
    } catch (e) {
      console.error('DistributedPrefs initKVManager failed: ' + JSON.stringify(e));
    }
  }

  /** 建 KVStore。默认 SINGLE_VERSION（单机）；多设备协同改 DEVICE_COLLABORATION + autoSync:true。 */
  public initKVStore(storeId: string = 'classicsStore'): void {
    if (this.kvManager === undefined) {
      return;
    }
    const options: distributedKVStore.Options = {
      createIfMissing: true,
      encrypt: false,
      backup: false,
      autoSync: false,
      kvStoreType: distributedKVStore.KVStoreType.SINGLE_VERSION,
      securityLevel: distributedKVStore.SecurityLevel.S1
    };
    try {
      this.kvManager.getKVStore<distributedKVStore.SingleKVStore>(storeId, options, (err, store) => {
        if (err) {
          console.error(`DistributedPrefs getKVStore failed: Code:${err.code},message:${err.message}`);
          return;
        }
        this.kvStore = store;
        // 多设备协同时建议在此注册 store.on('dataChange', ...) 监听对端变更。
      });
    } catch (e) {
      const err = e as BusinessError;
      console.error(`DistributedPrefs initKVStore error: Code:${err.code},message:${err.message}`);
    }
  }

  public put(key: string, value: string): void {
    if (this.kvStore === undefined) {
      return;
    }
    this.kvStore.put(key, value, (err: BusinessError) => {
      if (err) {
        console.error(`DistributedPrefs put failed: Code:${err.code},message:${err.message}`);
      }
    });
  }

  public get(key: string, callback: (value: string) => void): void {
    if (this.kvStore === undefined) {
      return;
    }
    this.kvStore.get(key).then((data) => {
      callback(data.toString());
    }).catch((err: BusinessError) => {
      console.error(`DistributedPrefs get failed: Code:${err.code},message:${err.message}`);
    });
  }

  public delete(key: string): void {
    if (this.kvStore === undefined) {
      return;
    }
    this.kvStore.delete(key, (err: BusinessError) => {
      if (err) {
        console.error(`DistributedPrefs delete failed: Code:${err.code},message:${err.message}`);
      }
    });
  }
}

export default new DistributedPrefs();
