/*
 * 地理编码 / 逆地理编码（构建块 · 未接线，翻写 NEXT）
 * 概念来源：GeoConvert（Java API8 ohos.location.GeoConvert）
 * 翻写：@kit.LocationKit geoLocationManager.getAddressesFromLocation / getAddressesFromLocationName
 * 适老化：标注古籍善本收藏地 / 道观位置 / 作者籍贯，给长辈可见的「地名」而非裸坐标
 * 接线前：module.json5 声明 ohos.permission.LOCATION（及按需 LOCATION_IN_BACKGROUND）；本块不预填权限
 */
import { geoLocationManager } from '@kit.LocationKit';
import { BusinessError } from '@kit.BasicServicesKit';

export class GeoCoder {
  /**
   * 经纬度 -> 地址描述（逆地理编码）
   * @param lat 纬度
   * @param lon 经度
   * @param maxItems 最多返回条数
   * @returns 拼接后的可读地址，失败返回 ''
   */
  static async fromLocation(lat: number, lon: number, maxItems: number = 1): Promise<string> {
    try {
      const list = await geoLocationManager.getAddressesFromLocation(
        { latitude: lat, longitude: lon },
        maxItems
      );
      if (!list || list.length === 0) {
        return '';
      }
      const a = list[0];
      return [a.countryName, a.administrativeArea, a.locality, a.placeName]
        .filter((s) => s !== undefined && s !== null && s !== '')
        .join(' ');
    } catch (e) {
      const err = e as BusinessError;
      console.error(`GeoCoder.fromLocation fail: ${err.code} ${err.message}`);
      return '';
    }
  }

  /**
   * 地址描述 -> 坐标（地理编码）
   * @param name 地址/地名（如「华为」「杭州西湖」）
   * @param maxItems 最多返回条数
   * @returns 坐标对象，失败返回 null
   */
  static async fromName(name: string, maxItems: number = 1): Promise<{ latitude: number; longitude: number } | null> {
    try {
      const list = await geoLocationManager.getAddressesFromLocationName(name, maxItems);
      if (!list || list.length === 0) {
        return null;
      }
      const a = list[0];
      return { latitude: a.latitude, longitude: a.longitude };
    } catch (e) {
      const err = e as BusinessError;
      console.error(`GeoCoder.fromName fail: ${err.code} ${err.message}`);
      return null;
    }
  }
}
