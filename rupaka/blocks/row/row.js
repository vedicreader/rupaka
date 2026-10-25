/* row: child blocks side by side; they wrap on a narrow page. */
Rupaka.block('row', (b, ctx) => Rupaka.el('div', {}, (b.blocks || []).map(ctx.build)));
