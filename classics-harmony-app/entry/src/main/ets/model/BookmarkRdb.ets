/**
 * 书签关系型存储构建块（relationalStore / RdbStore）。
 *
 * 来源：waylau ArkTSRdb 示例（relationalStore.getRdbStore + 建表 + CRUD），
 * 由回调式改写为 Promise 式，并把 AccountTable 泛型收敛为「书签」一张表。
 *
 * 用途：当前书签用 `ReaderPrefs.ts` 的 Preferences(JSON 数组) 保存，足够小量级。
 * 当书签量增长、需要「按书筛选 / 按时间倒序 / 多字段检索」时，可把书签层从
 * Preferences 迁到本 RDB，查询能力更强（样例 Rdb.query 支持 RdbPredicates）。
 *
 * 默认未接入主流程（保持 Preferences 方案为唯一事实来源，避免双写/迁移断裂）。
 * 接入步骤（待你点头）：
 *   1) module.json5 的 entry 模块无需额外权限（RDB 为本地库）；
 *   2) 在 EntryAbility.onCreate 调 initBookmarkRdb(this.context) 建库建表；
 *   3) 将 ReaderPrefs 的 addBookmark/removeBookmark/loadBookmarksAsync 改为调下方函数；
 *   4) 旧 Preferences 书签可一次性 importBookmarksFromPrefs 迁过来（或直接弃用）。
 */

import relationalStore from '@kit.ArkData';
import { common } from '@kit.AbilityKit';

const STORE_CONFIG: relationalStore.StoreConfig = {
  name: 'classics_reader.db',
  securityLevel: relationalStore.SecurityLevel.S1
};

const TABLE_NAME: string = 'bookmark';
const COLUMNS: Array<string> = ['id', 'bookId', 'chapterIndex', 'label', 'addedAt'];

const SQL_CREATE_TABLE: string =
  'CREATE TABLE IF NOT EXISTS bookmark (' +
  'id INTEGER PRIMARY KEY AUTOINCREMENT, ' +
  'bookId TEXT NOT NULL, ' +
  'chapterIndex INTEGER NOT NULL, ' +
  'label TEXT, ' +
  'addedAt INTEGER NOT NULL)';

let rdbStore: relationalStore.RdbStore | null = null;

/** 建库 + 建表（EntryAbility.onCreate 调一次）。 */
export function initBookmarkRdb(context: common.UIAbilityContext): Promise<void> {
  return new Promise((resolve) => {
    relationalStore.getRdbStore(context, STORE_CONFIG).then((store: relationalStore.RdbStore) => {
      store.executeSql(SQL_CREATE_TABLE);
      rdbStore = store;
      resolve();
    }).catch((err: Error) => {
      console.error(`initBookmarkRdb failed: ${err.message}`);
      resolve();
    });
  });
}

export interface BookmarkRow {
  bookId: string;
  chapterIndex: number;
  label: string;
  addedAt: number;
}

/** 加书签（按 bookId+chapterIndex 去重：存在则更新 label，不重复插入）。 */
export function addBookmarkRdb(row: BookmarkRow): Promise<number> {
  return new Promise((resolve) => {
    if (!rdbStore) {
      resolve(-1);
      return;
    }
    const predicates = new relationalStore.RdbPredicates(TABLE_NAME);
    predicates.equalTo('bookId', row.bookId).and().equalTo('chapterIndex', row.chapterIndex);
    rdbStore.query(predicates, COLUMNS).then((rs: relationalStore.ResultSet) => {
      const exists = rs.rowCount > 0;
      rs.close();
      if (exists) {
        const vb: relationalStore.ValuesBucket = { label: row.label, addedAt: row.addedAt };
        rdbStore!.update(vb, predicates).then((ret: number) => resolve(ret)).catch(() => resolve(-1));
        return;
      }
      const valueBucket: relationalStore.ValuesBucket = {
        bookId: row.bookId,
        chapterIndex: row.chapterIndex,
        label: row.label,
        addedAt: row.addedAt
      };
      rdbStore!.insert(TABLE_NAME, valueBucket).then((ret: number) => resolve(ret)).catch(() => resolve(-1));
    }).catch(() => resolve(-1));
  });
}

/** 删某书某章书签。 */
export function removeBookmarkRdb(bookId: string, chapterIndex: number): Promise<number> {
  return new Promise((resolve) => {
    if (!rdbStore) {
      resolve(-1);
      return;
    }
    const predicates = new relationalStore.RdbPredicates(TABLE_NAME);
    predicates.equalTo('bookId', bookId).and().equalTo('chapterIndex', chapterIndex);
    rdbStore.delete(predicates).then((ret: number) => resolve(ret)).catch(() => resolve(-1));
  });
}

/** 读全部书签，按 addedAt 倒序（最新在前）。 */
export function loadBookmarksRdb(): Promise<BookmarkRow[]> {
  return new Promise((resolve) => {
    if (!rdbStore) {
      resolve([]);
      return;
    }
    const predicates = new relationalStore.RdbPredicates(TABLE_NAME);
    predicates.orderByDesc('addedAt');
    rdbStore.query(predicates, COLUMNS).then((rs: relationalStore.ResultSet) => {
      const out: BookmarkRow[] = [];
      if (rs.rowCount > 0) {
        rs.goToFirstRow();
        for (let i = 0; i < rs.rowCount; i++) {
          out.push({
            bookId: rs.getString(rs.getColumnIndex('bookId')),
            chapterIndex: rs.getLong(rs.getColumnIndex('chapterIndex')),
            label: rs.getString(rs.getColumnIndex('label')),
            addedAt: rs.getLong(rs.getColumnIndex('addedAt'))
          });
          rs.goToNextRow();
        }
      }
      rs.close();
      resolve(out);
    }).catch(() => resolve([]));
  });
}

/** 按书筛选书签（首页「我的书签」可按当前书过滤时用）。 */
export function loadBookmarksByBookRdb(bookId: string): Promise<BookmarkRow[]> {
  return new Promise((resolve) => {
    if (!rdbStore) {
      resolve([]);
      return;
    }
    const predicates = new relationalStore.RdbPredicates(TABLE_NAME);
    predicates.equalTo('bookId', bookId).orderByDesc('addedAt');
    rdbStore.query(predicates, COLUMNS).then((rs: relationalStore.ResultSet) => {
      const out: BookmarkRow[] = [];
      if (rs.rowCount > 0) {
        rs.goToFirstRow();
        for (let i = 0; i < rs.rowCount; i++) {
          out.push({
            bookId: rs.getString(rs.getColumnIndex('bookId')),
            chapterIndex: rs.getLong(rs.getColumnIndex('chapterIndex')),
            label: rs.getString(rs.getColumnIndex('label')),
            addedAt: rs.getLong(rs.getColumnIndex('addedAt'))
          });
          rs.goToNextRow();
        }
      }
      rs.close();
      resolve(out);
    }).catch(() => resolve([]));
  });
}
