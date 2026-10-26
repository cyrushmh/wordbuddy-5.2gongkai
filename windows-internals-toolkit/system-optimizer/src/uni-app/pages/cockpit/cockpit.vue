<template>
  <view>
    <top-nav active="cockpit" />

    <view class="wrap">
      <view class="row">
        <button class="btn btn-primary" :disabled="loading" @click="load">
          {{ loading ? '跑总览中…' : '跑总览' }}
        </button>
        <text class="hint">{{ backend }}</text>
      </view>

      <view v-if="err" class="card"><text class="badge bad">{{ err }}</text></view>

      <!-- 报告信息 -->
      <view class="card" v-if="meta.version">
        <view class="card-h">报告信息</view>
        <view class="kv">
          <text><text class="k">宿主：</text>{{ meta.platform }}</text>
          <text><text class="k">架构：</text>{{ meta.machine }}</text>
          <text><text class="k">Python：</text>{{ meta.python }}</text>
          <text><text class="k">sysweeper：</text>v{{ meta.version }}</text>
        </view>
        <text class="muted" v-if="meta.generated_at">生成：{{ meta.generated_at }}</text>
      </view>

      <!-- 诊断状态计数 -->
      <view class="cards" v-if="tallyArr.length">
        <view v-for="t in tallyArr" :key="t.k" :class="['stat', statusClass(t.k)]">
          <view class="stat-n">{{ t.n }}</view>
          <view class="stat-l">{{ t.k }}</view>
        </view>
      </view>

      <!-- 量化评分 -->
      <view class="card" v-if="score">
        <view class="card-h">量化评分（加权求和 + Shannon 熵）</view>
        <view class="cards">
          <view class="stat ok"><view class="stat-n">{{ score.global_score }}</view><view class="stat-l">覆盖度总分</view></view>
          <view class="stat"><view class="stat-n">{{ score.normalized_entropy }}</view><view class="stat-l">归一化熵 H/log₂n</view></view>
          <view class="stat"><view class="stat-n">{{ score.gini }}</view><view class="stat-l">Gini 集中度</view></view>
          <view class="stat"><view class="stat-n">{{ score.total_tasks }}</view><view class="stat-l">任务总数</view></view>
        </view>
        <view class="kv" v-if="score.gaps">
          <text><text class="k">覆盖缺口：</text>{{ score.gaps }}</text>
        </view>
        <text class="muted" v-else>无覆盖缺口：每个分类都有任务</text>
      </view>

      <!-- 系统统筹总览 -->
      <view class="card" v-if="sysmapText">
        <view class="card-h">系统统筹总览</view>
        <text class="pre">{{ sysmapText }}{{ sysmapTruncated ? '…（已截断）' : '' }}</text>
      </view>

      <view class="hint" v-if="!meta.version && !loading && !err">点「跑总览」拉取本机只读诊断（需先在同机跑起 sysweeper web 控制台）。</view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { callApi, healthz } from '@/common/api.js'
import { statusClass, tallyList } from '@/common/format.js'

const backend = ref('后端: 检测中…')
const loading = ref(false)
const err = ref('')
const meta = ref({})
const tally = ref({})
const tallyArr = ref([])
const score = ref(null)
const sysmapText = ref('')
const sysmapTruncated = ref(false)

async function load() {
  loading.value = true
  err.value = ''
  try {
    const up = await healthz()
    backend.value = up ? '后端就绪 · 只读诊断' : '后端未响应（控制台未起？）'

    const [ping, sc, sm, dg] = await Promise.all([
      callApi('ping', { host: true }),
      callApi('score.overview', {}),
      callApi('sysmap', { max_chars: 40000 }),
      callApi('diagnose', { max_chars: 3000 }),
    ])

    const h = ping.host || {}
    const d = h.detected || {}
    meta.value = {
      platform:
        (d.platform || h.system || '?') +
        (d.version ? ' ' + d.version : '') +
        (d.distro ? ' · ' + d.distro : ''),
      machine: h.machine || '',
      python: h.python || '',
      version: ping.version || '',
      generated_at: '',
    }
    tally.value = (dg && dg.tally) || {}
    tallyArr.value = tallyList(tally.value)
    score.value = {
      global_score: Number(sc.global_score || 0).toFixed(3),
      normalized_entropy: Number(sc.normalized_entropy || 0).toFixed(3),
      gini: Number(sc.gini || 0).toFixed(3),
      total_tasks: sc.total_tasks || 0,
      gaps: (sc.gaps || []).join('、'),
    }
    sysmapText.value = (sm && sm.text) || '（空）'
    sysmapTruncated.value = !!(sm && sm.truncated)
  } catch (e) {
    err.value = '取不到总览：' + (e && e.message ? e.message : e)
  } finally {
    loading.value = false
  }
}

onShow(() => {
  load()
})
</script>
