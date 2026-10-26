"""uni-app 各小程序端（微信 / 支付宝 / 百度 / 抖音 / QQ / 快手）的核对与清理任务。

「触类旁通、举一反三」：内核、桌面、系统软件、鸿蒙之后落到**跨端框架的各目标端**——
每个小程序平台都有**自己的 API 规范与运行架构**，因此每项任务的标准依据指向该端自己的
官方文档（见 data/miniapp_docs.json），而不是套用某个通用模板：

- 微信 : wx.* + 双线程架构（逻辑层 AppService / 视图层 WebView）
- 支付宝: my.* + 域名白名单 + my.getAuthCode 授权
- 百度 : swan.*    抖音: tt.*    QQ: qq.*    快手: ks.*
- uni-app: uni.* 统一 API → 各端映射，差异用条件编译 #ifdef MP-XXX 隔离

未发现 uni-app 工程时，原生探测自动降级为「指引」，不强求配置。
清理类动作只清可重建的构建产物，且需 --apply。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

WX = "[国际] 微信小程序文档（developers.weixin.qq.com：wx.* API / 双线程架构 / app.json）"
ALI = "[国际] 支付宝小程序文档（opendocs.alipay.com：my.* API / 域名白名单 / getAuthCode）"
BD = "[国际] 百度智能小程序文档（smartprogram.baidu.com：swan.* API）"
DY = "[国际] 抖音小程序文档（developer.open-douyin.com：tt.* API）"
QQ = "[国际] QQ 小程序文档（q.qq.com/wiki：qq.* API）"
KS = "[国际] 快手小程序文档（mp.kuaishou.com：ks.* API）"
UNI = "[国际] uni-app 跨平台文档（条件编译 #ifdef MP-XXX + manifest mp-* 节点 + uni.* 映射）"


TASKS = [
    Task(
        id="mp_mapping_check",
        platform="uniapp",
        title="跨端映射核对（uni.* → 各端原生 API）",
        category="optimize",
        risk="low",
        desc="核对 manifest 中已启用的小程序端，及各端条件编译覆盖情况，避免运行时猜平台。",
        actions=[
            N("miniapp.mapping_report", "核对各端 mp-* 配置与条件编译覆盖（只读）"),
        ],
        standards=[UNI],
        notes=["参考 uni-app 跨平台文档：uni.* 统一 API 会映射到各端原生 API"
               "（uni.request → wx/my/swan/tt/qq/ks.request）。",
               "无法抹平的差异一律用 #ifdef MP-WEIXIN 等条件编译隔离，不要运行时猜平台。"],
        caveats=["仅核对工程配置与源码宏使用统计，不改任何文件。"],
    ),
    Task(
        id="mp_cross_lint",
        platform="uniapp",
        title="跨端静态检查（直调某端 API 未加条件编译保护）",
        category="optimize",
        risk="low",
        desc="静态扫描源码，找出直接调用某端原生 API（如 wx.request）却未用该端条件编译"
             "（#ifdef MP-WEIXIN）保护的位置——这类代码发行到别的端会直接报错。",
        actions=[
            N("miniapp.cross_platform_lint", "跨端静态检查（只读扫描，不改任何文件）"),
        ],
        standards=[UNI],
        notes=["参考 uni-app 跨平台文档：uni.* 统一 API 会映射到各端原生 API，"
               "因此业务代码应优先用 uni.request 而非 wx.request。",
               "确需调用某端独有 API 时，必须用该端条件编译包裹"
               "（wx.* → #ifdef MP-WEIXIN，my.* → #ifdef MP-ALIPAY，依此类推）。"],
        caveats=["纯静态扫描（不执行代码），可能有少量误报/漏报；结果供核对参考，"
                 "本任务绝不修改任何源码文件。"],
    ),
    Task(
        id="mp_weixin_check",
        platform="uniapp",
        title="微信小程序端核对（wx.* / 双线程）",
        category="optimize",
        risk="low",
        desc="核对微信端 mp-weixin 配置、产物与条件编译；按 wx.* 规范核对缓存与登录要点。",
        actions=[
            N("miniapp.weixin_report", "核对微信端配置/产物/条件编译（只读）"),
        ],
        standards=[WX],
        notes=["参考微信小程序文档：双线程架构（逻辑层 AppService + 视图层 WebView 经 Native 通信）；"
               "缓存 wx.getStorage/setStorage 有单 key 与总配额限制。",
               "登录以 wx.login 换 code 交服务端，勿在前端保存敏感凭据。"],
        caveats=["仅只读核对；微信端需 appid 与服务器域名配置，发行前在 manifest 的 mp-weixin 节点核对。"],
    ),
    Task(
        id="mp_alipay_check",
        platform="uniapp",
        title="支付宝小程序端核对（my.* / 白名单）",
        category="optimize",
        risk="low",
        desc="核对支付宝端 mp-alipay 配置与产物，按 my.* 规范提醒域名白名单与授权要点。",
        actions=[
            N("miniapp.alipay_report", "核对支付宝端配置/产物/条件编译（只读）"),
        ],
        standards=[ALI],
        notes=["参考支付宝小程序文档：网络请求域名必须加入白名单，否则真机必失败；"
               "授权用 my.getAuthCode 而非自行实现登录态。",
               "缓存接口（my.getStorage/setStorage）为异步回调风格，注意 success/fail 处理。"],
        caveats=["仅只读核对；支付宝端对支付/会员类能力有额外资质要求。"],
    ),
    Task(
        id="mp_baidu_check",
        platform="uniapp",
        title="百度智能小程序端核对（swan.*）",
        category="optimize",
        risk="low",
        desc="核对百度端 mp-baidu 配置与产物，按 swan.* 规范隔离差异。",
        actions=[
            N("miniapp.baidu_report", "核对百度端配置/产物/条件编译（只读）"),
        ],
        standards=[BD],
        notes=["参考百度智能小程序文档：能力经 swan.* 暴露（swan.request / swan.getStorage / swan.login）。",
               "百度端偏重搜索与 AI 能力接入；与微信同名不同前缀，勿直接沿用 wx.* 写法。"],
        caveats=["仅只读核对；涉及搜索/AI 能力的接口需按百度开放平台规范申请。"],
    ),
    Task(
        id="mp_douyin_check",
        platform="uniapp",
        title="抖音小程序端核对（tt.*）",
        category="optimize",
        risk="low",
        desc="核对抖音端 mp-toutiao 配置与产物，按 tt.* 规范隔离差异。",
        actions=[
            N("miniapp.douyin_report", "核对抖音端配置/产物/条件编译（只读）"),
        ],
        standards=[DY],
        notes=["参考抖音小程序文档：能力经 tt.* 暴露（tt.request / tt.getStorage / tt.login）。",
               "注意：抖音端在 uni-app 中的平台节点为 mp-toutiao，条件编译宏为 MP-TOUTIAO。"],
        caveats=["仅只读核对；内容发布相关接口审核较严，按官方审核规范准备资质。"],
    ),
    Task(
        id="mp_qq_check",
        platform="uniapp",
        title="QQ 小程序端核对（qq.*）",
        category="optimize",
        risk="low",
        desc="核对 QQ 端 mp-qq 配置与产物；QQ 端与微信同源度高，但仍需条件编译隔离差异。",
        actions=[
            N("miniapp.qq_report", "核对 QQ 端配置/产物/条件编译（只读）"),
        ],
        standards=[QQ],
        notes=["参考 QQ 小程序文档：能力经 qq.* 暴露，架构与微信小程序高度同源。",
               "差异主要在社交关系链与部分开放能力上，需按 QQ 开放平台规范申请权限。"],
        caveats=["仅只读核对；勿因同源度高就省掉条件编译。"],
    ),
    Task(
        id="mp_kuaishou_check",
        platform="uniapp",
        title="快手小程序端核对（ks.*）",
        category="optimize",
        risk="low",
        desc="核对快手端 mp-kuaishou 配置与产物，按 ks.* 规范隔离差异。",
        actions=[
            N("miniapp.kuaishou_report", "核对快手端配置/产物/条件编译（只读）"),
        ],
        standards=[KS],
        notes=["参考快手小程序文档：能力经 ks.* 暴露（ks.request / ks.getStorage / ks.login）。",
               "形态与字节/微信系相近，但自有内容生态与审核规范。"],
        caveats=["仅只读核对；勿复用其他端的权限判断逻辑。"],
    ),
    Task(
        id="mp_dist_cache",
        platform="uniapp",
        title="清理各小程序端构建产物（可重建）",
        category="cleanup",
        risk="low",
        desc="清理 unpackage/dist 与 dist 下各 mp-* 端构建产物，回收空间（重新发行即可恢复）。",
        actions=[
            S('rm -rf ./unpackage/dist/build/mp-* ./unpackage/dist/dev/mp-* '
              './dist/build/mp-* ./dist/dev/mp-* 2>/dev/null; true',
              "清理各小程序端构建产物（mp-* 目录，可重建）", rev=True),
        ],
        standards=[UNI],
        notes=["参考 uni-app 发行文档：mp-* 产物由发行操作生成，删除后重新发行即可恢复。",
               "需在 uni-app 工程根目录执行。"],
        caveats=["切勿删除 src/、manifest.json、pages.json 与 node_modules——前者丢失无法恢复，"
                 "后者需重新安装。删除前建议先提交版本库。"],
    ),
]
