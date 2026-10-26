/*
 * BackgroundService.ets —— 后台服务 + 远程调用(RPC)（构建块，翻 NEXT @kit.AbilityKit + @kit.IPCKit，未接线）
 * 来源：Batch30 两份旧代样例合并——
 *   ① JavaServiceAbilityLifeCycle（Java API8：TimeServiceAbility 生命周期
 *      onStart/onCommand/onConnect/onDisconnect/onBackground/onStop + LocalRemoteObject 暴露 LocalDateTime，
 *      客户端 connect 后取时间）
 *   ② JsFaCallPa（JS FA 调 Java PA：FeatureAbility.callAbility({bundleName, abilityName, messageCode:1001, data, syncOption})
 *      → PlayAbility.PlayRemote.onRemoteRequest(PLUS,...) 读参、算 1024+2048、reply 回写结果）
 * 代际：两份皆旧代（Java Ability / JS FA + PA）；NEXT 翻写。旧代 ServiceAbility + RemoteObject(onRemoteRequest by code)
 *       在 NEXT 即 ServiceExtensionAbility + @kit.IPCKit 的 rpc.RemoteObject（onRemoteRequest 语义一致），做成未接线块。
 * NEXT 对应：
 *   - 服务端：import { rpc } from '@kit.IPCKit'；class X extends rpc.RemoteObject implements rpc.IRemoteBroker，
 *     覆写 onRemoteRequest(code, data: rpc.MessageParcel, reply: rpc.MessageParcel, option: rpc.MessageOption)。
 *   - 客户端：import { common } from '@kit.AbilityKit'；
 *     context.connectServiceExtensionAbility(want, { onConnect(remote){}, onDisconnect(){} })
 *     拿到 rpc.IRemoteObject 后 remote.sendRequest(code, data, reply, option): Promise<rpc.SendRequestResult>。
 * 适老化：把「朗读服务 / 离线书目下载 / 后台计时（如老人久坐提醒）」做成常驻后台能力，前端 Ability 随时 connect 取状态、下发指令，
 *        服务不受 UI 关闭影响（配合 Batch24 DistributedFileAccess 写结果、Batch26 AsyncTaskRunner 搬耗时逻辑）。
 * 权限：无额外权限（同一应用内 IPC）；默认不接线（ServiceExtensionAbility 需在 module.json5 的 extensionAbilities 注册 type:"service"）。
 */
import { rpc } from '@kit.IPCKit';
import { common } from '@kit.AbilityKit';

/** RPC 请求约定（code 区分方法，params 透传结构化参数）。 */
export interface RpcRequest {
  code: number;
  params?: Record<string, Object>;
}

/** RPC 返回约定（与 JsFaCallPa 的 { code, abilityResult } 同构）。 */
export interface RpcResult {
  code: number;
  abilityResult?: Object;
}

/** 示例方法码（与旧代 PLUS=1001 对应；RPC_TIME 对应 JavaServiceAbilityLifeCycle 取时间）。 */
export const RPC_PLUS: number = 1001;
export const RPC_TIME: number = 1002;

/**
 * 服务端远程对象（在 ServiceExtensionAbility.onConnect 中 new 出来并返回）。
 * 旧代 PlayRemote.onRemoteRequest 的「按 code 分发 + reply 回写」范式直译。
 */
export class SampleRemoteObject extends rpc.RemoteObject implements rpc.IRemoteBroker {
  constructor() {
    super('SampleRemoteObject');
  }

  onRemoteRequest(code: number, data: rpc.MessageParcel, reply: rpc.MessageParcel,
                  options: rpc.MessageOption): boolean {
    switch (code) {
      case RPC_PLUS: {
        const json: string = data.readString();
        const req: RpcRequest = JSON.parse(json) as RpcRequest;
        const a: number = (req.params?.['firstNum'] as number) ?? 0;
        const b: number = (req.params?.['secondNum'] as number) ?? 0;
        const out: RpcResult = { code: 0, abilityResult: a + b };
        reply.writeString(JSON.stringify(out));
        return true;
      }
      case RPC_TIME: {
        const out: RpcResult = { code: 0, abilityResult: new Date().toISOString() };
        reply.writeString(JSON.stringify(out));
        return true;
      }
      default: {
        reply.writeString('service not defined');
        return false;
      }
    }
  }

  asObject(): rpc.IRemoteObject {
    return this;
  }
}

/** 客户端：连接后台服务，取回 RemoteObject（未接线返回 null）。 */
export function connectService(context: common.Context, want: Record<string, Object>): rpc.IRemoteObject | null {
  // 接线：
  // const uiCtx = context as common.UIAbilityContext;
  // let remote: rpc.IRemoteObject | null = null;
  // uiCtx.connectServiceExtensionAbility(want as Want, {
  //   onConnect: (r: rpc.IRemoteObject) => { remote = r; /* 缓存供后续 invoke */ },
  //   onDisconnect: () => { remote = null; }
  // });
  // return remote;
  void context;
  void want;
  return null;
}

/** 客户端：向已连接的远程对象发请求（未接线：返回错误桩）。 */
export function invoke(remote: rpc.IRemoteObject, req: RpcRequest): Promise<RpcResult> {
  // 接线：
  // const data = rpc.MessageParcel.create();
  // const reply = rpc.MessageParcel.create();
  // const option = new rpc.MessageOption();
  // data.writeString(JSON.stringify(req));
  // return remote.sendRequest(req.code, data, reply, option)
  //   .then((_res: rpc.SendRequestResult) => JSON.parse(reply.readString()) as RpcResult);
  void remote;
  void req;
  return Promise.resolve({ code: -1 });
}

/*
 * 接线伪代码（前端 Ability 取后台「当前时间 / 朗读进度」）：
 *   const remote = connectService(getContext(this) as common.Context,
 *     { bundleName: 'com.classics.hmos', abilityName: 'com.classics.hmos.ReadAloudService' });
 *   if (remote) {
 *     invoke(remote, { code: RPC_TIME }).then(r => {
 *       // r.abilityResult 即后台服务当前时间/进度，前端展示 + announce 读屏
 *     });
 *   }
 * ServiceExtensionAbility 服务端骨架（独立文件，module.json5 的 extensionAbilities 注册 type:"service"）：
 *   import { ServiceExtensionAbility } from '@kit.AbilityKit';
 *   export class ReadAloudService extends ServiceExtensionAbility {
 *     private remote = new SampleRemoteObject();
 *     onConnect(want: Want): rpc.IRemoteObject { return this.remote; }   // 覆写，返回 RPC 对象
 *     onDisconnect(want: Want): void {}
 *   }
 * 旧代对照：JavaServiceAbilityLifeCycle 的 onConnect 返回 LocalRemoteObject；JsFaCallPa 客户端 FeatureAbility.callAbility({messageCode})；
 *           NEXT 把「连接」与「单次调用」拆开：connectServiceExtensionAbility 拿长连 RemoteObject，sendRequest 发 code 调 onRemoteRequest。
 */
