<template>
  <view>
    <top-nav active="report" />

    <view class="wrap">
      <view class="row">
        <button class="btn btn-primary" @click="render">渲染报告</button>
        <button class="btn" @click="loadDemo">载入示例</button>
        <text class="hint">粘贴 sysweeper 快照 JSON（report.build 产出），数据不出机器也能看</text>
      </view>

      <textarea class="ta" v-model="raw" placeholder="把 sysweeper 快照 JSON 粘到这里…" />

      <view v-if="parseErr" class="card"><text class="badge bad">{{ parseErr }}</text></view>

      <block v-if="R">
        <!-- 报告信息 -->
        <view class="card">
          <view class="card-h">报告信息</view>
          <view class="kv">
            <text><text class="k">生成：</text>{{ R.meta.generated_at }}</text>
            <text><text class="k">宿主：</text>{{ R.meta.platform }}</text>
            <text><text class="k">架构：</text>{{ R.meta.machine }}</text>
            <text><text class="k">Python：</text>{{ R.meta.python }}</text>
            <text><text class="k">sysweeper：</text>v{{ R.meta.version }}</text>
          </view>
          <text class="muted" v-if="R.meta.note">{{ R.meta.note }}</text>
        </view>

        <!-- 诊断状态计数 -->
        <view class="cards" v-if="tallyArr.length">
          <view v-for="t in tallyArr" :key="t.k" :class="['stat', statusClass(t.k)]">
            <view class="stat-n">{{ t.n }}</view>
            <view class="stat-l">{{ t.k }}</view>
          </view>
        </view>

        <!-- 量化评分 -->
        <view class="card" v-if="R.score">
          <view class="card-h">量化评分（加权求和 + Shannon 熵）</view>
          <view class="cards">
            <view class="stat ok"><view class="stat-n">{{ R.score.global_score }}</view><view class="stat-l">覆盖度总分</view></view>
            <view class="stat"><view class="stat-n">{{ R.score.normalized_entropy }}</view><view class="stat-l">归一化熵</view></view>
            <view class="stat"><view class="stat-n">{{ R.score.gini }}</view><view class="stat-l">Gini</view></view>
            <view class="stat"><view class="stat-n">{{ R.score.total_tasks }}</view><view class="stat-l">任务总数</view></view>
          </view>
          <view class="kv" v-if="R.score.gaps"><text><text class="k">覆盖缺口：</text>{{ R.score.gaps }}</text></view>
          <text class="muted" v-else>无覆盖缺口</text>
        </view>

        <!-- 内核只读体检 -->
        <view class="card" v-if="R.kmod">
          <view class="card-h">内核 module / firmware / eBPF 只读体检
            <text :class="['badge', statusClass(R.kmod.status)]">{{ R.kmod.status }}</text>
          </view>
          <text class="pre">{{ R.kmod.text }}{{ R.kmod.truncated ? '…（已截断）' : '' }}</text>
        </view>

        <!-- OpenJDK 只读体检 -->
        <view class="card" v-if="R.jdk">
          <view class="card-h">OpenJDK / JVM 只读体检
            <text :class="['badge', statusClass(R.jdk.status)]">{{ R.jdk.status }}</text>
          </view>
          <text class="pre">{{ R.jdk.text }}{{ R.jdk.truncated ? '…（已截断）' : '' }}</text>
        </view>

        <!-- 系统统筹总览 -->
        <view class="card" v-if="R.sysmap">
          <view class="card-h">系统统筹总览</view>
          <text class="pre">{{ R.sysmap.text }}{{ R.sysmap.truncated ? '…（已截断）' : '' }}</text>
        </view>

        <!-- 子系统开关态 -->
        <view class="card" v-if="R.subsystems">
          <view class="card-h">子系统开关态（开 {{ R.subsystems.enabled.length }} / 关 {{ R.subsystems.disabled.length }}）</view>
          <view>
            <text v-for="k in R.subsystems.enabled" :key="'e'+k" class="chip on">{{ k }}</text>
            <text v-for="k in R.subsystems.disabled" :key="'d'+k" class="chip off">{{ k }}</text>
          </view>
        </view>

        <!-- 逐项诊断 -->
        <view class="card" v-if="R.diagnose.length">
          <view class="card-h">逐项诊断（{{ R.diagnose.length }} 项）</view>
          <view v-for="(it, i) in R.diagnose" :key="i" style="margin-bottom:10px">
            <view class="row" style="margin-bottom:4px">
              <text class="badge" :class="statusClass(it.status)">{{ it.status }}</text>
              <text style="font-weight:700">{{ it.label || it.key }}</text>
            </view>
            <text class="pre">{{ it.text }}</text>
          </view>
        </view>

        <!-- 参数与阈值 -->
        <view class="card" v-if="R.settings && R.settings.items && R.settings.items.length">
          <view class="card-h">参数与阈值</view>
          <view class="tbl">
            <view class="tbl"><text class="k">key</text><text class="k">值</text><text class="k">默认</text><text class="k">标签</text></view>
            <view v-for="s in R.settings.items" :key="s.key" class="tbl">
              <text class="k">{{ s.key }}{{ isChanged(R.settings, s.key) ? ' ●' : '' }}</text>
              <text>{{ s.value }}</text>
              <text>{{ s.default }}</text>
              <text>{{ s.label }}</text>
            </view>
          </view>
        </view>

        <!-- 变更留痕 -->
        <view class="card" v-if="R.history.length">
          <view class="card-h">变更留痕（{{ R.history.length }} 条）</view>
          <view v-for="(r, i) in R.history" :key="i" style="margin-bottom:8px">
            <text class="muted">{{ r.ts }} · {{ r.source }}{{ r.origin ? ' · ' + r.origin : '' }}</text>
            <view class="k" v-for="(v, k) in (r.changes || {})" :key="k">{{ k }}: {{ v.from }} → {{ v.to }}</view>
          </view>
        </view>
      </block>

      <view class="hint" v-if="!R && !parseErr">尚未载入报告。粘贴 JSON 后点「渲染报告」，或点「载入示例」看效果。</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { renderReport } from '@/common/report.js'
