/**
 * 开关构建块（来自 Switch，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.agp.components.Switch`（btn_switch）。
 * NEXT 用 ArkUI `Switch()`，@State isOn 双向绑定 onChange；
 * 适老化大号开关（复用长辈模式放大），状态文案同步。
 * 未接线构建块：默认不接入任何页面。
 */
import { Switch, Column, Text } from '@kit.ArkUI';

@Component
export struct SwitchView {
  @Prop isOn: boolean = false;
  @Prop label: string = '';
  private onChange: (on: boolean) => void = () => {};

  build() {
    Column({ space: 8 }) {
      if (this.label) {
        Text(`${this.label}：${this.isOn ? '开' : '关'}`).fontSize(20).fontColor('#333')
      }
      Switch({ isOn: this.isOn })
        .selectedColor('#1A73E8')
        .onChange((on: boolean) => {
          this.isOn = on;
          this.onChange(on);
        })
    }
  }
}
