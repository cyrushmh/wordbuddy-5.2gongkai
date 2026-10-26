/*
 * LocalFileHelper.ets —— 应用沙箱文本文件读写（构建块，翻 NEXT @kit.CoreFileKit）
 * 来源：Batch24(中断补) DataAbilityHelperAccessFile（Java API8：DataAbility.openFile + FileUtils 读 fd 内容）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「本地文本文件读写」概念做成未接线块。
 * NEXT 对应：import { fileIo as fs } from '@kit.CoreFileKit'（DataAbility 在 NEXT 已移除，原 openFile 暴露文件
 *        的范式统一改为应用沙箱内直接 fs 读写；跨设备同步另走 DistributedFileAccess / DeviceSync）。
 * 用途：读写应用私有文本——导出读书笔记、备份书签/批注、缓存离线书目索引。比 Preferences 适合「整段文本」。
 * 默认不接线：沙箱文件读写无需额外权限；导出到公共目录（如分享）才需对应权限，以 NEXT 当前 SDK 为准。
 */
import { fileIo as fs } from '@kit.CoreFileKit';
import { common } from '@kit.AbilityKit';

/** 写出文本文件到应用 filesDir（覆盖写）。 */
export function writeTextFile(context: common.Context, fileName: string, content: string): void {
  // 接线：
  // const filePath = context.filesDir + '/' + fileName;
  // const file = fs.openSync(filePath, fs.OpenMode.CREATE | fs.OpenMode.READ_WRITE | fs.OpenMode.TRUNC);
  // fs.writeSync(file.fd, content);
  // fs.closeSync(file);
  void context;
  void fileName;
  void content;
}

/** 读取应用 filesDir 下文本文件；不存在返回空串。 */
export function readTextFile(context: common.Context, fileName: string): string {
  // 接线：
  // const filePath = context.filesDir + '/' + fileName;
  // if (!fs.accessSync(filePath)) { return ''; }
  // return fs.readTextSync(filePath);
  void context;
  void fileName;
  return '';
}

/*
 * 接线伪代码（导出读书笔记为例）：
 *   const ctx = getContext(this) as common.Context;
 *   writeTextFile(ctx, 'notes_daodejing.txt', this.noteEditor);
 *   promptAction.showToast({ message: '已导出到应用私有目录' });
 * 旧代对照：原样例用 DataAbility.openFile(uri,'r') 拿 FileDescriptor 再 FileInputStream 读；NEXT 无 DataAbility，
 *          故改为沙箱 fs，调用方无需关心 URI/权限，逻辑更短。
 */
