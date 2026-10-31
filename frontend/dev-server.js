const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const hostFlag = process.argv.indexOf('--host');
const host = hostFlag >= 0 ? process.argv[hostFlag + 1] || '0.0.0.0' : '127.0.0.1';
const port = Number(process.env.PORT || 5173);
const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
};

const server = http.createServer((request, response) => {
  let requestPath;
  try {
    requestPath = decodeURIComponent(new URL(request.url, `http://${request.headers.host}`).pathname);
  } catch {
    response.writeHead(400).end('Bad request');
    return;
  }

  if (requestPath === '/runtime-config.js') {
    const apiBase = process.env.VITE_API_BASE_URL || process.env.BUGSENSE_API_BASE_URL || '';
    response.writeHead(200, {
      'Content-Type': 'text/javascript; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    });
    response.end(`window.BUGSENSE_API_BASE_URL = ${JSON.stringify(apiBase)};`);
    return;
  }

  const relativePath = requestPath === '/' ? 'index.html' : requestPath.replace(/^\/+/, '');
  const filePath = path.resolve(root, relativePath);
  if (filePath !== root && !filePath.startsWith(root + path.sep)) {
    response.writeHead(403).end('Forbidden');
    return;
  }

  fs.readFile(filePath, (error, content) => {
    if (error) {
      response.writeHead(error.code === 'ENOENT' ? 404 : 500).end('File not found');
      return;
    }
    response.writeHead(200, {
      'Content-Type': mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
      'X-Content-Type-Options': 'nosniff',
    });
    response.end(content);
  });
});

server.listen(port, host, () => {
  console.log(`BugSense AI frontend available at http://${host}:${port}`);
});
