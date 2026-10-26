/**
 * 今日经典：每日一句取经。
 *
 * 数据源为内置精选，不依赖外部网络；按「一年中的第几天」定位，
 * 保证同一天各设备看到同一句。元服务卡片（WidgetCard）与首页共用本模块。
 */
export interface DailyVerse {
  verse: string;
  source: string;
}

export const VERSES: DailyVerse[] = [
  { verse: '道可道，非常道；名可名，非常名。', source: '道德经·第一章' },
  { verse: '上善若水。水善利万物而不争，处众人之所恶，故几于道。', source: '道德经·第八章' },
  { verse: '知人者智，自知者明。胜人者有力，自胜者强。', source: '道德经·第三十三章' },
  { verse: '北冥有鱼，其名为鲲。鲲之大，不知其几千里也。', source: '南华真经·逍遥游' },
  { verse: '至人无己，神人无功，圣人无名。', source: '南华真经·逍遥游' },
  { verse: '天地有大美而不言，四时有明法而不议，万物有成理而不说。', source: '南华真经·知北游' },
  { verse: '有物混成，先天地生。寂兮寥兮，独立而不改，周行而不殆。', source: '道德经·第二十五章' },
  { verse: '致虚极，守静笃。万物并作，吾以观复。', source: '道德经·第十六章' },
  { verse: '见素抱朴，少私寡欲。', source: '道德经·第十九章' },
  { verse: '古之善为士者，微妙玄通，深不可识。', source: '道德经·第十五章' },
  { verse: '知其白，守其黑，为天下式。', source: '道德经·第二十八章' },
  { verse: '大方无隅，大器晚成，大音希声，大象无形。', source: '道德经·第四十一章' }
];

/** 按「年内的第几天」取一句，同年同天各端一致。 */
export function dailyVerse(): DailyVerse {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((now.getTime() - start.getTime()) / 86400000);
  return VERSES[dayOfYear % VERSES.length];
}
