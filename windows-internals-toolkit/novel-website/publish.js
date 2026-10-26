// 零依赖发布脚本：把一部小说编译为单文件、自包含 HTML（dist/<id>.html）
// 用法: node publish.js [novelId]
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA = join(__dirname, "data");
const DIST = join(__dirname, "dist");

// 极简 Markdown -> HTML（与前端 reader.js 保持一致）
function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
function inline(s) {
  return escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}
function renderMarkdown(md) {
  const lines = md.replace(/\r/g, "").split("\n");
  let html = "";
  let inUl = false;
  const closeUl = () => {
    if (inUl) {
      html += "</ul>";
      inUl = false;
    }
  };
  for (const line of lines) {
    const t = line.trimEnd();
    if (!t.trim()) {
      closeUl();
      continue;
    }
    if (/^---+$/.test(t)) {
      closeUl();
      html += "<hr>";
      continue;
    }
    if (t.startsWith("# ")) {
      closeUl();
      html += `<h1>${inline(t.slice(2))}</h1>`;
    } else if (t.startsWith("## ")) {
      closeUl();
      html += `<h2>${inline(t.slice(3))}</h2>`;
    } else if (t.startsWith("### ")) {
      closeUl();
      html += `<h3>${inline(t.slice(4))}</h3>`;
    } else if (/^[-*] /.test(t)) {
      if (!inUl) {
        html += "<ul>";
        inUl = true;
      }
      html += `<li>${inline(t.slice(2))}</li>`;
    } else {
      closeUl();
      html += `<p>${inline(t)}</p>`;
    }
  }
  closeUl();
  return html;
}

async function main() {
  const id = process.argv[2];
  const novels = JSON.parse(await readFile(join(DATA, "novels.json"), "utf8"));
  const target = id ? novels.find((n) => n.id === id) : novels[0];
  if (!target) {
    console.error("未找到作品:", id || "(默认第一部)");
    process.exit(1);
  }

  const chapters = [];
  for (const ch of target.chapters) {
    const md = await readFile(join(DATA, ch.file), "utf8");
    chapters.push({ title: ch.title, html: renderMarkdown(md) });
  }

  const toc = chapters
    .map((c, i) => `<li><a href="#ch${i}">${escapeHtml(c.title)}</a></li>`)
    .join("");
  const body = chapters
    .map((c, i) => `<section id="ch${i}">${c.html}</section>`)
    .join("");

  const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(target.title)}</title>
<style>
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",serif;max-width:720px;margin:0 auto;padding:1.2rem;line-height:1.8;color:#2b2b2b;background:#fbfaf6}
h1{font-size:1.8rem} h2{font-size:1.3rem;border-bottom:1px solid #e6e1d6;padding-bottom:.3rem}
.byline{color:#6b6b6b}
.toc{background:#fff;border:1px solid #e6e1d6;border-radius:12px;padding:1rem 1.4rem}
.toc a{color:#8a5a2b;text-decoration:none}
section{margin:2rem 0}
code{background:#eee;padding:0 .3em;border-radius:4px}
mark{background:#ffe9a8}
footer{color:#6b6b6b;font-size:.8rem;text-align:center;margin-top:3rem}
</style></head>
<body>
<h1>${escapeHtml(target.title)}</h1>
<p class="byline">${escapeHtml(target.author || "佚名")}</p>
<nav class="toc"><h3>目录</h3><ol>${toc}</ol></nav>
${body}
<footer>由 novel-website 发布脚本生成</footer>
</body></html>`;

  await mkdir(DIST, { recursive: true });
  const out = join(DIST, `${target.id}.html`);
  await writeFile(out, html, "utf8");
  console.log("✓ 已发布:", out, `(${chapters.length} 章)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
