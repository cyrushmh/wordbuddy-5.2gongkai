/**
 * PermissionHelper —— 运行时权限构建块（由 ArkTSUserGrant / UserGrantMicrophone / WantOpenSetting / WantOpenManageApplications 迁移）
 *
 * 当前应用（阅读设置 / 书签 / 道藏跳转 / 深链 / 轮播）均不需要运行时权限，故本模块默认「不接入」主流程。
 * 未来需要麦克风或联网时再接线（见底部「接入步骤」）：
 *   - 语音搜索 / 录音笔记（SpeechRecognizer / AudioCapturer）→ 需 ohos.permission.MICROPHONE
 *   - HttpFetcher 远程书目 / 道藏图（已建构建块）→ 需 ohos.permission.INTERNET（并在 module.json5 声明）
 *
 * 标准 API 来源：
 *   - abilityAccessCtrl.createAtManager().requestPermissionsFromUser(ctx, perms) → 弹系统授权框
 *   - atManager.checkAccessToken(token, perm) → 查询已授权状态（避免重复弹框）
 *   - context.startAbility(want) → 跳系统设置 / 应用管理（用户拒权后引导去手动开）
 */

import { abilityAccessCtrl, common, Permissions, Want } from '@kit.AbilityKit';
import { BusinessError } from '@kit.BasicServicesKit';

const GRANTED: number = 0;

/** 常用权限常量（按需取用，接入时再在 module.json5 的 requestPermissions 声明） */
export const Perms = {
  MICROPHONE: 'ohos.permission.MICROPHONE',
  INTERNET: 'ohos.permission.INTERNET',
  CAMERA: 'ohos.permission.CAMERA'
} as const;

/** 取 UIAbilityContext（页面内用 getContext(this)，Ability 内用 this.context） */
function uiContext(ctx: Object): common.UIAbilityContext {
  return ctx as common.UIAbilityContext;
}

/**
 * 请求一组权限，返回每个权限的授权结果（0=同意，非0=拒绝/其他）。
 * 用法：const results = await requestPermissions(getContext(this), [Perms.MICROPHONE]);
 */
export function requestPermissions(ctx: Object, permissions: Array<Permissions>): Promise<number[]> {
  const atManager: abilityAccessCtrl.AtManager = abilityAccessCtrl.createAtManager();
  return new Promise<number[]>((resolve, reject) => {
    atManager.requestPermissionsFromUser(uiContext(ctx), permissions).then((data) => {
      resolve(data.authResults);
    }).catch((err: BusinessError) => {
      reject(err);
    });
  });
}

/**
 * 查询某权限当前是否已授权（不弹框），用于进入功能前静默判断。
 */
export async function isGranted(ctx: Object, permission: Permissions): Promise<boolean> {
  const atManager: abilityAccessCtrl.AtManager = abilityAccessCtrl.createAtManager();
  const token: string = uiContext(ctx).tokenId.toString();
  try {
    const result: abilityAccessCtrl.GrantStatus = await atManager.checkAccessToken(token, permission);
    return result === abilityAccessCtrl.GrantStatus.PERMISSION_GRANTED;
  } catch (err) {
    return false;
  }
}

/**
 * 跳系统设置（用户拒权后引导去手动开启）。
 * 复刻 ArkTSWantOpenSetting：bundleName=com.huawei.hmos.settings, abilityName=...MainAbility
 */
export function openSettings(ctx: Object): void {
  const want: Want = {
    deviceId: '',
    bundleName: 'com.huawei.hmos.settings',
    abilityName: 'com.huawei.hmos.settings.MainAbility'
  };
  try {
    uiContext(ctx).startAbility(want);
  } catch (err) {
    // 设置页拉起失败（极少数系统版本差异），静默忽略
  }
}

/**
 * 跳应用管理（应用权限列表），复刻 ArkTSWantOpenManageApplications：action=ohos.settings.manage.applications
 */
export function openAppManagement(ctx: Object): void {
  const want: Want = {
    action: 'ohos.settings.manage.applications'
  } as Want;
  try {
    uiContext(ctx).startAbility(want);
  } catch (err) {
    // 静默忽略
  }
}

/**
 * 接入步骤（未来点名做麦克风/联网功能时）：
 * 1) module.json5 → module → requestPermissions 增加对应项（如 MICROPHONE），含 reason/usedScene
 * 2) 进入功能前：if (!(await isGranted(ctx, Perms.MICROPHONE))) { 弹框说明用途 → requestPermissions → 仍拒则 openAppManagement 引导 }
 * 3) 拿到授权结果后再初始化 SpeechRecognizer / AudioCapturer / HttpFetcher
 */
