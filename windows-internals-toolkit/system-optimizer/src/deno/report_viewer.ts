/**
 * sysweeper 报告查看器（0000.0000.0000.0018.20261025 + 圆光术视觉范式）—— 可部署到 Deno Deploy 的纯展示服务。
 *
 * 它是什么：把 `sysweeper webapi` 的 `report.build` 产出的**只读诊断快照 JSON**
 * 渲染成可读网页，便于分享 / 留档 / 前后对比。
 *
 * 它不是什么：**不含任何诊断逻辑，没有任何后端存储，连不到你的机器**。
 * 诊断必须在本机跑（sysfs/注册表/硬件只有本机读得到），跑完把 JSON
 * 粘进来 / 拖进来 / 用链接带来，这里只负责「看得清」。
 *
 * 部署到 Deno Deploy（过渡期可用，注意 Deno 团队已于 2026-10-09 加入 Cloudflare，
 * Deno Deploy 约 6 个月后退场）：
 *   1. 把本文件放进一个 git 仓库（或直接用 deployctl）：
 *        deployctl deploy --project=sysweeper-report src/deno/report_viewer.ts
 *   2. 或在 dash.deno.com 新建项目，关联仓库，入口文件选本文件。
 *   无环境变量、无密钥、无数据库——纯静态行为。
 *
 * 长期稳定方案：本文件吐出的页面已抽成单文件静态页 `report_viewer.html`，
 * 不依赖 Deno / 任何平台，双击即用，可直接放 GitHub Pages 等静态托管。
 *
 * 本地预览：
 *   deno run --allow-net src/deno/report_viewer.ts [--port 8899]
 *
 * 用户端人体工程学（《南华真经》核心理念，详见 concepts zhuangzi）：
 *   · 逍遥游 → 无待一步：拖文件 / 粘贴 / 示例 / 链接四种入口平权，
 *     任一入口直达渲染；两份报告依次渲染自动出前后对比。
 *   · 应帝王 → 顺应性情：渲染后输入区不锁死，「再载入一份做对比」与
 *     「返回重来」随时可达，默认视图即大多数人要看的对比结论。
 *   · 大宗师 → 意图宗师：JSON 解析失败不甩术语，直接给下一步
 *     （缺 schema 字段仍是好稿 / 文件是否下全 / 换粘贴入口再试）。
 *   · 养生主 → 不伤：URL 分享前明示隐私代价（公开发布），数据不出浏览器。
 *
 * 数据入口：
 *   - 网页里粘贴 / 拖入 JSON 文件（首选，报告不出机器也能看）；
 *   - URL 携带：/#r=<base64url(JSON)>（注意 URL 长度限制，报告大时用粘贴）。
 *   隐私：数据只留在浏览器里（不回传任何服务器）；用 URL 分享等于公开发布，自行斟酌。
 *
 * 视觉范式（《圆光术》指导理念，详见 concepts 文档 GUI圆光术指导理念与基本设计原则.md）：
 *   · 圆 → 中心辐射：报告结论居中呈现，不堆菜单；本查看器自身即以「圆」为体。
 *   · 光 → 明暗聚焦：异常 / 变化以光晕高亮，静默处自然淡出，不靠加重边框喧哗。
 *   · 术 → 整体全息：依次载入两份报告即自动出前后对比（全息并置），任何时刻可回看本理念。
 *   诚实边界：本查看器只读、纯展示、数据不出浏览器——概念系统的红线在 GUI 同样生效。
 */
// deno-lint-ignore-file no-explicit-any

const VERSION = "0000.0000.0000.0034.20261026";

