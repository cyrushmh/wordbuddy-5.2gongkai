/**
 * 缩放看图构建块（ArkTS 原生手势实现，无三方依赖）。
 *
 * 用途：道藏图册 / 古籍插图 / 碑帖的「双指缩放 + 旋转 + 单指拖拽」查看器。
 * 替代原 @ohos/photoview 三方库：用 PinchGesture + RotationGesture + PanGesture
 * 配合 Matrix4 自绘变换，零外部依赖、可离线编译、适老化可放大到 ≥4x。
 *
 * 可塞进 Swiper 做「左右翻页 + 单页缩放」图册（见下方 ZoomGallery）。
 *
 * 适老化要点：默认允许放大到 ≥4x；缩放/旋转状态用 accessibilityText 播报。
 */
import {
  Column,
  Stack,
  Image,
  ImageFit,
  Swiper,
  SwiperController,
  PinchGesture,
  RotationGesture,
  PanGesture,
  GestureGroup,
  GestureMode,
  PanDirection,
  Matrix4,
} from '@kit.ArkUI';

@Component
export struct ZoomImage {
  @State scale: number = 1;            // 缩放倍数（1~4）
  @State rotation: number = 0;         // 旋转角度（度）
  @State offsetX: number = 0;         // 拖拽位移 X
  @State offsetY: number = 0;         // 拖拽位移 Y
  @Prop resource: Resource = $r('app.media.startIcon');

  // 复位到初始视图
  private reset(): void {
    this.scale = 1;
    this.rotation = 0;
    this.offsetX = 0;
    this.offsetY = 0;
  }

  build() {
    Column() {
      Stack() {
        Image(this.resource)
          .width('100%')
          .height('100%')
          .objectFit(ImageFit.Contain)
          .transform(
            Matrix4.identity()
              .scale(this.scale, this.scale, 1)
              .rotate(this.rotation)
              .translate({ x: this.offsetX, y: this.offsetY })
          )
      }
      .width('100%')
      .height('100%')
      .gesture(
        GestureGroup(GestureMode.Parallel, [
          PinchGesture({ fingers: 2 })
            .onActionUpdate((e: GestureEvent) => {
              const next: number = this.scale * e.scale;
              this.scale = Math.min(4, Math.max(1, next));
            }),
          RotationGesture({ fingers: 2 })
            .onActionUpdate((e: GestureEvent) => {
              this.rotation = e.angle;
            }),
          PanGesture({ fingers: 1, direction: PanDirection.All })
            .onActionUpdate((e: GestureEvent) => {
              if (this.scale > 1) {
                this.offsetX += e.deltaX;
                this.offsetY += e.deltaY;
              }
            }),
        ])
      )
      .accessibilityText('古籍图片查看器，双指缩放旋转，单指拖动')
    }
    .width('100%')
    .height('100%')
  }
}

/** 翻页 + 缩放图册：Swiper 内嵌多张 ZoomImage（示意）。 */
@Component
export struct ZoomGallery {
  private controller: SwiperController = new SwiperController();
  @Prop resources: Resource[] = [];

  build() {
    Swiper(this.controller) {
      ForEach(this.resources, (res: Resource) => {
        ZoomImage({ resource: res });
      }, (res: Resource) => res.id?.toString() ?? '')
    }
    .loop(true)
    .indicator(true);
  }
}
