/* layer: one shape on the stage of a layers block. Its numbers are values or state keys. With drag, a handle writes the keys of x and y.
   A/D (←/→) and W/S (↑/↓) move the handle, ⇧ moves ten steps. While a change holds, a faint ghost stays where the layer was. */
(() => {
  const {sv} = Rupaka, HOR = 58;
  let seq = 0;
  const ART = {
    sky: () => {
      const id = `rk-warm-${++seq}`;
      return sv('g', {}, sv('defs', {}, sv('linearGradient', {id, x1: 0, y1: 0, x2: 0, y2: 1},
        sv('stop', {offset: 0, class: 'w0'}), sv('stop', {offset: 1, class: 'w1'}))),
        sv('rect', {class: 'sky', x: -60, y: -5, width: 280, height: 100}), sv('rect', {class: 'warm', x: -60, y: -5, width: 280, height: 100, fill: `url(#${id})`}));
    },
    hill: b => {
      let d = 'M -10 100';
      for (let x = -10; x <= 210; x += 5) d += ` L ${x} ${(HOR - 10 - 8 * Math.sin(x * .045 + (b.seed || 0)) - 5 * Math.sin(x * .11 + (b.seed || 0) * 2.3)).toFixed(2)}`;
      return sv('path', {class: 'hill', d: d + ' L 210 100 Z', style: b.tone != null ? `--tone: ${b.tone}` : null});
    },
    water: b => sv('g', {style: b.tone != null ? `--tone: ${b.tone}` : null}, sv('rect', {class: 'water', x: -60, y: HOR, width: 280, height: 40}),
      ...[[-20, 66, 14], [18, 72, 20], [60, 64, 12], [92, 76, 22], [130, 68, 16], [170, 74, 18]].map(([x, y, w]) => sv('line', {class: 'shine', x1: x, y1: y, x2: x + w, y2: y}))),
    sun: () => sv('g', {}, sv('circle', {class: 'halo', r: 10}), sv('circle', {class: 'disc', r: 5.5})),
    cloud: () => sv('g', {}, sv('ellipse', {cx: 0, cy: 0, rx: 9, ry: 3}), sv('ellipse', {cx: -4, cy: -2, rx: 5, ry: 3}), sv('ellipse', {cx: 4, cy: -1.5, rx: 5.5, ry: 3.2})),
    boat: () => sv('g', {}, sv('path', {class: 'hull', d: 'M -10 0 L 10 0 L 6.5 4.5 L -6.5 4.5 Z'}), sv('line', {class: 'mast', x1: 0, y1: 0, x2: 0, y2: -13}),
      sv('path', {class: 'sail', d: 'M 1 -12 L 9 -2 L 1 -2 Z'}), sv('path', {class: 'sail small', d: 'M -1 -10 L -6 -2 L -1 -2 Z'})),
  };

  Rupaka.block('layer', (b, ctx) => {
    const {sv, show, num} = Rupaka, s = ctx.s, P = ctx.stage;
    if (!P) throw new Error('a layer must be inside layers');
    if (!ART[b.art]) throw new Error(`unknown art "${b.art}"`);
    const drag = b.drag || '', step = b.step ?? .5, ghosted = b.ghost ?? !!drag;
    const body = ART[b.art](b), posed = sv('g', {class: 'pose'}, body);
    const gpose = ghosted ? sv('g', {class: 'ghost', 'aria-hidden': 'true'}, body.cloneNode(true)) : null;
    if (gpose) gpose.style.display = 'none';
    const node = sv('g', {class: `art-${b.art}`}, gpose, posed);
    const pose = st => {
      const yv = num(b.y, st, 0);
      return {x: num(b.x, st, 0) - P.pan(st) * (b.depth || 0), y: b.up ? P.H - yv : yv, k: num(b.scale, st, 1), r: num(b.rotate, st, 0), o: num(b.opacity, st, 1), tint: num(b.tint, st, 0)};
    };
    const tf = p => `translate(${p.x} ${p.y}) rotate(${p.r}) scale(${p.k})`;
    const hold = on => ctx.root.dispatchEvent(new CustomEvent('rk-hold', {detail: {on}}));
    let hand = null, txt, ring, timer;
    if (drag) {
      ring = sv('circle', {class: 'ring', r: 7});
      txt = sv('text', {class: 'tag', 'text-anchor': 'middle'});
      hand = sv('g', {class: 'handle', tabindex: 0, role: 'slider', 'aria-label': b.label || b.art}, ring, sv('circle', {class: 'dot', r: 1.6}), txt);
      P.top.append(hand);
      const rng = {x: b.xr || [0, P.W], y: b.yr || [0, P.H]}, axes = [...drag];
      const clamp = (v, [lo, hi]) => +Math.min(hi, Math.max(lo, Math.round(v / step) * step)).toFixed(6);
      const at = e => { const pt = P.svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; return pt.matrixTransform(P.svg.getScreenCTM().inverse()); };
      const put = (x, y) => { if (x != null && x !== s.get(b.x)) ctx.put(b, b.x, x); if (y != null && y !== s.get(b.y)) ctx.put(b, b.y, y); };
      let off = null;
      hand.addEventListener('pointerdown', e => {
        if (!ctx.live(b.lock)) return;
        e.stopPropagation(); hand.setPointerCapture(e.pointerId); hand.classList.add('held'); hold(true);
        const p = at(e), h = pose(s.st); off = {x: p.x - h.x, y: p.y - h.y};
      });
      hand.addEventListener('pointermove', e => {
        if (!hand.hasPointerCapture(e.pointerId)) return;
        const p = at(e), sh = pose(s.st).x - num(b.x, s.st, 0), yv = b.up ? P.H - (p.y - off.y) : p.y - off.y;
        put(axes.includes('x') ? clamp(p.x - off.x - sh, rng.x) : null, axes.includes('y') ? clamp(yv, rng.y) : null);
      });
      const drop = () => { if (!off) return; off = null; hand.classList.remove('held'); hold(false); };
      hand.addEventListener('pointerup', drop); hand.addEventListener('pointercancel', drop);
      hand.addEventListener('keydown', e => {
        const k = e.key.toLowerCase(), d = step * (e.shiftKey ? 10 : 1), one = axes.length === 1;
        const dx = ['arrowright', 'd'].includes(k) ? d : ['arrowleft', 'a'].includes(k) ? -d : 0;
        const up = ['arrowup', 'w'].includes(k) ? d : ['arrowdown', 's'].includes(k) ? -d : 0;
        let mx = axes.includes('x') ? dx || (one ? up : 0) : 0, my = axes.includes('y') ? (b.up ? up : -up) || (one ? dx : 0) : 0;
        if (!mx && !my) return;
        e.preventDefault();
        if (!timer) hold(true);
        clearTimeout(timer); timer = setTimeout(() => { timer = 0; hold(false); }, 800);
        put(mx ? clamp(+s.get(b.x) + mx, rng.x) : null, my ? clamp(+s.get(b.y) + my, rng.y) : null);
      });
    }
    s.on(() => {
      const p = pose(s.st);
      posed.setAttribute('transform', tf(p)); posed.setAttribute('opacity', p.o); posed.style.setProperty('--tint', p.tint);
      const h = gpose && P.held ? pose(P.held) : null;
      const moved = h && (Math.abs(h.x - p.x) + Math.abs(h.y - p.y) + Math.abs(h.k - p.k) + Math.abs(h.r - p.r) + Math.abs(h.tint - p.tint)) > .05;
      if (gpose) gpose.style.display = moved ? '' : 'none';
      if (moved) { gpose.setAttribute('transform', tf(h)); gpose.style.setProperty('--tint', h.tint); }
      if (hand) {
        hand.setAttribute('transform', `translate(${p.x} ${p.y})`);
        const v = +s.get(drag[0] === 'y' ? b.y : b.x), t = show(v, 1);
        txt.setAttribute('y', -9); txt.textContent = b.label ? `${b.label} ${t}` : t;
        hand.setAttribute('aria-valuenow', v); hand.setAttribute('aria-valuetext', `${b.label || b.art} ${t}`);
        hand.style.display = ctx.live(b.lock) ? '' : 'none';
      }
    });
    return node;
  });
})();
