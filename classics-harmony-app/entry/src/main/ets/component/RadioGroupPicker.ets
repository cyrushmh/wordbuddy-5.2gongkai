/**
 * 单选按钮组构建块（来自 RadioButtonRadioContainer，HarmonyOS Java API8 旧代）。
 *
 * 旧代用 RadioContainer + RadioButton 做互斥单选；NEXT 用 ArkUI Radio + RadioGroup。
 * 适老化：设置项互斥选择（字号档位 / 主题 / 是否开启听书）的大字号控件，触屏可点整行。
 *
 * 未接线构建块：默认不接入任何页面，需要时在表单页引用 <RadioGroupPicker> 并把选中值写回状态。
 */
import { Radio, RadioGroup, Row, Column, Text, ForEach } from '@kit.ArkUI';

export interface RadioOption {
  value: string;
  label: string;
}

@Component
export struct RadioGroupPicker {
  @Prop options: RadioOption[] = [];
  @Link selected: string;        // 当前选中 value
  @Prop fontSize: number = 18;   // 适老化：默认大字号

  build() {
    RadioGroup({ group: 'single' }) {
      Column() {
        ForEach(this.options, (opt: RadioOption) => {
          Row() {
            Radio({ value: opt.value, group: 'single' })
              .checked(this.selected === opt.value)
              .width(24)
              .height(24)
              .onChange((isOn: boolean) => {
                if (isOn) {
                  this.selected = opt.value;
                }
              })
            Text(opt.label)
              .fontSize(this.fontSize)
              .margin({ left: 12 })
          }
          .width('100%')
          .onClick(() => { this.selected = opt.value; })  // 整行可点，适老化
          .padding({ top: 12, bottom: 12 })
        }, (opt: RadioOption) => opt.value)
      }
    }
    .onChange((value: string) => { this.selected = value; })
  }
}
