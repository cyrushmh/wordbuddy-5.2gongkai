import SwiftUI

/// 书架（镜像 HarmonyOS 版 BookListView / pages）。
/// 整体推进：按分类分组（Section 表头）、组内按朝代时序排序——
/// 分组/排序逻辑统一走 BookShelf，与 macOS 分栏、HarmonyOS 端检索一致。
public struct BookListView: View {
    public init() {}

    public var body: some View {
        let sections = BookShelf.grouped()
        List {
            ForEach(sections, id: \.category) { section in
                Section(header: Text(section.category)) {
                    ForEach(section.books) { book in
                        NavigationLink(value: book) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(book.title).font(.headline)
                                Text("\(book.author) · \(book.dynasty) · \(book.category)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Text(book.summary)
                                    .font(.caption2)
                                    .foregroundStyle(.tertiary)
                                    .lineLimit(2)
                            }
                        }
                    }
                }
            }
        }
        .navigationTitle("国学经典")
        .navigationDestination(for: ClassicBook.self) { book in
            ReaderView(book: book)
        }
    }
}
