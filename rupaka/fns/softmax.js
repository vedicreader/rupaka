/* softmax: shares from scores, exp(x / t) / sum, with temperature t (a key or a number). A row of a grid works too. */
Rupaka.fn('softmax', (d, st) => {
  let xs = Rupaka.get(st, d.in) || [];
  if (Array.isArray(xs[0])) xs = xs[d.row || 0];
  const t = Math.max(1e-6, +(typeof d.t === 'number' ? d.t : d.t == null ? 1 : st[d.t])), mx = Math.max(...xs);
  const es = xs.map(x => Math.exp((x - mx) / t)), z = es.reduce((a, b) => a + b, 0);
  const labels = Array.isArray(d.labels) ? d.labels : d.labels ? Rupaka.get(st, d.labels) : null;
  const out = es.map((e, i) => ({id: String(labels ? labels[i] : i), value: e / z}));
  return d.sort ? out.sort((a, b) => b.value - a.value || a.id.localeCompare(b.id)) : out;
});
