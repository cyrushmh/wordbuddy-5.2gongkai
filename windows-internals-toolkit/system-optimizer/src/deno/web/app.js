/* sysweeper 本机 Web 控制台 —— 前端逻辑
 * 只做渲染与转发：所有数据都来自 /api → Python 后端。
 * 这里没有任何诊断逻辑，也不做任何写系统动作。
 */
"use strict";

const $ = (id) => document.getElementById(id);
const state = { settings: [], subsystems: [], report: null };

/* ── 基础 ── */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

let toastTimer = null;
function toast(msg, isErr) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = "toast"; }, 2600);
}

async function api(action, params) {
  // 大宗师·失败指路：三类失败（连不上 / 非 JSON / 业务错）各给下一步，不甩术语
  let r;
  try {
    r = await fetch("/api", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ action, params: params || {}, source: "web" }),
    });
  } catch {
    throw new Error("连不上控制台——确认 deno 控制台仍在运行、端口一致；可先开 " + location.origin + "/healthz 自检");
  }
  const j = await r.json().catch(() => null);
  if (!j) throw new Error("控制台返回异常（非 JSON）——刷新页面重试；持续失败先跑 python3 -m sysweeper webapi --once '{\"action\":\"ping\"}' 自查");
  if (!j.ok) throw new Error((j.error || "后端返回失败") + (j.hint ? "（下一步：" + j.hint + "）" : ""));
  return j.data;
}

/* ── 视图切换 ── */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    $("view-" + btn.dataset.view).classList.add("active");
    const load = {
      settings: loadSettings, subsystems: loadSubsystems,
      diagnose: loadDiagSelect, import: loadImportCaps, history: loadHistory,
      profiles: loadProfilesTab,
    }[btn.dataset.view];
    if (load) load();
  });
});

