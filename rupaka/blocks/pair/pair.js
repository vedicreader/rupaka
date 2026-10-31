/* pair: input cells, an arrow and the answer, as one row of a worked example: [18] → 47. The parts come in one by one. */
Rupaka.block('pair', (b, ctx) => {
  const {el, fmt} = Rupaka, cells = b.cells || [];
  const part = (cls, i, id) => el('span', {class: cls, style: `--i: ${i}`, 'data-rk-id': ctx.id(b, id)});
  const cs = cells.map((_, i) => part('cell', i, `cells.${i}`)), to = part('to', cells.length + 1, 'to');
  ctx.s.on(() => { cs.forEach((c, i) => { c.textContent = fmt(cells[i], ctx.s.st); }); to.textContent = fmt(b.to, ctx.s.st); });
  const heads = b.heads ? el('div', {class: 'heads'}, el('span', {text: b.heads[0]}), el('span', {text: b.heads[1]})) : null;
  return el('div', {}, heads, el('div', {class: 'line'}, b.n ? el('span', {class: 'n', text: b.n}) : null,
    el('span', {class: 'cells'}, cs), el('span', {class: 'arrow', style: `--i: ${cells.length}`, role: 'img', 'aria-label': 'gives'}), to));
});
