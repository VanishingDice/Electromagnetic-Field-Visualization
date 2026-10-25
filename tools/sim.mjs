// 从 index.html 抽出 <script>，用 Node 驱动粒子系统，把「拖尾层」按 TRAIL_ALPHA
// 精确衰减后累积成密度图，供 preview_flow.py 渲染离线截图。
//
// 输入：../index.html
// 输出：density.bin —— 3 个 float32 平面（+1.0q / +0.7q / 平板），GW × GH
//
// 用法：node tools/sim.mjs
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

// 与 index.html 的 W/H 保持一致
const GW = 1600, GH = 900;
const FRAMES = 340;   // 拖尾衰减时间常数 ≈ 255/TRAIL_ALPHA 帧，340 帧已到稳态

const html = fs.readFileSync(path.join(HERE, '..', 'index.html'), 'utf8');
const blocks = html.split('<script>');
const code = blocks[blocks.length - 1].split('</script>')[0];

// 注入 p5 的 random / TAU（用可复现的 LCG 代替 p5 的 PRNG）
const prelude = `
const TAU = Math.PI * 2;
let __seed = 20261025;
function random(a, b) {
  __seed = (Math.imul(__seed, 1664525) + 1013904223) >>> 0;
  const t = __seed / 4294967296;
  if (a === undefined) return t;
  if (b === undefined) return t * a;
  return a + t * (b - a);
}
`;

const factory = new Function(
  prelude + code +
  '\n;initParticles(); return {particles, advect, W, H, N_PARTICLES, TRAIL_ALPHA};',
);

const {particles, advect, W, H, N_PARTICLES, TRAIL_ALPHA} = factory();

const SCALE = W / GW;
const planes = [new Float32Array(GW * GH), new Float32Array(GW * GH), new Float32Array(GW * GH)];
const decay = 1 - TRAIL_ALPHA / 255;

function channelOf(col) {
  if (col[0] === 251) return 0;   // COL_A 玫瑰
  if (col[0] === 167) return 1;   // COL_C 紫
  return 2;                        // COL_P 青（平板）
}

let current = 0;

function stamp(x, y, w) {
  const gx = (x + W / 2) / SCALE;
  const gy = (y + H / 2) / SCALE;
  if (gx < 0 || gy < 0 || gx >= GW || gy >= GH) return;
  planes[current][(gy | 0) * GW + (gx | 0)] += w;
}

let segs = 0;

for (let f = 0; f < FRAMES; f++) {
  for (let k = 0; k < 3; k++) {
    const pl = planes[k];
    for (let i = 0; i < pl.length; i++) pl[i] *= decay;
  }

  for (let i = 0; i < particles.length; i++) {
    const s = advect(particles[i]);
    if (s.skip) continue;

    current = channelOf(s.col);
    const w = (s.a / 255) * 0.06;
    const dx = s.x1 - s.x0, dy = s.y1 - s.y0;
    const steps = Math.max(1, Math.ceil(Math.hypot(dx, dy) / (SCALE * 0.5)));
    for (let t = 0; t <= steps; t++) {
      stamp(s.x0 + dx * (t / steps), s.y0 + dy * (t / steps), w / (steps + 1));
    }
    segs++;
  }
}

const buf = Buffer.alloc(GW * GH * 3 * 4);
for (let k = 0; k < 3; k++) {
  Buffer.from(planes[k].buffer, 0, GW * GH * 4).copy(buf, k * GW * GH * 4);
}
fs.writeFileSync(path.join(HERE, 'density.bin'), buf);

const stats = planes.map(p => {
  let mx = 0, sum = 0;
  for (let i = 0; i < p.length; i++) {
    if (p[i] > mx) mx = p[i];
    sum += p[i];
  }
  return {max: +mx.toFixed(4), mean: +(sum / p.length).toFixed(5)};
});

console.log(JSON.stringify({GW, GH, FRAMES, N_PARTICLES, segments: segs, planes: stats}, null, 2));
