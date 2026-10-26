import SwiftUI
#if os(macOS)
import AppKit
#endif

/// 缩放看图（镜像 HarmonyOS 版 ZoomImage.ets 原生手势重构）：
/// 双指缩放（MagnificationGesture）+ 旋转（RotationGesture）+ 单指拖拽（DragGesture）叠加。
/// 零外部依赖，对应 ArkTS 的 PinchGesture/RotationGesture/PanGesture + Matrix4。
public struct ZoomImageView: View {
    let imageName: String
    @State private var scale: CGFloat = 1
    @State private var angle: Angle = .zero
    @State private var offset = CGSize.zero

    public init(imageName: String = "startIcon") {
        self.imageName = imageName
    }

    public var body: some View {
        #if os(macOS)
        Image(nsImage: NSImage(named: imageName) ?? NSImage())
        #else
        Image(imageName)
        #endif
        .resizable()
        .scaledToFit()
        .scaleEffect(scale)
        .rotationEffect(angle)
        .offset(offset)
        .gesture(
            MagnificationGesture()
                .onChanged { scale = min(4, max(1, $0)) }
                .simultaneously(with: RotationGesture().onChanged { angle = $0 })
                .simultaneously(with: DragGesture().onChanged {
                    if scale > 1 { offset = $0.translation }
                })
        )
        .accessibilityLabel("古籍图片查看器，双指缩放旋转，单指拖动")
    }
}
