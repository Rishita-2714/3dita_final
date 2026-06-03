const createTempleObj = ({ topScale = 0.45, height = 1.25, damage = 0 }) => `
v -1 0 -1
v 1 0 -1
v 1 0 1
v -1 0 1
v -0.65 ${height * (0.33 - damage)} -0.65
v 0.65 ${height * (0.33 - damage * 0.6)} -0.65
v 0.65 ${height * (0.33 - damage)} 0.65
v -0.65 ${height * (0.33 - damage * 0.4)} 0.65
v -${topScale} ${height} -${topScale}
v ${topScale} ${height} -${topScale}
v ${topScale} ${height} ${topScale}
v -${topScale} ${height} ${topScale}
f 1 2 6 5
f 2 3 7 6
f 3 4 8 7
f 4 1 5 8
f 5 6 10 9
f 6 7 11 10
f 7 8 12 11
f 8 5 9 12
f 9 10 11 12
`;

const createMockUrl = (content) =>
  URL.createObjectURL(new Blob([content], { type: "text/plain" }));

export const createMockReconstructionPayload = () => ({
  before_url: createMockUrl(
    createTempleObj({ topScale: 0.25, height: 1.05, damage: 0.18 }),
  ),
  after_url: createMockUrl(
    createTempleObj({ topScale: 0.42, height: 1.25, damage: 0 }),
  ),
  metadata: {
    component_class: "Mandapa Tower Segment",
    before_points: 148320,
    after_points: 215640,
    confidence: 0.94,
  },
});
