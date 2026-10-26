/*
 * 服务卡片（桌面 Widget）提供方范式（构建块 · 未接线，翻写 NEXT）
 * 概念来源：HelloDog（Java API8 FormController 抽象类：bindFormData/updateFormData/onTriggerFormEvent/getRoutePageSlice）
 * 翻写：@kit.FormKit FormExtensionAbility + formProvider + formBindingData
 * 适老化：桌面卡片展示「每日一句 / 读书进度」，长辈免进 App 即见内容（组网无障碍延伸）
 * 接线前：需新建 FormExtensionAbility（entry/.../FormAbility.ets）+ module.json5 注册 forms + 卡片布局，本块仅抽数据层范式
 */
import { formBindingData, formProvider } from '@kit.FormKit';

export class ServiceWidget {
  /**
   * 卡片数据绑定：把业务数据封装为卡片可渲染的 FormBindingData
   * @param data 卡片展示数据（如 { quote: '...', progress: '3/12' }）
   */
  static bindFormData(data: Record<string, Object>): formBindingData.FormBindingData {
    return formBindingData.createFormBindingData(data);
  }

  /**
   * 更新指定卡片
   * @param formId 卡片实例 ID（数字型）
   * @param data 新数据
   */
  static async updateForm(formId: number, data: Record<string, Object>): Promise<void> {
    try {
      const binding = formBindingData.createFormBindingData(data);
      await formProvider.updateForm(formId, binding);
    } catch (e) {
      console.error(`ServiceWidget.updateForm fail: ${(e as Error).message}`);
    }
  }

  /**
   * 卡片点击路由：解析卡片消息，决定跳转目标（如打开某本书）
   * 真实场景在 FormExtensionAbility.onFormEvent 中调用
   * @param message 卡片上报消息，约定形如 "openBook:123"
   * @returns 路由参数
   */
  static routeFromEvent(message: string): string {
    return message;
  }
}
