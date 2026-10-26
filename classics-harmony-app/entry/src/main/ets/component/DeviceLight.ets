/*
 * 设备灯 / 呼吸灯控制（构建块 · 未接线，翻写 NEXT）
 * 概念来源：LightAgent（Java API8 ohos.light.agent.LightAgent 控制指示灯/呼吸灯，非相机闪光灯）
 *   旧代逻辑：getLightIdList 查询硬件支持灯 → turnOn(lightId, LightEffect) 自定义闪烁/呼吸 → turnOff 关闭
 * 翻写：NEXT 灯光 API 包名待核验（原 ohos.light 可能并入 @kit.Device 设备硬件能力，或 @kit.Multimedia 闪光灯）— 块内以 @ohos.light 占位、未接线
 * 适老化：夜间起夜柔光提醒、长辈紧急呼叫本地闪烁（与 CommonEventBus 的长辈紧急广播联动点亮呼吸灯）
 * 警告：灯光是否为设备硬件特性取决于机型 —— 调用前务必先查询支持列表（原 getLightIdList），不支持的机型应静默降级
 * 权限：灯光控制通常属系统特性，接线前确认是否需声明设备硬件权限（待核验）
 */
import { light } from '@ohos.light'; // 待核验：NEXT 包名未确定（疑似仍留 @ohos.light 或 @kit.DeviceServiceKit），DevEco 最终确认

export class DeviceLight {
  /** 查询设备支持的灯 ID 列表（空数组表示本机不支持灯控，应静默降级） */
  static getSupportedLightIds(): number[] {
    try {
      return light.getLightIdList() ?? [];
    } catch (e) {
      console.error(`DeviceLight.getSupportedLightIds fail: ${(e as Error).message}`);
      return [];
    }
  }

  /**
   * 点亮一盏灯（可带呼吸/闪烁效果）
   * @param lightId getSupportedLightIds 返回的灯 ID
   * @param brightness RGB 亮度 [r,g,b]，默认白光满亮
   * @param onMs 亮起时长(ms)，0 表示常亮
   * @param offMs 熄灭间隔(ms)，用于呼吸/闪烁；onMs=offMs=0 为常亮
   */
  static turnOn(
    lightId: number,
    brightness: [number, number, number] = [255, 255, 255],
    onMs: number = 0,
    offMs: number = 0
  ): boolean {
    try {
      // 原 LightBrightness + LightEffect 的一次性/呼吸效果，NEXT 用 lightId + 参数表达
      if (onMs > 0 || offMs > 0) {
        light.turnOn(lightId, { brightnessRgb: brightness, onTime: onMs, offTime: offMs });
      } else {
        light.turnOn(lightId, { brightnessRgb: brightness });
      }
      return true;
    } catch (e) {
      console.error(`DeviceLight.turnOn fail: ${(e as Error).message}`);
      return false;
    }
  }

  /** 关闭一盏灯 */
  static turnOff(lightId: number): boolean {
    try {
      light.turnOff(lightId);
      return true;
    } catch (e) {
      console.error(`DeviceLight.turnOff fail: ${(e as Error).message}`);
      return false;
    }
  }
}
