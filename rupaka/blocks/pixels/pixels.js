/* pixels: a grey image of a list of rows of numbers, one square per cell. Read-only.
   The ramp goes from --rk-bg at lo to --rk-fg at hi, so it follows the theme. The label fills {path} from the state;
   it is the aria-label of the canvas and shows above it. */
Rupaka.block('pixels', (b, ctx) => {
  const {el, fmt} = Rupaka, s = ctx.s;
  const cv = el('canvas', {role: 'img', width: 0, height: 0, style: `width: ${b.size ?? 256}px`});
  const lbl = b.label ? el('span', {class: 'rk-lbl', 'aria-hidden': 'true'}) : null;
  const probe = el('canvas', {width: 1, height: 1}).getContext('2d', {willReadFrequently: true});
  const rgb = v => {
    cv.style.color = `var(${v})`; probe.clearRect(0, 0, 1, 1); probe.fillStyle = getComputedStyle(cv).color; cv.style.color = '';
    probe.fillRect(0, 0, 1, 1); return probe.getImageData(0, 0, 1, 1).data;
  };
  s.on(() => {
    const text = fmt(b.label || b.bind, s.st), v = s.get(b.bind) || [], m = Array.isArray(v[0]) ? v : [v];
    cv.setAttribute('aria-label', text); if (lbl) lbl.textContent = text;
    const nr = m.length, nc = m[0]?.length || 0, vs = m.flat();
    if (cv.width !== nc || cv.height !== nr) { cv.width = nc; cv.height = nr; }
    if (!nr || !nc) return;
    const lo = b.lo ?? Math.min(...vs), hi = b.hi ?? Math.max(...vs), bg = rgb('--rk-bg'), fg = rgb('--rk-fg');
    const img = new ImageData(nc, nr), px = img.data;
    vs.forEach((x, k) => {
      const t = hi > lo ? Math.min(1, Math.max(0, (x - lo) / (hi - lo))) : 0;
      for (let c = 0; c < 3; c++) px[4 * k + c] = bg[c] + (fg[c] - bg[c]) * t;
      px[4 * k + 3] = 255;
    });
    cv.getContext('2d').putImageData(img, 0, 0);
  });
  return el('div', {}, lbl, cv);
});
