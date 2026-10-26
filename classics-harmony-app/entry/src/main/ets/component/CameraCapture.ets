/**
 * 相机拍照构建块（来自 Batch21 的 CameraKit Java API8 样例，已翻成 HarmonyOS NEXT 的
 * @kit.CameraKit 概念；与 Batch18 的 ZoomImage 配合 = 「碑帖/古籍实物拍照 → 缩放精读」闭环）。
 *
 * 用途：适老化「长辈放大精读」的实物入口——把书架上的线装书、碑帖拓片、课堂板书拍下来，
 * 存为图片后交给 ZoomImage 双指缩放细看；也可用于「拍古籍→OCR/检索」的后续扩展。
 *
 * 默认不接线：相机是重能力（XComponent 表面 + 相机会话），需真机验证。本块给出骨架与
 * 关键步骤，SDK 未验证（沙箱无 NEXT SDK），API 名与生命周期以官方文档/编译器为准。
 *
 * 接线（待你定）：
 *   1) 在需要拍照的页放 <CameraCapture({ onPhoto: (uri) => this.openZoom(uri) }) />；
 *   2) onPhoto 拿到图片 URI 后 router 到 ZoomImage 页（或同页叠 ZoomImage 组件）；
 *   3) 关闭页时 release() 释放相机，避免占用。
 *
 * 权限（接线前需在 module.json5 声明）：
 *   - ohos.permission.CAMERA  （必填，敏感权限，需用户授权；可借 Batch14 的权限申请范式）
 * 适老化要点：快门按钮放大（≥44）、有「已拍好」语音反馈；拍完直接进放大视图，减少跳转困惑。
 */
import { camera } from '@kit.CameraKit';
import { XComponent, XComponentController } from '@kit.ArkUI';

@Component
export struct CameraCapture {
  /** 拍到照片后的回调，uri 为图片路径。 */
  onPhoto: (uri: string) => void = () => {};
  private xcCtl: XComponentController = new XComponentController();
  private cameraMgr?: camera.CameraManager;

  build() {
    Column() {
      // 预览表面：相机画面输出到这里
      XComponent({ id: 'cameraPreview', type: XComponentType.SURFACE, controller: this.xcCtl })
        .width('100%')
        .height(300)
        .onLoad((surfaceId: string) => {
          // TODO(真机)：用 surfaceId 创建相机输入→预览输出→会话开始；
          //   this.cameraMgr = camera.getCameraManager(ctx);
          //   const cam = this.cameraMgr.getSupportedCameras()[0];
          //   const previewOutput = this.cameraMgr.createPreviewOutput(surfaceId);
          //   const session = this.cameraMgr.createSession();
          //   session.addOutput(previewOutput); session.start();
        })

      Button('拍照')
        .width(120)
        .height(48)
        .margin({ top: 12 })
        .onClick(() => {
          // TODO(真机)：触发拍照，photoOutput.on('photoAssetAvailable', (uri) => this.onPhoto(uri))
        })
    }
  }

  /** 关闭页时释放相机资源。 */
  release(): void {
    // TODO(真机)：this.cameraMgr?.releaseSession(); 释放相机
  }
}
