import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, unlink } from 'node:fs/promises';

let Resvg;
try {
  ({ Resvg } = await import('@resvg/resvg-js'));
} catch {
  test('resvg not available -> skip', { skip: true }, () => {});
}

if (Resvg) {
  const src = await readFile(new URL('../api/recently-played.png.ts', import.meta.url), 'utf8');
  const tmp = new URL('./recently-played.tmp.mjs', import.meta.url);
  await writeFile(tmp, src, 'utf8');
  const { default: handler } = await import(tmp.href);
  await unlink(tmp);

  globalThis.fetch = async () =>
    new Response('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40"></svg>');

  test('handler renders png', async () => {
    const req = { headers: { host: 'example.com' }, url: '/api/recently-played.png' };
    const res = {
      statusCode: 200,
      headers: {},
      setHeader(k, v) {
        this.headers[k] = v;
      },
      status(c) {
        this.statusCode = c;
        return this;
      },
      end(d) {
        this.body = Buffer.isBuffer(d) ? d : Buffer.from(d || '');
      },
      send(d) {
        this.end(d);
      },
    };
    await handler(req, res);
    assert.equal(res.headers['Content-Type'], 'image/png');
    const buf = res.body;
    assert.equal(buf[0], 0x89);
    assert.equal(buf[1], 0x50);
    assert.equal(buf[2], 0x4e);
    assert.equal(buf[3], 0x47);
  });
}
