/**
 * 阅读偏好（跨页面共享 + 持久化）。
 *
 * - UI 响应式层：AppStorage（@StorageLink 双向绑定，会话内即时生效）。
 * - 持久化层：Preferences（@ohos.data.preferences，重启后保留）。
 *   来源：PDF《HarmonyOS应用开发API-ArkTs&NativeAPI》第 34245 行起「用户首选项」，
 *   及 waylau HarmonyOS Tutorial 的 ArkTSPreferences 示例。
 *
 * 对应待办「阅读页加阅读设置面板（字号/行距/配色/简繁，对齐 legado 模型）」。
 */

import dataPreferences from '@ohos.data.preferences';
import { common } from '@kit.AbilityKit';

export enum ReaderTheme {
  Light = 'light',
  Sepia = 'sepia',
  Dark = 'dark'
}

export const READER_KEYS = {
  fontScale: 'reader_fontScale',
  lineScale: 'reader_lineScale',
  theme: 'reader_theme',
  trad: 'reader_trad',
  elderMode: 'reader_elderMode',
  highContrast: 'reader_highContrast',
  followSystemFont: 'reader_followSystemFont'
};

const STORE_NAME: string = 'classics_reader_prefs';

export interface ThemeColors {
  bg: string;
  text: string;
  sub: string;
  accent: string;
}

let prefsStore: dataPreferences.Preferences | undefined = undefined;

/** 在 EntryAbility.onCreate 调用，传入 AbilityContext，完成 Preferences 实例加载与回灌。 */
export function initReaderPrefs(context: common.UIAbilityContext): void {
  // 先以默认值为 AppStorage 兜底，保证首帧 UI 有值（Preferences 异步回灌在其后覆盖）。
  AppStorage.setOrCreate(READER_KEYS.fontScale, 1.0);
  AppStorage.setOrCreate(READER_KEYS.lineScale, 1.0);
  AppStorage.setOrCreate(READER_KEYS.theme, ReaderTheme.Light);
  AppStorage.setOrCreate(READER_KEYS.trad, false);
  AppStorage.setOrCreate(READER_KEYS.elderMode, false);
  AppStorage.setOrCreate(READER_KEYS.highContrast, false);
  AppStorage.setOrCreate(READER_KEYS.followSystemFont, false);

  try {
    dataPreferences.getPreferences(context, STORE_NAME).then((store: dataPreferences.Preferences) => {
      prefsStore = store;
      loadKey(READER_KEYS.fontScale, 1.0);
      loadKey(READER_KEYS.lineScale, 1.0);
      loadKey(READER_KEYS.theme, ReaderTheme.Light);
      loadKey(READER_KEYS.trad, false);
      loadKey(READER_KEYS.elderMode, false);
      loadKey(READER_KEYS.highContrast, false);
      loadKey(READER_KEYS.followSystemFont, false);
    }).catch((err: Error) => {
      console.error(`initReaderPrefs getPreferences failed: ${err.message}`);
    });
  } catch (e) {
    console.error(`initReaderPrefs exception: ${(e as Error).message}`);
  }
}

/** 若磁盘有值则回灌 AppStorage，否则用默认值落盘。 */
function loadKey(key: string, def: number | string | boolean): void {
  if (!prefsStore) {
    return;
  }
  prefsStore.has(key).then((exists: boolean) => {
    if (exists) {
      prefsStore!.get(key, def).then((v: number | string | boolean) => {
        AppStorage.setOrCreate(key, v);
      }).catch((err: Error) => {
        console.error(`loadKey get ${key} failed: ${err.message}`);
      });
    } else {
      // 首次运行：默认值写入磁盘，保证后续有值可读。
      prefsStore!.put(key, def).then(() => prefsStore!.flush()).catch((err: Error) => {
        console.error(`loadKey seed ${key} failed: ${err.message}`);
      });
    }
  }).catch((err: Error) => {
    console.error(`loadKey has ${key} failed: ${err.message}`);
  });
}

/** 页面改值时调用：同步 AppStorage（响应式）并落盘 Preferences。 */
export function persistReaderPref(key: string, value: number | string | boolean): void {
  AppStorage.setOrCreate(key, value);
  if (!prefsStore) {
    return;
  }
  prefsStore.put(key, value).then(() => prefsStore!.flush()).catch((err: Error) => {
    console.error(`persistReaderPref ${key} failed: ${err.message}`);
  });
}

/**
 * 读书书签（对应 waylau Todo 示例的「列表 + 数据模型 + 持久化」模式）。
 * 一条书签 = 某书某章；持久化到同一 Preferences 库，重启后仍在。
 */
export interface BookmarkItem {
  bookId: string;
  index: number;
  label: string;
}

const BOOKMARK_KEY: string = 'reader_bookmarks';

/** 同步读取当前书签（prefsStore 未就绪时返回空）。 */
function readBookmarks(): BookmarkItem[] {
  if (!prefsStore) {
    return [];
  }
  try {
    const raw = prefsStore.get(BOOKMARK_KEY, '[]') as string;
    return JSON.parse(raw) as BookmarkItem[];
  } catch (e) {
    return [];
  }
}

/** 异步加载书签（页面 aboutToAppear 调用，回填 @State）。 */
export function loadBookmarksAsync(): Promise<BookmarkItem[]> {
  return new Promise((resolve) => {
    if (!prefsStore) {
      resolve([]);
      return;
    }
    prefsStore.get(BOOKMARK_KEY, '[]').then((raw: Object) => {
      try {
        resolve(JSON.parse(raw as string) as BookmarkItem[]);
      } catch (e) {
        resolve([]);
      }
    }).catch(() => resolve([]));
  });
}