function page(): string {
  // 注意：内嵌 JS 刻意不用模板字符串，避免与 TS 模板插值打架
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>sysweeper 诊断报告查看器</title>
<style>
:root{--bg:#0f1216;--bg2:#161b22;--bg3:#1c232c;--line:#2a323d;--fg:#d8dee6;--dim:#8b97a6;
--acc:#4a9eff;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.6 -apple-system,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
.top{display:flex;align-items:center;justify-content:space-between;padding:10px 18px;
background:var(--bg2);border-bottom:1px solid var(--line)}
.brand{font-weight:700}.brand .logo{color:var(--acc)}.brand .sub{color:var(--dim);font-size:12px;font-weight:400}
.wrap{padding:16px 18px 60px;max-width:1100px;margin:0 auto}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;align-items:center}
.btn{padding:6px 14px;border-radius:6px;cursor:pointer;font-size:13px;background:var(--bg3);
color:var(--fg);border:1px solid var(--line);min-width:24px;min-height:24px}
.btn:hover{border-color:var(--acc)}.btn.primary{background:#1f6feb;border-color:#1f6feb;color:#fff}
/* 键盘焦点可见兜底（WCAG 2.4.7 / docs/66 §四）+ skip link（2.4.1） */
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.skip{position:absolute;left:-9999px;top:0;z-index:30;padding:8px 14px;background:var(--bg3);
color:var(--fg);border:1px solid var(--acc);border-radius:6px;font-size:13px;text-decoration:none}
.skip:focus{left:8px;top:8px}
.hint{color:var(--dim);font-size:12px}
#drop{border:2px dashed var(--line);border-radius:10px;padding:26px;text-align:center;color:var(--dim);
margin-bottom:14px;transition:border-color .15s}
#drop.over{border-color:var(--acc);color:var(--acc)}
textarea{width:100%;min-height:170px;background:var(--bg3);color:#c3ccd7;border:1px solid var(--line);
border-radius:8px;padding:10px 12px;font-family:var(--mono);font-size:12px;resize:vertical}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:12px}
.card h3{margin:0 0 8px;font-size:14px}
pre{margin:0;padding:10px 12px;background:var(--bg3);border-radius:6px;font-family:var(--mono);
font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;max-height:480px;overflow:auto;color:#c3ccd7}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.stat{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:10px 16px;min-width:100px}
.stat .n{font-size:20px;font-weight:700}.stat .l{font-size:12px;color:var(--dim)}
.stat.ok .n{color:var(--ok)}.stat.warn .n{color:var(--warn)}.stat.bad .n{color:var(--bad)}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:6px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:400}
code,.k{font-family:var(--mono);font-size:12px}
.badge{padding:2px 9px;border-radius:999px;font-size:12px;border:1px solid var(--line);display:inline-block}
.badge.正常{color:var(--ok);border-color:#23532f}.badge.提示{color:var(--warn);border-color:#5c4715}
.badge.不适用{color:var(--dim)}.badge.异常{color:var(--bad);border-color:#5c2220}
.dg{margin-bottom:10px}
.dg .head{display:flex;gap:10px;align-items:center;margin-bottom:6px}
.diff-new{color:var(--warn)}.diff-old{color:var(--dim);text-decoration:line-through}
.hidden{display:none}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:var(--bg3);
border:1px solid var(--line);padding:9px 18px;border-radius:8px;opacity:0;transition:all .18s;font-size:13px}
.toast.show{opacity:1}
details summary{cursor:pointer;color:var(--acc);font-size:13px;margin-bottom:6px}
/* ── 圆光术视觉范式：圆（中心辐射）· 光（明暗聚焦）· 术（整体全息） ── */
.dot{display:inline-block;width:16px;height:16px;border-radius:50%;margin-right:7px;
vertical-align:-3px;background:radial-gradient(circle at 35% 32%,#bfe0ff,var(--acc) 55%,rgba(74,158,255,.12) 78%,transparent);
box-shadow:0 0 10px rgba(74,158,255,.65),0 0 22px rgba(74,158,255,.35)}
.banner{margin:0 0 14px}
.banner>summary{color:var(--fg);font-weight:600;font-size:13px;list-style:none}
.banner>summary::-webkit-details-marker{display:none}
.banner>summary:before{content:"◉";color:var(--acc);margin-right:7px;
text-shadow:0 0 8px rgba(74,158,255,.7)}
.banner .b-in{margin-top:8px;border:1px solid var(--line);border-radius:10px;padding:11px 14px;
font-size:12.5px;line-height:1.75;color:var(--dim);
background:radial-gradient(130% 130% at 50% 0%,rgba(74,158,255,.10),rgba(157,108,255,.05) 45%,transparent 70%)}
.banner .b-in b{color:var(--fg)}
.halo{box-shadow:0 0 0 1px var(--line),0 0 20px rgba(74,158,255,.22) inset}
.glow-new{color:var(--warn);text-shadow:0 0 8px rgba(210,153,34,.5)}
.glow-ok{color:var(--ok);text-shadow:0 0 8px rgba(63,185,80,.45)}
</style>
</head>
<body>
<a class="skip" href="#main">跳到主内容（报告输入与渲染区）</a>
<header class="top">
  <div class="brand"><span class="dot"></span> sysweeper <span class="sub">诊断报告查看器 · 圆光术范式 · 纯展示 · 无后端存储</span></div>
  <div class="hint">数据只留在你的浏览器里</div>
</header>
<main class="wrap" id="main">
  <details class="banner" open>
    <summary>圆光术理念 · 本查看器如何「以圆为体、以光为用」</summary>
    <div class="b-in">
      <b>圆（中心辐射）</b>：报告结论居中呈现，不堆菜单、不诱导下钻；<b>光（明暗聚焦）</b>：异常 / 变化以光晕高亮（详见下方逐项诊断与对比），静默处自然淡出；
      <b>术（整体全息）</b>：依次载入两份报告即自动出「前后对比」全息并置，任何时刻可折叠回看本理念。
      本查看器<b>只读 · 纯展示 · 数据不出浏览器</b>——概念系统的诚实边界（红线）在 GUI 同样生效，绝不代行任何写操作。
    </div>
  </details>
  <div id="input">
    <div id="drop">把报告 JSON 文件拖到这里，或点击选择　<label style="cursor:pointer;text-decoration:underline"><input type="file" id="file" accept=".json,application/json" class="hidden">选文件</label></div>
    <div class="row">
      <textarea id="raw" placeholder="或把 sysweeper 快照 JSON 粘到这里（本机控制台「快照报告」页可生成/复制）…"></textarea>
    </div>
    <div class="row">
      <button class="btn primary" id="render">渲染报告</button>
      <button class="btn" id="demo">载入示例</button>
      <span class="hint">两份报告依次渲染可自动出「前后对比」；渲染后可返回或再载入一份</span>
    </div>
  </div>
  <div id="out" class="hidden"></div>
</main>
<div class="toast" id="toast"></div>
<script>
var REPORTS = [];
function $(id){return document.getElementById(id)}
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function toast(m){var t=$("toast");t.textContent=m;t.className="toast show";
  setTimeout(function(){t.className="toast"},2400)}
function cls(k){return k==="正常"?"ok":(k==="异常"?"bad":"warn")}
function pct(x){return (Number(x||0)*100).toFixed(1)+"%";}
function num(x,d){return Number(x||0).toFixed(d===undefined?3:d);}
function fx(v){
  if(typeof v!=="number") return esc(v);
  return Number.isInteger(v)?String(v):v.toFixed(3);
}

function tallyCards(t){
  return '<div class="cards">'+Object.keys(t||{}).sort().map(function(k){
    return '<div class="stat '+cls(k)+'"><div class="n">'+t[k]+'</div><div class="l">'+esc(k)+'</div></div>'
  }).join("")+'</div>';
}

function renderOne(rep){
  var h = rep.host||{}, d = h.detected||{};
  var html = "";
  html += '<div class="card"><h3>报告信息</h3><table>'+
    '<tr><th>生成时间</th><td>'+esc(rep.generated_at)+'</td>'+
    '<th>sysweeper</th><td>v'+esc(rep.version)+'</td></tr>'+
    '<tr><th>宿主</th><td>'+esc(d.platform||h.system||"?")+' '+(d.version||"")+
      (d.distro?" · "+esc(d.distro):"")+' · '+esc(h.machine||"")+'</td>'+
    '<th>Python</th><td>'+esc(h.python||"")+'</td></tr></table>'+
    (rep.note?'<div class="hint" style="margin-top:6px">'+esc(rep.note)+'</div>':"")+'</div>';
  if(rep.tally) html += tallyCards(rep.tally);
  if(rep.score){
    var sc = rep.score, sp = sc.global_parts||{};
    html += '<div class="card"><h3>量化评分（加权求和 + Shannon 熵）</h3>'+
      '<div class="cards">'+
      '<div class="stat ok"><div class="n">'+num(sc.global_score)+'</div><div class="l">覆盖度总分</div></div>'+
      '<div class="stat"><div class="n">'+num(sc.normalized_entropy)+'</div><div class="l">归一化熵 H/log₂n</div></div>'+
      '<div class="stat"><div class="n">'+num(sc.gini)+'</div><div class="l">Gini 集中度</div></div>'+
      '<div class="stat"><div class="n">'+Number(sc.total_tasks||0)+'</div><div class="l">任务总数</div></div>'+
      '</div>'+
      '<table><tr><th>维度</th><th>值</th><th>维度</th><th>值</th></tr>'+
      '<tr><td>覆盖广度 breadth</td><td>'+pct(sp.breadth)+'</td>'+
      '<td>分布均衡 entropy</td><td>'+pct(sp.entropy)+'</td></tr>'+
      '<tr><td>任务深度 depth</td><td>'+pct(sp.depth)+'</td>'+
      '<td>安全性 safety</td><td>'+pct(sp.safety)+'</td></tr>'+
      '<tr><td>Shannon 熵 H</td><td>'+num(sc.entropy_bits)+' bit</td>'+
      '<td>平台</td><td>'+esc(sc.platform||"?")+' '+esc(sc.version||"")+'</td></tr>'+
      '</table>'+
      (Object.keys(sc.distribution||{}).length?
        '<details><summary>分类分布（'+Object.keys(sc.distribution).length+' 类）</summary>'+
        '<table><tr><th>分类</th><th>任务数</th></tr>'+
        Object.keys(sc.distribution).sort(function(a,b){return sc.distribution[b]-sc.distribution[a]})
          .map(function(k){return '<tr><td class="k">'+esc(k)+'</td><td>'+sc.distribution[k]+'</td></tr>'}).join("")+
        '</table></details>':"")+
      (Object.keys(sc.platform_counts||{}).length?
        '<details><summary>各平台任务数（'+Object.keys(sc.platform_counts).length+' 个平台）</summary>'+
        '<table><tr><th>平台</th><th>任务数</th></tr>'+
        Object.keys(sc.platform_counts).map(function(k){
          return '<tr><td class="k">'+esc(k)+'</td><td>'+sc.platform_counts[k]+'</td></tr>'}).join("")+
        '</table></details>':"")+
      '<div class="hint" style="margin-top:6px">'+
        ((sc.gaps&&sc.gaps.length)?'覆盖缺口：'+sc.gaps.map(esc).join("、")
          :'无覆盖缺口：每个分类都有任务')+'</div>'+
      '</div>';
  }
  if(rep.kmod){
    var km = rep.kmod;
    html += '<div class="card"><h3>内核 module / firmware / eBPF 只读体检 '+
      '<span class="badge '+esc(km.status)+'">'+esc(km.status)+'</span></h3>'+
      '<div class="hint">'+esc(km.summary||"")+
        ' · 全部只读：不写 sysfs、不加载卸载模块、不替换固件、不 attach eBPF</div>'+
      '<details><summary>体检正文</summary><pre>'+esc(km.text||"（无）")+
        (km.truncated?"\\n…（已截断）":"")+'</pre></details>'+
      ((km.environment&&km.environment.length)?
        '<details><summary>接口可用性</summary><pre>'+esc(km.environment.join("\\n"))+'</pre></details>':"")+
      ((km.docs&&km.docs.length)?
        '<details><summary>kernel.org 文档引用（'+km.docs.length+' 条）</summary><pre>'+
        esc(km.docs.join("\\n"))+'</pre></details>':"")+
      ((km.forbidden&&km.forbidden.length)?
        '<details><summary>明确不执行的高危命令（'+km.forbidden.length+' 条，只给指引）</summary><pre>'+
        esc(km.forbidden.join("\\n"))+'</pre></details>':"")+
      '</div>';
  }
  if(rep.jdk){
    var jk = rep.jdk;
    html += '<div class="card"><h3>OpenJDK / JVM 只读体检 '+
      '<span class="badge '+esc(jk.status)+'">'+esc(jk.status)+'</span></h3>'+
      '<div class="hint">'+esc(jk.summary||"")+
        ' · 全部只读：不改 JAVA_HOME、不改 JVM 标志、不录制 JFR、不 attach 进程</div>'+
      '<details><summary>体检正文</summary><pre>'+esc(jk.text||"（无）")+
        (jk.truncated?"\\n…（已截断）":"")+'</pre></details>'+
      ((jk.environment&&jk.environment.length)?
        '<details><summary>接口可用性</summary><pre>'+esc(jk.environment.join("\\n"))+'</pre></details>':"")+
      ((jk.docs&&jk.docs.length)?
        '<details><summary>OpenJDK 文档引用（'+jk.docs.length+' 条）</summary><pre>'+
        esc(jk.docs.join("\\n"))+'</pre></details>':"")+
      ((jk.forbidden&&jk.forbidden.length)?
        '<details><summary>明确不执行的高危子命令（'+jk.forbidden.length+' 条，只给指引）</summary><pre>'+
        esc(jk.forbidden.join("\\n"))+'</pre></details>':"")+
      '</div>';
  }
  if(rep.distcompute){
    var dc = rep.distcompute;
    html += '<div class="card"><h3>分布式计算共享 '+
      '<span class="badge '+esc(dc.status)+'">'+esc(dc.status)+'</span></h3>'+
      '<div class="hint">'+esc(dc.summary||"")+
        ' · 只读：不执行任意代码 / 不下载可执行程序 / 不主动连外部服务器</div>'+
      '<details><summary>总报告</summary><pre>'+esc(dc.text||"（无）")+
        (dc.truncated?"\\n…（已截断）":"")+'</pre></details>'+
      '<div class="hint">看门狗：sysweeper 绝不自动重启任何进程；重启只出命令文本，由你显式执行。</div>'+
      '</div>';
  }
  if(rep.sysmap) html += '<div class="card"><h3>系统统筹总览</h3><pre>'+esc(rep.sysmap.text)+
    (rep.sysmap.truncated?"\\n…（已截断）":"")+'</pre></div>';
  if(rep.subsystems){
    var en = rep.subsystems.enabled||[], dis = rep.subsystems.disabled||[];
    html += '<div class="card"><h3>子系统开关态（已开启 '+en.length+' / 关闭 '+dis.length+'）</h3>'+
      '<div>'+en.map(function(k){return '<span class="badge 正常" style="margin:2px">'+esc(k)+'</span>'}).join("")+
      dis.map(function(k){return '<span class="badge 不适用" style="margin:2px">'+esc(k)+'</span>'}).join("")+'</div></div>';
  }
  if(rep.diagnose && rep.diagnose.length){
    html += '<div class="card"><h3>逐项诊断（'+rep.diagnose.length+' 项）</h3>'+
      rep.diagnose.map(function(it){
        return '<div class="dg"><div class="head"><b>'+esc(it.label||it.key)+'</b>'+
          '<span class="badge '+esc(it.status)+'">'+esc(it.status)+'</span>'+
          '<span class="hint">'+esc(it.layer||"")+' · '+esc(it.key)+(it.truncated?" · 已截断":"")+'</span></div>'+
          '<details><summary>展开正文</summary><pre>'+esc(it.text||"（无）")+'</pre></details></div>';
      }).join("")+'</div>';
  }
  if(rep.settings && rep.settings.items){
    var ch = {}; (rep.settings.changed||[]).forEach(function(k){ch[k]=1});
    html += '<div class="card"><h3>参数与阈值</h3><table><tr><th>key</th><th>值</th><th>默认</th><th>标签</th></tr>'+
      rep.settings.items.map(function(s){
        return '<tr'+(ch[s.key]?' class="diff-new"':"")+'><td class="k">'+esc(s.key)+
          (ch[s.key]?" ●":"")+'</td><td>'+esc(s.value)+'</td><td>'+esc(s.default)+'</td><td>'+esc(s.label)+'</td></tr>';
      }).join("")+'</table></div>';
  }
  if(rep.history && rep.history.length){
    html += '<div class="card"><h3>变更留痕（'+rep.history.length+' 条）</h3>'+
      rep.history.slice().reverse().map(function(r){
        return '<div style="margin-bottom:8px"><div class="hint">'+esc(r.ts)+' · '+esc(r.source)+
          (r.origin?" · "+esc(r.origin):"")+'</div><div class="k">'+
          Object.keys(r.changes||{}).map(function(k){
            return esc(k)+': '+esc(r.changes[k].from)+' → '+esc(r.changes[k].to)}).join("；")+
          '</div>'+(r.note?'<div class="hint">备注：'+esc(r.note)+'</div>':"")+'</div>';
      }).join("")+'</div>';
  }
  return html;
}

function diffReports(a, b){
  var rows = [];
  function map(s){var m={};(s&&s.items||[]).forEach(function(x){m[x.key]=x});return m}
  var ma = map(a.settings), mb = map(b.settings);
  Object.keys(ma).forEach(function(k){
    if(!mb[k]) return;
    if(String(ma[k].value)!==String(mb[k].value))
      rows.push({k:k, a:ma[k].value, b:mb[k].value, label:mb[k].label});
  });
  var ta=a.tally||{}, tb=b.tally||{}, keys={}, trows=[];
  Object.keys(ta).concat(Object.keys(tb)).forEach(function(k){keys[k]=1});
  Object.keys(keys).sort().forEach(function(k){
    var x=ta[k]||0, y=tb[k]||0; if(x!==y) trows.push({k:k,a:x,b:y});
  });
  var html = '<div class="card"><h3>前后对比</h3><div class="hint">'+
    esc(a.generated_at)+" → "+esc(b.generated_at)+'</div>';
  if(trows.length) html += '<h3 style="margin-top:10px">诊断状态计数</h3><table><tr><th>状态</th><th>前</th><th>后</th></tr>'+
    trows.map(function(r){return '<tr><td>'+esc(r.k)+'</td><td>'+r.a+'</td><td>'+r.b+'</td></tr>'}).join("")+'</table>';
  var sa=a.score||{}, sb=b.score||{};
  if(sa.global_score!==undefined && sb.global_score!==undefined){
    html += '<h3 style="margin-top:10px">量化评分</h3>'+
      '<table><tr><th>指标</th><th>前</th><th>后</th></tr>'+
      [["覆盖度总分",sa.global_score,sb.global_score],
       ["归一化熵",sa.normalized_entropy,sb.normalized_entropy],
       ["Gini 集中度",sa.gini,sb.gini],
       ["任务总数",sa.total_tasks,sb.total_tasks]].map(function(r){
        var same = String(r[1])===String(r[2]);
        return '<tr><td class="k">'+esc(r[0])+'</td>'+
          '<td'+(same?"":' class="diff-old"')+'>'+fx(r[1])+'</td>'+
          '<td'+(same?"":' class="diff-new"')+'>'+fx(r[2])+'</td></tr>'}).join("")+
      '</table>';
  }
  if(rows.length) html += '<h3 style="margin-top:10px">参数变化（'+rows.length+' 项）</h3>'+
    '<table><tr><th>key</th><th>前</th><th>后</th><th>标签</th></tr>'+
    rows.map(function(r){return '<tr><td class="k">'+esc(r.k)+'</td><td class="diff-old">'+esc(r.a)+
      '</td><td class="diff-new">'+esc(r.b)+'</td><td>'+esc(r.label)+'</td></tr>'}).join("")+'</table>';
  else html += '<div class="hint" style="margin-top:8px">参数无变化</div>';
  return html+'</div>';
}

function render(rep){
  REPORTS.push(rep);
  var box = $("out");
  var html = '<div class="row">'+
    '<button class="btn" id="back">返回重来</button>'+
    '<button class="btn" id="again">再载入一份（自动出对比）</button>'+
    '<button class="btn" id="share">生成分享链接</button>'+
    '<span class="hint">共 '+REPORTS.length+' 份已载入；数据只留在你的浏览器里</span>'+
    '</div>';
  if(REPORTS.length > 1)
    html += diffReports(REPORTS[REPORTS.length-2], REPORTS[REPORTS.length-1]);
  html += renderOne(rep);
  html += '<div class="hint" style="margin-top:14px">再渲染一份即自动出对比；刷新页面清空。</div>';
  box.innerHTML = html;
  box.classList.remove("hidden");
  $("input").classList.add("hidden");
  window.scrollTo(0,0);
  $("back").addEventListener("click", function(){ location.hash=""; location.reload(); });
  $("again").addEventListener("click", function(){
    box.classList.add("hidden"); $("input").classList.remove("hidden");
    $("raw").focus(); window.scrollTo(0,0);
  });
  $("share").addEventListener("click", shareCurrent);
}

function shareCurrent(){
  try{
    var rep = REPORTS[REPORTS.length-1];
    var s = btoa(unescape(encodeURIComponent(JSON.stringify(rep))))
      .replace(/\\+/g,"-").replace(/\\\//g,"_").replace(/=+$/,"");
    var u = location.origin + location.pathname + "#r=" + s;
    function copied(ok){
      toast(ok ? "分享链接已复制（注意：URL 分享=公开发布，报告大时优先发文件）"
               : "链接已写入地址栏（自动复制失败，请手动复制）");
    }
    if(navigator.clipboard && navigator.clipboard.writeText)
      navigator.clipboard.writeText(u).then(function(){copied(true)}, function(){copied(false)});
    else copied(false);
    history.replaceState(null, "", u);
  }catch(e){ toast("生成分享链接失败: "+e.message); }
}

function tryParse(text){
  var rep;
  try{ rep = JSON.parse(text); }
  catch(e){
    toast("JSON 解析失败：" + e.message +
          " —— 检查是否整段复制、文件是否下载完整；不行就改用「拖文件」或「载入示例」");
    return;
  }
  if(!rep || !rep.schema || String(rep.schema).indexOf("sysweeper-report")!==0)
    toast("不是标准 sysweeper 快照（缺 schema 字段），仍按原文渲染");
  render(rep);
}

$("render").addEventListener("click", function(){
  var t = $("raw").value.trim(); if(!t){ toast("先粘贴或拖入报告 JSON"); return; }
  tryParse(t);
});
$("file").addEventListener("change", function(e){
  var f = e.target.files[0]; if(!f) return;
  var rd = new FileReader();
  rd.onload = function(){ $("raw").value = rd.result; tryParse(String(rd.result)); };
  rd.readAsText(f);
});
var drop = $("drop");
["dragover","dragenter"].forEach(function(ev){
  drop.addEventListener(ev, function(e){e.preventDefault();drop.classList.add("over")})});
["dragleave","drop"].forEach(function(ev){
  drop.addEventListener(ev, function(e){e.preventDefault();drop.classList.remove("over")})});
drop.addEventListener("drop", function(e){
  var f = e.dataTransfer.files[0]; if(!f) return;
  var rd = new FileReader();
  rd.onload = function(){ $("raw").value = rd.result; tryParse(String(rd.result)); };
  rd.readAsText(f);
});
$("demo").addEventListener("click", function(){
  tryParse(JSON.stringify(DEMO));
});

// URL 携带（#r=base64url）：可分享，但报告大时用粘贴
(function(){
  var h = location.hash.match(/^#r=(.+)$/);
  if(!h) return;
  try{
    var b = h[1].replace(/-/g,"+").replace(/_/g,"/");
    var s = decodeURIComponent(escape(atob(b)));
    $("raw").value = s; tryParse(s);
  }catch(e){ toast("URL 里的报告解析失败"); }
})();

var DEMO = {
  schema:"sysweeper-report/1", version:"0000.0000.0000.0018.20261025",
  generated_at:new Date().toISOString().slice(0,19),
  note:"示例数据，仅演示渲染效果",
  host:{python:"3.11.0",system:"Linux",machine:"x86_64",
    detected:{platform:"linux",version:"24.04",distro:"Ubuntu 24.04.3 LTS"}},
  tally:{"正常":41,"提示":6,"不适用":4},
  sysmap:{ok:true,status:"提示",text:"==== 系统统筹总览 ====\\n（示例）整体健康：41 项正常 / 6 项提示"},
  subsystems:{enabled:["network","kernel","kmod","firmware","modules","hardware","storage"],
    disabled:["tor","dosbox"]},
  settings:{changed:["cmd.timeout"],
    items:[{key:"cmd.timeout",label:"命令执行超时",value:300,default:120,unit:"秒"},
           {key:"scan.limit",label:"扫描条数上限",value:10,default:10,unit:"条"}]},
  history:[{ts:"2026-10-10T10:00:00",source:"web",origin:"web",note:"Web 控制台保存",
    changes:{"cmd.timeout":{from:120,to:300}}}],
  diagnose:[{key:"kernel",label:"内核调优(sysctl)",layer:"内核",status:"正常",
    text:"==== 内核调优(sysctl) 诊断 ====\\n（示例正文）vm.swappiness=60"}
  ]
};
</script>
</body>
</html>`;
}

async function handler(_req: Request): Promise<Response> {
  // 单页应用：所有路径都回同一页面（Deploy 的路由只需这一个文件）
  return new Response(page(), {
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

if (import.meta.main) {
  let port = 8899;
  const argv = Deno.args.slice();
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--port" || argv[i] === "-p") port = Number(argv[++i]) || port;
    else if (argv[i] === "--help" || argv[i] === "-h") {
      console.log("sysweeper 报告查看器（纯展示）\n  deno run --allow-net src/deno/report_viewer.ts [--port 8899]");
      Deno.exit(0);
    }
  }
  Deno.serve({ hostname: "0.0.0.0", port }, handler);
}
