import Foundation

/// 经典分类（经史子集 + 道藏）。
/// 借鉴 baochuquan/Books、NicholasBxt/FreeBook 的反面教训：扁平文件堆 + 仅靠文件名承载信息
/// 在书目稍多时即不可检索；经典文库必须有显式、可检索的分类维度。
public enum ClassicCategory: String, CaseIterable, Identifiable {
    case jing, shi, zi, ji, daozang
    public var id: String { rawValue }
    /// 中文标签
    public var label: String {
        switch self {
        case .jing: return "经"
        case .shi: return "史"
        case .zi: return "子"
        case .daozang: return "道藏"
        case .ji: return "集"
        }
    }
}

/// 经典书目（镜像 HarmonyOS 版 ClassicsData.ts 的 ClassicBook）。
/// 跨端一致：iOS / macOS / HarmonyOS NEXT 三端共用同一数据契约。
public struct ClassicBook: Identifiable, Hashable {
    public let id: String
    public let title: String
    public let author: String
    public let dynasty: String
    public let category: String          // 经 / 史 / 子 / 集 / 道藏
    public let summary: String
    public var chapters: [ClassicChapter]
    // —— 导入 book 类仓库教训：结构化元数据是刚需 ——
    public let volumes: Int?             // 卷数
    public let commentator: String?      // 注者（如「王弼注」）
    public let daozangNid: Int?          // 道藏部册号（在线跳转用）
    public let daozangId: Int?           // 道藏经号
    public let onlineUrl: String?        // 在线阅读地址

    public init(id: String, title: String, author: String, dynasty: String,
                category: String, summary: String, chapters: [ClassicChapter] = [],
                volumes: Int? = nil, commentator: String? = nil,
                daozangNid: Int? = nil, daozangId: Int? = nil, onlineUrl: String? = nil) {
        self.id = id
        self.title = title
        self.author = author
        self.dynasty = dynasty
        self.category = category
        self.summary = summary
        self.chapters = chapters
        self.volumes = volumes
        self.commentator = commentator
        self.daozangNid = daozangNid
        self.daozangId = daozangId
        self.onlineUrl = onlineUrl
    }
}

/// 章节（原文 + 译文，镜像 ArkTS 的 original / translation 字段）。
public struct ClassicChapter: Identifiable, Hashable {
    public let id: String
    public let title: String
    public let original: String
    public let translation: String
    /// 注文（如宋·蒋慎修《黄庭内外玉景经解》逐句注）；与 translation（白话译文）分工
    public let commentary: String

    public init(id: String, title: String, original: String, translation: String,
                commentary: String = "") {
        self.id = id
        self.title = title
        self.original = original
        self.translation = translation
        self.commentary = commentary
    }
}
