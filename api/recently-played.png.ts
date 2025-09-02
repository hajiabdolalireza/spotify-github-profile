import { createHash } from 'node:crypto';
import { Resvg } from '@resvg/resvg-js';

const CACHE_CONTROL = 'public, max-age=60, stale-while-revalidate=30';

export default async function handler(req, res) {
  try {
    const proto = req.headers['x-forwarded-proto'] || 'https';
    const host = req.headers['x-forwarded-host'] || req.headers.host;
    if (!host) {
      res.statusCode = 500;
      res.end('Missing host header');
      return;
    }

    const search = req.url && req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';
    const svgUrl = new URL(`/api/recently-played${search}`, `${proto}://${host}`).toString();

    const upstream = await fetch(svgUrl, {
      headers: {
        'user-agent': 'resvg',
        ...(req.headers['if-none-match'] ? { 'if-none-match': req.headers['if-none-match'] } : {}),
      },
    });

    if (upstream.status === 304) {
      res.statusCode = 304;
      res.setHeader('Cache-Control', CACHE_CONTROL);
      res.end();
      return;
    }

    if (!upstream.ok) {
      res.statusCode = 502;
      res.end(`Upstream error ${upstream.status}`);
      return;
    }

    const svg = await upstream.text();
    const etag = `W/"${createHash('sha1').update(svg).digest('hex')}"`;

    if (req.headers['if-none-match'] === etag) {
      res.statusCode = 304;
      res.setHeader('ETag', etag);
      res.setHeader('Cache-Control', CACHE_CONTROL);
      res.end();
      return;
    }

    const widthParam = new URLSearchParams(search.startsWith('?') ? search.slice(1) : '').get('width');
    const widthNum = Number(widthParam);
    const width = Number.isFinite(widthNum) && widthNum > 0 ? widthNum : 920;

    const png = new Resvg(svg, { fitTo: { mode: 'width', value: width } }).render().asPng();

    res.statusCode = 200;
    res.setHeader('Content-Type', 'image/png');
    res.setHeader('ETag', etag);
    res.setHeader('Cache-Control', CACHE_CONTROL);
    res.end(Buffer.from(png));
  } catch (err) {
    res.statusCode = 500;
    res.end(err.message);
  }
}