function writeBookmarks(list: BookmarkItem[]): void {
  if (!prefsStore) {
    return;
  }
  prefsStore.put(BOOKMARK_KEY, JSON.stringify(list)).then(() => prefsStore!.flush()).catch((err: Error) => {
    console.error(`writeBookmarks failed: ${err.message}`);
  });
}

/** 加入书签（按 bookId+index 去重）。 */
export function addBookmark(item: BookmarkItem): void {
  const list = readBookmarks().filter(
    (b: BookmarkItem) => !(b.bookId === item.bookId && b.index === item.index)
  );
  list.push(item);
  writeBookmarks(list);
}

/** 删除某书某章的书签。 */
export function removeBookmark(bookId: string, index: number): void {
  const list = readBookmarks().filter(
    (b: BookmarkItem) => !(b.bookId === bookId && b.index === index)
  );
  writeBookmarks(list);
}

/** 简体→繁體轻量字典；未收录的字原样保留（优雅降级）。 */
const S2T: Record<string, string> = {
  '无': '無', '为': '為', '气': '氣', '后': '後', '与': '與', '时': '時',
  '万': '萬', '个': '個', '来': '來', '国': '國', '学': '學', '实': '實',
  '点': '點', '专': '專', '图': '圖', '书': '書', '体': '體', '会': '會',
  '产': '產', '发': '發', '义': '義', '张': '張', '强': '強', '当': '當',
  '应': '應', '开': '開', '关': '關', '门': '門', '问': '問', '间': '間',
  '从': '從', '这': '這', '那': '那', '里': '裡', '说': '說', '话': '話',
  '对': '對', '岁': '歲', '历': '歷', '总': '總', '网': '網', '见': '見',
  '视': '視', '觉': '覺', '观': '觀', '亲': '親', '让': '讓', '认': '認',
  '语': '語', '读': '讀', '课': '課', '请': '請', '谢': '謝', '许': '許',
  '论': '論', '设': '設', '务': '務', '机': '機', '权': '權', '构': '構',
  '处': '處', '备': '備', '制': '製', '获': '獲', '据': '據', '扫': '掃',
  '择': '擇', '击': '擊', '担': '擔', '扩': '擴', '极': '極', '欢': '歡',
  '饮': '飲', '饭': '飯', '馆': '館', '车': '車', '军': '軍', '农': '農',
  '动': '動', '势': '勢', '县': '縣', '参': '參', '灵': '靈', '云': '雲',
  '电': '電', '园': '園', '远': '遠', '边': '邊', '办': '辦', '过': '過',
  '进': '進', '达': '達', '还': '還', '运': '運', '经': '經', '东': '東',
  '长': '長', '风': '風', '鸟': '鳥', '鱼': '魚', '马': '馬', '龙': '龍',
  '虫': '蟲', '诗': '詩', '词': '詞', '贤': '賢', '圣': '聖', '师': '師',
  '帅': '帥', '归': '歸', '梦': '夢', '爱': '愛', '药': '藥', '医': '醫',
  '证': '證', '译': '譯', '议': '議', '识': '識', '质': '質', '财': '財',
  '责': '責', '费': '費', '贸': '貿', '资': '資', '购': '購', '贱': '賤',
  '贼': '賊', '赏': '賞', '赐': '賜', '赠': '贈', '输': '輸', '辞': '辭',
  '辩': '辯', '协': '協', '单': '單', '卖': '賣', '变': '變', '态': '態',
  '报': '報', '执': '執', '复': '復', '杂': '雜', '宝': '寶', '丽': '麗',
  '寿': '壽', '号': '號', '敌': '敵', '积': '積', '称': '稱', '礼': '禮',
  '神': '神', '绝': '絕', '纳': '納', '维': '維', '织': '織', '终': '終',
  '练': '練', '统': '統', '续': '續', '缘': '緣', '隐': '隱', '难': '難',
  '静': '靜', '题': '題', '频': '頻', '类': '類', '额': '額', '飞': '飛',
  '饥': '飢', '旧': '舊', '乐': '樂', '乡': '鄉', '阴': '陰', '阳': '陽',
  '阶': '階', '际': '際', '陆': '陸', '陈': '陳', '阵': '陣', '随': '隨',
  '顾': '顧', '顿': '頓', '颁': '頒', '颂': '頌', '领': '領', '颇': '頗',
  '颈': '頸', '须': '須', '饲': '飼'
};

/** 简体串转繁體（未收录字原样保留）。 */
export function s2t(text: string): string {
  if (!text) {
    return text;
  }
  let out = '';
  for (const ch of text) {
    out += S2T[ch] ?? ch;
  }
  return out;
}

/** 按主题取配色。 */
export function themeColors(theme: string): ThemeColors {
  switch (theme) {
    case ReaderTheme.Sepia:
      return { bg: '#f5ecd8', text: '#4a3f2f', sub: '#8a7a5c', accent: '#9a6a2a' };
    case ReaderTheme.Dark:
      return { bg: '#1a1a1a', text: '#d8d8d8', sub: '#888888', accent: '#5aa6a6' };
    default:
      return { bg: '#ffffff', text: '#222222', sub: '#666666', accent: '#aa3333' };
  }
}
