/**
 * 修真图谱（修真图谱数据层在 App 侧的第一屏）。
 *
 * 数据流：research/xiuzhen/build_xiuzhen_map.py → map_canonical.json
 *   → sysweeper/data/xiuzhen_map.json（引擎侧）与 model/XiuzhenMap.generated.ts（本页）。
 *   布局与关系文案为纯函数（model/XiuzhenMapLayout.ts），本页只做呈现与交互。
 *
 * 三种视图（同一数据的三种等价读法，缺一不可）：
 *   1) 邻域探索：聚焦节点居中，邻节点环绕，Canvas 画骨架，标签为覆盖层 Text（可点、可读屏）；
 *   2) 分层全景：五条横带按层均布全部节点，跨层关系画为骨架直线（结构性边/相关性边分色）；
 *   3) 文本等价视图：始终渲染的关系/节点列表——视障读屏与长辈模式的完整信息通道。
 *      （Canvas 是「好看」，列表是「等价」，缺列表即信息丢失。）
 *
 * 无障碍：节点命中区即 Text（自带 accessibilityText）；切换视图/聚焦均 announce 播报；
 * 装饰性元素（太极、色条）不参与读屏。适老化：字号下限 11vp 仅在来源/出处等辅助行使用。
 */
import { router, Canvas, CanvasRenderingContext2D, Color, AccessibilityLevel, Alignment } from '@kit.ArkUI';
import { MAP_NODES, MAP_EDGES, MapNode } from '../model/XiuzhenMap.generated';
import {
  CANVAS_W,
  CANVAS_H,
  LAYER_ORDER,
  LAYER_NAMES,
  LAYER_COLORS,
  TYPE_NAMES,
  MapIndex,
  OverviewLayout,
  NeighborLayout,
  EdgeRef,
  NodeBox,
  EdgeSeg,
  NeighborPair,
  buildIndex,
  overviewLayout,
  neighborLayout,
  relationText
} from '../model/XiuzhenMapLayout';
import { openExternal } from '../model/OpenUrl';
import { announce } from '../model/Accessibility';
import { TaijiDecor } from '../component/TaijiDecor';

type ViewMode = 'neighbor' | 'overview';

/** 文本等价视图的一行（关系行/节点行/分组头）。 */
interface MapListItem {
  key: string;
  title: string;
  sub: string;
  a11y: string;
  /** 点击后要聚焦的节点 id；空串表示不可跳转。 */
  jumpId: string;
  header: boolean;
}

@Entry
@Component
struct XiuzhenMap {
  private graph: MapIndex = buildIndex();
  private overview: OverviewLayout = overviewLayout(this.graph);
  private ctx: CanvasRenderingContext2D = new CanvasRenderingContext2D();
  @State focusId: string = 'book:daodejing';
  @State mode: ViewMode = 'neighbor';

  /** 当前聚焦节点（找不到时兜底首个节点，绝不为空）。 */
  private get focusNode(): MapNode {
    const found: MapNode = this.graph.byId[this.focusId];
    if (found) {
      return found;
    }
    return MAP_NODES[0];
  }

  private get current(): NeighborLayout {
    return neighborLayout(this.graph, this.focusId);
  }

  /** 分层计数文案：道藏 23 · 典籍 12 · … */
  private get countsLine(): string {
    const c = this.graph.counts;
    return (
      `道藏 ${c['daozang']} · 典籍 ${c['classics']} · 专题 ${c['topics']} · ` +
      `旁参 ${c['external']} · 语料 ${c['corpus']}`
    );
  }

  /** 邻域模式的文本等价视图：聚焦行 + 每条关联一行。 */
  private get relationItems(): MapListItem[] {
    const items: MapListItem[] = [];
    const focus: MapNode = this.focusNode;
    const head: string = focus.label;
    items.push({
      key: 'focus',
      title: head,
      sub: `当前聚焦 · ${TYPE_NAMES[focus.type]} · ${LAYER_NAMES[focus.layer]}`,
      a11y: `${head}，${TYPE_NAMES[focus.type]}，${LAYER_NAMES[focus.layer]}层。${focus.detail}`,
      jumpId: '',
      header: false
    });
    const refs: EdgeRef[] = this.graph.incident[focus.id] ? this.graph.incident[focus.id] : [];
    if (refs.length === 0) {
      items.push({
        key: 'no-rel',
        title: '该节点暂无关联关系',
        sub: '可在分层全景中浏览其他节点',
        a11y: '该节点暂无关联关系，可在分层全景中浏览其他节点',
        jumpId: '',
        header: false
      });
      return items;
    }
    refs.forEach((ref: EdgeRef, i: number) => {
      const other: MapNode = this.graph.byId[ref.other];
      items.push({
        key: `${i}:${ref.edge.from}->${ref.edge.to}:${ref.edge.type}`,
        title: relationText(ref, this.graph),
        sub: other ? `${TYPE_NAMES[other.type]} · ${LAYER_NAMES[other.layer]}` : '',
        a11y: `${relationText(ref, this.graph)}。点击查看该节点的关联`,
        jumpId: ref.other,
        header: false
      });
    });
    return items;
  }

