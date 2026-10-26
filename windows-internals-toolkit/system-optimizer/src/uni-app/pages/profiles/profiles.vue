<template>
  <view>
    <top-nav active="profiles" />

    <view class="wrap">
      <view class="row">
        <button class="btn btn-primary" :disabled="loading" @click="load">刷新</button>
        <text class="hint">任务档位 + 量化评分 + 内核 / OpenJDK 只读体检；全部只读</text>
      </view>

      <view v-if="err" class="card"><text class="badge bad">{{ err }}</text></view>

      <!-- 量化评分 -->
      <view class="card" v-if="score">
        <view class="card-h">量化评分（加权求和 + Shannon 熵）</view>
        <view class="cards">
          <view class="stat ok"><view class="stat-n">{{ score.global_score }}</view><view class="stat-l">覆盖度总分</view></view>
          <view class="stat"><view class="stat-n">{{ score.normalized_entropy }}</view><view class="stat-l">归一化熵</view></view>
          <view class="stat"><view class="stat-n">{{ score.gini }}</view><view class="stat-l">Gini</view></view>
          <view class="stat"><view class="stat-n">{{ score.total_tasks }}</view><view class="stat-l">任务总数</view></view>
        </view>
        <view class="kv" v-if="score.gaps"><text><text class="k">覆盖缺口：</text>{{ score.gaps }}</text></view>
        <text class="muted" v-else>无覆盖缺口</text>
      </view>

      <!-- 任务档位 -->
      <view class="card" v-if="profiles.length">
        <view class="card-h">任务档位</view>
        <view class="tbl">
          <view class="tbl"><text class="k">档位</text><text class="k">中文名</text><text class="k">最大风险</text><text class="k">含 opt-in</text><text class="k">命中</text></view>
          <view v-for="p in profiles" :key="p.name" class="tbl">
            <text class="k">{{ p.name }}</text>
            <text>{{ p.title }}</text>
            <text>{{ p.max_risk }}</text>
            <text>{{ p.include_opt_in ? '是' : '否' }}</text>
            <text>{{ p.count }}</text>
          </view>
          <view v-for="s in scenarios" :key="s.name" class="tbl">
            <text class="k">{{ s.name }}</text>
            <text>{{ s.title }}（场景档）</text>
            <text>—</text>
            <text>—</text>
            <text>{{ s.count }}</text>
          </view>
        </view>
      </view>

      <!-- 内核只读体检 -->
      <view class="card">
        <view class="card-h">内核 module / firmware / eBPF 只读体检</view>
        <view class="row">
          <button class="btn" :disabled="kmodRunning" @click="runKmod">{{ kmodRunning ? '跑中…' : '跑内核只读体检' }}</button>
          <text v-if="kmod.status" :class="['badge', statusClass(kmod.status)]">{{ kmod.status }} {{ kmod.summary }}</text>
        </view>
        <text class="pre" v-if="kmod.text">{{ kmod.text }}{{ kmod.truncated ? '…（已截断）' : '' }}</text>
      </view>

      <!-- OpenJDK 只读体检 -->
      <view class="card">
        <view class="card-h">OpenJDK / JVM 只读体检</view>
        <view class="row">
          <button class="btn" :disabled="jdkRunning" @click="runJdk">{{ jdkRunning ? '跑中…' : '跑 JDK/JVM 体检' }}</button>
          <text v-if="jdk.status" :class="['badge', statusClass(jdk.status)]">{{ jdk.status }} {{ jdk.summary }}</text>
        </view>
        <text class="pre" v-if="jdk.text">{{ jdk.text }}{{ jdk.truncated ? '…（已截断）' : '' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onShow } from '@dcloudio/uni-app'
import { callApi } from '@/common/api.js'
import { statusClass } from '@/common/format.js'

const loading = ref(false)
const err = ref('')
const score = ref(null)
const profiles = ref([])
const scenarios = ref([])
const kmod = ref({})
const jdk = ref({})
const kmodRunning = ref(false)
const jdkRunning = ref(false)

async function load() {
  loading.value = true
  err.value = ''
  try {
    const [pl, sc] = await Promise.all([
      callApi('profiles.list', {}),
      callApi('score.overview', {}),
    ])
    profiles.value = (pl && pl.profiles) || []
    scenarios.value = (pl && pl.scenarios) || []
    score.value = {
      global_score: Number(sc.global_score || 0).toFixed(3),
      normalized_entropy: Number(sc.normalized_entropy || 0).toFixed(3),
      gini: Number(sc.gini || 0).toFixed(3),
      total_tasks: sc.total_tasks || 0,
      gaps: (sc.gaps || []).join('、'),
    }
  } catch (e) {
    err.value = '载入失败: ' + (e && e.message ? e.message : e)
  } finally {
    loading.value = false
  }
}

async function runKmod() {
  kmodRunning.value = true
  try {
    const d = await callApi('kmod.report', { max_chars: 40000 })
    kmod.value = { status: d.status, summary: d.summary, text: d.text, truncated: d.truncated }
  } catch (e) {
    kmod.value = { status: '异常', summary: '', text: '失败: ' + (e && e.message ? e.message : e), truncated: false }
  } finally {
    kmodRunning.value = false
  }
}

async function runJdk() {
  jdkRunning.value = true
  try {
    const d = await callApi('jdk.report', { max_chars: 40000 })
    jdk.value = { status: d.status, summary: d.summary, text: d.text, truncated: d.truncated }
  } catch (e) {
    jdk.value = { status: '异常', summary: '', text: '失败: ' + (e && e.message ? e.message : e), truncated: false }
  } finally {
    jdkRunning.value = false
  }
}

onShow(() => {
  load()
})
</script>
