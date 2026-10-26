// 展示层小工具：状态配色、百分比、数值格式化。
export function statusClass(k) {
  return k === '正常' ? 'ok' : k === '异常' ? 'bad' : 'warn'
}

export function pct(x) {
  return (Number(x || 0) * 100).toFixed(1) + '%'
}

export function fx(x, d) {
  if (typeof x !== 'number') return x == null ? '' : String(x)
  return Number.isInteger(x) ? String(x) : Number(x).toFixed(d === undefined ? 3 : d)
}

export function num(x, d) {
  return Number(x || 0).toFixed(d === undefined ? 3 : d)
}

// 把 状态->数量 的 tally 转成可遍历数组，按 key 排序
export function tallyList(t) {
  const o = t || {}
  return Object.keys(o)
    .sort()
    .map((k) => ({ k, n: o[k] }))
}
