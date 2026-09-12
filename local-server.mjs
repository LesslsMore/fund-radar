// 本地联调服务器: 静态托管 frontend/dist + 同源挂载 /api/*
// 用法: node local-server.mjs  (先 npm run build 生成 dist)
import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import fundsHandler from './api/funds.js';
import metaHandler from './api/meta.js';
import fundDetailHandler from './api/funds/[code].js';

const root = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(root, 'frontend', 'dist');
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.webmanifest': 'application/manifest+json',
  '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.woff2': 'font/woff2'
};

http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/api/funds') return fundsHandler(req, res);
  if (u.pathname === '/api/meta') return metaHandler(req, res);
  if (u.pathname.startsWith('/api/funds/')) return fundDetailHandler(req, res);

  let p = decodeURIComponent(u.pathname);
  if (p === '/') p = '/index.html';
  let fp = path.join(dist, p);
  if (!fs.existsSync(fp) || !fs.statSync(fp).isFile()) fp = path.join(dist, 'index.html'); // SPA fallback
  res.setHeader('Content-Type', MIME[path.extname(fp)] || 'application/octet-stream');
  fs.createReadStream(fp).pipe(res);
}).listen(3000, () => console.log('http://localhost:3000'));
