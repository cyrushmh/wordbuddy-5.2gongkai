/**
 * sysweeper 本机 Web 控制台（0000.0000.0000.0018.20261025）—— 零依赖 Deno HTTP 外壳。
 *
 * 架构：Python 当逻辑层，Deno 只做 HTTP 外壳。
 *   浏览器 ──HTTP──▶ 本文件 ──JSONL(长连接)──▶ `python3 -m sysweeper webapi`
 * 所有诊断、参数、子系统、导入逻辑都在 Python 侧已经写全了（GUI/CLI 同款），
 * 这里一行都不重写，只负责转发与托管静态页面，避免两套实现对不上。
 *
 * 用户端人体工程学口径（《南华真经》核心理念，详见 concepts zhuangzi）：
 *   · 逍遥游 → 无待一步：启动横幅即打印动作目录摘要；/manifest 让前端
 *     「发现式」取目录，不预设用户会背 action 名。
 *   · 应帝王 → 默认即最佳：只监听 127.0.0.1（默认），启动即自检后端连通，
 *     失败早说并给恢复命令，不让用户打开页面才看到红字。
 *   · 大宗师 → 意图宗师：失败响应统一带 hint（原因 + 下一步命令），
 *     每个错误都指路、可回退。
 *
 * 为什么必须跑在本机：这个工具的核心价值是**读本机**（sysfs / 注册表 / 硬件 /
 * 已装软件），远端沙箱读不到你的机器。所以部署到云端的只有「报告查看器」，
 * 真操作必须在本机 —— 也就是这个控制台。
 *
 * 用法：
 *   deno run --allow-net --allow-read --allow-run src/deno/console.ts [--port 8787]
 *   sysweeper web                       # Python CLI 一键拉起（会自动找 deno）
 *
 * 权限说明（为什么要最小权限，而不是 --allow-all）：
 *   --allow-net   监听端口
 *   --allow-read  读 src/deno/web 下的静态页面
 *   --allow-run   起 python 子进程（唯一的逻辑后端）
 * 刻意**不申请** --allow-write 与 --allow-env：控制台本身不写任何文件、也不读环境变量
 * （Python 路径改用 `-c` 引导注入 sys.path，避免靠 PYTHONPATH）。
 * 写配置一律走 Python 侧的动作白名单，且只写用户自己的配置文件。
 *
 * CORS：为支持 uni-app H5 等同源外端口前端跨域读取，/api 自动回 CORS 头，
 *   默认反射请求方 Origin；可用 SYSWEEPER_CORS_ORIGIN 锁死为单一可信源。只读、无凭据。
 */
// deno-lint-ignore-file no-explicit-any

const VERSION = "0000.0000.0000.0034.20261026";

// ── 路径解析 ──────────────────────────────────────────────────────────────
/** 本文件位于 <repo>/src/deno/console.ts，往上两级即仓库根。 */
const HERE = new URL(".", import.meta.url);
const REPO_ROOT_URL = new URL("../../", import.meta.url);

/** file:// URL → 本地路径（Windows 需去掉开头的 /，这里做兼容处理）。 */
function urlToPath(u: URL): string {
  let p = decodeURIComponent(u.pathname);
  if (/^\/[A-Za-z]:/.test(p)) p = p.slice(1); // /C:/... → C:/...
  return p;
}

const REPO_ROOT = urlToPath(REPO_ROOT_URL);

// ── 参数 ──────────────────────────────────────────────────────────────────
type Opts = {
  port: number;
  host: string;
  python: string;
  open: boolean;
};

/** 读环境变量；没授予 --allow-env 时不抛，退回 fallback（权限最小化）。 */
function envGet(key: string, fallback: string): string {
  try {
    return Deno.env.get(key) || fallback;
  } catch {
    return fallback;
  }
}

function parseArgs(argv: string[]): Opts {
  const opts: Opts = {
    port: 8787,
    host: "127.0.0.1",
    python: envGet("SYSWEEPER_PYTHON", "python3"),
    open: true,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i] ?? "";
    if (a === "--port" || a === "-p") opts.port = Number(next()) || opts.port;
    else if (a === "--host") opts.host = next() || opts.host;
    else if (a === "--python") opts.python = next() || opts.python;
    else if (a === "--no-open") opts.open = false;
    else if (a === "--open") opts.open = true;
    else if (a === "--help" || a === "-h") {
      console.log(HELP);
      Deno.exit(0);
    }
  }
  return opts;
}

