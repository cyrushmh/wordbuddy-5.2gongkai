/**
 * 组网无障碍 · 网络构建块（默认未接入主流程）。
 *
 * 由 Batch15「ArkTSWifiManagerConnectToWifi」样例迁移其核心模式：
 *   wifiManager.addCandidateConfig(config) → wifiManager.connectToCandidateConfig(result)
 * 封装成「读联网状态 / 主动连网 / 开关 WiFi」的可复用、可构建、文档完整模块。
 *
 * 与 DeviceSync（分布式 KV 组网）的关系：
 *   - DeviceSync 管「多设备协同数据」（阅读偏好/书签漫游）；
 *   - 本文件管「底层 WiFi 联网」；
 *   - 二者合起来覆盖用户要的「组网无障碍」：既能感知/管理网络连接，
 *     也能把数据在设备间无障碍同步。
 *
 * 默认未接入主流程：当前阅读器功能（设置/书签/道藏/深链/轮播）不需要主动联网，
 *   仅首页「组网无障碍」卡片用 isNetworkActive() 只读呈现 WiFi 状态（无需权限弹框）。
 *
 * 接线须知（需主动连网时按此启用）：
 *   - module.json5 声明 ohos.permission.GET_WIFI_INFO（读状态）/ ohos.permission.SET_WIFI_INFO（连网/开关）；
 *   - 主动连网前用 PermissionHelper.isGranted 判 SET_WIFI_INFO，未授权则 requestPermissions 或引导 openAppManagement。
 */
import { wifiManager } from '@kit.ConnectivityKit';
import { announce } from './Accessibility';

/** 只读：WiFi 是否已开启/活跃。失败（无权限/异常）安全返回 false，不崩。 */
export function isNetworkActive(): boolean {
  try {
    return wifiManager.isWifiActive();
  } catch (e) {
    console.error(`isNetworkActive failed: ${(e as Error).message}`);
    return false;
  }
}

/** 组网无障碍播报：用通俗语言告知当前 WiFi 联网状态（读屏/长辈模式用）。 */
export function announceNetworkStatus(): void {
  announce(isNetworkActive() ? 'WiFi 已联网，可同步与在线阅读' : 'WiFi 未连接，部分在线功能暂不可用');
}

/**
 * 连接指定 WiFi（Batch15 样例模式）：添加候选配置 → 连接该配置。
 * 需 ohos.permission.SET_WIFI_INFO（+ 部分场景需定位）。默认未接线。
 * @returns 是否成功发起连接流程（不代表最终连上；结果以系统通知/状态为准）。
 */
export function connectWifi(ssid: string, password: string): boolean {
  if (!ssid) {
    return false;
  }
  try {
    const config: wifiManager.WifiDeviceConfig = {
      ssid: ssid,
      preSharedKey: password,
      securityType: 3 // WPA / WPA2-PSK
    };
    wifiManager.addCandidateConfig(config).then((result: number) => {
      wifiManager.connectToCandidateConfig(result);
      announce(`正在连接 ${ssid}`);
    }).catch((err: number) => {
      console.error(`connectWifi failed: ${err}`);
    });
    return true;
  } catch (e) {
    console.error(`connectWifi exception: ${(e as Error).message}`);
    return false;
  }
}

/** 开关 WiFi（需 SET_WIFI_INFO）。默认未接线。 */
export function setWifiEnabled(enabled: boolean): boolean {
  try {
    return wifiManager.enableWifi(enabled);
  } catch (e) {
    console.error(`setWifiEnabled failed: ${(e as Error).message}`);
    return false;
  }
}
