/* Small list helpers: ids, pick, sort, and fmt (a template into a string). */
Rupaka.fn('ids', (d, st) => (Rupaka.get(st, d.from) || []).map(x => x && typeof x === 'object' ? x.id : x));
Rupaka.fn('pick', (d, st) => (Rupaka.get(st, d.from) || []).map(x => x == null ? x : x[d.field]));
Rupaka.fn('sort', (d, st) => {
  const v = x => d.by ? (x || {})[d.by] : x;
  return [...(Rupaka.get(st, d.from) || [])].sort((a, b) => (v(a) > v(b) ? 1 : v(a) < v(b) ? -1 : 0) * (d.desc ? -1 : 1));
});
Rupaka.fn('fmt', (d, st) => Rupaka.fmt(d.text, st));