const HELP = `sysweeper 本机 Web 控制台

  deno run --allow-net --allow-read --allow-run src/deno/console.ts [选项]

选项:
  -p, --port <N>      监听端口（默认 8787）
      --host <ADDR>   监听地址（默认 127.0.0.1，只本机可访问）
      --python <CMD>  Python 解释器（默认 $SYSWEEPER_PYTHON 或 python3）
      --no-open       启动后不自动开浏览器
  -h, --help          显示本帮助

说明：控制台本身不含诊断逻辑，所有数据来自本机 Python 后端
（等价于 \`sysweeper webapi\`）。绝不暴露任何写系统动作。

端点：
  /healthz     健康检查（版本 / Python 连通）
  /manifest    动作白名单目录（名称 / 读写性质 / 说明）
  /api         JSON 转发（GET ?action=… 或 POST {action, params}）

用户端口径（南华真经）：无待一步（一屏直达）· 默认即最佳 · 失败指路可回退。`;

/** Python CLI 拉起本控制台时的推荐权限串（两处保持一致）。 */
export const RUN_FLAGS = [
  "--allow-net",
  "--allow-read",
  "--allow-run",
];

// ── Python 后端长连接 ──────────────────────────────────────────────────────
/**
 * 起一个 `python3 -m sysweeper webapi` 常驻进程，按行喂请求、按行读响应。
 *
 * 为什么要常驻：每个请求冷起一次解释器要几百毫秒且每次都重新 import 整个包，
 * 点一下按钮卡半天。JSONL 长连接让一个进程一直活着，响应就是毫秒级。
 *
 * 请求串行化：Python 侧是单线程顺序处理，这里用一条 Promise 链排队，
 * 保证「先写的请求先收到响应」不会错位。
 */
class PythonBridge {
  #child: Deno.ChildProcess | null = null;
  #writer: WritableStreamDefaultWriter<Uint8Array> | null = null;
  #reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  #buf = "";
  #tail = Promise.resolve();
  #opts: Opts;
  #lastError = "";
  #manifest: any = null;

  constructor(opts: Opts) {
    this.#opts = opts;
  }

  get alive(): boolean {
    return this.#child !== null;
  }

  /** 动作目录（manifest，带缓存；南华·逍遥游：发现式取目录，不预设用户会背 action）。 */
  async manifest(): Promise<any> {
    if (this.#manifest !== null) return this.#manifest;
    const resp = await this.call({ action: "manifest", params: {}, source: "web" });
    if (resp && resp.ok !== false) {
      this.#manifest = resp.data ?? {};
    } else {
      this.#manifest = { ok: false, error: resp?.error || "manifest 查询失败" };
    }
    return this.#manifest;
  }

  start(): void {
    if (this.#child) return;
    // 用 `-c` 引导而不是改 PYTHONPATH：这样不必申请 --allow-env，
    // 子进程还能完整继承父进程环境（HOME / PATH / DISPLAY 等都要用）。
    const boot = "import sys; sys.path.insert(0, " +
      JSON.stringify(REPO_ROOT + "/src/python") + "); " +
      "from sysweeper.cli import main as _m; sys.exit(_m(['webapi']))";

    const cmd = new Deno.Command(this.#opts.python, {
      args: ["-c", boot],
      cwd: REPO_ROOT,
      stdin: "piped",
      stdout: "piped",
      stderr: "piped",
    });
    try {
      this.#child = cmd.spawn();
    } catch (e) {
      this.#lastError = `起不来 Python 后端（${this.#opts.python}）: ${e}`;
      return;
    }
    this.#writer = this.#child.stdin.getWriter();
    this.#reader = this.#child.stdout.getReader();
    // stderr 单独收着，出错时能给前端一句人话
    const errReader = this.#child.stderr.getReader();
    const dec = new TextDecoder();
    (async () => {
      try {
        for (;;) {
          const { value, done } = await errReader.read();
          if (done) break;
          const s = dec.decode(value);
          if (s.trim()) this.#lastError = (this.#lastError + s).slice(-2000);
        }
      } catch { /* 进程已退出 */ }
    })();
  }

  /** 读一整行（自带缓冲，跨 chunk 也能拼对）。 */
  async #readLine(): Promise<string | null> {
    const r = this.#reader;
    if (!r) return null;
    const dec = new TextDecoder();
    for (;;) {
      const nl = this.#buf.indexOf("\n");
      if (nl >= 0) {
        const line = this.#buf.slice(0, nl);
        this.#buf = this.#buf.slice(nl + 1);
        return line;
      }
      const { value, done } = await r.read();
      if (done) return null;
      this.#buf += dec.decode(value, { stream: true });
    }
  }

