/**
 * 系统矢量图标构建块（来自 ArkUISymbolGlyphSymbolSpan 的 SymbolGlyph / SymbolSpan 用法）。
 *
 * 为什么值得用：
 *   - 矢量、主题/高对比自适应——开启「高对比 / 长辈模式」时图标自动随色彩方案变化，
 *     无需为不同模式准备多套位图，直接服务「系统使用无障碍 + 适老化」。
 *   - 免位图资源，减小包体；用 $r('sys.symbol.xxx') 引用系统预置符号。
 *   - 可着色（fontColor）、可缩放（fontSize）、可加粗（fontWeight）、可单/多色渲染、
 *     可加动效（scale / bounce / hierarchical）。
 *   - SymbolSpan 可作为 Text 的子组件，在正文里行内嵌图标（如「已同步 ◉」）。
 *
 * 默认不接线：当前 Index 组网卡 WiFi 指示、书签增删、BottomTabs 图标仍用位图/Resource；
 * 替换需核对现有资源且无法 SDK 验证，故先沉淀为本块，待你定。
 *
 * 接线（待你定）：
 *   1) 组网状态卡把 WiFi 图换成 `SymbolGlyph($r('sys.symbol.ohos_wifi'))`，高对比模式自动适配；
 *   2) 书签「加入/删除」按钮改用 ohos_folder_badge_plus / ohos_trash，免去两张 PNG；
 *   3) BottomTabs 标签图标改用 SymbolGlyph，省去选中/未选中两套图。
 *
 * 适老化要点：图标尺寸建议 ≥24、配高对比 fontColor；装饰性图标仍用 AccessibilityLevel.No 降权。
 */
import { SymbolGlyph, SymbolSpan, Text, Row, Column, Button, SymbolEffectStrategy, EffectFillStyle, HierarchicalSymbolEffect, FontWeight } from '@kit.ArkUI';

/** 应用常用系统符号名（按需取用，避免散落硬编码字符串）。 */
export const AppSymbols = {
  wifi: 'sys.symbol.ohos_wifi',
  add: 'sys.symbol.ohos_folder_badge_plus',
  trash: 'sys.symbol.ohos_trash',
  bookmark: 'sys.symbol.ohos_bookmark',
  search: 'sys.symbol.ohos_search',
  person: 'sys.symbol.ohos_person',
  grid: 'sys.symbol.ohos_grid',
} as const;

/** 单个矢量图标：可着色、可缩放、可加动效。 */
@Component
export struct SymIcon {
  @Prop name: string = AppSymbols.wifi;
  @Prop size: number = 28;
  @Prop color: string | Color = '#222222';
  @Prop active: boolean = true; // 是否播放层级动效（如 WiFi 连接态）

  build() {
    SymbolGlyph($r(this.name))
      .fontSize(this.size)
      .fontColor([this.color as Color])
      .symbolEffect(new HierarchicalSymbolEffect(EffectFillStyle.ITERATIVE), this.active);
  }
}

/** 行内图标文本：在一段文字里嵌矢量图标（如「已同步」后接 wifi 符号）。 */
@Component
export struct SymText {
  @Prop leadIcon?: string;
  @Prop text: string = '';
  @Prop tailIcon?: string;
  @Prop size: number = 16;
  @Prop color: string | Color = '#222222';

  build() {
    Text() {
      if (this.leadIcon) {
        SymbolSpan($r(this.leadIcon)).fontSize(this.size).fontColor([this.color as Color]);
      }
      Span(this.text);
      if (this.tailIcon) {
        SymbolSpan($r(this.tailIcon)).fontSize(this.size).fontColor([this.color as Color]);
      }
    }
    .fontSize(15)
    .fontColor(this.color as Color);
  }
}
