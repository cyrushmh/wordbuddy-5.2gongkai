// 全文搜索：拉取所有作品的章节 Markdown，建立内存索引，匹配关键词并展示高亮片段
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
function escapeReg(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function highlight(text, q) {
  const re = new RegExp("(" + escapeReg(q) + ")", "gi");
  return escapeHtml(text).replace(re, "<mark>$1</mark>");
}
function snippet(text, q) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return text.slice(0, 80);
  const s = Math.max(0, i - 30);
  return (s > 0 ? "…" : "") + text.slice(s, s + 120);
}

async function buildIndex() {
  const novels = await getNovels();
  const index = [];
  for (const n of novels) {
    for (let ci = 0; ci < n.chapters.length; ci++) {
      const ch = n.chapters[ci];
      const md = await getMarkdown(ch.file);
      index.push({ novel: n, chapter: ch, ci, text: md.replace(/\r/g, "") });
    }
  }
  return index;
}

let INDEX = null;
async function ensureIndex() {
  if (!INDEX) INDEX = await buildIndex();
  return INDEX;
}

async function search(q) {
  const k = q.trim();
  const box = document.getElementById("results");
  if (!k) {
    box.innerHTML = '<p class="hint">输入关键词，跨所有作品的正文检索。</p>';
    return;
  }
  const index = await ensureIndex();
  const lower = k.toLowerCase();
  const hits = index.filter((it) => it.text.toLowerCase().includes(lower));
  if (!hits.length) {
    box.innerHTML = `<p class="empty">没有匹配「${escapeHtml(k)}」的内容。</p>`;
    return;
  }
  box.innerHTML =
    `<p class="count">命中 ${hits.length} 个章节</p>` +
    hits
      .map(
        (it) => `
      <a class="result" href="/reader.html?novel=${encodeURIComponent(
        it.novel.id
      )}&chapter=${it.ci}">
        <div class="r-head"><span class="r-book">${escapeHtml(
          it.novel.title
        )}</span> · <span class="r-ch">${escapeHtml(it.chapter.title)}</span></div>
        <div class="r-snippet">${highlight(snippet(it.text, k), k)}</div>
      </a>`
      )
      .join("");
}

const input = document.getElementById("q");
input.addEventListener("input", (e) => search(e.target.value));

// 支持 ?q= 直达
const init = new URLSearchParams(location.search).get("q");
if (init) {
  input.value = init;
  search(init);
}
