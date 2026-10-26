import Foundation

/// 书目分组与排序（书架 / 分栏 共用）：按分类分组（经史子集道藏），组内按朝代时序排序。
/// 抽出单点，避免 iOS 书架与 macOS 分栏各写一套、日后漂移。
public enum BookShelf {
    /// 朝代时序（组内排序基准；未知朝代沉底，保证不崩）。
    private static let dynastyOrder = [
        "春秋", "战国", "秦", "西汉", "东汉", "三国", "西晋", "东晋",
        "十六国", "南北朝", "隋", "唐", "五代", "十国", "宋", "元", "明", "清", "近现代"
    ]

    /// 分类排序优先级：经 → 史 → 子 → 集 → 道藏（其余沉底）。
    public static func categoryRank(_ cat: String) -> Int {
        let order = ["经", "史", "子", "集", "道藏"]
        for (i, key) in order.enumerated() where cat.contains(key) {
            return i
        }
        return order.count
    }

    /// 朝代在时序中的序号；未知朝代排末尾。
    public static func dynastyRank(_ dynasty: String) -> Int {
        dynastyOrder.firstIndex(of: dynasty) ?? dynastyOrder.count
    }

    /// 返回「分类 → 已排序书目」的分组结果，分类与组内均有序。
    public static func grouped() -> [(category: String, books: [ClassicBook])] {
        let groups = Dictionary(grouping: ClassicsData.books) { $0.category }
        let keys = groups.keys.sorted {
            if categoryRank($0) != categoryRank($1) {
                return categoryRank($0) < categoryRank($1)
            }
            return $0 < $1
        }
        return keys.map { key in
            let items = (groups[key] ?? []).sorted {
                if dynastyRank($0.dynasty) != dynastyRank($1.dynasty) {
                    return dynastyRank($0.dynasty) < dynastyRank($1.dynasty)
                }
                return $0.title < $1.title
            }
            return (key, items)
        }
    }
}
