/* layers: a flat picture of layer blocks, back to front, on a 160 x 90 stage. A layer with depth shifts by -pan * depth (parallax).
   A control that starts a change sends rk-hold on the demo root; while it holds, each layer can show a faint ghost at the held values. */
Rupaka.block('layers', (b, ctx) => {
  const {el, sv} = Rupaka, s = ctx.s, W = 160, H = 90;
  const svg = sv('svg', {viewBox: `0 0 ${W} ${H}`, role: 'group', 'aria-label': b.label || 'A picture in layers', class: 'stage'});
  const stage = {svg, W, H, held: null, top: sv('g', {class: 'handles'}), pan: st => Rupaka.num(b.pan, st, 0)};
  ctx.root.addEventListener('rk-hold', e => { stage.held = e.detail.on ? structuredClone(s.st) : null; s.emit('hold'); });
  const c2 = Object.assign(Object.create(ctx), {stage});
  svg.append(...(b.blocks || []).map(k => Rupaka.build(k, c2)), stage.top);
  return el('div', {}, svg, b.note ? el('div', {class: 'rk-note', text: b.note}) : null);
});
