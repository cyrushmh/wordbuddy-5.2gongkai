/*
 * CharCounter.ets —— 字符/字数统计（ArkTS NEXT 真代码提炼，可直接接线）
 * 来源：Batch23 CountTheNumberOfCharacters（ArkTS struct Index，this.s.length 统计字符）
 * 代际：ArkTS NEXT，语法已验证，无需翻写；本块直接提炼为可复用工具 + 进度小卡。
 * 用途：章节字数统计、阅读进度（已读字符/总字符）、听书播报「本章共 N 字」——服务视障/长辈听书进度感知。
 * 默认不接线；纯 ArkTS 字符串 .length（按 UTF-16 code unit，中文每字计 1），可直接调用，无需 SDK 校验。
 */
import { announce } from '../model/Accessibility';

/** 统计字符数（中文按字计 1，与 this.s.length 行为一致）。 */
export function countChars(text: string): number {
  return text.length;
}

/** 阅读进度百分比（已读字符 / 总字符），0~100，越界钳制。 */
export function readingPercent(read: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round((read / total) * 100)));
}

/** 进度小卡：展示「共 N 字 · 已读 M%」，带读屏播报。可直接放进阅读页底部（系统使用无障碍）。 */
@Component
export struct ProgressStat {
  @Prop total: number = 0;
  @Prop read: number = 0;

  build() {
    Row() {
      Text(`共 ${this.total} 字 · 已读 ${readingPercent(this.read, this.total)}%`)
        .fontSize(13)
        .fontColor('#888')
        .accessibilityText(`本章共 ${this.total} 字，已读百分之 ${readingPercent(this.read, this.total)}`)
    }
    .onClick(() => {
      announce(undefined, `本章共 ${this.total} 字，已读百分之 ${readingPercent(this.read, this.total)}`);
    })
  }
}
