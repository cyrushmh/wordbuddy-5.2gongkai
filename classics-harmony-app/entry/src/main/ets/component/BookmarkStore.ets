/*
 * BookmarkStore.ets —— 书签 RDB 持久化（概念，翻 NEXT relationalStore）
 * 来源：Batch23 DataAbilityHelperAccessDatabase（Java API8：DataAbility + UserStore RDB）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「关系型数据库持久化」概念，补全书签存储。
 * NEXT 对应：import { relationalStore } from '@kit.ArkData'（RDB）；DataAbility 已在 NEXT 移除，改用 RDB / Preferences。
 * 用途：当前书签走 Preferences（轻量键值，见 ReaderPrefs.addBookmark）；RDB 支持更复杂书签元数据
 *       （批注/标签/跨书检索/全文），为书签持久化升级备选，非必需。默认不接线。
 * 字段对齐 ReaderPrefs 的 BookmarkItem（bookId / index / 标题/位置等）。
 */
export interface BookmarkRow {
  bookId: string;       // 所属书
  chapterIndex: number; // 章序号
  note: string;         // 批注/标记文本
  ts: number;           // 创建时间戳（用于排序）
}

/*
 * 接线伪代码（以 RDB 存书签为例，具体 API 以 NEXT 当前 SDK 为准）：
 * import { relationalStore } from '@kit.ArkData';
 * const STORE_CONFIG = { name: 'classics_bookmarks.db', securityLevel: relationalStore.SecurityLevel.S1 };
 * const SQL_CREATE = 'CREATE TABLE IF NOT EXISTS bookmark (bookId TEXT, chapterIndex INTEGER, note TEXT, ts INTEGER)';
 * let rdb: relationalStore.RdbStore;
 * relationalStore.getRdbStore(context, STORE_CONFIG, (err, store) => {
 *   rdb = store;
 *   rdb.executeSql(SQL_CREATE);
 * });
 * // 增：rdb.insert('bookmark', { bookId, chapterIndex, note, ts } as BookmarkRow);
 * // 查：rdb.query('bookmark', ...);
 * 权限：RDB 本地存储无需额外权限；如需跨设备同步则交 DeviceSync（分布式 KV），勿重复造轮子。
 */
