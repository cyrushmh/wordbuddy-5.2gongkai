/*
 * 修真图谱 App 侧布局纯函数的 Node 断言测试（无 HarmonyOS SDK 环境下可跑的真实验证）。
 *
 * 用法：
 *   cd classics-harmony-app
 *   tsc --target es2019 --module commonjs --outDir /tmp/xzcheck \
 *     entry/src/main/ets/model/XiuzhenMapLayout.ts \
 *     entry/src/main/ets/model/XiuzhenMap.generated.ts
 *   node tests/test_xiuzhen_map_layout.cjs /tmp/xzcheck
 *
 * 断言内容：
 *   1) 索引完整性：节点数/边数/每层计数；悬空边必须为 0（与数据层自检同一标准）；
 *   2) relationText 文案正确性与「命中 N 次」后缀规则；
 *   3) overviewLayout：盒数=节点数、边数=去悬空后全量、坐标全部落在画布内；
 *   4) neighborLayout：对【每一个】节点冒烟——位置有限且在画布（含标签）范围内、邻节点 ≤12；
 *   5) 聚焦默认节点 book:daodejing 的邻域规模（3 个邻节点 / 5 条边）。
 */
'use strict';

const path = require('path');

const outDir = process.argv[2] || '/tmp/xzcheck';
const L = require(path.join(outDir, 'XiuzhenMapLayout.js'));
const G = require(path.join(outDir, 'XiuzhenMap.generated.js'));

let failed = 0;
function check(name, cond, extra) {
  if (cond) {
    console.log(`  ok  ${name}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${name}${extra ? '  -> ' + extra : ''}`);
  }
}

console.log('== 1) 索引完整性 ==');
const index = L.buildIndex();
check('节点总数 = 67', G.MAP_NODES.length === 67, String(G.MAP_NODES.length));
check('边总数 = 66', G.MAP_EDGES.length === 66, String(G.MAP_EDGES.length));
check('byId 覆盖全部节点', Object.keys(index.byId).length === G.MAP_NODES.length);
const dangling = G.MAP_EDGES.filter((e) => !index.byId[e.from] || !index.byId[e.to]);
check('悬空边 = 0', dangling.length === 0, JSON.stringify(dangling.slice(0, 3)));
check('道藏部类 = 23', index.counts['daozang'] === 23, String(index.counts['daozang']));
check('典籍 = 12', index.counts['classics'] === 12, String(index.counts['classics']));
check('专题 = 7', index.counts['topics'] === 7, String(index.counts['topics']));
check('旁参经论 = 10', index.counts['external'] === 10, String(index.counts['external']));
check('语料 = 15', index.counts['corpus'] === 15, String(index.counts['corpus']));
const selfLoops = G.MAP_EDGES.filter((e) => e.from === e.to).length;
check('incident 双向索引边数守恒',
  Object.values(index.incident).reduce((s, a) => s + a.length, 0) === G.MAP_EDGES.length * 2 - selfLoops,
  `自环 ${selfLoops} 条`);

console.log('== 2) relationText ==');
const ddBelong = index.incident['book:daodejing'].find((r) => r.edge.type === 'belongs_to');
check('道德经 属于 道德真经', L.relationText(ddBelong, index) === '道德经（老子） 属于 道德真经',
  L.relationText(ddBelong, index));
const artTopic = index.incident['art:2025-11-02_脾好不好看大便，肾强不强看小便，身体的“诚实报告”']
  .find((r) => r.edge.type === 'has_topic' && r.edge.to === 'topic:脏腑辨证');
check('主题命中 135 次带后缀', L.relationText(artTopic, index).includes('命中 135 次'),
  L.relationText(artTopic, index));
const sameTrad = index.incident['ext:老子'].find((r) => r.edge.type === 'same_tradition');
check('同传统 无权重后缀', L.relationText(sameTrad, index) === '老子 同传统 道德经（老子）',
  L.relationText(sameTrad, index));

