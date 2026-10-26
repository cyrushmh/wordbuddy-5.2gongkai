/*
 * TrafficStats.ets —— 设备流量统计（构建块，翻 NEXT @kit.NetworkKit statistics）
 * 来源：Batch24(中断补) DataFlowStatistics（Java API8：ohos.net.DataFlowStatistics.getAllRxBytes/getAllTxBytes + NetManager）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「查询上下行累计流量」概念做成未接线块（组网无障碍的辅助观测）。
 * NEXT 对应：import { statistics } from '@kit.NetworkKit'（getAllRxBytes / getAllTxBytes / getRxBytes(iface) 等）。
 * 用途：读书类场景一般不直接用，但「听书/下载离线书目」时显示本次消耗流量、设阈值提醒长辈，属于无障碍透明化。
 * 默认不接线：流量统计可能需 ohos.permission.GET_NETWORK_INFO（以 NEXT 当前 SDK 为准）；INTERNET 已声明。
 */
import { statistics } from '@kit.NetworkKit';

/** 抓取当前上下行累计字节数快照（未接线返回 0）。 */
export function snapshotRxTx(): { rx: number; tx: number } {
  // 接线（注意：statistics 接口在部分 NEXT 版本以 Promise/回调返回，以当前 SDK 为准）：
  // const rx = statistics.getAllRxBytes();
  // const tx = statistics.getAllTxBytes();
  // return { rx, tx };
  void statistics;
  return { rx: 0, tx: 0 };
}

/** 两次快照的差值（本次操作消耗的上下行字节）。 */
export function deltaRxTx(before: { rx: number; tx: number }, after: { rx: number; tx: number }): { rx: number; tx: number } {
  return { rx: after.rx - before.rx, tx: after.tx - before.tx };
}

/*
 * 接线伪代码（下载离线书目前后测流量）：
 *   const before = snapshotRxTx();
 *   await this.downloadBook(url);          // 听书/离线书目下载
 *   const used = deltaRxTx(before, snapshotRxTx());
 *   promptAction.showToast({ message: `本次下载约 ${(used.rx / 1048576).toFixed(1)} MB` });
 * 旧代对照：原样例用 ohos.net.DataFlowStatistics 同步取全域 rx/tx，再 NetManager 开连接测单请求差值；
 *          NEXT 的 statistics 直接对齐这两方法，NetManager 收口进 @kit.NetworkKit 的 net/connection。
 */
