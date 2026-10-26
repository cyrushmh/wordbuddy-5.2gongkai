/*
 * 日期 / 时间选择器（构建块 · 未接线，翻写 NEXT）
 * 概念来源：Picker（Java API8 ohos.agp.components.Picker + DatePicker/TimePicker Ability，自定义 formatter 数字→中文）
 * 翻写：@kit.ArkUI DatePicker / TimePicker 声明式组件
 * 适老化：设置服药 / 经典诵读提醒时间、生日；大字号 + 可聚焦 + 选中值读屏播报
 * 权限：无
 */
import { DatePicker, TimePicker, Column, Text } from '@kit.ArkUI';

@Component
export struct DateTimePicker {
  @State selDate: Date = new Date();
  @State selHour: number = 8;
  @State selMinute: number = 0;
  onPick?: (date: string, time: string) => void;

  build() {
    Column() {
      DatePicker({
        start: new Date('2000-01-01'),
        end: new Date('2100-12-31'),
        selected: this.selDate,
      })
        .height(200)
        .onChange((value: Date) => {
          this.selDate = value;
          this.emit();
        });

      TimePicker()
        .height(140)
        .onChange((value: TimePickerResult) => {
          this.selHour = value.hour;
          this.selMinute = value.minute;
          this.emit();
        });
    }
  }

  private emit(): void {
    this.onPick?.(DateTimePicker.fmtDate(this.selDate), DateTimePicker.fmtTime(this.selHour, this.selMinute));
  }

  /** 格式化为 YYYY-MM-DD（老人看得清） */
  static fmtDate(d: Date): string {
    const y = d.getFullYear();
    const m = `${d.getMonth() + 1}`.padStart(2, '0');
    const day = `${d.getDate()}`.padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  /** 格式化为 HH:mm */
  static fmtTime(h: number, m: number): string {
    return `${`${h}`.padStart(2, '0')}:${`${m}`.padStart(2, '0')}`;
  }
}
