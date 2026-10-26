// 把 sysweeper 快照 JSON（report.build 产出）整理成前端好渲染的结构。
// 与 report_viewer.html / report_viewer.ts 的渲染逻辑一一对应，只是换成数据而非 HTML。
import { pct, num } from './format.js'

export function renderReport(rep) {
  if (!rep) return null
  const out = {
    meta: {},
    tally: {},
    score: null,
    kmod: null,
    jdk: null,
    sysmap: null,
    subsystems: null,
    diagnose: [],
    settings: null,
    history: [],
  }

  const h = rep.host || {}
  const d = h.detected || {}
  out.meta = {
    generated_at: rep.generated_at || '',
    version: rep.version || '',
    platform:
      (d.platform || h.system || '?') +
      (d.version ? ' ' + d.version : '') +
      (d.distro ? ' · ' + d.distro : ''),
    machine: h.machine || '',
    python: h.python || '',
    note: rep.note || '',
  }
  out.tally = rep.tally || {}

  if (rep.score) {
    const s = rep.score
    const sp = s.global_parts || {}
    out.score = {
      global_score: num(s.global_score),
      normalized_entropy: num(s.normalized_entropy),
      gini: num(s.gini),
      total_tasks: s.total_tasks || 0,
      parts: [
        ['覆盖广度 breadth', pct(sp.breadth)],
        ['分布均衡 entropy', pct(sp.entropy)],
        ['任务深度 depth', pct(sp.depth)],
        ['安全性 safety', pct(sp.safety)],
      ],
      gaps: (s.gaps || []).join('、'),
    }
  }

  if (rep.kmod) out.kmod = rep.kmod
  if (rep.jdk) out.jdk = rep.jdk
  if (rep.sysmap) out.sysmap = rep.sysmap
  if (rep.subsystems) {
    out.subsystems = {
      enabled: rep.subsystems.enabled || [],
      disabled: rep.subsystems.disabled || [],
    }
  }
  out.diagnose = rep.diagnose || []
  if (rep.settings) out.settings = rep.settings
  out.history = rep.history || []
  return out
}
