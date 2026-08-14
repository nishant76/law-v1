/**
 * Node.js HTTP server wrapping the Cloudflare Workers-format handler
 * produced by @lovable.dev/vite-tanstack-config.
 *
 * The built dist/server/server.js exports { fetch(request, env, ctx) }
 * which is the Fetch API handler from src/server.ts. Node.js 18+ has the
 * Web Fetch API built-in, so this runs with zero extra dependencies.
 */
import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { join, extname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dir = fileURLToPath(new URL('.', import.meta.url));
const clientDir = resolve(__dir, 'dist/client');

// Use the self-contained esbuild bundle (all React/TanStack deps inlined)
const { default: handler } = await import('./dist/server.bundle.mjs');

const MIME = {
  '.js':    'application/javascript',
  '.mjs':   'application/javascript',
  '.css':   'text/css',
  '.html':  'text/html; charset=utf-8',
  '.json':  'application/json',
  '.ico':   'image/x-icon',
  '.png':   'image/png',
  '.jpg':   'image/jpeg',
  '.jpeg':  'image/jpeg',
  '.gif':   'image/gif',
  '.svg':   'image/svg+xml',
  '.webp':  'image/webp',
  '.woff':  'font/woff',
  '.woff2': 'font/woff2',
  '.ttf':   'font/ttf',
  '.txt':   'text/plain',
  '.xml':   'application/xml',
};

const PORT = parseInt(process.env.PORT || '8080', 10);

const server = createServer(async (nodeReq, nodeRes) => {
  try {
    const urlPath = nodeReq.url || '/';

    // Serve static files from dist/client/ directly (fast path)
    const staticFile = join(clientDir, urlPath);
    if (existsSync(staticFile)) {
      const stat = statSync(staticFile);
      if (stat.isFile()) {
        const ext = extname(staticFile).toLowerCase();
        nodeRes.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
        // Hash-named assets are content-addressed — cache forever
        if (urlPath.startsWith('/assets/')) {
          nodeRes.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
        }
        createReadStream(staticFile).pipe(nodeRes);
        return;
      }
    }

    // Collect request body (skip for GET/HEAD)
    let body = null;
    if (nodeReq.method !== 'GET' && nodeReq.method !== 'HEAD') {
      const chunks = [];
      for await (const chunk of nodeReq) chunks.push(chunk);
      if (chunks.length > 0) body = Buffer.concat(chunks);
    }

    // Build the full URL — respect X-Forwarded-Proto/Host (Cloud Run sets these)
    const proto = String(nodeReq.headers['x-forwarded-proto'] || 'http').split(',')[0].trim();
    const host  = String(nodeReq.headers['x-forwarded-host']  || nodeReq.headers.host || 'localhost');
    const url   = `${proto}://${host}${urlPath}`;

    const webReq = new Request(url, {
      method:  nodeReq.method,
      headers: nodeReq.headers,
      body,
      duplex:  body ? 'half' : undefined,
    });

    const webRes = await handler.fetch(webReq, {}, {
      waitUntil:             () => {},
      passThroughOnException: () => {},
    });

    nodeRes.statusCode = webRes.status;
    for (const [k, v] of webRes.headers.entries()) nodeRes.setHeader(k, v);

    if (webRes.body) {
      const reader = webRes.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        nodeRes.write(Buffer.from(value));
      }
    }
    nodeRes.end();
  } catch (err) {
    console.error('[serve] Request error:', err);
    if (!nodeRes.headersSent) nodeRes.statusCode = 500;
    nodeRes.end('Internal Server Error');
  }
});

server.listen(PORT, '0.0.0.0', () =>
  console.log(`SuperAdvocate frontend on port ${PORT}`)
);
