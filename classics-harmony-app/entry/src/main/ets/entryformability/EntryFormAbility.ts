import formInfo from '@ohos.app.form.formInfo';
import formBindingData from '@ohos.app.form.formBindingData';
import FormExtensionAbility from '@ohos.app.form.FormExtensionAbility';
import { dailyVerse } from '../model/DailyVerse';

/**
 * 今日经典卡片的 FormExtensionAbility。
 * 参考 waylau ArkTSAtomicService 的 EntryFormAbility 骨架，
 * onAddForm / onUpdateForm 把每日一句以 formBindingData 推到卡片。
 */
export default class EntryFormAbility extends FormExtensionAbility {
  onAddForm(want: Want): formBindingData.FormBindingData {
    const v = dailyVerse();
    return formBindingData.createFormBindingData({ verse: v.verse, source: v.source });
  }

  onCastToNormalForm(formId: string): void {
    // 临时卡片转为常态卡片时的回调，无需处理。
  }

  onUpdateForm(formId: string): void {
    // 系统触发刷新时重新推送当日经典。
    const v = dailyVerse();
    formBindingData.createFormBindingData({ verse: v.verse, source: v.source });
  }

  onChangeFormVisibility(newStatus: Record<string, number>): void {
    // 卡片可见性变化，无需处理。
  }

  onFormEvent(formId: string, message: string): void {
    // 卡片自定义事件，无需处理。
  }

  onRemoveForm(formId: string): void {
    // 卡片销毁，无需处理。
  }

  onAcquireFormState(want: Want): formInfo.FormState {
    return formInfo.FormState.READY;
  }
};
