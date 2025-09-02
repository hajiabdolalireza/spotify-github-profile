import { Resvg } from '@resvg/resvg-js';
import { createHash } from 'node:crypto';

const CACHE_CONTROL = 'public, max-age=60, stale-while-revalidate=30';

export default async function handler(req) {
  const url = new URL(req.url);
  const width = parseInt(url.searchParams.get('width') || '') || 920;
  const upstream = `${url.origin}${url.pathname.replace(/\.png$/, '')}${url.search}`;
  const svgResp = await fetch(upstream, { headers: { 'user-agent': 'resvg' } });
  const svg = await svgResp.text();
  const etag = 'W/"' + createHash('sha1').update(svg).digest('base64') + '"';
  const headers = {
    'ETag': etag,
    'Cache-Control': CACHE_CONTROL,
  };
  if (req.headers.get('If-None-Match') === etag) {
    return new Response(null, { status: 304, headers });
  }
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: width } }).render().asPng();
  headers['Content-Type'] = 'image/png';
  return new Response(png, { status: 200, headers });
}
