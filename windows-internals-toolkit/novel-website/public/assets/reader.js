// 阅读页逻辑：根据 ?novel=<id>&chapter=<序号> 加载章节 Markdown 并渲染，支持翻页
const mdCache = new Map();

async function getNovels() {
  const r = await fetch("/data/novels.json");
  return r.json();
}
async function getMarkdown(path) {
  if (mdCache.has(path)) return mdCache.get(path);
  const r = await fetch("/data/" + path);
  const t = await r.text();
  mdCache.set(path, t);
  return t;
}

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// 极简 Markdown -> HTML：分段、标题、粗体/斜体/行内代码、无序列表
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
    const text = line.trimEnd();
    if (!text.trim()) {
      closeUl();
      continue;
    }
    if (/^---+$/.test(text)) {
      closeUl();
      html += "<hr>";
      continue;
    }
    if (text.startsWith("# ")) {
      closeUl();
      html += `<h1>${inline(text.slice(2))}</h1>`;
    } else if (text.startsWith("## ")) {
      closeUl();
      html += `<h2>${inline(text.slice(3))}</h2>`;
    } else if (text.startsWith("### ")) {
      closeUl();
      html += `<h3>${inline(text.slice(4))}</h3>`;
    } else if (/^[-*] /.test(text)) {
      if (!inUl) {
        html += "<ul>";
        inUl = true;
      }
      html += `<li>${inline(text.slice(2))}</li>`;
    } else {
      closeUl();
      html += `<p>${inline(text)}</p>`;
    }
  }
  closeUl();
  return html;
}

function inline(s) {
  return escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

async function init() {
  const p = new URLSearchParams(location.search);
  const novelId = p.get("novel");
  const chapterIdx = parseInt(p.get("chapter") || "0", 10);
  const novels = await getNovels();
  const novel = novels.find((n) => n.id === novelId);
  if (!novel) {
    document.getElementById("chapter").innerHTML =
      "<p class='error'>未找到该作品</p>";
    return;
  }
  document.getElementById("title").textContent = novel.title;
  document.title = `${novel.title} · 阅读`;

  const ch = novel.chapters[chapterIdx];
  if (!ch) {
    document.getElementById("chapter").innerHTML =
      "<p class='error'>章节不存在</p>";
    return;
  }
  const md = await getMarkdown(ch.file);
  document.getElementById("chapter").innerHTML = renderMarkdown(md);

  const pager = document.getElementById("pager");
  const prev =
    chapterIdx > 0
      ? `<a href="/reader.html?novel=${encodeURIComponent(
          novelId
        )}&chapter=${chapterIdx - 1}">← 上一章</a>`
      : "";
  const next =
    chapterIdx < novel.chapters.length - 1
      ? `<a href="/reader.html?novel=${encodeURIComponent(
          novelId
        )}&chapter=${chapterIdx + 1}">下一章 →</a>`
      : "";
  pager.innerHTML = `<span class="ch-title">${escapeHtml(ch.title)}</span>${prev}${next}`;
}

init();
