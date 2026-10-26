<template>
  <view class="topnav">
    <view :class="['tn', active === 'cockpit' ? 'on' : '']" @click="go('pages/cockpit/cockpit')">总览</view>
    <view :class="['tn', active === 'report' ? 'on' : '']" @click="go('pages/report/report')">报告</view>
    <view :class="['tn', active === 'profiles' ? 'on' : '']" @click="go('pages/profiles/profiles')">档位</view>
  </view>
</template>

<script setup>
const props = defineProps({
  active: { type: String, default: '' },
})

function go(url) {
  // 已在当前页则不动；否则替换当前页（避免页面栈无限叠加）
  if (url.endsWith(props.active)) return
  uni.redirectTo({ url: '/' + url })
}
</script>
