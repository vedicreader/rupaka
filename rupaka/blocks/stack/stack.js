/* stack: child blocks one above the other, as one group (one `after` can hide them all). */
Rupaka.block('stack', (b, ctx) => Rupaka.el('div', {}, (b.blocks || []).map(ctx.build)));
