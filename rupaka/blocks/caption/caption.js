/* caption: the explain text. Only **bold** and {path} are special; all text goes in with textContent, so no HTML runs. */
Rupaka.block('caption', (b, ctx) => {
  const {el, rich} = Rupaka, p = el('p');
  ctx.s.on(() => p.replaceChildren(...rich(b.text, ctx.s.st)));
  return el('div', {}, Rupaka.label(b), p);
});
