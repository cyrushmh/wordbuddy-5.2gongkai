import SwiftUI

/// 整体容器：iOS 用底部 TabView（书架 / 对弈 / 设置），macOS 用 NavigationSplitView（书目 + 详情）。
/// 镜像 HarmonyOS 版 BottomTabs / Tabs，体现「整体与局部」——整体导航结构一致，局部按平台落地。
public enum Pane: Hashable { case reader, games, settings, importText }

public struct ContentView: View {
    @State private var selectedBook: ClassicBook?
    @State private var pane: Pane = .reader

    public init() {}

    public var body: some View {
        #if os(macOS)
        NavigationSplitView {
            List {
                ForEach(BookShelf.grouped(), id: \.category) { section in
                    Section(section.category) {
                        ForEach(section.books) { book in
                            Button {
                                selectedBook = book
                                pane = .reader
                            } label: {
                                Label(book.title, systemImage: "book.closed")
                            }
                        }
                    }
                }
                Section("工具") {
                    Button { pane = .games } label: { Label("对弈", systemImage: "puzzlepiece") }
                    Button { pane = .importText } label: { Label("导入", systemImage: "square.and.arrow.down") }
                    Button { pane = .settings } label: { Label("设置", systemImage: "gearshape") }
                }
            }
            .navigationTitle("国学经典")
        } detail: {
            detailView
        }
        .frame(minWidth: 820, minHeight: 620)
        #else
        TabView {
            NavigationStack {
                BookListView()
            }
            .tabItem { Label("书架", systemImage: "books.vertical") }

            GamesView()
                .tabItem { Label("对弈", systemImage: "puzzlepiece") }

            ImportView()
                .tabItem { Label("导入", systemImage: "square.and.arrow.down") }

            SettingsView()
                .tabItem { Label("设置", systemImage: "gearshape") }
        }
        #endif
    }

    @ViewBuilder
    private var detailView: some View {
        switch pane {
        case .reader:
            if let book = selectedBook {
                ReaderView(book: book)
            } else {
                Text("选择左侧书目开始阅读").foregroundStyle(.secondary)
            }
        case .games:
            GamesView()
        case .importText:
            ImportView()
        case .settings:
            SettingsView()
        }
    }
}
