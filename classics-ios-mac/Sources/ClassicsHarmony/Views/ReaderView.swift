import SwiftUI

/// 阅读页（镜像 HarmonyOS 版 ReaderView + TextView.ets 文本综合）：
/// 原文（衬线大字）/ 译文（次级）/ 字号可调（适老化）。
public struct ReaderView: View {
    let book: ClassicBook
    @State private var fontSize: Double = 19

    public init(book: ClassicBook) {
        self.book = book
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(book.title).font(.largeTitle.bold())
                Text("\(book.author) · \(book.dynasty) · \(book.category)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(book.summary)
                    .font(.body.italic())
                    .foregroundStyle(.secondary)

                Divider()

                if book.chapters.isEmpty {
                    Text("（本样本版仅列书目；全本原文请见 HarmonyOS 版 ClassicsData.ts，按 ClassicChapter 结构迁移即可。）")
                        .font(.callout)
                        .foregroundStyle(.tertiary)
                } else {
                    ForEach(book.chapters) { ch in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(ch.title).font(.headline)
                            Text(ch.original)
                                .font(.system(size: fontSize, design: .serif))
                                .lineSpacing(6)
                            Text(ch.translation)
                                .font(.system(size: fontSize * 0.9))
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .padding()
            .frame(maxWidth: 720, alignment: .leading)
        }
        .navigationTitle(book.title)
        .toolbar {
            Slider(value: $fontSize, in: 14...34) { Text("字号") }
                .frame(width: 160)
        }
    }
}
