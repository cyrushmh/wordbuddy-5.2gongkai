/*
 * UDP Socket 通信（构建块 · 未接线，翻写 NEXT）
 * 概念来源：NetManagerHandleSocket（Java API8 ohos.net.NetManager + NetHandle.bindSocket + DatagramSocket 收发）
 * 翻写：@kit.NetworkKit socket.constructUDPSocketInstance + bind / send / on('message')；多网卡场景用 connection 选网
 * 适老化：局域网设备间通信（子女端 ↔ 老人端 指令/状态对讲）、本地回环自测
 * 权限：ohos.permission.INTERNET（NEXT 需在 module.json5 声明）；GET/SET_NETWORK_INFO 在 api9+ 多并入 INTERNET 或省略
 */
import { socket } from '@kit.NetworkKit';

export class UdpSocket {
  private inst: socket.UDPSocket | null = null;

  /** 创建并绑定端口（port 缺省由系统分配） */
  async bind(port?: number): Promise<void> {
    try {
      this.inst = socket.constructUDPSocketInstance();
      const opts: socket.UDPSocketBindOptions = {};
      if (port !== undefined) {
        opts.address = port;
      }
      await this.inst.bind(opts);
    } catch (e) {
      console.error(`UdpSocket.bind fail: ${(e as Error).message}`);
    }
  }

  /** 发送数据报到目标 host:port（data 为文本或二进制） */
  async send(host: string, port: number, data: string | ArrayBuffer): Promise<void> {
    if (!this.inst) {
      return;
    }
    try {
      const msg: socket.UDPSendOptions = {
        data,
        address: { address: host, port },
      };
      await this.inst.send(msg);
    } catch (e) {
      console.error(`UdpSocket.send fail: ${(e as Error).message}`);
    }
  }

  /** 监听收到的数据报，回调 (数据文本, 远端地址) */
  onMessage(cb: (data: string, remote: string) => void): void {
    if (!this.inst) {
      return;
    }
    this.inst.on('message', (msg: socket.UDPSocketMessageInfo) => {
      const text = typeof msg.message === 'string' ? msg.message : '';
      const remote = msg.remoteInfo?.address ?? '';
      cb(text, remote);
    });
  }

  offMessage(): void {
    this.inst?.off('message');
  }

  close(): void {
    this.inst?.close();
    this.inst = null;
  }
}
