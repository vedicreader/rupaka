/* sample and dft: signals from a formula in time. `sample` takes the value at each tick of a rate; `dft` gives the strength of each whole frequency.
   Both read the formula with Rupaka.expr, so there is no eval. The Python twins are in nbs/00_spec.ipynb. */
(() => {
  const cache = {}, f_of = src => cache[src] ||= Rupaka.expr(src), num = (d, st, k) => +(typeof d[k] === 'number' ? d[k] : st[d[k]]);
  // sample: the points {x, y} of the formula at x = lo, lo + 1/rate, ... up to hi, with `over: {"t": [lo, hi]}`.
  Rupaka.fn('sample', (d, st) => {
    const f = f_of(d.expr), [name, [lo, hi]] = Object.entries(d.over)[0], rate = num(d, st, 'rate');
    if (!(rate > 0)) throw new Error('sample: rate must be above 0');
    const n = Math.floor((hi - lo) * rate + 1e-9) + 1;
    if (n > 4000) throw new Error('sample: more than 4000 points');
    return Array.from({length: n}, (_, k) => { const x = lo + k / rate; return {x, y: f({...st, [name]: x})}; });
  });
  // dft: the amplitude of each frequency k / (hi - lo) for k = 0 .. upto, from n ticks of the formula over [lo, hi) with `over: {"t": [lo, hi, n]}`.
  Rupaka.fn('dft', (d, st) => {
    const f = f_of(d.expr), [name, [lo, hi, n = 64]] = Object.entries(d.over)[0], T = hi - lo, up = Math.min(d.upto ?? n / 2, Math.floor(n / 2));
    const ys = Array.from({length: n}, (_, i) => f({...st, [name]: lo + T * i / n}));
    return Array.from({length: up + 1}, (_, k) => {
      let re = 0, im = 0;
      ys.forEach((y, i) => { const a = 2 * Math.PI * k * i / n; re += y * Math.cos(a); im -= y * Math.sin(a); });
      return {id: String(k / T), value: Math.hypot(re, im) / n * (k === 0 || 2 * k === n ? 1 : 2)};
    });
  });
})();
