import SwiftUI
import UniformTypeIdentifiers

/// 导入页（镜像 HarmonyOS 版 ImportText.ets）：从外部 txt 导入纯文本，
/// 经 TextEncoding 安全解码（BOM 剥离 → 严格 UTF-8 → 严格 GB18030 → 有损兜底），
/// 并做乱码指纹自检，把编码防护落到用户路径（呼应 justjavac/unicode-encoding-error-table）。
///
/// 与 HarmonyOS 端同一套防护逻辑：经典文本内嵌一律 UTF-8，本页只服务「外部导入」入口，
/// 防止错配编码（古文码/口字码/锟拷码）污染正文。
public struct ImportView: View {
    @State private var showImporter = false
    @State private var importedText = ""
    @State private var fileName = ""
    @State private var mojibake = false
    @State private var errorMessage = ""

    public init() {}

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Button {
                    showImporter = true
                } label: {
                    Label("选择 txt 文件导入", systemImage: "doc.badge.plus")
                }
                .buttonStyle(.borderedProminent)
                if !fileName.isEmpty {
                    Text(fileName)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            if !errorMessage.isEmpty {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .font(.callout)
            }

            if mojibake {
                Label("疑似编码错配（命中典型乱码指纹）。已按最安全方式解码，建议你确认原文件编码后重新导出。",
                      systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange)
                    .font(.callout)
                    .padding(10)
                    .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))
            }

            if importedText.isEmpty {
                ContentUnavailableView(
                    "尚未导入",
                    systemImage: "tray",
                    description: Text("从本地选择一本 txt 古籍／文本，自动识别 UTF-8 / GB18030 编码并安全解码。")
                )
            } else {
                ScrollView {
                    Text(importedText)
                        .font(.system(size: 17, design: .serif))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .textSelection(.enabled)
                }
                .frame(minHeight: 220)
            }
        }
        .padding()
        .navigationTitle("导入文本")
        .fileImporter(
            isPresented: $showImporter,
            allowedContentTypes: [.text],
            allowsMultipleSelection: false
        ) { result in
            handleResult(result)
        }
    }

    private func handleResult(_ result: Result<[URL], Error>) {
        errorMessage = ""
        switch result {
        case .failure(let err):
            errorMessage = "无法读取文件：\(err.localizedDescription)"
        case .success(let urls):
            guard let url = urls.first else { return }
            guard url.startAccessingSecurityScopedResource() else {
                errorMessage = "无法访问所选文件（权限受限）。"
                return
            }
            defer { url.stopAccessingSecurityScopedResource() }
            do {
                let data = try Data(contentsOf: url)
                importedText = TextEncoding.decodeSafe(data)
                fileName = url.lastPathComponent
                mojibake = TextEncoding.looksLikeMojibake(importedText)
            } catch {
                errorMessage = "读取失败：\(error.localizedDescription)"
            }
        }
    }
}
