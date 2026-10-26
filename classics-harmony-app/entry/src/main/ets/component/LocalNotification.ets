/*
 * 本地通知（构建块 · 未接线，翻写 NEXT）
 * 概念来源：Notification / NotificationOnPhone（Java API8 ohos.event.notification NotificationHelper + NotificationSlot + NotificationRequest）
 * 翻写：@kit.NotificationKit notificationManager.publishNotification + NotificationRequest（标题/正文）
 * 适老化：服药提醒、久坐提醒、子女远程呼叫到达——老人无需开 App 即在通知栏/锁屏看到；
 *          可配合 B29 CommonEventBus 长辈紧急广播 与 B31 DeviceLight 呼吸灯联动，多通道防漏看
 * 权限：通知默认开放；若需自定义渠道级别/振动/呼吸灯，按 NEXT 通知渠道规则声明（接线前确认）
 */
import { notificationManager } from '@kit.NotificationKit';

export class LocalNotification {
  private idSeq = 0;

  /** 发一条普通文本通知（title 标题 / text 正文），返回通知 id 便于后续取消 */
  publish(title: string, text: string): number {
    const id = ++this.idSeq;
    const request: notificationManager.NotificationRequest = {
      id,
      content: {
        contentType: notificationManager.ContentType.NOTIFICATION_CONTENT_BASIC_TEXT,
        normal: {
          title,
          text,
        },
      } as notificationManager.NotificationBasicContent,
    };
    notificationManager.publishNotification(request).catch((err: Error) => {
      console.error(`LocalNotification.publish fail: ${err.message}`);
    });
    return id;
  }

  /** 取消指定 id 的通知；不传则取消上一条 */
  cancel(id?: number): void {
    const target = id ?? this.idSeq;
    notificationManager.cancelNotification(target).catch(() => {});
  }
}
