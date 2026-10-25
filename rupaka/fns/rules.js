/* rules: the first table row whose `when` lists hold the inputs wins. `{x}` in `out` takes the state value x.
   `alts` are what the other rows give: plausible wrong answers for a gate, in a stable order. */
Rupaka.fn('rules', (d, st, spec) => {
  const rows = (spec.tables || {})[d.table];
  if (!rows) throw new Error(`rules: no table "${d.table}"`);
  const sub = t => String(t).replace(/\{(\w+)\}/g, (_, k) => st[k] ?? '');
  const hit = rows.find(r => Object.entries(r.when || {}).every(([k, vs]) => (Array.isArray(vs) ? vs : [vs]).includes(st[k]))) || {out: '?', name: 'no rule'};
  const out = sub(hit.out), alts = [out];
  for (const r of rows) { const a = sub(r.out); if (!alts.includes(a)) alts.push(a); if (alts.length >= (d.alts || 4)) break; }
  const seed = [...(d.in || []).map(k => st[k]).join('|')].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 7);
  const rank = a => [...a].reduce((h, c) => (h * 33 + c.charCodeAt(0) + seed) | 0, 5) & 1023;
  alts.sort((x, y) => rank(x) - rank(y) || x.localeCompare(y));
  return {...hit, out, alts};
});
