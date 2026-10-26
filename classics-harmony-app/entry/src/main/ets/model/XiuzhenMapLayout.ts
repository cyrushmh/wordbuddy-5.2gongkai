// 修真图谱布局与关系文案（纯函数层，无 UI 依赖，可单测）。
//
// 数据源：XiuzhenMap.generated.ts（由 research/xiuzhen/build_xiuzhen_map.py 从
// map_canonical.json 生成；NVKeyValues 同源）。本文件只回答三个问题：
//   1) 图怎么摆（overviewLayout 分层全景 / neighborLayout 邻域聚焦）；
//   2) 一条边用中文怎么说（relationText，供读屏与文本等价视图）；
//   3) 节点/层的中文名与配色（LAYER_NAMES / TYPE_NAMES / LAYER_COLORS）。
//
// 纪律：与数据层一致——每条关系必须来自可复现的 join，无出处不入图；
//      悬空边（端点不在节点表）在布局中被剔除，构建期另有自检。
import { MAP_NODES, MAP_EDGES, MapNode, MapEdge } from './XiuzhenMap.generated';

/** 画布逻辑尺寸（vp）：固定坐标系让布局确定可测，窄屏居中即可。 */
export const CANVAS_W: number = 320;
export const CANVAS_H: number = 280;

/** 层的展示顺序（自上而下）。 */
export const LAYER_ORDER: string[] = ['daozang', 'classics', 'topics', 'external', 'corpus'];

export const LAYER_NAMES: Record<string, string> = {
  daozang: '道藏部类',
  classics: '典籍',
  topics: '专题',
  external: '旁参经论',
  corpus: '语料'
};

export const LAYER_COLORS: Record<string, string> = {
  daozang: '#8a6d3b',
  classics: '#aa3333',
  topics: '#2a7a4f',
  external: '#3a6ea5',
  corpus: '#7a7a7a'
};

export const TYPE_NAMES: Record<string, string> = {
  book: '典籍',
  daozang_category: '道藏部类',
  topic: '专题',
  classic_mention: '旁参经论',
  article: '语料文章',
  corpus: '语料集'
};

export const EDGE_RELATIONS: Record<string, string> = {
  belongs_to: '属于',
  has_topic: '主题',
  mentions: '旁引',
  same_tradition: '同传统',
  corpus_covered_by: '由语料覆盖',
  intro_mentions: '简介提及'
};

/** 结构性边（归属）与相关性边（主题/旁引）分色，读图不糊。 */
const STRUCT_TYPES: string[] = ['belongs_to', 'corpus_covered_by'];

/** 一条有向边在某个端点视角下的引用。 */
export interface EdgeRef {
  edge: MapEdge;
  /** 'out'：该端点是 from；'in'：该端点是 to。 */
  dir: 'out' | 'in';
  /** 对端（邻节点）id。 */
  other: string;
}

export interface MapIndex {
  byId: Record<string, MapNode>;
  /** 节点 → 其所有关联边（双向索引）。 */
  incident: Record<string, EdgeRef[]>;
  nodesByLayer: Record<string, MapNode[]>;
  counts: Record<string, number>;
}

export interface NodeBox {
  id: string;
  label: string;
  cx: number;
  cy: number;
  r: number;
  color: string;
  layer: string;
  type: string;
}

export interface EdgeSeg {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  kind: 'struct' | 'corr';
}

export interface NeighborPair {
  to: string;
  kind: 'struct' | 'corr';
}

export interface OverviewLayout {
  boxes: NodeBox[];
  edges: EdgeSeg[];
  bandCenters: Record<string, number>;
  width: number;
  height: number;
}

export interface NeighborLayout {
  focus: NodeBox;
  /** 全部邻节点（未截断，供文本等价视图）。 */
  nodes: NodeBox[];
  /** 去重后的邻接连线（Canvas 绘制用）。 */
  pairs: NeighborPair[];
  /** 该聚焦节点的全部关联边（文本等价视图用）。 */
  refs: EdgeRef[];
  width: number;
  height: number;
}

/** 建索引：节点表 + 双向边索引 + 按层分组（纯内存，数据层已保证无悬空）。 */
export function buildIndex(): MapIndex {
  const byId: Record<string, MapNode> = {};
  MAP_NODES.forEach((n: MapNode) => {
    byId[n.id] = n;
  });
  const incident: Record<string, EdgeRef[]> = {};
  MAP_NODES.forEach((n: MapNode) => {
    incident[n.id] = [];
  });
  MAP_EDGES.forEach((e: MapEdge) => {
    if (incident[e.from]) {
      incident[e.from].push({ edge: e, dir: 'out', other: e.to });
    }
    if (incident[e.to] && e.from !== e.to) {
      incident[e.to].push({ edge: e, dir: 'in', other: e.from });
    }
  });
  const nodesByLayer: Record<string, MapNode[]> = {};
  const counts: Record<string, number> = {};
  LAYER_ORDER.forEach((l: string) => {
    nodesByLayer[l] = [];
    counts[l] = 0;
  });
  MAP_NODES.forEach((n: MapNode) => {
    if (nodesByLayer[n.layer]) {
      nodesByLayer[n.layer].push(n);
      counts[n.layer] = counts[n.layer] + 1;
    }
  });
  return { byId, incident, nodesByLayer, counts };
}

/** 取节点；查无返回 null（调用方兜底）。 */
export function nodeOf(index: MapIndex, id: string): MapNode | null {
  const found = index.byId[id];
  if (found) {
    return found;
  }
  return null;
}

