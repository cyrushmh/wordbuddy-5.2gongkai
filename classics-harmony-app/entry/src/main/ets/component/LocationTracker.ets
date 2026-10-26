/*
 * 定位获取当前坐标（构建块 · 未接线，翻写 NEXT）
 * 概念来源：Locator（Java API8 ohos.location.Locator + RequestParam(PRIORITY_ACCURACY) + LocatorCallback 持续回调）
 * 翻写：@kit.LocationKit geoLocationManager.getCurrentLocation / on('locationChange') / off('locationChange')
 * 适老化：老人防走失（子女端经 Batch23 DeviceSync 跨设备查实时位置）、附近书院/国学馆导航
 * 权限：ohos.permission.LOCATION（NEXT 需在 module.json5 声明 + 运行时 atManager 动态申请；首次定位前务必授权）
 */
import { geoLocationManager } from '@kit.LocationKit';

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export class LocationTracker {
  /** 单次定位：返回当前经纬度（精度优先）；失败返回 null */
  static async getCurrentLocation(): Promise<GeoPoint | null> {
    try {
      const loc: geoLocationManager.Location = await geoLocationManager.getCurrentLocation();
      return { latitude: loc.latitude, longitude: loc.longitude };
    } catch (e) {
      console.error(`LocationTracker.getCurrentLocation fail: ${(e as Error).message}`);
      return null;
    }
  }

  /** 开始持续定位，回调每次位置更新 */
  static startUpdates(onUpdate: (p: GeoPoint) => void): void {
    try {
      geoLocationManager.on('locationChange', (loc: geoLocationManager.Location) => {
        onUpdate({ latitude: loc.latitude, longitude: loc.longitude });
      });
    } catch (e) {
      console.error(`LocationTracker.startUpdates fail: ${(e as Error).message}`);
    }
  }

  /** 停止持续定位（callback 留空则注销全部监听） */
  static stopUpdates(callback?: (loc: geoLocationManager.Location) => void): void {
    try {
      geoLocationManager.off('locationChange', callback);
    } catch (e) {
      console.error(`LocationTracker.stopUpdates fail: ${(e as Error).message}`);
    }
  }
}