/* ── 总览 ── */
async function loadOverview() {
  const btn = $("ov-refresh");
  btn.disabled = true;
  btn.textContent = "跑总览中…";
  try {
    const [ping, sysmap, diag, man] = await Promise.all([
      api("ping", { host: true }),
      api("sysmap", { max_chars: 40000 }),
      api("diagnose", { max_chars: 4000 }),
      api("manifest", {}),
    ]);
    const h = ping.host || {};
    const d = h.detected || {};
    const acts = (man && man.actions) || [];
    const roN = acts.filter((a) => a.readonly).length;
    $("ov-host").innerHTML =
      `<b>宿主</b>：${esc(d.platform || h.system)} ${esc(d.version || "")}` +
      `${d.distro ? " · " + esc(d.distro) : ""} · ${esc(h.machine)} · Python ${esc(h.python)}` +
      `<br><span class="hint">sysweeper v${esc(ping.version)} · 参数 ${ping.settings_count} 项 · 子系统 ${ping.subsystem_count} 项 · ` +
      `动作白名单 ${acts.length} 个（只读 ${roN} / 需确认 ${acts.length - roN}，见 GET /manifest）</span>`;
    const tally = diag.tally || {};
    $("ov-tally").innerHTML = Object.keys(tally).sort()
      .map((k) => {
        const cls = k === "正常" ? "ok" : (k === "异常" ? "bad" : "warn");
        return `<div class="stat ${cls}"><div class="n">${tally[k]}</div><div class="l">${esc(k)}</div></div>`;
      }).join("");
    $("ov-sysmap").textContent = sysmap.text || "（空）";
    toast("总览已刷新");
  } catch (e) {
    $("ov-sysmap").textContent = "取不到总览：" + e.message;
    toast("刷新失败: " + e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "刷新总览";
  }
}
$("ov-refresh").addEventListener("click", loadOverview);

/* ── 参数与阈值 ── */
function ctlHtml(s) {
  const v = s.value;
  const unit = s.unit ? `<span class="unit">${esc(s.unit)}</span>` : "";
  if (s.kind === "int") {
    return `<input type="number" data-key="${esc(s.key)}" value="${esc(v)}"
      min="${esc(s.min == null ? "" : s.min)}" max="${esc(s.max == null ? "" : s.max)}">${unit}`;
  }
  if (s.kind === "enum") {
    const opts = (s.choices || []).map((c) =>
      `<option value="${esc(c)}" ${String(v) === String(c) ? "selected" : ""}>${esc(c || "（空·跟随环境）")}</option>`).join("");
    return `<select data-key="${esc(s.key)}">${opts}</select>`;
  }
  if (s.kind === "path" || s.kind === "str") {
    return `<input type="text" data-key="${esc(s.key)}" value="${esc(v)}" style="min-width:220px">`;
  }
  if (s.kind === "bool") {
    return `<input type="checkbox" data-key="${esc(s.key)}" ${v ? "checked" : ""}>`;
  }
  return `<span class="hint">${esc(String(v))}</span>`;
}

function renderSettings(items, changed, filterText) {
  const f = (filterText || "").trim().toLowerCase();
  const groups = {};
  items.forEach((s) => {
    if (f && !(s.key + s.label + s.group + s.desc).toLowerCase().includes(f)) return;
    (groups[s.group] = groups[s.group] || []).push(s);
  });
  const set = new Set(changed || []);
  let html = "";
  for (const g of Object.keys(groups)) {
    html += `<div class="group"><h4>${esc(g)}（${groups[g].length} 项）</h4>`;
    for (const s of groups[g]) {
      const isCh = set.has(s.key);
      html += `<div class="item ${isCh ? "changed" : ""}">
        <div class="k">${isCh ? '<span class="dot">●</span> ' : ""}${esc(s.key)}
          <span class="lb">${esc(s.label)}　默认 ${esc(s.default)}</span></div>
        <div><span class="desc">${esc(s.desc)}</span><span class="apply">生效点：${esc(s.apply)}</span></div>
        <div class="ctl">${ctlHtml(s)}
          <button class="btn" data-reset="${esc(s.key)}" title="恢复默认值">复位</button></div>
      </div>`;
    }
    html += `</div>`;
  }
  $("st-list").innerHTML = html || '<div class="hint">没有匹配的参数</div>';
  $("st-list").querySelectorAll("[data-reset]").forEach((b) =>
    b.addEventListener("click", () => resetOne(b.dataset.reset)));
}

async function loadSettings() {
  try {
    const d = await api("settings.list");
    state.settings = d.items;
    renderSettings(d.items, d.changed, $("st-filter").value);
    $("st-changed").textContent = d.changed.length
      ? `已改动 ${d.changed.length} 项：${d.changed.join("、")}` : "全部为默认值";
  } catch (e) { toast("参数载入失败: " + e.message, true); }
}

function collectPairs() {
  const pairs = {};
  state.settings.forEach((s) => {
    const el = $("st-list").querySelector(`[data-key="${s.key}"]`);
    if (!el) return;
    let v;
    if (s.kind === "int") v = Number(el.value);
    else if (s.kind === "bool") v = el.checked;
    else v = el.value;
    if (String(v) !== String(s.value)) pairs[s.key] = v;
  });
  return pairs;
}

async function saveSettings() {
  const pairs = collectPairs();
  if (!Object.keys(pairs).length) { toast("没有改动"); return; }
  try {
    const d = await api("settings.set", { pairs, note: "Web 控制台保存" });
    const bad = d.results.filter((r) => !r.ok);
    if (bad.length) toast(`有 ${bad.length} 项被拒绝：${bad[0].why}`, true);
    else toast(`已保存 ${Object.keys(pairs).length} 项`);
    await loadSettings();
  } catch (e) { toast("保存失败: " + e.message, true); }
}

async function resetOne(key) {
  try {
    await api("settings.reset_one", { key });
    toast(`已复位 ${key}`);
    await loadSettings();
  } catch (e) { toast("复位失败: " + e.message, true); }
}

$("st-refresh").addEventListener("click", loadSettings);
$("st-save").addEventListener("click", saveSettings);
$("st-filter").addEventListener("input", () =>
  renderSettings(state.settings, state.settings.filter((s) =>
    String(s.value) !== String(s.default)).map((s) => s.key), $("st-filter").value));
$("st-reset").addEventListener("click", async () => {
  if (!confirm("全部参数与阈值恢复默认值？")) return;
  try { await api("settings.reset", {}); toast("已全部恢复默认"); await loadSettings(); }
  catch (e) { toast("恢复失败: " + e.message, true); }
});

/* ── 子系统开关 ── */
function renderSubsystems(items, filterText) {
  const f = (filterText || "").trim().toLowerCase();
  const shown = items.filter((s) =>
    !f || (s.key + s.label + s.layer).toLowerCase().includes(f));
  $("ss-list").innerHTML = `<div class="ss-grid">` + shown.map((s) => `
    <label class="ss ${s.enabled ? "" : "off"}">
      <input type="checkbox" data-key="${esc(s.key)}" ${s.enabled ? "checked" : ""}>
      <div class="meta">
        <div class="lab">${esc(s.label)}</div>
        <div class="sub2">${esc(s.key)} · ${esc(s.module)}.${esc(s.fn)}()</div>
        <div class="layer">${esc(s.layer)}</div>
      </div>
    </label>`).join("") + `</div>`;
  $("ss-count").textContent = `显示 ${shown.length} / ${items.length}，已开启 ${items.filter((s) => s.enabled).length}`;
  $("ss-list").querySelectorAll("input[data-key]").forEach((cb) =>
    cb.addEventListener("change", () => toggleOne(cb.dataset.key, cb.checked)));
}

async function loadSubsystems() {
  try {
    const d = await api("subsystems.list");
    state.subsystems = d.items;
    renderSubsystems(d.items, $("ss-filter").value);
  } catch (e) { toast("子系统载入失败: " + e.message, true); }
}

async function toggleOne(key, on) {
  try {
    await api("subsystems.set", { key, on });
    toast(`${key} 已${on ? "开启" : "关闭"}`);
    await loadSubsystems();
  } catch (e) { toast("开关失败: " + e.message, true); await loadSubsystems(); }
}

$("ss-refresh").addEventListener("click", loadSubsystems);
$("ss-filter").addEventListener("input", () =>
  renderSubsystems(state.subsystems, $("ss-filter").value));
$("ss-all-on").addEventListener("click", () => setAll(true));
$("ss-all-off").addEventListener("click", () => setAll(false));
async function setAll(on) {
  if (!confirm(on ? "开启全部子系统？" : "关闭全部子系统？（总览将不再嵌入任何子系统）")) return;
  try { await api("subsystems.all", { on }); toast(on ? "已全开" : "已全关"); await loadSubsystems(); }
  catch (e) { toast("操作失败: " + e.message, true); }
}

/* ── 单子系统诊断 ── */
async function loadDiagSelect() {
  if ($("dg-key").options.length) return;
  try {
    const d = await api("subsystems.list");
    state.subsystems = d.items;
    $("dg-key").innerHTML = d.items.map((s) =>
      `<option value="${esc(s.key)}">${esc(s.label)}（${esc(s.key)}）${s.enabled ? "" : " [已关闭]"}</option>`).join("");
  } catch (e) { toast("子系统清单载入失败: " + e.message, true); }
}

async function runDiagnose() {
  const key = $("dg-key").value;
  if (!key) return;
  const btn = $("dg-run");
  btn.disabled = true; btn.textContent = "跑中…";
  $("dg-result").innerHTML = `<div class="card"><h3>${esc(key)}</h3><pre class="out">运行中…</pre></div>`;
  try {
    const d = await api("diagnose", { keys: [key], max_chars: 60000 });
    const it = d.items[0] || {};
    $("dg-result").innerHTML = `
      <div class="dg-card">
        <div class="dg-head">
          <b>${esc(it.label || key)}</b>
          <span class="badge ${esc(it.status)}">${esc(it.status)}</span>
          <span class="hint">${esc(it.layer || "")} · ${esc(key)}${it.truncated ? " · 正文已截断" : ""}</span>
        </div>
        <pre class="out">${esc(it.text || "（无输出）")}</pre>
      </div>`;
  } catch (e) {
    $("dg-result").innerHTML = `<div class="card"><pre class="out">诊断失败: ${esc(e.message)}</pre></div>`;
  } finally { btn.disabled = false; btn.textContent = "跑诊断"; }
}
$("dg-run").addEventListener("click", runDiagnose);

/* ── 导入 ── */
async function loadImportCaps() {
  try {
    const d = await api("import.capabilities");
    if (!$("im-source").options.length) {
      $("im-source").innerHTML = d.sources.map((s) =>
        `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join("");
    }
    $("im-caps").innerHTML =
      `<b>可用来源</b>：${d.sources.map((s) => esc(s.label) + "（" + esc(s.key) + "）").join(" / ")}
       <br><b>二维码后端</b>：${(d.qr_backends || []).map(esc).join("/") || "无（pip install opencv-python 或 pyzbar）"}
       <br><b>剪贴板后端</b>：${(d.clipboard_backends || []).map(esc).join("/") || "无（回退 tk）"}
       <br><b>读入上限</b>：${esc(d.max_bytes)} 字节`;
  } catch (e) { $("im-caps").textContent = "能力探测失败: " + e.message; }
}

$("im-read").addEventListener("click", async () => {
  $("im-text").textContent = "读取中…";
  try {
    const d = await api("import.read", { source: $("im-source").value, path: $("im-path").value });
    $("im-text").textContent = d.ok ? (d.text || "（空）") : "读取失败：" + d.note;
    $("im-msg").textContent = d.ok
      ? `来源 ${d.source} · ${d.length} 字符${d.truncated ? "（已截断显示）" : ""} · ${d.note}`
      : d.note;
  } catch (e) { $("im-text").textContent = "读取失败: " + e.message; }
});

$("im-load").addEventListener("click", async () => {
  if (!confirm("把导入内容里的设置 JSON 载入为参数？（只写你自己的配置文件）")) return;
  try {
    const d = await api("import.load", { source: $("im-source").value, path: $("im-path").value });
    $("im-msg").textContent = d.ok
      ? `已载入 ${d.applied.length} 项：${d.applied.map((a) => a.key).join("、")}` +
        (d.rejected.length ? `　已忽略：${d.rejected.join("、")}` : "")
      : "未载入：" + d.error;
    toast(d.ok ? "已载入为参数" : "未载入", !d.ok);
  } catch (e) { $("im-msg").textContent = "载入失败: " + e.message; }
});

/* ── 变更留痕 ── */
async function loadHistory() {
  try {
    const d = await api("settings.history", { limit: 100 });
    const rows = (d.rows || []).slice().reverse();
    $("hs-list").innerHTML = rows.length ? rows.map((r) => `
      <div class="hs">
        <div class="head">${esc(r.ts)} · 来源 ${esc(r.source)}${r.origin ? " · " + esc(r.origin) : ""}</div>
        <div class="ch">${Object.keys(r.changes || {}).map((k) =>
          `${esc(k)}: ${esc(r.changes[k].from)} <span class="arrow">→</span> ${esc(r.changes[k].to)}`).join("<br>")}</div>
        ${r.note ? `<div class="note">备注：${esc(r.note)}</div>` : ""}
      </div>`).join("") : '<div class="hint">暂无变更留痕</div>';
  } catch (e) { toast("留痕载入失败: " + e.message, true); }
}
$("hs-refresh").addEventListener("click", loadHistory);
$("hs-clear").addEventListener("click", async () => {
  if (!confirm("清空全部变更留痕？（参数值本身不变）")) return;
  try { await api("settings.history.clear", {}); toast("已清空"); await loadHistory(); }
  catch (e) { toast("清空失败: " + e.message, true); }
});

/* ── 快照报告 ── */
async function buildReport() {
  const inc = ["host", "settings", "subsystems"];
  if ($("rp-diagnose").checked) inc.push("diagnose");
  if ($("rp-sysmap").checked) inc.push("sysmap");
  if ($("rp-history").checked) inc.push("history");
  const btn = $("rp-build");
  btn.disabled = true; btn.textContent = "生成中…";
  $("rp-text").textContent = "生成中（含逐项诊断时要跑几十个只读探测，稍等）…";
  try {
    const rep = await api("report.build", { include: inc, max_chars: 8000 });
    state.report = rep;
    const t = rep.tally || {};
    $("rp-summary").innerHTML = Object.keys(t).sort().map((k) => {
      const cls = k === "正常" ? "ok" : (k === "异常" ? "bad" : "warn");
      return `<div class="stat ${cls}"><div class="n">${t[k]}</div><div class="l">${esc(k)}</div></div>`;
    }).join("") + `<div class="stat"><div class="n">${(rep.subsystems?.enabled || []).length}</div><div class="l">已开启子系统</div></div>`;
    $("rp-text").textContent = JSON.stringify(rep, null, 2).slice(0, 200000);
    toast("快照已生成");
  } catch (e) {
    $("rp-text").textContent = "生成失败: " + e.message;
    toast("生成失败", true);
  } finally { btn.disabled = false; btn.textContent = "生成快照"; }
}
$("rp-build").addEventListener("click", buildReport);
$("rp-download").addEventListener("click", () => {
  if (!state.report) { toast("先生成快照", true); return; }
  const blob = new Blob([JSON.stringify(state.report, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `sysweeper-report-${state.report.generated_at.replace(/[:T]/g, "-").slice(0, 19)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
});
$("rp-copy").addEventListener("click", async () => {
  if (!state.report) { toast("先生成快照", true); return; }
  try {
    await navigator.clipboard.writeText(JSON.stringify(state.report, null, 2));
    toast("已复制到剪贴板（可粘到远端报告查看器）");
  } catch { toast("复制失败，请手动从文本框选取", true); }
});

/* ── 档位与评分 ── */
const pct1 = (x) => (Number(x || 0) * 100).toFixed(1) + "%";
const fx3 = (x) => (typeof x === "number" ? (Number.isInteger(x) ? String(x) : x.toFixed(3)) : esc(x));

async function loadScore() {
  try {
    const s = await api("score.overview", {});
    $("pf-stats").innerHTML = [
      ["覆盖度总分", fx3(s.global_score), "ok"],
      ["归一化熵 H/log₂n", fx3(s.normalized_entropy), ""],
      ["Gini 集中度", fx3(s.gini), ""],
      ["任务总数", s.total_tasks, ""],
    ].map(([l, n, c]) => `<div class="stat ${c}"><div class="n">${esc(n)}</div><div class="l">${esc(l)}</div></div>`).join("");
    const p = s.global_parts || {};
    $("pf-parts").innerHTML =
      "<tr><th>维度</th><th>值</th><th>维度</th><th>值</th></tr>" +
      `<tr><td>覆盖广度 breadth</td><td>${pct1(p.breadth)}</td>` +
      `<td>分布均衡 entropy</td><td>${pct1(p.entropy)}</td></tr>` +
      `<tr><td>任务深度 depth</td><td>${pct1(p.depth)}</td>` +
      `<td>安全性 safety</td><td>${pct1(p.safety)}</td></tr>`;
    const d = s.distribution || {};
    const dist = Object.keys(d).sort((a, b) => d[b] - d[a])
      .map((k) => `${esc(k)}=${d[k]}`).join("  ");
    $("pf-gaps").textContent =
      (s.gaps && s.gaps.length ? "覆盖缺口：" + s.gaps.join("、") : "无覆盖缺口：每个分类都有任务")
      + (dist ? " ｜ 分类分布: " + dist : "");
  } catch (e) {
    $("pf-stats").innerHTML = `<div class="stat bad"><div class="n">!</div><div class="l">${esc(e.message)}</div></div>`;
  }
}

async function loadProfiles() {
  try {
    const d = await api("profiles.list", {});
    $("pf-table").innerHTML =
      "<tr><th>档位</th><th>中文名</th><th>最大风险</th><th>含 opt-in</th><th>命中任务</th></tr>" +
      d.profiles.map((p) =>
        `<tr><td class="k">${esc(p.name)}</td><td>${esc(p.title)}</td>` +
        `<td>${esc(p.max_risk)}</td><td>${p.include_opt_in ? "是" : "否"}</td>` +
        `<td>${p.count}</td></tr>`).join("") +
      d.scenarios.map((s) =>
        `<tr><td class="k">${esc(s.name)}</td><td>${esc(s.title)}（场景档，基于 ${esc(s.base)}）</td>` +
        `<td>—</td><td>—</td><td>${s.count}</td></tr>`).join("");
    const opts = d.profiles.map((p) => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join("");
    ["pf-name", "pf-against"].forEach((id) => { $(id).innerHTML = opts; });
    $("pf-name").value = "minimal";
    $("pf-against").value = "full";
  } catch (e) {
    $("pf-table").innerHTML = `<tr><td>${esc(e.message)}</td></tr>`;
  }
}

async function loadProfilesTab() {
  await loadScore();
  await loadProfiles();
}

$("pf-refresh").addEventListener("click", loadProfilesTab);
$("pf-show").addEventListener("click", async () => {
  $("pf-detail").textContent = "查询中…";
  try {
    const d = await api("profiles.show", { name: $("pf-name").value, limit: 40 });
    $("pf-detail").textContent =
      (d.detail || `档位 ${d.name}（场景档/无比对文本）`) +
      `\n\n── 任务清单（共 ${d.count} 项，展示前 ${Math.min(40, d.count)} 项）──\n` +
      (d.tasks || []).map((t) =>
        `  ${t.id}${t.opt_in ? " [opt_in]" : ""}  [${t.category}/${t.risk}]  ${t.title}`).join("\n");
  } catch (e) { $("pf-detail").textContent = "查询失败: " + e.message; }
});
$("pf-cmp").addEventListener("click", async () => {
  $("pf-detail").textContent = "对比中…";
  try {
    const d = await api("profiles.compare",
      { name: $("pf-name").value, against: $("pf-against").value, sample: 15 });
    $("pf-detail").textContent =
      `档位对比 ${d.a} vs ${d.b}（平台 ${d.platform} ${d.version}）\n` +
      `  任务数: ${d.a}=${d.count_a}   ${d.b}=${d.count_b}\n` +
      `  Jaccard 重合度 = ${d.jaccard.toFixed(4)}（|A∩B|/|A∪B|，1=完全相同）\n` +
      `  共有 ${d.shared_count} 项\n` +
      `  仅 ${d.a} 有: ${d.only_a_count} 项${d.only_a_sample.length ? "  例: " + d.only_a_sample.join(", ") : ""}\n` +
      `  仅 ${d.b} 有: ${d.only_b_count} 项${d.only_b_sample.length ? "  例: " + d.only_b_sample.join(", ") : ""}`;
  } catch (e) { $("pf-detail").textContent = "对比失败: " + e.message; }
});
$("pf-kmod").addEventListener("click", async () => {
  const btn = $("pf-kmod");
  btn.disabled = true; btn.textContent = "跑体检中…";
  $("pf-kmod-out").textContent = "跑只读探测中…";
  try {
    const d = await api("kmod.report", { max_chars: 40000 });
    $("pf-kmod-status").innerHTML =
      `<span class="badge ${esc(d.status)}">${esc(d.status)}</span> ${esc(d.summary)}`;
    $("pf-kmod-out").textContent = d.text + (d.truncated ? "\n…（已截断）" : "");
  } catch (e) {
    $("pf-kmod-status").textContent = "失败: " + e.message;
    $("pf-kmod-out").textContent = "失败: " + e.message;
  } finally { btn.disabled = false; btn.textContent = "跑内核只读体检"; }
});

$("pf-jdk").addEventListener("click", async () => {
  const btn = $("pf-jdk");
  btn.disabled = true; btn.textContent = "跑体检中…";
  $("pf-jdk-out").textContent = "跑只读探测中…";
  try {
    const d = await api("jdk.report", { max_chars: 40000 });
    $("pf-jdk-status").innerHTML =
      `<span class="badge ${esc(d.status)}">${esc(d.status)}</span> ${esc(d.summary)}`;
    $("pf-jdk-out").textContent = d.text + (d.truncated ? "\n…（已截断）" : "");
  } catch (e) {
    $("pf-jdk-status").textContent = "失败: " + e.message;
    $("pf-jdk-out").textContent = "失败: " + e.message;
  } finally { btn.disabled = false; btn.textContent = "跑 JDK/JVM 体检"; }
});

/* ── 启动自检 ── */
(async function boot() {
  try {
    const p = await api("ping", { host: false });
    $("backend").textContent = `后端就绪 · sysweeper v${p.version}`;
    $("backend").className = "pill pill-safe";
    $("readonly").textContent = `只读诊断 · 配置 ${p.settings_count} 项 / 子系统 ${p.subsystem_count} 项`;
  } catch (e) {
    $("backend").textContent = "后端未就绪: " + e.message;
    $("backend").className = "pill pill-bad";
    $("readonly").textContent = "下一步：重开控制台（deno run … src/deno/console.ts）或跑 webapi 自查";
  }
})();