console.log('== 3) overviewLayout ==');
const ov = L.overviewLayout(index);
check('盒数 = 节点数', ov.boxes.length === 67, String(ov.boxes.length));
check('边数 = 66（无悬空可剔）', ov.edges.length === 66, String(ov.edges.length));
check('层中心 5 个', Object.keys(ov.bandCenters).length === 5);
const outOf = ov.boxes.filter((b) => !(b.cx >= 0 && b.cx <= ov.width && b.cy >= 0 && b.cy <= ov.height));
check('所有盒在画布内', outOf.length === 0, JSON.stringify(outOf.slice(0, 2)));
const finite = ov.edges.every((e) =>
  [e.x1, e.y1, e.x2, e.y2].every((v) => Number.isFinite(v)));
check('所有边坐标有限', finite);

console.log('== 4) neighborLayout 全节点冒烟 ==');
let smokeBad = null;
let maxNeighbors = 0;
G.MAP_NODES.forEach((n) => {
  const nl = L.neighborLayout(index, n.id);
  const all = [nl.focus].concat(nl.nodes);
  for (const b of all) {
    if (![b.cx, b.cy, b.r].every(Number.isFinite)) { smokeBad = n.id + ' 非有限坐标'; }
    // 标签随圆点下方 +12 起、高约 16：节点圆 + 标签必须整体留在画布内
    if (b.cx - 44 - 2 < 0 || b.cx + 44 + 2 > nl.width || b.cy - b.r - 2 < 0 || b.cy + b.r + 2 + 16 > nl.height) {
      smokeBad = n.id + ' 越界 ' + b.id + ' @' + b.cx.toFixed(1) + ',' + b.cy.toFixed(1);
    }
  }
  if (nl.nodes.length > 12) { smokeBad = n.id + ' 邻节点超 12'; }
  if (nl.refs.length !== index.incident[n.id].length) { smokeBad = n.id + ' refs 数量不符'; }
  maxNeighbors = Math.max(maxNeighbors, nl.nodes.length);
});
check('全节点位置/规模合法', smokeBad === null, smokeBad);
check('最大邻节点数 ≤ 12', maxNeighbors <= 12, String(maxNeighbors));
check('孤立节点（0 关联）被容忍', G.MAP_NODES.every((n) => neighborSmokeOk(index, n.id)));
function neighborSmokeOk(ix, id) {
  const nl = L.neighborLayout(ix, id);
  return nl.focus.id === id && Array.isArray(nl.nodes) && Array.isArray(nl.refs);
}

console.log('== 5) 默认聚焦 book:daodejing ==');
const dd = L.neighborLayout(index, 'book:daodejing');
check('聚焦居中', dd.focus.cx === L.CANVAS_W / 2 && dd.focus.cy === L.CANVAS_H / 2);
check('3 个唯一邻节点', dd.nodes.length === 3, String(dd.nodes.length));
check('4 条关联边', dd.refs.length === 4, String(dd.refs.length));
check('邻节点含 dzcat:15/ext:老子/ext:道德经',
  ['dzcat:15', 'ext:老子', 'ext:道德经'].every((id) => dd.nodes.some((b) => b.id === id)));

console.log('== 6) 边界与兜底 ==');
check('nodeOf 未知 id 返回 null', L.nodeOf(index, 'nope') === null);
const nlUnknown = L.neighborLayout(index, 'nope');
check('未知聚焦兜底首节点', nlUnknown.focus.id === G.MAP_NODES[0].id, nlUnknown.focus.id);
const nei = L.neighborLayout(index, 'corpus:suwen');
check('corpus:suwen 2 个邻节点', nei.nodes.length === 2, String(nei.nodes.length));

if (failed > 0) {
  console.error(`\n${failed} 项断言失败`);
  process.exit(1);
}
console.log('\n全部断言通过');
