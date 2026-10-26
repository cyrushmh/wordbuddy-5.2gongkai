/**
 * 蜂窝信号查询与监听构建块（来自 RadioInfoManager + RadioStateObserver，HarmonyOS Java API8 旧代）。
 *
 * 旧代 RadioInfoManager.getInstance().getSignalInfoList(slotId) 读网络类型/信号强度；
 *   RadioStateObserver 用 addObserver(observer, OBSERVE_MASK_NETWORK_STATE | OBSERVE_MASK_SIGNAL_INFO) 持续监听。
 * NEXT 用 @kit.TelephonyKit 的 @ohos.telephony.signal：getSignalInformation(slotId) + on('signalInfoChange')。
 * 适老化：老人看信号格判断网络；弱信号时提示「切 Wi-Fi / 走近窗口」或把在线服务降级走离线。
 *
 * 权限：ohos.permission.GET_NETWORK_INFO（块内标注，module.json5 的 requestPermissions 接线时补）。
 * 未接线构建块：默认不接入任何页面。
 */
import signal from '@ohos.telephony.signal'; // 待核验：NEXT 疑似 @kit.TelephonyKit，DevEco 最终确认

export interface SignalSnapshot {
  slotId: number;
  networkType: number;   // 见 radio.NetworkType / NetworkGeneration
  signalLevel: number;   // 0~4 格
}

export class CellSignal {
  /** 读一次当前信号（网络类型 + 信号格）。 */
  async read(slotId: number = 0): Promise<SignalSnapshot[]> {
    const list: Array<ESObject> = await signal.getSignalInformation(slotId);
    return list.map((s: ESObject) => ({
      slotId,
      networkType: s.networkType,
      signalLevel: s.signalLevel
    }));
  }

  /** 持续监听信号/网络状态变化，返回取消函数。 */
  watch(slotId: number = 0, cb: (snaps: SignalSnapshot[]) => void): () => void {
    const handler = async (): Promise<void> => {
      cb(await this.read(slotId));
    };
    signal.on('signalInfoChange', slotId, handler);
    return (): void => {
      signal.off('signalInfoChange', slotId, handler);
    };
  }
}
