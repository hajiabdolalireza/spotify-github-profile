import { test } from 'node:test';
import assert from 'node:assert/strict';

let Resvg;
try {
    ({ Resvg } = await import('@resvg/resvg-js'));
      } catch {

    test('resvg not available -> skip', { skip: true }, () => {});
}

if (Resvg) {
    test('Resvg can render a tiny PNG (smoke)', () => {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40"><rect width="100" height="40" fill="black"/></svg>`;
        const png = new Resvg(svg, { fitTo: { mode: 'width', value: 100 } }).render().asPng();

assert.equal(png[0], 0x89);
assert.equal(png[1], 0x50);
assert.equal(png[2], 0x4e);
assert.equal(png[3], 0x47);
});
}
