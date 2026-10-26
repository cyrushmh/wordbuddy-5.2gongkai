/**
 * BLE 中心设备扫描/广播构建块（来自 Batch20 的 BleCentralManager Java API8 样例，
 * 已翻成 HarmonyOS NEXT 的 @kit.ConnectivityKit.ble 概念）。
 *
 * 用途：组网无障碍的「本机侧」——发现附近同样装了本 App 的设备（广播同一服务 UUID），
 * 拿到设备名/地址后交给 DeviceSync 做分布式书签/进度同步；也可本机广播，让对方来发现。
 * 典型场景：长辈两台设备（手机+平板）靠近即互见，一键把正在读的《道德经》续到平板上。
 *
 * 默认不接线：组网同步真正落地仍由 DeviceSync（分布式 KV）完成，本块只负责「发现」这半步。
 * SDK 未验证（沙箱无 NEXT SDK），API 名称按官方文档写，真机接线以编译器为准。
 *
 * 接线（待你定）：
 *   1) 在组网状态卡加「发现附近设备」按钮 → scanner.discover();
 *   2) onFound 回调拿到 deviceId/name，列在组网卡下方，点击即 DeviceSync.connectTo(deviceId)；
 *   3) 本机需被发现的场景：scanner.advertise(SERVICE_UUID)。
 *
 * 权限（接线前需在 module.json5 声明，沙箱无法验证，名字以官方为准）：
 *   - ohos.permission.ACCESS_BLUETOOTH  （BLE 扫描/连接，必填）
 *   - 定位权限（ohos.permission.LOCATION / APPROXIMATELY_LOCATION，部分系统 BLE 扫描需）
 * 适老化要点：发现的设备名要随列表 announce 读屏；失败（蓝牙关闭）要有明确语音提示。
 */
import { ble } from '@kit.ConnectivityKit';

export interface BlePeer {
  deviceId: string;   // 设备地址（NEXT 中以 deviceId 标识）
  name: string;
}

export class BleScanner {
  private discovering: boolean = false;
  /** 发现附近设备时回调（每发现一个调一次）。 */
  onFound: (peer: BlePeer) => void = () => {};
  /** 扫描失败回调（如蓝牙未开）。 */
  onError: (code: number) => void = () => {};

  /** 开始扫描广播了指定服务 UUID 的设备（不传 uuid 则不过滤）。 */
  discover(serviceUuid?: string): void {
    if (this.discovering) return;
    this.discovering = true;

    const filters: ble.ScanFilter[] = [];
    if (serviceUuid) {
      filters.push({ serviceUuid: serviceUuid } as ble.ScanFilter);
    }

    const options: ble.ScanOptions = {
      interval: 0,
      dutyMode: ble.ScanDuty.SCAN_MODE_LOW_POWER,
      matchMode: ble.MatchMode.MATCH_MODE_AGGRESSIVE
    } as ble.ScanOptions;

    ble.startBLEScan(filters, options, (err: BusinessError, result?: ble.ScanResult) => {
      if (err) {
        this.discovering = false;
        this.onError(err.code);
        return;
      }
      if (result) {
        this.onFound({ deviceId: result.deviceId, name: result.deviceName ?? '' });
      }
    });
  }

  /** 停止扫描。 */
  stop(): void {
    if (this.discovering) {
      ble.stopBLEScan();
      this.discovering = false;
    }
  }

  /** 本机开始广播一个服务 UUID，让附近设备能发现本机。 */
  advertise(serviceUuid: string): void {
    const setting: ble.AdvertiseSetting = {
      interval: ble.AdvertiseInterval.INTERVAL_SLOT_DEFAULT,
      txPower: ble.TxPower.TX_POWER_DEFAULT,
      connectable: true
    } as ble.AdvertiseSetting;

    const data: ble.AdvertiseData = {
      serviceUuids: [serviceUuid],
      serviceData: undefined
    } as ble.AdvertiseData;

    ble.startAdvertising(setting, data, (err: BusinessError) => {
      if (err) this.onError(err.code);
    });
  }

  /** 停止广播。 */
  stopAdvertise(): void {
    ble.stopAdvertising();
  }
}
