/*
 * 表格布局构建块（来自 TableLayout，HarmonyOS Java API8 旧代）。
 * 旧代 <TableLayout ohos:row_count="2" ohos:column_count="2"> 声明 2x2 表格，
 *   子 Text 用 ohos:text_alignment="center" 居中，单元格用 margin 拉开间距。
 * NEXT 用 ArkUI Table({ columns }) 原生表格容器 + TableCell 子组件（非 List 行列）。
 *   每格放一个 Text，textAlign(TextAlign.Center) 对应旧代居中；背景/边距用 TableCell 修饰符。
 * 适老化：对比表 / 参数表（字号档位、典籍篇幅、穴位对照）等规整数据一目了然。
 * 未接线构建块：默认不接入任何页面。
 */
import { Table, TableCell, Text, Column, TextAlign } from '@kit.ArkUI';

@Component
export struct TableView {
  build() {
    Column({ space: 8 }) {
      Table({ columns: 2 }) {
        TableCell() {
          Text('1')
            .fontSize(40)
            .textAlign(TextAlign.Center)
            .accessibilityText('第 1 格')
        }
        .width('50%')
        .padding(8)
        .backgroundColor('#3F56EA')

        TableCell() {
          Text('2')
            .fontSize(40)
            .textAlign(TextAlign.Center)
            .accessibilityText('第 2 格')
        }
        .width('50%')
        .padding(8)
        .backgroundColor('#00AAEE')

        TableCell() {
          Text('3')
            .fontSize(40)
            .textAlign(TextAlign.Center)
            .accessibilityText('第 3 格')
        }
        .width('50%')
        .padding(8)
        .backgroundColor('#00BFC9')

        TableCell() {
          Text('4')
            .fontSize(40)
            .textAlign(TextAlign.Center)
            .accessibilityText('第 4 格')
        }
        .width('50%')
        .padding(8)
        .backgroundColor('#00C0C0')
      }
      .width('100%')
      .backgroundColor('#87CEEB')
      .padding(8)
    }
    .width('100%')
  }
}
