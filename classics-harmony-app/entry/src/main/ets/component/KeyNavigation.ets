/*
 * 按键 / 遥控器导航（构建块 · 未接线，翻写 NEXT）
 * 概念来源：MultimodalEvent（Java API8 Component.setKeyEventListener + KeyEvent DPAD 方向键/中心键）
 * 翻写：ArkUI onKeyEvent(event: KeyEvent) + KeyCode（方向键/确认键/返回键）；NEXT 多模输入 @ohos.multimodalInput.keyEvent（包名待核验 @kit.InputKit）
 * 适老化：大屏（智慧屏/电视）遥控器导航——老人用 方向键 + 确认键 操作，免触屏；与 Tabs/List 焦点联动滚动
 * 用法：在组件 onKeyEvent((e) => { const k = KeyNavigation.map(e.keyCode); /* 派发方向/确认 */ }) 中调用
 */
import { KeyCode } from '@kit.InputKit';

export type NavKey = 'up' | 'down' | 'left' | 'right' | 'enter' | 'back' | 'other';

export class KeyNavigation {
  /** 把按键码映射为导航语义键（集中处理 DPAD 与回车/返回） */
  static map(code: number): NavKey {
    switch (code) {
      case KeyCode.KEY_DPAD_UP:
        return 'up';
      case KeyCode.KEY_DPAD_DOWN:
        return 'down';
      case KeyCode.KEY_DPAD_LEFT:
        return 'left';
      case KeyCode.KEY_DPAD_RIGHT:
        return 'right';
      case KeyCode.KEY_DPAD_CENTER:
      case KeyCode.KEY_ENTER:
        return 'enter';
      case KeyCode.KEY_BACK:
        return 'back';
      default:
        return 'other';
    }
  }
}
