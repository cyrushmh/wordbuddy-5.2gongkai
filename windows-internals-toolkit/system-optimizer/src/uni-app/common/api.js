// 与 sysweeper 本机控制台的 JSON 接口层对接。
// 协议：POST {BASE_URL}/api  { action, params, source }  ->  { ok, data } / { ok:false, error }
import { BASE_URL } from './config.js'

// 单例化 uni.request 的 Promise 封装；串行排队避免同时多个只读探测互相干扰。
let chain = Promise.resolve()

export function callApi(action, params = {}) {
  const run = () =>
    new Promise((resolve, reject) => {
      uni.request({
        url: BASE_URL + '/api',
        method: 'POST',
        header: { 'content-type': 'application/json' },
        data: { action, params, source: 'uni-app' },
        timeout: 120000,
        success: (r) => {
          if (r.statusCode !== 200) {
            reject(new Error('HTTP ' + r.statusCode))
            return
          }
          const j = r.data
          if (!j || j.ok === false) {
            reject(new Error((j && j.error) || '后端返回失败'))
            return
          }
          resolve(j.data)
        },
        fail: (e) => reject(new Error(e.errMsg || '网络错误')),
      })
    })
  // 串行化：前一个 settle 才轮到下一个（与 Deno 控制台的桥一致）
  const p = chain.then(run, run)
  chain = p.then(() => {}, () => {})
  return p
}

export function healthz() {
  return new Promise((resolve) => {
    uni.request({
      url: BASE_URL + '/healthz',
      method: 'GET',
      timeout: 8000,
      success: (r) => resolve(r.statusCode === 200),
      fail: () => resolve(false),
    })
  })
}
