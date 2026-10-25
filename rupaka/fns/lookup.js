/* lookup: the row of a table for a key. A whole number picks by position; any other value picks the row whose `by` field (default id) matches. */
Rupaka.fn('lookup', (d, st, spec) => {
  const rows = (spec.tables || {})[d.table];
  if (!rows) throw new Error(`lookup: no table "${d.table}"`);
  const v = Rupaka.get(st, d.key), by = d.by || 'id';
  if (!d.by && Number.isInteger(v)) return rows[((v % rows.length) + rows.length) % rows.length];
  return rows.find(r => String(r[by]) === String(v)) ?? null;
});