  /** 发一条请求，收一条响应（JSON 对象）。 */
  async call(req: unknown): Promise<any> {
    const run = async (): Promise<any> => {
      if (!this.#child || !this.#writer) {
        this.start();
      }
      if (!this.#child || !this.#writer) {
        return {
          ok: false,
          error: this.#lastError || "Python 后端未启动",
          hint: "确认已装 Python 3.8+，或用 --python 指定解释器路径",
        };
      }
      const line = JSON.stringify(req);
      try {
        await this.#writer.write(new TextEncoder().encode(line + "\n"));
      } catch (e) {
        this.#child = null;
        return { ok: false, error: `写请求失败: ${e}`, stderr: this.#lastError,
                 hint: "Python 后端可能已退出：刷新页面会自动重连；持续失败先跑 " +
                       "`python3 -m sysweeper webapi --once '{\"action\":\"ping\"}'` 自查" };
      }
      const resp = await this.#readLine();
      if (!resp) {
        const why = this.#lastError || "Python 后端提前退出（无输出）";
        this.#child = null;
        return {
          ok: false,
          error: why,
          hint: "先在命令行试 `python3 -m sysweeper webapi --once '{\"action\":\"ping\"}'`",
        };
      }
      try {
        return JSON.parse(resp);
      } catch {
        return { ok: false, error: "后端返回非 JSON", raw: resp.slice(0, 500),
                 hint: "多为 Python 侧警告/日志混进了 stdout：检查 webapi 是否在 " +
                       "REPL 之外被打印过东西；本页刷新即重来" };
      }
    };
    // 串行化：排队执行，前一个 settle 才轮到下一个
    const p = this.#tail.then(run, run);
    this.#tail = p.then(() => {}, () => {});
    return p;
  }

  stop(): void {
    try {
      this.#child?.kill("SIGTERM");
    } catch { /* 已退出 */ }
    this.#child = null;
    this.#writer = null;
    this.#reader = null;
    this.#buf = "";
  }
}

// ── 静态资源 ──────────────────────────────────────────────────────────────
const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

async function serveStatic(pathname: string): Promise<Response> {
  let rel = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  if (rel.includes("..")) {
    return new Response("bad path", { status: 400 });
  }
  const url = new URL("web/" + rel, HERE);
  try {
    const data = await Deno.readFile(url);
    const ext = rel.slice(rel.lastIndexOf("."));
    return new Response(data, {
      headers: { "content-type": MIME[ext] || "application/octet-stream" },
    });
  } catch {
    return new Response("静态资源缺失: " + rel + "（控制台需与 src/deno/web 一起存放）", {
      status: 404,
    });
  }
}

// ── HTTP 服务 ─────────────────────────────────────────────────────────────
function jsonRes(body: unknown, status = 200, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...extra },
  });
}

/**
 * CORS 头：让 uni-app H5 / 同源其他端口的前端能跨域读只读接口。
 * 默认反射请求方 Origin（本地开发最省心）；可用 SYSWEEPER_CORS_ORIGIN
 * 锁死为单一可信源。本接口只读、不带凭据，反射 Origin 无凭据泄露风险。
 */
function corsHeaders(req: Request): Record<string, string> {
  const pinned = envGet("SYSWEEPER_CORS_ORIGIN", "");
  const origin = req.headers.get("origin") || "";
  const allowOrigin = pinned || origin || "*";
  return {
    "access-control-allow-origin": allowOrigin,
    "access-control-allow-methods": "GET, POST, OPTIONS",
    "access-control-allow-headers": "content-type",
    "access-control-max-age": "86400",
  };
}

