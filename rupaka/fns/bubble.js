/* bubble: one step of a bubble sort of a list. Step 0 is the list as given, and step k is the list after the k-th compare.
   A demo reads each view (bars, counts, code line) from this one row, so the views always show the same run at the same step. */
Rupaka.fn('bubble', (d, st) => {
  const a = [...(Rupaka.get(st, d.from) || [])], n = a.length, last = n * (n - 1) / 2, x = Math.floor(Rupaka.num(d.at, st, 0));
  const k = Number.isFinite(x) ? Math.min(last, Math.max(0, x)) : 0;
  let comps = 0, swaps = 0, j = -1, left = null, right = null, swap = false;
  for (let i = 0; i < n - 1; i++) for (let q = 0; q < n - 1 - i && comps < k; q++) {
    comps++; j = q; left = a[q]; right = a[q + 1]; swap = left > right;
    if (swap) { a[q] = right; a[q + 1] = left; swaps++; }
  }
  const line = comps === 0 ? 1 : swap ? 4 : 3, did = comps === 0 ? 'start' : swap ? 'swap' : 'keep';
  return {step: k, last, list: a, bars: a.map((v, i) => ({id: `a[${i}]`, value: v, parts: j >= 0 && (i === j || i === j + 1) ? [v, 0] : [0, v]})),
          j, left, right, swap, did, cmp: comps === 0 ? '' : `${left} ${swap ? '>' : '≤'} ${right}`, comps, swaps, line,
          mark: [1, 2, 3, 4].map(l => l === line ? '▶' : '·')};
});
