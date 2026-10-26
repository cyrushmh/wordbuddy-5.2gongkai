/**
 * 太极装饰组件（来自 ArkUIDrawingComponents 的 Shape / Path / Circle 绘制）。
 *
 * 用 Path 画太极 S 分隔 + 双鱼眼，作为道家意象装饰；纯装饰故 accessibilityLevel(No) 降权，
 * 不挡读屏与长辈模式。
 *
 * 几何（viewPort 0..100，示意非精确）：外圆淡描边；右侧阴形由 S 曲面包络填充；
 * 上鱼眼在阴中留白、下鱼眼在阳中填色，读作太极。
 *
 * 接线（待你定）：在需要道家意象题头处放 <TaijiDecor({ size: 96 }) />，
 * 可替补 / 并列现有龙纹（chineseloong）。
 */
import { AccessibilityLevel } from '@kit.ArkUI';

@Component
export struct TaijiDecor {
  @Prop size: number = 96;
  @Prop color: string = '#aa3333';

  build() {
    Shape() {
      // 外圆（淡描边）
      Circle({ width: 100, height: 100 })
        .fillOpacity(0)
        .stroke(this.color)
        .strokeWidth(2);
      // 太极 S 分隔（右侧阴形）
      Path()
        .width(100)
        .height(100)
        .commands('M50 0 A50 50 0 0 1 50 100 A25 25 0 0 1 50 50 A25 25 0 0 0 50 0 Z')
        .fill(this.color);
      // 双鱼眼：上眼（阴中有阳，留白）/ 下眼（阳中有阴，填色）
      Circle({ width: 16, height: 16 })
        .offset({ x: 42, y: 17 })
        .fillOpacity(0)
        .stroke(this.color)
        .strokeWidth(2);
      Circle({ width: 16, height: 16 })
        .offset({ x: 42, y: 67 })
        .fill(this.color);
    }
    .viewPort({ x: 0, y: 0, width: 100, height: 100 })
    .width(this.size)
    .height(this.size)
    .accessibilityLevel(AccessibilityLevel.No);
  }
}
