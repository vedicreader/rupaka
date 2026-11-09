/* keyframes: the value at time `in` from [[t, v], ...] keys that go up in t. Before the first key it holds the first value, after the last key the last.
   Each segment eases from its own key: [t, v, 'out'] sets the curve of that segment; `ease` is the default (linear). */
Rupaka.fn('keyframes', (d, st) => {
  const ks = d.keys, x = Rupaka.num(d.in, st), E = Rupaka.EASE;
  if (!Array.isArray(ks) || !ks.length) throw new Error('keyframes: needs a list of [t, value] keys');
  if (x <= ks[0][0]) return ks[0][1];
  const i = ks.findIndex(k => x < k[0]);
  if (i < 0) return ks[ks.length - 1][1];
  const [t0, v0, e] = ks[i - 1], [t1, v1] = ks[i], kind = e || d.ease || 'linear';
  if (!Object.hasOwn(E, kind)) throw new Error(`keyframes: "${kind}" is not a curve`);
  return v0 + (v1 - v0) * E[kind]((x - t0) / (t1 - t0));
});
