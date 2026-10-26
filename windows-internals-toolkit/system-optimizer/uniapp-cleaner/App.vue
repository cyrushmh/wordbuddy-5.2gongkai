<script>
// uni-app 应用入口。默认页面见 pages.json（pages/cleanup/cleanup）。
// 本工程是 system-optimizer 中 uniapp 目标端「端上 storage 清理」任务的真实落地页：
// 对应 sysweeper 任务 uniapp_storage / uniapp_h5_storage。
export default {
  onLaunch() {
    // 无需全局初始化；清理逻辑全部在 cleanup 页面内。
  },
}
</script>

<style>
page {
  background: #f5f6f7;
}
</style>
