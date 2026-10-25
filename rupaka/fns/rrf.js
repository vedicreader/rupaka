/* rrf: reciprocal rank fusion of the ranked lists named in `in`, with k from the key `k` (or a number). Ranks start at 1. */
Rupaka.fn('rrf', (d, st) => {
  const k = +(typeof d.k === 'number' ? d.k : st[d.k]), acc = {};
  d.in.forEach((name, j) => (st[name] || []).forEach((id, i) => { (acc[id] ||= {id, value: 0, parts: d.in.map(() => 0)}).parts[j] += 1 / (k + i + 1); }));
  return Object.values(acc).map(x => ({...x, value: x.parts.reduce((a, b) => a + b, 0)})).sort((a, b) => b.value - a.value || a.id.localeCompare(b.id));
});