  /** 分层全景模式的文本等价视图：按层分组的全量节点（共 67 节点全量呈现）。 */
  private get overviewItems(): MapListItem[] {
    const items: MapListItem[] = [];
    LAYER_ORDER.forEach((layer: string) => {
      const nodes: MapNode[] = this.graph.nodesByLayer[layer];
      items.push({
        key: `h:${layer}`,
        title: `${LAYER_NAMES[layer]}（${nodes.length}）`,
        sub: '',
        a11y: `${LAYER_NAMES[layer]}分组，共 ${nodes.length} 个节点`,
        jumpId: '',
        header: true
      });
      nodes.forEach((n: MapNode) => {
        items.push({
          key: n.id,
          title: n.label,
          sub: TYPE_NAMES[n.type],
          a11y: `${n.label}，${TYPE_NAMES[n.type]}，${n.detail}`,
          jumpId: n.id,
          header: false
        });
      });
    });
    return items;
  }

  private get listItems(): MapListItem[] {
    if (this.mode === 'neighbor') {
      return this.relationItems;
    }
    return this.overviewItems;
  }

  /** 聚焦某节点：切入邻域模式、重绘、读屏播报。 */
  private focusNodeById(id: string, label: string): void {
    this.focusId = id;
    this.mode = 'neighbor';
    this.draw();
    const ctx = this.getUIContext().getHostContext();
    announce(ctx, `已聚焦 ${label}，共 ${this.current.refs.length} 条关联关系`);
  }

  private setMode(m: ViewMode): void {
    this.mode = m;
    this.draw();
    const ctx = this.getUIContext().getHostContext();
    announce(ctx, m === 'neighbor' ? '已切换邻域探索视图' : '已切换分层全景视图');
  }

  // ---------- Canvas 骨架绘制（只用本项目已实证的 2D API：arc/fill/stroke/lineTo） ----------

  private draw(): void {
    const c: CanvasRenderingContext2D = this.ctx;
    c.clearRect(0, 0, CANVAS_W, CANVAS_H);
    if (this.mode === 'overview') {
      this.drawOverview(c);
    } else {
      this.drawNeighbor(c);
    }
  }

  private drawOverview(c: CanvasRenderingContext2D): void {
    const bandH: number = CANVAS_H / LAYER_ORDER.length;
    // 层分隔线 + 左侧层色条
    c.strokeStyle = '#e6dcc6';
    c.lineWidth = 1;
    for (let i: number = 1; i < LAYER_ORDER.length; i++) {
      c.beginPath();
      c.moveTo(4, i * bandH);
      c.lineTo(CANVAS_W - 4, i * bandH);
      c.stroke();
    }
    LAYER_ORDER.forEach((layer: string, li: number) => {
      c.fillStyle = LAYER_COLORS[layer];
      c.fillRect(2, li * bandH + 8, 4, bandH - 16);
    });
    // 跨层关系（骨架直线）：结构性边深、相关性边浅
    this.overview.edges.forEach((e: EdgeSeg) => {
      c.strokeStyle = e.kind === 'struct' ? '#a98f63' : '#d9cfbc';
      c.lineWidth = e.kind === 'struct' ? 1.5 : 1;
      c.beginPath();
      c.moveTo(e.x1, e.y1);
      c.lineTo(e.x2, e.y2);
      c.stroke();
    });
    // 节点（圆点）；聚焦节点加高亮圈
    this.overview.boxes.forEach((b: NodeBox) => {
      if (b.id === this.focusId) {
        c.strokeStyle = '#aa3333';
        c.lineWidth = 2;
        c.beginPath();
        c.arc(b.cx, b.cy, 8, 0, 2 * Math.PI);
        c.stroke();
      }
      c.fillStyle = b.color;
      c.beginPath();
      c.arc(b.cx, b.cy, b.r, 0, 2 * Math.PI);
      c.fill();
    });
  }

