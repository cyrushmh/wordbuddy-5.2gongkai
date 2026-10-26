/*
 * 后台异步任务派发（构建块 · 未接线，翻写 NEXT）
 * 概念来源：EventHandler（Java API8 EventRunner + EventHandler + InnerEvent 后台线程事件）
 * 翻写：@kit.ArkTS taskpool（官方建议替代 EventHandler 的后台线程方案）
 * 适老化：离线书目下载 / 听书缓存 / 道藏图解码 / 全文检索建索引等耗时操作放后台，避免卡 UI 冻屏
 * 用法：getHeavyResult = await AsyncTaskRunner.run(200000)
 *      真实任务请自行定义顶层 @Concurrent 函数，再 new taskpool.Task(fn, ...args) 派发
 */
import { taskpool } from '@kit.ArkTS';

// 示例耗时任务：须为顶层 @Concurrent 函数，taskpool 才能序列化派发到后台线程
@Concurrent
function sampleHeavyTask(rounds: number): number {
  let sum = 0;
  for (let i = 0; i < rounds; i++) {
    sum += i;
  }
  return sum;
}

export class AsyncTaskRunner {
  /**
   * 派发后台任务（不阻塞 UI 线程）
   * @param rounds 计算量占位，真实场景替换为实际耗时逻辑（或改写为调用你的 @Concurrent 任务）
   * @returns 任务返回值；失败返回 -1
   */
  static async run(rounds: number = 100000): Promise<number> {
    try {
      const task = new taskpool.Task(sampleHeavyTask, rounds);
      return (await taskpool.execute(task)) as number;
    } catch (e) {
      console.error(`AsyncTaskRunner.run fail: ${(e as Error).message}`);
      return -1;
    }
  }
}
