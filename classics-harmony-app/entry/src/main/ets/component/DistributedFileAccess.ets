/*
 * DistributedFileAccess.ets —— 分布式文件读写（构建块，翻 NEXT @kit.DistributedFS）
 * 来源：Batch24 DistributedFile（Java API8：AbilitySlice.getDistributedDir() 写入分布式目录，自动跨设备同步）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「拿远端设备文件路径 + 沙箱 fs 读写」概念做成未接线块（组网无障碍）。
 * NEXT 对应：import { distributedFile } from '@kit.DistributedFS'（getRemotePath(deviceId, path) 取远端路径）
 *          + import { fileIo as fs } from '@kit.CoreFileKit'（本地/远端同一套读写 API）。
 * 用途：读书笔记/书签在「手机写、平板读」无缝同步——比 DeviceSync(KV) 更适合整文件（如导出笔记 txt、离线书目包）。
 *       与 Batch23 DeviceSync（键值后台同步）、RemoteContinue（会话迁移）三件套构成完整组网无障碍。
 * 权限：需 ohos.permission.DISTRIBUTED_DATASYNC（已在 module.json5 声明）+ 设备可信组网；默认不接线。
 */
import { distributedFile } from '@kit.DistributedFS';
import { fileIo as fs } from '@kit.CoreFileKit';

/** 取某可信设备上的远端文件路径（未接线返回空串）。 */
export function getRemoteFilePath(deviceId: string, fileName: string): string {
  // 接线：return distributedFile.getRemotePath(deviceId, '/' + fileName);
  void deviceId;
  void fileName;
  return '';
}

/** 写远端设备文件（覆盖写），路径无效则静默返回。 */
export function writeRemoteFile(deviceId: string, fileName: string, content: string): void {
  const remotePath = getRemoteFilePath(deviceId, fileName);
  if (!remotePath) {
    return;
  }
  // 接线：
  // const file = fs.openSync(remotePath, fs.OpenMode.CREATE | fs.OpenMode.READ_WRITE | fs.OpenMode.TRUNC);
  // fs.writeSync(file.fd, content);
  // fs.closeSync(file);
  void content;
}

/** 读远端设备文件，不存在返回空串。 */
export function readRemoteFile(deviceId: string, fileName: string): string {
  const remotePath = getRemoteFilePath(deviceId, fileName);
  if (!remotePath || !fs.accessSync(remotePath)) {
    return '';
  }
  // 接线：return fs.readTextSync(remotePath);
  return '';
}

/*
 * 接线伪代码（手机写完笔记，平板直接读）：
 *   const dev = this.targetDeviceId;           // 来自 RemoteAbilityLauncher.listTrustedDevices
 *   writeRemoteFile(dev, 'notes_daodejing.txt', this.noteEditor);   // 手机写
 *   // 平板上：const s = readRemoteFile(dev, 'notes_daodejing.txt'); // 同路径即同步内容
 * 旧代对照：原 getDistributedDir() 返回应用分布式目录，写文件后由系统自动跨设备同步；
 *          NEXT 改为 distributedFile.getRemotePath(deviceId, path) 显式指定远端设备，再用同一套 fs 读写，更可控。
 */
