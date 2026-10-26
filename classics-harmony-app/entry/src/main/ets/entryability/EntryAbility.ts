import { AbilityConstant, UIAbility, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { window } from '@kit.ArkUI';
import { initReaderPrefs } from '../model/ReaderPrefs';
import DeviceSync from '../model/DeviceSync';

const DOMAIN: number = 0x0000;

/**
 * 深链捕获：外部以 classics://book?bookId=X&chapterId=Y 拉起时，
 * 把启动目标存进 AppStorage，首页 Index 据此直达指定典籍/章节。
 * 系统会把 viewData URI 的 query 解析进 want.parameters；这里再兜底直解 want.uri。
 */
function captureLaunchTarget(want: Want): void {
  let bookId: string = '';
  let chapterId: number = -1;
  const p = want.parameters as Record<string, Object> | undefined;
  if (p) {
    bookId = (p['bookId'] as string) ?? '';
    chapterId = (p['chapterId'] as number) ?? -1;
  }
  if ((!bookId || chapterId < 0) && want.uri) {
    try {
      const u = new URL(want.uri);
      const b = u.searchParams.get('bookId');
      const c = u.searchParams.get('chapterId');
      if (b) {
        bookId = b;
      }
      if (c !== null) {
        chapterId = Number(c);
      }
    } catch (e) {
      hilog.error(DOMAIN, 'testTag', 'Failed to parse deep link uri: %{public}s', JSON.stringify(e));
    }
  }
  if (bookId) {
    AppStorage.setOrCreate('launchTarget', { bookId, chapterId });
  }
}

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onCreate');
    initReaderPrefs(this.context);
    DeviceSync.init(this.context);
    captureLaunchTarget(want);
  }

  onDestroy(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onDestroy');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageCreate');
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        hilog.error(DOMAIN, 'testTag', 'Failed to load the content. Cause: %{public}s', JSON.stringify(err));
        return;
      }
      hilog.info(DOMAIN, 'testTag', '%{public}s', 'Succeeded in loading the content.');
    });
  }

  onWindowStageDestroy(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageDestroy');
  }

  onForeground(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onForeground');
  }

  onBackground(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onBackground');
  }
}
