/*
 * AbilityResultCaller.ets —— 带结果的启动（构建块，翻 NEXT @kit.AbilityKit）
 * 来源：Batch28 IntentOperationWithAction（Java API8：startAbilityForResult(intent, CODE) + onAbilityResult 取回参数）
 *   旧代范式：主 Ability 用 startAbilityForResult 拉起 WeatherAbility，被拉起方设结果后，主方 onAbilityResult 中
 *   resultData.getStringParam("temperature") 取回返回值。
 * 代际：旧版 Java 工程，NEXT 翻写；旧代 startAbilityForResult + onAbilityResult 在 NEXT 即
 *   context.startAbilityForResult(want): Promise<AbilityResult>，回调即 Promise.then，语义一致，做成未接线块。
 * NEXT 对应：import { common, Want } from '@kit.AbilityKit'；AbilityResult = { resultCode: number; want?: Want }
 * 适老化：用于「向子 Ability 取一个选择结果」——如读书页拉起「字号选择面板」取回用户所选档位，再写回 Preferences。
 * 权限：无额外权限；默认不接线。
 */
import { common, Want } from '@kit.AbilityKit';

/** 取回结果的承载。 */
export interface AbilityResult {
  resultCode: number;
  parameters?: Record<string, Object>;
}

/**
 * 启动一个 Ability 并等待其返回结果（对应旧代 startAbilityForResult + onAbilityResult）。
 * @param context UIAbility 上下文
 * @param want    目标 Ability 的 Want（含 bundleName/abilityName/parameters）
 * @returns 被拉起方通过 terminateSelfWithResult 回传的 { resultCode, parameters }
 */
export function callForResult(context: common.Context, want: Want): Promise<AbilityResult> {
  // 接线：
  // const uiCtx = context as common.UIAbilityContext;
  // return uiCtx.startAbilityForResult(want).then((r) => ({
  //   resultCode: r.resultCode,
  //   parameters: r.want?.parameters as Record<string, Object> | undefined
  // }));
  void context;
  void want;
  return Promise.resolve({ resultCode: -1, parameters: undefined });
}

/*
 * 接线伪代码（读书页拉起「字号选择面板」取回档位）：
 *   callForResult(getContext(this) as common.Context, {
 *     bundleName: 'com.classics.hmos',
 *     abilityName: 'com.classics.hmos.FontPickerAbility',
 *     parameters: { current: 'large' }
 *   }).then((res) => {
 *     const picked = res.parameters?.['fontSize'] as string;
 *     if (picked) { /* 写回 Preferences + 触发 Batch22 SystemEventHub 跟随 *\/ }
 *   });
 * 旧代对照：原样例 startAbilityForResult(intent, CODE) 后于 onAbilityResult(reqCode, resultCode, data)
 *           用 data.getStringParam("temperature") 取回；NEXT 改为 Promise 回调，requestCode 由闭包捕获，
 *           回传值从 resultData 改为 AbilityResult.want.parameters。
 */
