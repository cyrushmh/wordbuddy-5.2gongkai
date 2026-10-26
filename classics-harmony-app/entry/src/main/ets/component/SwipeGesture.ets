/**
 * 滑动手势构建块（来自 SwipeJs，HarmonyOS JS FA 旧代）。
 *
 * 旧代 .hml `onswipe="touchMove"` + index.js `touchMove(e){ e.direction }` 处理滑动方向，
 * 另含 router.replace 页面跳转。
 * NEXT 用 ArkUI `SwipeGesture({ direction })` + `.onAction((e) => e.direction)`，
 * 或 `Swiper` 做整屏滑动；方向枚举 SwipeDirection.Left / Right / Up / Down / All。
 * 适老化：大滑动手势翻页 / 返回，比小按钮更好够到。
 * 未接线构建块：默认不接入任何页面。
 */
import { Column, Text, SwipeGesture, SwipeDirection } from '@kit.ArkUI';

@Component
export struct SwipeGestureView {
  @State hint: string = '左右滑动试试';
  private onSwipe: (dir: string) => void = () => {};

  build() {
    Column() {
      Text(this.hint).fontSize(24).fontColor('#333')
    }
    .width('100%')
    .height('100%')
    .gesture(
      SwipeGesture({ direction: SwipeDirection.All })
        .onAction((e) => {
          const dirMap: Record<number, string> = {
            [SwipeDirection.Left]: '左',
            [SwipeDirection.Right]: '右',
            [SwipeDirection.Up]: '上',
            [SwipeDirection.Down]: '下'
          };
          const name: string = dirMap[e.direction] ?? '';
          this.hint = `向${name}滑`;
          this.onSwipe(name);
        })
    )
  }
}
