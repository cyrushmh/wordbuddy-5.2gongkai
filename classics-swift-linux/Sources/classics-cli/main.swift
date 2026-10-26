import Foundation
import ClassicsCore

// Linux 命令行前端。命令面与 classics-linux(C) / classics-rs(Rust) 保持一致，
// 便于三份实现互相对照验证「同一编码安全哲学」在不同语言下的行为一致性。

let VERSION = "1.0.0"

func usage() -> String {
    """
    classics \(VERSION) — 典籍阅读与编码安全工具（Swift on Linux）

    用法:
      classics list                       列出书目（按分类分组、组内按朝代时序）
      classics show <书名或id> [章号]      显示原文与译文；章号省略则显示全书
      classics decode <文件>              安全解码外部文本（UTF-8 → GB18030 → 有损标注）
      classics lint  <文件>               乱码特征自检

    说明:
      核心逻辑（ClassicsCore）与 iOS/macOS 端同源拷贝，数据契约完全一致。
      编码策略：绝不崩溃，宁可缺字不崩；宁可标注乱码，绝不假装解码成功。
    """
}

func cmdList() -> Int32 {
    for (cat, books) in BookShelf.grouped() {
        print("【\(cat)】")
        for b in books {
            let n = b.chapters.count
            var line = "  \(b.id)  《\(b.title)》  \(b.dynasty)·\(b.author)  \(n) 章"
            if let v = b.volumes { line += "  \(v) 卷" }
            if let c = b.commentator { line += "  \(c)" }
            print(line)
        }
    }
    let total = ClassicsData.books.count
    let chaps = ClassicsData.books.reduce(0) { $0 + $1.chapters.count }
    print("\n共 \(total) 部典籍，\(chaps) 章")
    return 0
}

func cmdShow(_ query: String, _ chapter: String?) -> Int32 {
    guard let book = ClassicsData.books.first(where: { $0.id == query || $0.title == query }) else {
        FileHandle.standardError.write("classics: 未找到《\(query)》，用 `list` 查看已安装典籍\n".data(using: .utf8)!)
        return 1
    }
    print("《\(book.title)》 \(book.dynasty)·\(book.author)")
    print("分类：\(book.category)")
    print("提要：\(book.summary)")
    print(String(repeating: "─", count: 40))

    if let c = chapter {
        guard let ch = book.chapters.first(where: { $0.id == "\(book.id)-\(c)" || $0.title == c || $0.title == "第\(c)章" }) else {
            FileHandle.standardError.write("classics: 《\(book.title)》无此章：\(c)\n".data(using: .utf8)!)
            return 1
        }
        print("【\(ch.title)】\n\(ch.original)\n\n译：\(ch.translation)")
        return 0
    }
    for ch in book.chapters {
        print("【\(ch.title)】\n\(ch.original)\n译：\(ch.translation)\n")
    }
    return 0
}

func readFile(_ path: String) -> Data? {
    guard let fh = FileHandle(forReadingAtPath: path) else { return nil }
    defer { try? fh.close() }
    return try? fh.readToEnd()
}

func cmdDecode(_ path: String) -> Int32 {
    guard let data = readFile(path) else {
        FileHandle.standardError.write("classics: 无法读取 \(path)\n".data(using: .utf8)!)
        return 1
    }
    let text = TextEncoding.decodeSafe(data)
    // 判定实际走了哪条路径（与 C/Rust 版输出口径一致，便于三实现对照）
    let enc: String
    if String(data: data, encoding: .utf8) != nil {
        enc = "utf-8"
    } else if text.contains("\u{FFFD}") {
        enc = "lossy(有损替换)"
    } else {
        enc = "gb18030"
    }
    print("文件=\(path)  字节=\(data.count)  判为=\(enc)")
    if TextEncoding.looksLikeMojibake(text) {
        print("警告：文本疑似编码错配（检出乱码指纹）")
    }
    print(String(repeating: "─", count: 40))
    print(text)
    return 0
}

func cmdLint(_ path: String) -> Int32 {
    guard let data = readFile(path) else {
        FileHandle.standardError.write("classics: 无法读取 \(path)\n".data(using: .utf8)!)
        return 1
    }
    let text = TextEncoding.decodeSafe(data)
    let f = FileHandle.standardError
    if TextEncoding.looksLikeMojibake(text) {
        f.write("\(path): 检出乱码指纹，疑似编码错配\n".data(using: .utf8)!)
        return 1
    }
    if text.contains("\u{FFFD}") {
        f.write("\(path): 存在无法映射的字节（U+FFFD），请确认原始编码\n".data(using: .utf8)!)
        return 1
    }
    print("\(path): OK（UTF-8 或 GB18030 严格解码通过，无乱码指纹）")
    return 0
}

// —— 入口 ——
let args = Array(CommandLine.arguments.dropFirst())
guard let cmd = args.first else {
    print(usage())
    exit(0)
}
switch cmd {
case "list":                      exit(cmdList())
case "show" where args.count >= 2: exit(cmdShow(args[1], args.count >= 3 ? args[2] : nil))
case "decode" where args.count >= 2: exit(cmdDecode(args[1]))
case "lint" where args.count >= 2:   exit(cmdLint(args[1]))
case "-h", "--help", "help":     print(usage()); exit(0)
case "-V", "--version":          print("classics \(VERSION) (Swift on Linux)"); exit(0)
default:
    FileHandle.standardError.write("classics: 未知命令 \(cmd)\n\n".data(using: .utf8)!)
    print(usage())
    exit(2)
}
