/* ease: a number moved from 0 to 1 along a curve (linear, in, out, inout, step). The curves are in Rupaka.EASE, and keyframes uses them too. */
(() => {
  const EASE = {linear: u => u, in: u => u * u, out: u => 1 - (1 - u) * (1 - u), inout: u => u < .5 ? 2 * u * u : 1 - (2 - 2 * u) * (2 - 2 * u) / 2, step: u => u < 1 ? 0 : 1};
  Rupaka.EASE = EASE;
  Rupaka.num = (v, st, d) => v == null ? d : typeof v === 'number' ? v : +Rupaka.get(st, v);
  Rupaka.fn('ease', (d, st) => {
    const [a, b] = d.over || [0, 1], kind = d.kind || 'linear';
    if (!Object.hasOwn(EASE, kind)) throw new Error(`ease: "${kind}" is not a curve`);
    return EASE[kind](Math.min(1, Math.max(0, (Rupaka.num(d.in, st) - a) / (b - a))));
  });
})();
