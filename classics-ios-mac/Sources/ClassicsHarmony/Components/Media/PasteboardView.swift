import SwiftUI

/// 系统剪贴板（镜像 HarmonyOS 版 PasteboardOps.ets / @kit.BasicServicesKit）：
/// iOS 用 UIPasteboard，macOS 用 NSPasteboard。
public struct PasteboardView: View {
    @State private var text = "道生一，一生二"
    @State private var paste = ""

    public init() {}

    public var body: some View {
        VStack(spacing: 10) {
            TextField("待复制", text: $text)
                .textFieldStyle(.roundedBorder)
            Button("复制") { setClipboard(text) }
            Button("粘贴") { paste = getClipboard() }
            Text("剪贴板内容：\(paste)")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text("系统剪贴板（镜像 @kit.BasicServicesKit pasteboard）")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
    }

    private func setClipboard(_ s: String) {
        #if os(iOS)
        UIPasteboard.general.string = s
        #elseif os(macOS)
        let pb = NSPasteboard.general
        pb.clearContents()
        pb.setString(s, forType: .string)
        #endif
    }

    private func getClipboard() -> String {
        #if os(iOS)
        return UIPasteboard.general.string ?? ""
        #elseif os(macOS)
        return NSPasteboard.general.string(forType: .string) ?? ""
        #else
        return ""
        #endif
    }
}