import { statusClass, tallyList } from '@/common/format.js'

const raw = ref('')
const R = ref(null)
const parseErr = ref('')
const tallyArr = ref([])

function isChanged(settings, key) {
  return (settings.changed || []).indexOf(key) >= 0
}

function render() {
  parseErr.value = ''
  R.value = null
  tallyArr.value = []
  if (!raw.value.trim()) {
    parseErr.value = '先粘贴报告 JSON'
    return
  }
  try {
    const rep = JSON.parse(raw.value)
    const out = renderReport(rep)
    if (!out) throw new Error('解析为空')
    R.value = out
    tallyArr.value = tallyList(out.tally)
  } catch (e) {
    parseErr.value = 'JSON 解析失败: ' + (e && e.message ? e.message : e)
  }
}

function loadDemo() {
  raw.value = JSON.stringify(demo(), null, 2)
  render()
}

function demo() {
  return {
    schema: 'sysweeper-report/1',
    version: '0.6.27',
    generated_at: new Date().toISOString().slice(0, 19),
    note: '示例数据，仅演示渲染效果',
    host: { python: '3.11.0', system: 'Linux', machine: 'x86_64',
      detected: { platform: 'linux', version: '24.04', distro: 'Ubuntu 24.04.3 LTS' } },
    tally: { 正常: 41, 提示: 6, 不适用: 4 },
    score: { global_score: 0.782, normalized_entropy: 0.93, gini: 0.21, total_tasks: 312,
      global_parts: { breadth: 0.88, entropy: 0.93, depth: 0.71, safety: 1.0 },
      gaps: [], distribution: { 内核: 40, 存储: 35, 网络: 52 } },
    kmod: { status: '正常', summary: '10/10 项可读', text: '==== 内核 module / firmware / eBPF 只读体检 ====\n（示例）全部只读：不写 sysfs', truncated: false },
    jdk: { status: '正常', summary: '10/10 项只读接口可读', text: '==== OpenJDK 只读体检总报告 ====\n（示例）java = /usr/lib/jvm/java-20-openjdk/bin/java', truncated: false },
    sysmap: { ok: true, status: '提示', text: '==== 系统统筹总览 ====\n（示例）整体健康：41 项正常 / 6 项提示', truncated: false },
    subsystems: { enabled: ['network', 'kernel', 'kmod', 'firmware', 'storage'], disabled: ['tor', 'dosbox'] },
    diagnose: [{ key: 'kernel', label: '内核调优(sysctl)', status: '正常', text: '==== 内核调优(sysctl) 诊断 ====\n（示例）vm.swappiness=60' }],
    settings: { changed: ['cmd.timeout'],
      items: [{ key: 'cmd.timeout', label: '命令执行超时', value: 300, default: 120, unit: '秒' }] },
    history: [{ ts: '2026-10-10T10:00:00', source: 'web', origin: 'web', note: 'Web 控制台保存',
      changes: { 'cmd.timeout': { from: 120, to: 300 } } }],
  }
}

// 支持从 #r=<base64url(JSON)> 带入报告（H5 分享链接场景）
function tryFromHash() {
  try {
    const h = (typeof location !== 'undefined' && location.hash) || ''
    const m = h.match(/^#r=(.+)$/)
    if (!m) return
    const b = m[1].replace(/-/g, '+').replace(/_/g, '/')
    const s = decodeURIComponent(escape(atob(b)))
    raw.value = s
    render()
  } catch (e) {
    parseErr.value = 'URL 里的报告解析失败'
  }
}

onLoad((query) => {
  if (query && query.r) {
    try {
      const b = query.r.replace(/-/g, '+').replace(/_/g, '/')
      raw.value = decodeURIComponent(escape(atob(b)))
      render()
    } catch (e) {
      parseErr.value = '链接报告解析失败'
    }
    return
  }
  tryFromHash()
})
</script>
