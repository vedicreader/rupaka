/* field: an expr formula on each cell of an n x n grid, as a list of n rows. Row i and column j go from 0 to n - 1.
   The formula can call noise(i, j): a value with mean 0 and variance 1, the same for the same seed, i and j.
   noise is a sum of four uniform hashes (murmur3 fmix32), so Python gives the same bits. */
(() => {
  const mix = h => { h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b); h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35); return (h ^ h >>> 16) >>> 0; };
  const step = (h, x) => mix(((h ^ x) + 0x9e3779b9) >>> 0);
  const noise = (seed, i, j) => {
    const h = step(step(seed >>> 0, i >>> 0), j >>> 0);
    return ((step(h, 0) + step(h, 1) + step(h, 2) + step(h, 3)) / 4294967296 - 2) * Math.sqrt(3);
  };
  const cache = {};
  Rupaka.fn('field', (d, st) => {
    const n = d.n ?? 16, seed = d.seed ?? 0;
    if (!(Number.isInteger(n) && n >= 1 && n <= 64)) throw new Error('field: n must be an int from 1 to 64');
    const f = cache[`${seed}|${d.expr}`] ||= Rupaka.expr(d.expr, {noise: (i, j) => noise(seed, i, j)});
    return Array.from({length: n}, (_, i) => Array.from({length: n}, (_, j) => f({...st, i, j})));
  });
})();