  private drawNeighbor(c: CanvasRenderingContext2D): void {
    const cur: NeighborLayout = this.current;
    // 边：聚焦 → 各邻节点（结构性边/相关性边分色）
    cur.pairs.forEach((p: NeighborPair) => {
      const other: NodeBox | null = this.boxOf(cur, p.to);
      if (!other) {
        return;
      }
      c.strokeStyle = p.kind === 'struct' ? '#a98f63' : '#c9b992';
      c.lineWidth = p.kind === 'struct' ? 2 : 1;
      c.beginPath();
      c.moveTo(cur.focus.cx, cur.focus.cy);
      c.lineTo(other.cx, other.cy);
      c.stroke();
    });
    // 邻节点
    cur.nodes.forEach((b: NodeBox) => {
      c.fillStyle = b.color;
      c.beginPath();
      c.arc(b.cx, b.cy, b.r, 0, 2 * Math.PI);
      c.fill();
      c.strokeStyle = '#faf7f0';
      c.lineWidth = 1.5;
      c.beginPath();
      c.arc(b.cx, b.cy, b.r, 0, 2 * Math.PI);
      c.stroke();
    });
    // 聚焦节点（底板圆 + 主圆）
    c.fillStyle = '#f3ead8';
    c.beginPath();
    c.arc(cur.focus.cx, cur.focus.cy, cur.focus.r + 9, 0, 2 * Math.PI);
    c.fill();
    c.fillStyle = '#aa3333';
    c.beginPath();
    c.arc(cur.focus.cx, cur.focus.cy, cur.focus.r, 0, 2 * Math.PI);
    c.fill();
    c.strokeStyle = '#7d2020';
    c.lineWidth = 2;
    c.beginPath();
    c.arc(cur.focus.cx, cur.focus.cy, cur.focus.r, 0, 2 * Math.PI);
    c.stroke();
  }

  private boxOf(cur: NeighborLayout, id: string): NodeBox | null {
    for (let i: number = 0; i < cur.nodes.length; i++) {
      if (cur.nodes[i].id === id) {
        return cur.nodes[i];
      }
    }
    return null;
  }

