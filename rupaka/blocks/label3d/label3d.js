/* label3d: a chip pinned to a point of a scene, with a thin leader line that ends in a dot at the point. `at` is in the frame of
   the body `on` (or in the world). The text fills {path} from the state, as a readout does. The scene places the chips so that
   they never overlap: a chip that has no free place does not show. */
Rupaka.block('label3d', (b, ctx) => {
  const S = ctx.scene;
  if (!S) throw new Error('a label3d must be inside a scene');
  if (b.on && !S.ids.has(b.on)) throw new Error(`the label is on "${b.on}", which is not a body`);
  return S.part(b, {anchor: () => S.T ? S.point(b.on, b.at) : null}, S.chip(b, b.text));
});
