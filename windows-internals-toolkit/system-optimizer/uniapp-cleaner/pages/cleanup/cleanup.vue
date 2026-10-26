<template>
  <view class="page">
    <view class="card">
      <view class="card-title">设备信息</view>
      <view class="row"><text class="k">运行端</text><text class="v">{{ sys.platform }}</text></view>
      <view class="row"><text class="k">系统版本</text><text class="v">{{ sys.osVersion || '—' }}</text></view>
      <view class="row"><text class="k">storage 配额</text><text class="v">{{ quotaText }}</text></view>
    </view>

    <view class="card">
      <view class="card-title row-between">
        <text>端上存储占用</text>
        <text class="used">{{ storageInfo.currentSize }} KB / {{ storageInfo.limitSize }} KB</text>
      </view>
      <view v-if="keys.length === 0" class="empty">暂无存储数据（端上未写入或受限）</view>
      <view v-for="item in keys" :key="item.key" class="item" @tap="toggle(item.key)">
        <text class="check">{{ selectedSet.has(item.key) ? '☑' : '☐' }}</text>
        <text class="key">{{ item.key }}</text>
        <text class="size">{{ item.size }} KB</text>
      </view>
    </view>

    <view class="actions">
      <button class="btn danger" @tap="clearAll">清空全部 storage</button>
      <button class="btn" :disabled="selected.length === 0" @tap="clearSelected">清理选中（{{ selected.length }}）</button>
      <button class="btn warn" @tap="clearCache">清理端上缓存（H5/App）</button>
      <button class="btn ghost" @tap="refresh">重新统计</button>
    </view>

    <view v-if="report" class="card report">
      <view class="card-title">本次清理报告</view>
      <text class="rp">{{ report }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const sys = reactive({ platform: '—', osVersion: '' })
const storageInfo = reactive({ currentSize: 0, limitSize: 0, keys: [] })
const keys = ref([])
const selected = ref([])
const report = ref('')

const selectedSet = computed(() => new Set(selected.value))

const quotaText = computed(() => {
  const kb = storageInfo.limitSize || 0
  return kb >= 1024 ? (kb / 1024).toFixed(1) + ' MB' : kb + ' KB'
})

// 估算单个 key 的字节占用（/1024 得 KB，向上取整）
function estimate(key) {
  try {
    const v = uni.getStorageSync(key)
    if (v == null) return 0
    const s = typeof v === 'string' ? v.length : JSON.stringify(v).length
    return Math.max(1, Math.ceil(s / 1024))
  } catch (e) {
    return 0
  }
}

function refresh() {
  try {
    const info = uni.getStorageInfoSync()
    storageInfo.currentSize = info.currentSize || 0
    storageInfo.limitSize = info.limitSize || 0
    const ks = info.keys || []
    keys.value = ks.map((k) => ({ key: k, size: estimate(k) }))
    storageInfo.keys = ks
    report.value = ''
  } catch (e) {
    uni.showToast({ title: '无法读取存储信息', icon: 'none' })
  }
}

function toggle(key) {
  const i = selected.value.indexOf(key)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(key)
}

// 清空全部：先展示占用，再经 showModal 二次确认，最后 clearStorageSync
function clearAll() {
  if (storageInfo.currentSize === 0 && keys.value.length === 0) {
    uni.showToast({ title: '没有可清理的存储', icon: 'none' })
    return
  }
  uni.showModal({
    title: '确认清空全部 storage？',
    content: '将删除端上所有本地存储（含登录态与本地草稿），不可恢复。建议先导出重要数据。',
    confirmText: '确认清空',
    confirmColor: '#e54d42',
    success: (res) => {
      if (!res.confirm) return
      const before = storageInfo.currentSize
      uni.clearStorageSync()
      report.value = `清理前占用 ${before} KB，清理后 0 KB，释放约 ${before} KB。`
      uni.showToast({ title: '已清空', icon: 'success' })
      selected.value = []
      refresh()
    },
  })
}

// 清理选中：仅移除指定 key（removeStorageSync），同样需确认
function clearSelected() {
  if (selected.value.length === 0) return
  const list = selected.value.slice()
  uni.showModal({
    title: `确认清理选中的 ${list.length} 项？`,
    content: list.join('、'),
    confirmText: '确认清理',
    success: (res) => {
      if (!res.confirm) return
      const before = storageInfo.currentSize
      list.forEach((k) => {
        try { uni.removeStorageSync(k) } catch (e) { /* 忽略已不存在的 key */ }
      })
      refresh()
      const freed = before - storageInfo.currentSize
      report.value = `清理前 ${before} KB，清理后 ${storageInfo.currentSize} KB，释放约 ${freed} KB。`
      uni.showToast({ title: '已清理选中项', icon: 'success' })
      selected.value = []
    },
  })
}

onMounted(() => {
  try {
    const s = uni.getSystemInfoSync()
    sys.platform = s.platform || '—'
    sys.osVersion = s.osVersion || s.system || ''
  } catch (e) { /* ignore */ }
  refresh()
})

// 识别运行期（与 data/uniapp_api.json 的 system 组思路一致：先识别端再分支）
// 返回 'app'（5+ 引擎）/ 'h5'（浏览器，含 Cache API）/ 'mp'（小程序）/ 'unknown'
function detectRuntime() {
  try {
    if (typeof plus !== 'undefined' && plus.os) return 'app'
  } catch (e) { /* ignore */ }
  // H5：浏览器环境，且存在 Cache Storage（仅 https/localhost 安全上下文可用）
  if (typeof window !== 'undefined' && typeof window.caches !== 'undefined') return 'h5'
  if (typeof wx !== 'undefined') return 'mp'
  return 'unknown'
}

// 清理端上「运行期缓存」：按端分支（H5 用 Cache API，App 用 5+ plus.cache.clear）。
// 注意：这是「应用缓存」，与上面的 storage 清理互相独立——storage 用 clearStorageSync，
// 这里只清运行期缓存（图片缓存/离线包等），不碰登录态。
async function clearCache() {
  const runtime = detectRuntime()
  if (runtime === 'app') {
    if (typeof plus === 'undefined' || !plus.cache) {
      uni.showToast({ title: '非 App 端', icon: 'none' })
      return
    }
    uni.showModal({
      title: '清理 App 运行期缓存？',
      content: '将调用 plus.cache.clear 清理应用运行期缓存（图片/离线包等），不删除登录态与本地草稿。',
      confirmText: '确认清理',
      success: (res) => {
        if (!res.confirm) return
        // 5+ API：清空应用缓存目录，成功后回调
        plus.cache.clear('/', () => {
          report.value = 'App 端：已通过 plus.cache.clear 清理运行期缓存。'
          uni.showToast({ title: '已清理缓存', icon: 'success' })
        }, (e) => {
          report.value = 'App 端：plus.cache.clear 失败（' + (e?.message || e) + '）'
          uni.showToast({ title: '清理失败', icon: 'none' })
        })
      },
    })
    return
  }
  if (runtime === 'h5') {
    try {
      if (!('caches' in window)) {
        uni.showToast({ title: '当前环境无 Cache API', icon: 'none' })
        return
      }
      const keys = await window.caches.keys()
      if (!keys.length) {
        report.value = 'H5 端：无 Service Worker 缓存可清理。'
        uni.showToast({ title: '无需清理', icon: 'none' })
        return
      }
      await Promise.all(keys.map((k) => window.caches.delete(k)))
      report.value = `H5 端：已清理 ${keys.length} 个 Service Worker 缓存（Cache API）。`
      uni.showToast({ title: '已清理缓存', icon: 'success' })
    } catch (e) {
      report.value = 'H5 端：Cache API 不可用（需 https/localhost 安全上下文）：' + e
      uni.showToast({ title: 'H5 清理失败', icon: 'none' })
    }
    return
  }
  // 小程序/未知端：Cache API 不是标准能力，引导用上方 storage 清理
  uni.showModal({
    title: '缓存清理说明',
    content: '当前端（小程序/其他）不支持 Cache API。如需释放端上空间，请使用上方「清空全部 storage」清理端上存储。',
    showCancel: false,
  })
}
</script>

<style scoped>
.page { padding: 24rpx; background: #f5f6f7; min-height: 100vh; }
.card { background: #fff; border-radius: 16rpx; padding: 24rpx; margin-bottom: 24rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04); }
.card-title { font-size: 30rpx; font-weight: 600; color: #1a1a1a; margin-bottom: 16rpx; }
.row { display: flex; justify-content: space-between; padding: 8rpx 0; font-size: 26rpx; }
.row-between { display: flex; justify-content: space-between; align-items: center; }
.k { color: #888; }
.v { color: #1a1a1a; }
.used { font-size: 24rpx; color: #e54d42; }
.empty { color: #999; font-size: 26rpx; padding: 16rpx 0; }
.item { display: flex; align-items: center; padding: 14rpx 0; border-top: 1rpx solid #f0f0f0; }
.check { width: 44rpx; color: #007aff; font-size: 32rpx; }
.key { flex: 1; font-size: 28rpx; color: #333; word-break: break-all; }
.size { color: #999; font-size: 24rpx; }
.actions { display: flex; flex-direction: column; gap: 16rpx; margin-bottom: 24rpx; }
.btn { background: #007aff; color: #fff; border-radius: 12rpx; font-size: 28rpx; }
.btn.danger { background: #e54d42; }
.btn.warn { background: #ff9500; }
.btn.ghost { background: #fff; color: #007aff; border: 1rpx solid #007aff; }
.report .rp { font-size: 26rpx; color: #333; line-height: 1.6; }
</style>
