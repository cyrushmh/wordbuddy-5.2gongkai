/**
 * 经典蓝牙（BR/EDR）设备发现 + 配对构建块（来自 Batch21 的 BluetoothHost /
 * BluetoothRemoteDevice 两个 Java API8 样例，已翻成 HarmonyOS NEXT 的
 * @kit.ConnectivityKit.bluetooth 概念）。
 *
 * 用途：组网无障碍的「备选近场通道」——当对面设备不支持分布式组网、或长辈更习惯
 * 「蓝牙配对」心智时，用经典蓝牙发现附近手机/平板并配对，配对后可由 DeviceSync 走
 * 已配对链路同步书签。与 Batch20 的 BleScanner 同源目标（发现附近设备），BLE 更省电、
 * 经典蓝牙兼容性更广，两块并存由你按场景选。
 *
 * 默认不接线：仅封装「开蓝牙→发现→配对」三步概念，未接 DeviceSync。SDK 未验证
 * （沙箱无 NEXT SDK），经典蓝牙 API 名在不同 NEXT 版本有变动，真机以编译器为准。
 *
 * 接线（待你定）：
 *   1) 组网卡加「蓝牙配对附近设备」入口 → finder.enableAndDiscover();
 *   2) onDiscovered 拿到 deviceId/name，列表展示，点击 finder.pair(deviceId)；
 *   3) 配对成功后 onPaired 回调里 DeviceSync.connectTo(deviceId)。
 *
 * 权限（接线前需在 module.json5 声明，沙箱无法验证，名字以官方为准）：
 *   - ohos.permission.USE_BLUETOOTH        （使用蓝牙，必填）
 *   - ohos.permission.DISCOVER_BLUETOOTH   （可被/主动发现，必填）
 *   - ohos.permission.LOCATION / APPROXIMATELY_LOCATION （设备发现常需定位，按系统）
 * 适老化要点：发现/配对结果要 announce 读屏；配对是敏感操作，需用户明确点击确认。
 */
import { bluetooth } from '@kit.ConnectivityKit';

export interface BtPeer {
  deviceId: string;
  name: string;
  paired: boolean;
}

export class BtPeerFinder {
  /** 发现到设备回调。 */
  onDiscovered: (peer: BtPeer) => void = () => {};
  /** 配对状态变化回调。 */
  onPaired: (deviceId: string, ok: boolean) => void = () => {};
  /** 蓝牙未开/失败回调。 */
  onError: (msg: string) => void = () => {};

  private host?: bluetooth.BluetoothHost;

  /** 打开蓝牙并开始发现（NEXT 经典蓝牙 API 形态，真机以编译器为准）。 */
  enableAndDiscover(): void {
    try {
      this.host = bluetooth.getHost();
      if (!this.host.getBluetoothState()) {
        this.host.enableBluetooth();
      }
      // 监听系统设备发现事件；NEXT 多以 bluetooth.on('deviceDiscover', cb) 形式
      bluetooth.on('deviceDiscover', (device: bluetooth.BluetoothRemoteDevice) => {
        this.onDiscovered({
          deviceId: device.getDeviceId(),
          name: device.getDeviceName() ?? '',
          paired: device.getPairState() === 1
        });
      });
      this.host.startBluetoothDiscovery();
    } catch (e) {
      this.onError(String(e));
    }
  }

  /** 配对指定设备。 */
  pair(deviceId: string): void {
    try {
      const dev = this.host?.getRemoteDevice(deviceId);
      if (dev) {
        dev.pair();
        this.onPaired(deviceId, true);
      }
    } catch (e) {
      this.onPaired(deviceId, false);
      this.onError(String(e));
    }
  }

  /** 停止发现。 */
  stop(): void {
    this.host?.stopBluetoothDiscovery();
    bluetooth.off('deviceDiscover');
  }
}