/** 一条边的中文关系描述（文本等价视图与读屏共用）。 */
export function relationText(ref: EdgeRef, index: MapIndex): string {
  const from = nodeOf(index, ref.edge.from);
  const to = nodeOf(index, ref.edge.to);
  const fromLabel = from ? from.label : ref.edge.from;
  const toLabel = to ? to.label : ref.edge.to;
  const rel = EDGE_RELATIONS[ref.edge.type];
  const relText = rel ? rel : ref.edge.type;
  if (ref.edge.weight > 1) {
    if (ref.edge.type === 'has_topic' || ref.edge.type === 'mentions') {
      return `${fromLabel} ${relText} ${toLabel}（命中 ${ref.edge.weight} 次）`;
    }
    return `${fromLabel} ${relText} ${toLabel}（关联强度 ${ref.edge.weight}）`;
  }
  return `${fromLabel} ${relText} ${toLabel}`;
}

/** 分层全景布局：五条横带，带内均布节点；跨层边画为直线（骨架感）。 */
export function overviewLayout(index: MapIndex): OverviewLayout {
  const bandH: number = CANVAS_H / LAYER_ORDER.length;
  const bandCenters: Record<string, number> = {};
  const boxes: NodeBox[] = [];
  const posOf: Record<string, NodeBox> = {};
  const left: number = 54;
  const right: number = CANVAS_W - 10;
  LAYER_ORDER.forEach((layer: string, li: number) => {
    const y: number = bandH * li + bandH / 2;
    bandCenters[layer] = y;
    const nodes: MapNode[] = index.nodesByLayer[layer];
    nodes.forEach((n: MapNode, i: number) => {
      let cx: number;
      if (nodes.length <= 1) {
        cx = (left + right) / 2;
      } else {
        cx = left + ((right - left) * i) / (nodes.length - 1);
      }
      const box: NodeBox = {
        id: n.id,
        label: n.label,
        cx: cx,
        cy: y,
        r: 4,
        color: LAYER_COLORS[layer] ? LAYER_COLORS[layer] : '#666666',
        layer: layer,
        type: n.type
      };
      boxes.push(box);
      posOf[n.id] = box;
    });
  });
  const edges: EdgeSeg[] = [];
  MAP_EDGES.forEach((e: MapEdge) => {
    const a: NodeBox = posOf[e.from];
    const b: NodeBox = posOf[e.to];
    if (!a || !b) {
      return; // 悬空边不入图（与构建期自检同一标准）
    }
    const kind: 'struct' | 'corr' = STRUCT_TYPES.indexOf(e.type) >= 0 ? 'struct' : 'corr';
    edges.push({ x1: a.cx, y1: a.cy, x2: b.cx, y2: b.cy, kind: kind });
  });
  return { boxes: boxes, edges: edges, bandCenters: bandCenters, width: CANVAS_W, height: CANVAS_H };
}

/** 邻域聚焦布局：聚焦节点居中，邻节点环绕一圈；边按去重后邻接连线绘制。 */
export function neighborLayout(index: MapIndex, focusId: string): NeighborLayout {
  const focusNode: MapNode | null = nodeOf(index, focusId);
  let focus: MapNode;
  if (focusNode) {
    focus = focusNode;
  } else {
    focus = MAP_NODES[0];
  }
  const cx: number = CANVAS_W / 2;
  const cy: number = CANVAS_H / 2;
  const color: string = LAYER_COLORS[focus.layer] ? LAYER_COLORS[focus.layer] : '#666666';
  const focusBox: NodeBox = {
    id: focus.id,
    label: focus.label,
    cx: cx,
    cy: cy,
    r: 15,
    color: color,
    layer: focus.layer,
    type: focus.type
  };
  const refs: EdgeRef[] = index.incident[focus.id] ? index.incident[focus.id] : [];
  // 邻节点去重（两端可能有多条边，如「简介提及 + 同传统」）。
  const seen: Record<string, boolean> = {};
  const nodes: NodeBox[] = [];
  const pairs: NeighborPair[] = [];
  const radius: number = Math.min(CANVAS_W, CANVAS_H) / 2 - 30;
  const shown: number = Math.min(refs.length, 12);
  let drawn: number = 0;
  refs.forEach((ref: EdgeRef, i: number) => {
    if (i >= 12) {
      return;
    }
    const otherNode: MapNode | null = nodeOf(index, ref.other);
    if (!otherNode) {
      return;
    }
    if (!seen[ref.other]) {
      seen[ref.other] = true;
      const angle: number = -Math.PI / 2 + (2 * Math.PI * drawn) / shown;
      drawn = drawn + 1;
      const nColor: string = LAYER_COLORS[otherNode.layer] ? LAYER_COLORS[otherNode.layer] : '#666666';
      nodes.push({
        id: otherNode.id,
        label: otherNode.label,
        cx: cx + radius * Math.cos(angle),
        cy: cy + radius * Math.sin(angle),
        r: 9,
        color: nColor,
        layer: otherNode.layer,
        type: otherNode.type
      });
      const kind: 'struct' | 'corr' = STRUCT_TYPES.indexOf(ref.edge.type) >= 0 ? 'struct' : 'corr';
      pairs.push({ to: ref.other, kind: kind });
    }
  });
  return { focus: focusBox, nodes: nodes, pairs: pairs, refs: refs, width: CANVAS_W, height: CANVAS_H };
}
