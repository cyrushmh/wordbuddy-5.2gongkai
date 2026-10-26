/*
 * SystemIntentLauncher.ets —— 本地系统意图 / 深链 / 拨号（构建块，翻 NEXT @kit.AbilityKit）
 * 来源：Batch28 五个同系样本（Java API8：Intent.OperationBuilder().withXxx().build() + startAbility）
 *   - IntentOperationWithUri        → withUri("https://...")               打开网页/深链/浏览器
 *   - IntentOperationWithActionSearch → withAction(ACTION_SEARCH)          系统搜索
 *   - IntentOperationWithActionManageApplicationsSettings → ACTION_MANAGE_APPLICATIONS_SETTINGS  应用设置
 *   - IntentOperationWithActionDial → withAction(ACTION_DIAL).withUri("tel:...")  拨号（可带号码）
 * 代际：旧版 Java 工程，NEXT 翻写；旧代 Intent/OperationBuilder 在 NEXT 即 Want 对象字面量 + context.startAbility，语义一致，做成未接线块。
 * NEXT 对应：import { common, Want } from '@kit.AbilityKit'；context.startAbility(want) / context.startAbilityByType(...)
 * 适老化：本块是「一键直达系统能力」入口——长辈端可绑「一键打开系统设置调字号/对比度」「一键拨子女」，免层层菜单。
 * 权限：拨号/深链/设置均为系统隐式意图，一般无需本应用额外声明权限；默认不接线。
 *
 * 关于 action 取值：NEXT 用字符串 action（如 'ohos.want.action.dial'、'ohos.want.action.viewData'）。
 *   严格写法可 import { wantConstant } from '@kit.AbilityKit' 用 wantConstant.Action.* 枚举，本块保留字符串以便快速替换与拼装。
 */
import { common, Want } from '@kit.AbilityKit';

/**
 * 在当前 UIAbility 上下文拉起一个系统/隐式意图。
 * 接线：把 want 交给 (getContext(this) as common.UIAbilityContext).startAbility(want)。
 */
function launch(context: common.Context, want: Want): void {
  // 接线：
  // (context as common.UIAbilityContext).startAbility(want);
  void context;
  void want;
}

/** 打开 URI（网页 / 深链 / 自定义 scheme）。对应旧代 withUri("https://...")。 */
export function openUri(uri: string): void {
  const want: Want = {
    action: 'ohos.want.action.viewData', // 等价于旧代 withUri + 默认 view 动作
    uri
  };
  // 备选（按文件类型派发）：context.startAbilityByType('webview' | mimeType, want, ...)
  launch(globalThis.__classicsCtx ?? (null as unknown as common.Context), want);
}

/** 触发一个系统 action（如搜索、应用设置）。对应旧代 withAction(ACTION_XXX)。 */
export function startSystemAction(action: string, parameters?: Record<string, Object>): void {
  const want: Want = { action, parameters: parameters ?? {} };
  launch(globalThis.__classicsCtx ?? (null as unknown as common.Context), want);
}

/** 系统搜索。对应旧代 ACTION_SEARCH。 */
export function openSearch(keyword?: string): void {
  startSystemAction('ohos.want.action.search', keyword ? { searchKey: keyword } : undefined);
}

/** 打开应用管理/设置。对应旧代 ACTION_MANAGE_APPLICATIONS_SETTINGS（适老化：一键进字号对比度设置）。 */
export function openAppSettings(): void {
  startSystemAction('ohos.want.action.manageApplicationsSettings');
}

/**
 * 拨号（适老化：一键拨子女）。对应旧代 ACTION_DIAL + withUri("tel:num")。
 * @param number 目标号码；省略则只拉起拨号盘不预填。
 */
export function dial(number?: string): void {
  const want: Want = number
    ? { action: 'ohos.want.action.dial', uri: `tel:${number}` }
    : { action: 'ohos.want.action.dial' };
  launch(globalThis.__classicsCtx ?? (null as unknown as common.Context), want);
}

/*
 * 接线伪代码（长辈端「一键拨子女」按钮）：
 *   Button('一键拨子女')
 *     .onClick(() => dial('18088888888'))
 * 旧代对照：
 *   原样例 intent.setOperation(new Intent.OperationBuilder()
 *     .withAction(IntentConstants.ACTION_DIAL).withUri(Uri.parse("tel:18088888888")).build());
 *   NEXT 把 OperationBuilder 收敛为 want 对象字面量，action/uri 字段同名语义不变。
 *
 * 适老化延伸：把 openAppSettings() 绑到「调大字号」入口，配合 Batch22 SystemEventHub 自动跟随，
 *   长辈无需在系统设置里翻找即可一键直达对比度/字号页。
 */
