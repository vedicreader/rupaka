/* plot: a line (or dots) through a derived series of {x, y}, on its axis. With `ghost`, the line from before the latest change stays faint.
   With `guess` (a gate id) and `guesses` (one series key for each option of that gate, in the order of its options), the curve that the learner
   predicted is drawn dashed beside the true one from the moment of Lock in. It is a copy made then, so it stays while the inputs move. */
Rupaka.block('plot', (b, ctx) => {
  const {sv} = Rupaka, P = ctx.plane;
  if (!P) throw new Error('a plot must be inside an axis');
  const ghost = sv('path', {class: 'gh', 'clip-path': P.clip}), path = sv('path', {class: 'ln', 'clip-path': P.clip}), dots = sv('g', {class: 'dots', 'clip-path': P.clip});
  const gs = sv('path', {class: 'gs', 'clip-path': P.clip}), guess = b.guess && b.guesses && !b.dots;
  const g = sv('g', {role: 'img', 'aria-label': b.label || b.series}, ...b.ghost && !b.dots ? [ghost] : [], ...guess ? [gs] : [], path, dots);
  if (b.tone) g.classList.add(`t-${b.tone}`);
  let cur = null, old = '', at = -1e9, kept = null;   // the line now, the line before this burst of changes, the time of the last change, the guess drawn
  const line = xs => { let d = '', pen = false; for (const p of xs) { const ok = Number.isFinite(p.y) && Math.abs(P.Y(p.y)) < 1e5; if (ok) { d += `${pen ? 'L' : 'M'}${P.X(p.x).toFixed(2)} ${P.Y(p.y).toFixed(2)}`; pen = true; } else pen = false; } return d; };
  const pts = k => (ctx.s.get(k) || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
  // The curve of the option that the learner locked in, copied once; a gate opened again takes it away.
  const guessed = () => {
    if (!guess) return;
    if (ctx.s.get(`gate.${b.guess}`) !== 'done') { kept = null; gs.removeAttribute('d'); return; }
    if (kept) return;
    const gt = ctx.gates?.find(x => x.id === b.guess), log = [...(ctx.s.get('log') || [])].reverse().find(e => e.gate === b.guess);
    const k = gt && log && b.guesses[gt.options().indexOf(log.picked)];
    if (!k) return;
    kept = pts(k); gs.setAttribute('d', line(kept));
    gs.setAttribute('aria-label', 'what you predicted');
  };
  ctx.s.on(() => {
    guessed();
    const xs = (ctx.s.get(b.series) || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
    let d = '', pen = false;
    for (const p of xs) {
      const ok = Number.isFinite(p.y) && Math.abs(P.Y(p.y)) < 1e5;
      if (ok) { d += `${pen ? 'L' : 'M'}${P.X(p.x).toFixed(2)} ${P.Y(p.y).toFixed(2)}`; pen = true; } else pen = false;
    }
    if (b.ghost && cur !== null && d !== cur) {
      const now = performance.now();
      if (now - at > 500) { old = cur; ghost.setAttribute('d', old); }
      at = now;
    }
    cur = d;
    path.setAttribute('d', b.dots ? '' : d);
    dots.replaceChildren(...(b.dots ? xs.filter(p => Number.isFinite(p.y)).map(p => sv('circle', {cx: P.X(p.x), cy: P.Y(p.y), r: 3.5})) : []));
  });
  return g;
});
