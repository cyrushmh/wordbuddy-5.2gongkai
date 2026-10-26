/**
 * 轻量偏好存储构建块（来自 Preferences，HarmonyOS Java API8 旧代）。
 *
 * 旧代 DatabaseHelper.getPreferences + putX/getX/flush + registerObserver；
 * NEXT 用 @kit.ArkTS 的 data.preferences（getPreferences + put/get/flush + on('change')）。
 * 适老化：长辈模式开关 / 字号档位 / 高对比 / 是否开启听书等设置的持久化，
 *   进程重启后自动恢复（呼应 B23 无障碍基线）。
 *
 * 未接线构建块：默认不接入任何页面；引用前在工程已内置 @kit.ArkTS（data.preferences 无需额外权限）。
 * 注意：data.preferences 异步，UI 用 @State 持有，open 后回填。
 */
import dataPreferences from '@kit.ArkData';
import { common } from '@kit.AbilityKit';

export class AppPreferences {
  private store: dataPreferences.Preferences | undefined;

  /** 打开（或创建）偏好文件。需在 UI 上下文（context）中调用。 */
  async open(context: common.UIAbilityContext, name: string): Promise<void> {
    this.store = await dataPreferences.getPreferences(context, name);
  }

  /** 写入并落盘（异步 flush）。 */
  async put(key: string, value: number | string | boolean): Promise<void> {
    if (!this.store) {
      return;
    }
    this.store.put(key, value);
    await this.store.flush();
  }

  async getNumber(key: string, def: number): Promise<number> {
    return this.store ? (await this.store.get(key, def) as number) : def;
  }

  async getString(key: string, def: string): Promise<string> {
    return this.store ? (await this.store.get(key, def) as string) : def;
  }

  async getBool(key: string, def: boolean): Promise<boolean> {
    return this.store ? (await this.store.get(key, def) as boolean) : def;
  }

  /** 监听某 key 变化（适老化：长辈模式开关后实时重载 UI）。 */
  watch(key: string, cb: () => void): void {
    this.store?.on('change', key, cb);
  }

  /** 移除某 key（delete + flush）。 */
  async remove(key: string): Promise<void> {
    if (!this.store) {
      return;
    }
    this.store.delete(key);
    await this.store.flush();
  }
}
