// 书库首页：拉取 data/novels.json 并渲染作品卡片
let ALL_NOVELS = [];

function cardHtml(n) {
  return `
      <a class="card" href="/reader.html?novel=${encodeURIComponent(n.id)}">
        <div class="cover">${n.cover || "📖"}</div>
        <div class="meta">
          <h2>${escapeHtml(n.title)}</h2>
          <p class="author">${escapeHtml(n.author || "佚名")}</p>
          <p class="blurb">${escapeHtml(n.blurb || "")}</p>
          <p class="count">${n.chapters.length} 章</p>
        </div>
      </a>`;
}

function renderShelf(list) {
  const shelf = document.getElementById("shelf");
  if (!list.length) {
    shelf.innerHTML = '<p class="empty">没有匹配的作品。</p>';
    return;
  }
  shelf.innerHTML = list.map(cardHtml).join("");
}

async function loadShelf() {
  const shelf = document.getElementById("shelf");
  try {
    const res = await fetch("/data/novels.json");
    if (!res.ok) throw new Error("无法加载书库");
    ALL_NOVELS = await res.json();
    if (!Array.isArray(ALL_NOVELS) || ALL_NOVELS.length === 0) {
      shelf.innerHTML =
        '<p class="empty">暂无作品，向 data/novels.json 添加一部吧。</p>';
      return;
    }
    renderShelf(ALL_NOVELS);
  } catch (e) {
    shelf.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  }
}

function filterShelf(q) {
  const k = q.trim().toLowerCase();
  if (!k) return renderShelf(ALL_NOVELS);
  renderShelf(
    ALL_NOVELS.filter(
      (n) =>
        (n.title || "").toLowerCase().includes(k) ||
        (n.author || "").toLowerCase().includes(k) ||
        (n.blurb || "").toLowerCase().includes(k)
    )
  );
}

const box = document.getElementById("q");
if (box) box.addEventListener("input", (e) => filterShelf(e.target.value));

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

loadShelf();