  build() {
    Scroll() {
      Column() {
        // 顶部栏：返回 + 标题
        Row() {
          Button('返回')
            .fontSize(15)
            .height(44)
            .accessibilityText('返回上一页')
            .onClick(() => router.back());
          Text('修真图谱')
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#333')
            .layoutWeight(1)
            .textAlign(TextAlign.Center);
        }
        .width('100%')
        .padding({ left: 12, right: 12, top: 8, bottom: 4 })
        .alignItems(VerticalAlign.Center);

        // 总览：太极装饰 + 规模统计
        Row({ space: 10 }) {
          TaijiDecor({ size: 40 });
          Column() {
            Text(`共 ${MAP_NODES.length} 节点 / ${MAP_EDGES.length} 关系`)
              .fontSize(13)
              .fontWeight(FontWeight.Medium)
              .fontColor('#6a5a3a');
            Text(this.countsLine)
              .fontSize(11)
              .fontColor('#8a7a5a')
              .margin({ top: 2 });
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1);
        }
        .width('94%')
        .accessibilityText(`修真图谱总览：${MAP_NODES.length} 节点，${MAP_EDGES.length} 关系，${this.countsLine}`);

        // 视图切换
        Row({ space: 10 }) {
          Button('邻域探索')
            .fontSize(14)
            .height(36)
            .backgroundColor(this.mode === 'neighbor' ? '#aa3333' : '#efe8d8')
            .fontColor(this.mode === 'neighbor' ? '#ffffff' : '#6a5a3a')
            .accessibilityText('切换到邻域探索视图：聚焦节点及其关联')
            .onClick(() => this.setMode('neighbor'));
          Button('分层全景')
            .fontSize(14)
            .height(36)
            .backgroundColor(this.mode === 'overview' ? '#aa3333' : '#efe8d8')
            .fontColor(this.mode === 'overview' ? '#ffffff' : '#6a5a3a')
            .accessibilityText('切换到分层全景视图：按道藏、典籍、专题、旁参、语料五层展示全部节点')
            .onClick(() => this.setMode('overview'));
        }
        .width('94%')
        .margin({ top: 6 });

        // 图谱画布（固定坐标系 320×280）：Canvas 画骨架，Text 覆盖层做标签与命中区
        Stack({ alignContent: Alignment.TopStart }) {
          Canvas(this.ctx)
            .width(CANVAS_W)
            .height(CANVAS_H)
            .backgroundColor('#faf7f0')
            .borderRadius(10)
            .onReady(() => this.draw());

          if (this.mode === 'overview') {
            // 层名（左侧，纯提示）
            ForEach(LAYER_ORDER, (layer: string) => {
              Text(LAYER_NAMES[layer])
                .fontSize(10)
                .fontColor('#7a6a4a')
                .width(46)
                .position({ x: 8, y: this.overview.bandCenters[layer] - 24 })
                .accessibilityLevel(AccessibilityLevel.No);
            }, (layer: string) => layer);
            // 节点命中区（与 Canvas 圆点同心的透明 Text，读屏文案 = 节点全量信息）
            ForEach(this.overview.boxes, (b: NodeBox) => {
              Text('●')
                .fontSize(13)
                .fontColor(Color.Transparent)
                .width(28)
                .height(28)
                .textAlign(TextAlign.Center)
                .position({ x: b.cx - 14, y: b.cy - 14 })
                .accessibilityText(`${b.label}，${TYPE_NAMES[b.type]}，${LAYER_NAMES[b.layer]}层，点击查看其关联关系`)
                .onClick(() => this.focusNodeById(b.id, b.label));
            }, (b: NodeBox) => b.id);
          } else {
            // 邻节点标签（居中于圆点下方，兼作命中区）
            ForEach(this.current.nodes, (b: NodeBox) => {
              Text(b.label)
                .fontSize(10)
                .fontColor('#4a4436')
                .width(88)
                .textAlign(TextAlign.Center)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
                .position({ x: b.cx - 44, y: b.cy + b.r + 2 })
                .accessibilityText(`${b.label}，${TYPE_NAMES[b.type]}，点击查看其关联关系`)
                .onClick(() => this.focusNodeById(b.id, b.label));
            }, (b: NodeBox) => b.id);
            // 聚焦节点标签（加粗）
            Text(this.current.focus.label)
              .fontSize(11)
              .fontWeight(FontWeight.Bold)
              .fontColor('#7d2020')
              .width(140)
              .textAlign(TextAlign.Center)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
              .position({ x: this.current.focus.cx - 70, y: this.current.focus.cy + this.current.focus.r + 4 })
              .accessibilityText(`当前聚焦：${this.current.focus.label}`);
          }
        }
        .width(CANVAS_W)
        .height(CANVAS_H)
        .margin({ top: 8 });

        // 聚焦节点详情
        Column() {
          Row() {
            Text(this.focusNode.label)
              .fontSize(16)
              .fontWeight(FontWeight.Bold)
              .fontColor('#333')
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis })
              .layoutWeight(1);
            Text(`${TYPE_NAMES[this.focusNode.type]} · ${LAYER_NAMES[this.focusNode.layer]}`)
              .fontSize(11)
              .fontColor('#999');
          }
          .width('100%');

          Text(this.focusNode.detail)
            .fontSize(12)
            .fontColor('#666')
            .margin({ top: 4 })
            .maxLines(3)
            .textOverflow({ overflow: TextOverflow.Ellipsis });

          Text(`出处：${this.focusNode.source}`)
            .fontSize(10)
            .fontColor('#aaa')
            .margin({ top: 4 });

          if (this.focusNode.link) {
            Row() {
              Button('打开原文链接')
                .fontSize(13)
                .height(32)
                .accessibilityText('在浏览器中打开该典籍的原文页面')
                .onClick(() => openExternal(this.focusNode.link));
            }
            .width('100%')
            .margin({ top: 6 });
          }
        }
        .alignItems(HorizontalAlign.Start)
        .width('94%')
        .padding(12)
        .backgroundColor('#ffffff')
        .borderRadius(10)
        .margin({ top: 8 });

        // 文本等价视图（读屏/长辈模式的完整信息通道，两条视图模式各自等价）
        Text(this.mode === 'neighbor' ? '关联关系（文本等价视图）' : '全量节点 · 按层分组（文本等价视图）')
          .fontSize(14)
          .fontWeight(FontWeight.Medium)
          .fontColor('#6a5a3a')
          .alignSelf(HorizontalAlign.Start)
          .margin({ top: 10, bottom: 4 });

        List() {
          ForEach(this.listItems, (it: MapListItem) => {
            ListItem() {
              Column() {
                Text(it.title)
                  .fontSize(it.header ? 15 : 14)
                  .fontWeight(it.header ? FontWeight.Medium : FontWeight.Normal)
                  .fontColor(it.header ? '#7a5a20' : '#333')
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis });
                if (it.sub) {
                  Text(it.sub)
                    .fontSize(11)
                    .fontColor('#999')
                    .margin({ top: 2 })
                    .maxLines(1)
                    .textOverflow({ overflow: TextOverflow.Ellipsis });
                }
              }
              .alignItems(HorizontalAlign.Start)
              .padding({ left: 12, right: 12, top: 8, bottom: 8 });
            }
            .width('100%')
            .backgroundColor(it.header ? '#f5ecd8' : '#ffffff')
            .accessibilityText(it.a11y)
            .onClick(() => {
              if (it.jumpId) {
                this.focusNodeById(it.jumpId, it.title);
              }
            });
          }, (it: MapListItem) => it.key);
        }
        .width('94%')
        .height(230)
        .backgroundColor('#f5f5f5')
        .borderRadius(10)
        .margin({ top: 2, bottom: 20 });
      }
      .width('100%')
      .alignItems(HorizontalAlign.Center);
    }
    .width('100%')
    .height('100%');
  }
}