function startServer(opts: Opts, bridge: PythonBridge): Deno.HttpServer {
  const handler = async (req: Request): Promise<Response> => {
    const url = new URL(req.url);

    // CORS 预检：跨域 POST 前浏览器先发 OPTIONS，直接放行 /api
    if (req.method === "OPTIONS" && url.pathname === "/api") {
      return new Response(null, { status: 204, headers: corsHeaders(req) });
    }

    if (req.method === "GET" && url.pathname === "/healthz") {
      return jsonRes({ ok: true, version: VERSION, python: bridge.alive });
    }

    // 逍遥游·发现式目录：前端不预设用户会背 action 名，先问目录再渲染按钮
    if (req.method === "GET" && url.pathname === "/manifest") {
      const ch = corsHeaders(req);
      const man = await bridge.manifest();
      return jsonRes(man, 200, ch);
    }

    if (url.pathname === "/api") {
      const ch = corsHeaders(req);
      let payload: unknown = null;
      if (req.method === "POST") {
        try {
          payload = await req.json();
        } catch {
          return jsonRes({ ok: false, error: "请求体不是合法 JSON" }, 400, ch);
        }
      } else if (req.method === "GET") {
        // 便于 curl 调试：/api?action=settings.list&params={...}
        const action = url.searchParams.get("action") || "";
        if (!action) return jsonRes({ ok: false, error: "缺少 action",
                                      hint: "可先看 GET /manifest 取全部动作目录" }, 400, ch);
        let params: Record<string, unknown> = {};
        const raw = url.searchParams.get("params");
        if (raw) {
          try {
            params = JSON.parse(raw);
          } catch {
            return jsonRes({ ok: false, error: "params 不是合法 JSON" }, 400, ch);
          }
        } else {
          for (const [k, v] of url.searchParams.entries()) {
            if (k === "action" || k === "source") continue;
            params[k] = v;
          }
        }
        payload = {
          action,
          params,
          source: url.searchParams.get("source") || "web",
        };
      } else {
        return jsonRes({ ok: false, error: "只支持 GET / POST" }, 405, ch);
      }
      const resp = await bridge.call(payload);
      return jsonRes(resp, 200, ch);
    }

    if (req.method === "GET") {
      return await serveStatic(url.pathname);
    }
    return new Response("method not allowed", { status: 405 });
  };

  return Deno.serve({ hostname: opts.host, port: opts.port }, handler);
}

// ── 打开浏览器（失败静默，无图形环境也不该报错）───────────────────────────
async function openBrowser(url: string): Promise<void> {
  const cmds: Record<string, string[]> = {
    darwin: ["open", url],
    windows: ["cmd", "/c", "start", url],
    linux: ["xdg-open", url],
  };
  const c = cmds[Deno.build.os];
  if (!c) return;
  try {
    const p = new Deno.Command(c[0], { args: c.slice(1), stdout: "null", stderr: "null" }).spawn();
    await p.status;
  } catch { /* 没有浏览器/无图形会话：忽略 */ }
}

// ── 主流程 ────────────────────────────────────────────────────────────────
async function main(): Promise<void> {
  const opts = parseArgs(Deno.args.slice());
  const bridge = new PythonBridge(opts);

  // 先探一次活：Python 起不来就早说，别让用户打开页面才看到红字
  const ping = await bridge.call({ action: "ping", params: { host: true }, source: "web" });
  if (!ping || ping.ok === false) {
    console.error("⚠ Python 后端未就绪：", ping?.error || "未知原因");
    console.error("  提示：先跑一下 `python3 -m sysweeper webapi --once '{\"action\":\"ping\"}'` 看看。");
    console.error("  页面仍会启动，但所有数据都会取不到。");
  }

  const server = startServer(opts, bridge);
  const base = `http://${opts.host}:${opts.port}`;
  console.log(`sysweeper Web 控制台 v${VERSION}`);
  console.log(`  本机地址: ${base}`);
  console.log(`  后端: ${opts.python} → sysweeper webapi（常驻长连接）`);
  console.log(`  只监听 ${opts.host}，外部机器访问不到；诊断只读，不暴露任何写系统动作`);

  // 逍遥游·一屏直达：启动即打印动作目录摘要（前 12 条 + 总数），
  // 全部目录与读写性质见 GET /manifest（前端「发现式」消费）。
  try {
    const man = await bridge.manifest();
    const actions: Array<{ action: string; readonly: boolean; desc: string }> =
      (man && man.actions) || [];
    const ro = actions.filter((a) => a.readonly).length;
    if (actions.length) {
      console.log(`  动作白名单: ${actions.length} 个（只读 ${ro} / 需确认 ${actions.length - ro}）`);
      for (const a of actions.slice(0, 12)) {
        console.log(`    ${a.readonly ? "只读" : "写  "} ${a.action}  ${a.desc}`);
      }
      if (actions.length > 12) console.log(`    …其余 ${actions.length - 12} 个见 /manifest`);
    } else {
      console.log(`  动作目录读取失败（${man?.error || "空"}）；页面启动后仍可尝试`);
    }
  } catch { /* 目录查询失败不应阻塞控制台启动 */ }

  console.log("  Ctrl+C 退出");

  if (opts.open) await openBrowser(base);

  const stop = () => {
    try {
      server.shutdown();
    } catch { /* ignore */ }
    bridge.stop();
  };
  Deno.addSignalListener("SIGINT", () => { stop(); Deno.exit(0); });
  Deno.addSignalListener("SIGTERM", () => { stop(); Deno.exit(0); });

  await server.finished;
}

if (import.meta.main) {
  await main();
}
