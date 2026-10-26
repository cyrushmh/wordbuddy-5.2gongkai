// sysweeper 本机控制台地址（uni-app 端共用）。
//
// 默认值只适合「模拟器/本地同机」场景。手机真机要访问时，把这里改成电脑的
// 局域网 IP，例如 http://192.168.1.20:8787 ；同时控制台要用
//   deno run --allow-net --allow-read --allow-run src/deno/console.ts --host 0.0.0.0
// 才会监听外部网卡（默认只监听 127.0.0.1，外部访问不到）。
//
// 注意：控制台 /api 未开 CORS。所以「实时」模式在 App / 小程序端正常；
// H5（浏览器）跨域访问会被拦——H5 请用下方「报告查看器」的粘贴 JSON 模式
// （数据不出机器也能看，全端通用）。
export const BASE_URL = 'http://127.0.0.1:8787'

// 本前端随 sysweeper 主版本号走
export const APP_VERSION = '0.6.27'
