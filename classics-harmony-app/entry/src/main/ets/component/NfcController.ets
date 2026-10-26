/*
 * NFC 状态查询（构建块 · 未接线，翻写 NEXT）
 * 概念来源：NfcController（Java API8 ohos.nfc.NfcController isNfcAvailable / isNfcOpen / openNfc）
 * 翻写：@kit.ConnectivityKit nfcController.isNfcAvailable / isNfcEnabled
 * 适老化：老人机 NFC 门禁/公交卡场景前的硬件可用性自检；NEXT 不提供程序化开启（需用户授权），
 *          开启走系统设置——接 B28 SystemIntentLauncher 跳 NFC 设置页
 * 权限：NFC 相关权限（ohos.permission.NFC_TAG 等）接线前声明，本块仅查询不预填
 */
import { nfcController } from '@kit.ConnectivityKit';

export class NfcController {
  /** 本机是否具备 NFC 硬件 */
  isAvailable(): boolean {
    try {
      return nfcController.isNfcAvailable();
    } catch (e) {
      console.error(`NfcController.isAvailable fail: ${(e as Error).message}`);
      return false;
    }
  }

  /** NFC 当前是否已开启 */
  isEnabled(): boolean {
    try {
      return nfcController.isNfcEnabled();
    } catch (e) {
      console.error(`NfcController.isEnabled fail: ${(e as Error).message}`);
      return false;
    }
  }

  /** 引导用户去系统 NFC 设置页开启（程序无法代开，需用户手动授权） */
  openSettingsHint(): string {
    // 接 SystemIntentLauncher.openAppSettings('nfc') 或 action.system.settings
    return 'nfc_settings';
  }
}
