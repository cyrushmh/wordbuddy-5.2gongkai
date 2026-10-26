/**
 * 阅读相关跨页/跨进程公共事件。
 *
 * 参考 waylau ArkTSCommonEventService 示例（@ohos.commonEventManager 发布/订阅）。
 *
 * 为什么不用 AppStorage：AppStorage 是单 UIAbility 进程内的响应式状态，
 * 跨进程（如 Form 卡片扩展 Ability）收不到。书签在 ChapterDetail 变更后，
 * 用户按返回键回 Index 时 Index.aboutToAppear 不会重新触发，列表会陈旧；
 * 用 CommonEvent 广播可让首页书签列表即时刷新，也可被今日经典卡片（Form）订阅。
 */
import commonEventManager from '@ohos.commonEventManager';

/** 书签变更事件名（自定义公共事件）。 */
export const READING_EVENT_BOOKMARK_CHANGED: string = 'reading.bookmark.changed';

/** 当前进程的订阅者句柄（单例，避免重复订阅）。 */
let subscriber: commonEventManager.CommonEventSubscriber | null = null;

/** 创建订阅者并订阅「书签变更」事件。重复调用安全（已订阅则忽略）。 */
export function subscribeBookmarkChanged(onChanged: () => void): void {
  if (subscriber) {
    return;
  }
  commonEventManager.createSubscriber(
    { events: [READING_EVENT_BOOKMARK_CHANGED] },
    (err: Error, sub: commonEventManager.CommonEventSubscriber) => {
      if (err) {
        console.error(`subscribeBookmarkChanged createSubscriber failed: ${err.message}`);
        return;
      }
      subscriber = sub;
      commonEventManager.subscribe(sub, (e: Error, data: commonEventManager.CommonEventData) => {
        if (!e) {
          onChanged();
        }
      });
    }
  );
}

/** 发布「书签变更」事件（跨页/跨进程广播）。 */
export function publishBookmarkChanged(): void {
  commonEventManager.publish(READING_EVENT_BOOKMARK_CHANGED, (err: Error) => {
    if (err) {
      console.error(`publishBookmarkChanged failed: ${err.message}`);
    }
  });
}

/** 退订并释放订阅者句柄。 */
export function unsubscribeBookmarkChanged(): void {
  if (!subscriber) {
    return;
  }
  const sub = subscriber;
  subscriber = null;
  commonEventManager.unsubscribe(sub, (err: Error) => {
    if (err) {
      console.error(`unsubscribeBookmarkChanged failed: ${err.message}`);
    }
  });
}
