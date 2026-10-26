/*
 * 页内导航 + 页面生命周期（构建块 · 未接线，翻写 NEXT）
 * 概念来源：PageAndAbilitySliceLifeCycle（Java API8 AbilitySlice 生命周期 + present() 切片间跳转）
 * 翻写：@kit.ArkUI router.pushUrl / replaceUrl / back + 页面生命周期 aboutToAppear / onPageShow / onPageHide / aboutToDisappear
 * 适老化：经典阅读 App 的书架 → 阅读器 → 章节 三级跳转主干；参数随路由传递，免全局状态、防老人误触丢上下文
 * 权限：无（纯路由，不涉敏感权限）
 *
 * 旧代 AbilitySlice 生命周期 → NEXT 页面/组件生命周期 对照：
 *   onStart     → aboutToAppear（组件/页面即将出现，做初始化）
 *   onActive    → onPageShow（页面前台可见，可刷新数据）
 *   onInactive  → onPageHide（页面退到后台但仍存活）
 *   onBackground→ 应用进入后台（无单页直接等价，用 onPageHide 近似即可）
 *   onForeground→ onPageShow（回到前台）
 *   onStop     → aboutToDisappear（组件/页面销毁，释放资源）
 */
import { router } from '@kit.ArkUI';

export class PageNavigator {
  /** 压入新页面（保留当前页，可返回），params 随路由带参 */
  static push(url: string, params?: object): void {
    router.pushUrl({ url, params });
  }

  /** 替换当前页（清空返回栈，适合引导/登录后跳主页，老人误点返回不会回到上一步） */
  static replace(url: string, params?: object): void {
    router.replaceUrl({ url, params });
  }

  /** 返回上一页；name 可选，指定则返回到某页 url */
  static back(name?: string): void {
    if (name) {
      router.back({ url: name });
    } else {
      router.back();
    }
  }

  /** 读取上页 push 时传入的路由入参 */
  static params<T = object>(): T {
    return router.getParams() as T;
  }
}
