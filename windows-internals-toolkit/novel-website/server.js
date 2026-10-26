// 零依赖静态文件服务器（仅用 Node.js 内置模块）
// 用途：本地预览 novel-website，无需 npm install。
import http from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const PUBLIC = join(__dirname, "public");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

const server = http.createServer(async (req, res) => {
  try {
    const urlPath = decodeURIComponent(
      new URL(req.url, `http://${req.headers.host}`).pathname
    );
    let filePath;
    if (urlPath === "/") {
      filePath = join(PUBLIC, "index.html");
    } else if (urlPath.startsWith("/data/") || urlPath.startsWith("/api/")) {
      // 允许访问 public 之外的 data 目录（novels.json / 章节 md）
      filePath = join(__dirname, normalize(urlPath));
    } else {
      filePath = join(PUBLIC, normalize(urlPath));
    }

    let body;
    try {
      body = await readFile(filePath);
    } catch {
      // 未知路径回退到首页
      filePath = join(PUBLIC, "index.html");
      body = await readFile(filePath);
    }
    const type = MIME[extname(filePath)] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": type });
    res.end(body);
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("500 Internal Server Error\n" + err.message);
  }
});

server.listen(PORT, () =>
  console.log(`小说网站预览: http://localhost:${PORT}`)
);
