/*
 * 并行任务组（构建块 · 未接线，翻写 NEXT）
 * 概念来源：ParallelTaskDispatcher（Java API8 createParallelTaskDispatcher + createDispatchGroup + asyncGroupDispatch + groupDispatchNotify 栅栏）
 * 翻写：@kit.ArkTS taskpool 多任务并行 execute + Promise.all 充当 groupDispatchNotify（全部完成后再继续）
 * 适老化：并行加载多本古籍 / 批量解码多张道藏图 / 并行建全文检索索引，完成后统一刷新，避免串行卡顿冻屏
 * 用法：const r = await ParallelTasks.all([ new taskpool.Task(loadBook, 1), new taskpool.Task(loadBook, 2) ])
 *      真实任务请改写顶层 @Concurrent 函数，再 new taskpool.Task(fn, ...args)
 */
import { taskpool } from '@kit.ArkTS';

export class ParallelTasks {
  /** 并行派发多个 @Concurrent 任务，全部完成后按入参顺序返回结果数组（任一失败返回空数组） */
  static async all(tasks: taskpool.Task[]): Promise<Object[]> {
    try {
      const pending = tasks.map((t) => taskpool.execute(t));
      return await Promise.all(pending);
    } catch (e) {
      console.error(`ParallelTasks.all fail: ${(e as Error).message}`);
      return [];
    }
  }

  /** 并行派发并取首个完成结果（竞速，谁先好用谁） */
  static async race(tasks: taskpool.Task[]): Promise<Object | null> {
    try {
      return await Promise.race(tasks.map((t) => taskpool.execute(t)));
    } catch (e) {
      console.error(`ParallelTasks.race fail: ${(e as Error).message}`);
      return null;
    }
  }
}
